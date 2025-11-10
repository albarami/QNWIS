"""
Audit trail generation for Layer 4 verification.

Assembles tamper-evident audit manifests capturing complete provenance,
verification results, and reproducibility metadata for each orchestration run.
"""

from __future__ import annotations

import json
import logging
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..data.deterministic.models import QueryResult
from .audit_utils import (
    canonical_json,
    compute_params_hash,
    hmac_sha256,
    redact_text,
    reproducibility_snippet,
    sha256_digest,
    slugify_filename,
)
from .citation_enforcer import CitationReport
from .schemas import ResultVerificationReport, VerificationSummary

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AuditManifest:
    """
    Tamper-evident audit manifest for a single orchestration run.

    Captures complete provenance chain including:
    - Request and execution metadata
    - Data sources and freshness
    - Verification results (Layers 2-4)
    - Citation enforcement
    - Reproducibility instructions

    Attributes:
        audit_id: Unique identifier for this audit run (UUID)
        created_at: Timestamp when manifest was created (ISO 8601)
        request_id: Original request tracking identifier
        registry_version: Data registry version/hash at execution time
        code_version: Git commit hash of executing code
        data_sources: Union of all dataset IDs from QueryResults
        query_ids: All query IDs used in this run
        freshness: Per-source freshness timestamps (ISO 8601)
        citations: Citation enforcement summary (counts, issues)
        verification: Verification summary (pass/fail, issue codes)
        orchestration: Routing, agents, timings
        reproducibility: Python snippet + params hash
        pack_paths: File paths written in audit pack
        digest_sha256: SHA-256 digest of canonical manifest
        hmac_sha256: Optional HMAC signature if key provided
    """

    audit_id: str
    created_at: str
    request_id: str
    registry_version: str
    code_version: str
    data_sources: list[str]
    query_ids: list[str]
    freshness: dict[str, str]
    citations: dict[str, Any]
    verification: dict[str, Any]
    orchestration: dict[str, Any]
    reproducibility: dict[str, Any]
    pack_root: str = ""
    pack_paths: dict[str, str] = field(default_factory=dict)
    digest_sha256: str = ""
    hmac_sha256: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "audit_id": self.audit_id,
            "created_at": self.created_at,
            "request_id": self.request_id,
            "registry_version": self.registry_version,
            "code_version": self.code_version,
            "data_sources": self.data_sources,
            "query_ids": self.query_ids,
            "freshness": self.freshness,
            "citations": self.citations,
            "verification": self.verification,
            "orchestration": self.orchestration,
            "reproducibility": self.reproducibility,
            "pack_root": self.pack_root,
            "pack_paths": self.pack_paths,
            "digest_sha256": self.digest_sha256,
            "hmac_sha256": self.hmac_sha256,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AuditManifest:
        """Create from dictionary."""
        return cls(**data)


class AuditTrail:
    """
    Audit trail builder and pack writer.

    Assembles AuditManifest from orchestration components and writes
    evidence packs to disk with optional SQLite indexing.
    """

    def __init__(
        self,
        pack_dir: str,
        sqlite_path: str | None = None,
        hmac_key: bytes | None = None,
    ):
        """
        Initialize audit trail with storage configuration.

        Args:
            pack_dir: Directory to write audit packs (will be created if needed)
            sqlite_path: Optional SQLite database path for indexing
            hmac_key: Optional secret key for HMAC signatures
        """
        self.pack_dir = Path(pack_dir)
        self.sqlite_path = Path(sqlite_path) if sqlite_path else None
        self.hmac_key = hmac_key

        # Create pack directory if it doesn't exist
        self.pack_dir.mkdir(parents=True, exist_ok=True)
        logger.info("Audit trail initialized: pack_dir=%s", self.pack_dir)

    def generate_trail(
        self,
        response_md: str,
        qresults: list[QueryResult],
        verification: VerificationSummary,
        citations: CitationReport,
        orchestration_meta: dict[str, Any],
        code_version: str,
        registry_version: str,
        request_id: str,
    ) -> AuditManifest:
        """
        Assemble audit manifest from orchestration components.

        Does not perform I/O. Use write_pack() to persist to disk.

        Args:
            response_md: Final narrative markdown response
            qresults: List of QueryResult objects used
            verification: Verification summary from Layers 2-4
            citations: Citation enforcement report
            orchestration_meta: Orchestration metadata (routing, agents, timings)
            code_version: Git commit hash
            registry_version: Data registry version
            request_id: Request tracking ID

        Returns:
            AuditManifest ready for writing
        """
        audit_id = str(uuid.uuid4())
        created_at = datetime.now(UTC).isoformat()

        # Extract data sources and freshness
        data_sources_set: set[str] = set()
        query_ids = [qr.query_id for qr in qresults]

        freshness: dict[str, str] = {}
        for qr in qresults:
            source_key = (
                qr.provenance.dataset_id
                or qr.provenance.locator
                or qr.query_id
            )
            data_sources_set.add(source_key)
            # Prefer updated_at if available, fallback to asof_date
            timestamp = qr.freshness.updated_at or qr.freshness.asof_date or "unknown"
            freshness[source_key] = timestamp

        data_sources = sorted(data_sources_set)

        # Make freshness deterministic for hashing purposes
        freshness = {key: freshness[key] for key in sorted(freshness)}

        # Citations summary (redact uncited examples for PII safety)
        citations_dict = {
            "ok": citations.ok,
            "total_numbers": citations.total_numbers,
            "cited_numbers": citations.cited_numbers,
            "sources_used": citations.sources_used,
            "uncited_count": len(citations.uncited),
            "malformed_count": len(citations.malformed),
            "missing_qid_count": len(citations.missing_qid),
            # Include redacted examples (first 3)
            "uncited_examples": [
                {
                    "value_text": redact_text(issue.value_text),
                    "message": redact_text(issue.message),
                }
                for issue in citations.uncited[:3]
            ],
        }

        # Verification summary
        verification_dict = {
            "ok": verification.ok,
            "issues_count": len(verification.issues),
            "redactions_applied": verification.applied_redactions,
            "stats": verification.stats,
            "issue_codes": [
                f"{issue.layer}/{issue.code}" for issue in verification.issues
            ],
        }

        # Result verification summary (if available)
        if verification.result_verification_report:
            result_report = verification.result_verification_report
            verification_dict["result_verification"] = {
                "ok": result_report.ok,
                "claims_total": result_report.claims_total,
                "claims_matched": result_report.claims_matched,
                "math_checks": result_report.math_checks,
            }

        # Orchestration metadata
        orchestration_dict = {
            "routing": orchestration_meta.get("routing", {}),
            "agents": orchestration_meta.get("agents", []),
            "timings": orchestration_meta.get("timings", {}),
            "cache_stats": orchestration_meta.get("cache_stats", {}),
        }

        # Reproducibility snippet
        snippet = reproducibility_snippet(query_ids, registry_version)
        params_hash = compute_params_hash(orchestration_meta.get("params", {}))
        reproducibility_dict = {
            "snippet": snippet,
            "params_hash": params_hash,
            "registry_version": registry_version,
            "code_version": code_version,
        }

        # Create manifest (without digest/paths yet)
        manifest = AuditManifest(
            audit_id=audit_id,
            created_at=created_at,
            request_id=request_id,
            registry_version=registry_version,
            code_version=code_version,
            data_sources=sorted(data_sources),
            query_ids=query_ids,
            freshness=freshness,
            citations=citations_dict,
            verification=verification_dict,
            orchestration=orchestration_dict,
            reproducibility=reproducibility_dict,
        )

        logger.info(
            "Generated audit manifest: audit_id=%s, sources=%d, queries=%d",
            audit_id,
            len(data_sources),
            len(query_ids),
        )

        return manifest

    def write_pack(  # noqa: C901
        self,
        manifest: AuditManifest,
        response_md: str,
        qresults: list[QueryResult],
        citations: CitationReport,
        result_report: ResultVerificationReport | None,
        replay_stub: dict[str, Any] | None = None,
    ) -> AuditManifest:
        """
        Write audit pack to disk and compute digests.

        Creates directory structure:
        ```
        audit_packs/<audit_id>/
          manifest.json       # Manifest with digest/HMAC
          narrative.md        # Final response markdown
          evidence/           # QueryResult JSONs
            <query_id>.json
          verification/       # Verification reports
            citations.json
            result_verification.json
          reproducibility.py  # Executable reproduction snippet
        ```

        Args:
            manifest: Audit manifest to write
            response_md: Final narrative markdown
            qresults: QueryResult objects to preserve
            citations: Citation report for detailed storage
            result_report: Result verification report (if available)
            replay_stub: Optional replay metadata for offline dry-runs

        Returns:
            Updated manifest with pack_paths and digest_sha256/hmac_sha256 filled
        """
        pack_root = self.pack_dir / manifest.audit_id
        pack_root.mkdir(parents=True, exist_ok=True)

        evidence_dir = pack_root / "evidence"
        evidence_dir.mkdir(exist_ok=True)

        verification_dir = pack_root / "verification"
        verification_dir.mkdir(exist_ok=True)

        pack_paths: dict[str, str] = {}

        def _record_path(label: str, file_path: Path) -> None:
            """Store pack-relative path for manifest bookkeeping."""
            try:
                pack_paths[label] = str(file_path.relative_to(pack_root))
            except ValueError:
                pack_paths[label] = str(file_path)

        # Write narrative
        narrative_path = pack_root / "narrative.md"
        narrative_path.write_text(redact_text(response_md), encoding="utf-8")
        _record_path("narrative", narrative_path)

        # Write evidence (QueryResults)
        qid_counts: defaultdict[str, int] = defaultdict(int)
        for qr in qresults:
            qid_counts[qr.query_id] += 1
            suffix = "" if qid_counts[qr.query_id] == 1 else f"_{qid_counts[qr.query_id]-1:02d}"
            evidence_filename = f"{qr.query_id}{suffix}.json"
            evidence_path = evidence_dir / evidence_filename
            evidence_path.write_text(
                json.dumps(qr.model_dump(), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            _record_path(f"evidence/{evidence_filename}", evidence_path)

        # Write deduplicated source descriptors
        sources_dir = pack_root / "sources"
        sources_dir.mkdir(exist_ok=True)
        source_index: dict[str, dict[str, Any]] = {}
        for qr in qresults:
            provenance = qr.provenance
            key = f"{provenance.dataset_id}:{provenance.locator}"
            entry = source_index.setdefault(
                key,
                {
                    "dataset_id": provenance.dataset_id,
                    "source": provenance.source,
                    "locator": provenance.locator,
                    "fields": provenance.fields,
                    "query_ids": [],
                },
            )
            entry["query_ids"].append(qr.query_id)

        slug_counts: defaultdict[str, int] = defaultdict(int)
        for entry in source_index.values():
            slug = slugify_filename(entry["dataset_id"], default="source")
            slug_counts[slug] += 1
            if slug_counts[slug] > 1:
                slug = f"{slug}-{slug_counts[slug]-1}"
            source_path = sources_dir / f"{slug}.json"
            source_payload = {
                **entry,
                "query_ids": sorted(set(entry["query_ids"])),
            }
            source_path.write_text(
                json.dumps(source_payload, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            _record_path(f"sources/{slug}.json", source_path)

        # Write citations report
        citations_path = verification_dir / "citations.json"
        citations_path.write_text(
            json.dumps(citations.model_dump(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        _record_path("citations", citations_path)

        # Write result verification report if available
        if result_report:
            result_path = verification_dir / "result_verification.json"
            result_path.write_text(
                json.dumps(result_report.model_dump(), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            _record_path("result_verification", result_path)

        # Write reproducibility snippet
        snippet_path = pack_root / "reproducibility.py"
        snippet_path.write_text(
            manifest.reproducibility["snippet"],
            encoding="utf-8",
        )
        _record_path("reproducibility", snippet_path)

        # Write replay stub if provided
        if replay_stub:
            replay_path = pack_root / "replay.json"
            replay_path.write_text(
                json.dumps(replay_stub, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            _record_path("replay", replay_path)

        # Update manifest with pack paths
        manifest_dict = manifest.to_dict()
        manifest_dict["pack_root"] = str(pack_root)
        manifest_dict["pack_paths"] = pack_paths

        # Compute digest over canonical form (excluding digest/hmac fields)
        digest_manifest = {
            k: v
            for k, v in manifest_dict.items()
            if k not in ("digest_sha256", "hmac_sha256")
        }
        canonical = canonical_json(digest_manifest)
        digest = sha256_digest(canonical)
        manifest_dict["digest_sha256"] = digest

        # Compute HMAC if key provided
        if self.hmac_key:
            signature = hmac_sha256(canonical, self.hmac_key)
            manifest_dict["hmac_sha256"] = signature

        # Write manifest
        manifest_path = pack_root / "manifest.json"
        manifest_path.write_text(
            json.dumps(manifest_dict, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        _record_path("manifest", manifest_path)

        # Create final manifest
        final_manifest = AuditManifest.from_dict(manifest_dict)

        logger.info(
            "Wrote audit pack: path=%s, size=%d files, digest=%s",
            pack_root,
            len(pack_paths),
            digest[:16],
        )

        # Index in SQLite if configured
        if self.sqlite_path:
            try:
                from .audit_store import SQLiteAuditTrailStore

                store = SQLiteAuditTrailStore(str(self.sqlite_path))
                store.upsert(final_manifest)
                logger.debug("Indexed audit pack in SQLite: %s", manifest.audit_id)
            except Exception as exc:
                logger.warning("Failed to index in SQLite: %s", exc)

        return final_manifest

    def verify_pack(self, audit_id: str) -> tuple[bool, list[str]]:
        """
        Verify integrity of an audit pack by recomputing digest.

        Args:
            audit_id: Audit ID to verify

        Returns:
            Tuple of (is_valid, reasons)
            - is_valid: True if all checks pass
            - reasons: List of verification failures (empty if valid)
        """
        pack_path = self.pack_dir / audit_id
        manifest_path = pack_path / "manifest.json"

        if not manifest_path.exists():
            return False, [f"Manifest not found: {manifest_path}"]

        try:
            manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
            stored_digest = manifest_data.get("digest_sha256")
            stored_hmac = manifest_data.get("hmac_sha256")

            # Recompute digest
            digest_manifest = {
                k: v
                for k, v in manifest_data.items()
                if k not in ("digest_sha256", "hmac_sha256")
            }
            canonical = canonical_json(digest_manifest)
            computed_digest = sha256_digest(canonical)

            reasons = []

            if computed_digest != stored_digest:
                reasons.append(
                    f"Digest mismatch: expected {stored_digest}, got {computed_digest}"
                )

            # Verify HMAC if present
            if stored_hmac and self.hmac_key:
                computed_hmac = hmac_sha256(canonical, self.hmac_key)
                if computed_hmac != stored_hmac:
                    reasons.append(
                        "HMAC mismatch: signature verification failed"
                    )
            elif stored_hmac and not self.hmac_key:
                reasons.append("HMAC present but no key provided for verification")

            if reasons:
                return False, reasons
            return True, []

        except Exception as exc:
            return False, [f"Verification failed: {type(exc).__name__}: {exc}"]
