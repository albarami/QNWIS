"""
Unit tests for audit trail generation and pack writing.

Tests AuditManifest creation, pack file structure, digest computation,
and integrity verification.
"""

import json
from datetime import datetime

import pytest

from src.qnwis.data.deterministic.models import (
    Freshness,
    Provenance,
    QueryResult,
    Row,
)
from src.qnwis.verification.audit_trail import AuditManifest, AuditTrail
from src.qnwis.verification.schemas import (
    CitationReport,
    VerificationSummary,
)


@pytest.fixture
def sample_query_results():
    """Create sample QueryResult objects for testing."""
    return [
        QueryResult(
            query_id="qid_abc123",
            rows=[Row(data={"metric": "retention", "value": 0.85})],
            unit="percent",
            provenance=Provenance(
                source="csv",
                dataset_id="lmis_workforce",
                locator="/data/workforce.csv",
                fields=["metric", "value"],
            ),
            freshness=Freshness(
                asof_date="2024-01-15",
                updated_at="2024-01-15T10:00:00Z",
            ),
        ),
        QueryResult(
            query_id="qid_def456",
            rows=[Row(data={"sector": "oil_gas", "count": 1500})],
            unit="count",
            provenance=Provenance(
                source="csv",
                dataset_id="lmis_sectors",
                locator="/data/sectors.csv",
                fields=["sector", "count"],
            ),
            freshness=Freshness(
                asof_date="2024-01-10",
                updated_at="2024-01-10T08:30:00Z",
            ),
        ),
    ]


@pytest.fixture
def sample_verification():
    """Create sample VerificationSummary for testing."""
    return VerificationSummary(
        ok=True,
        issues=[],
        applied_redactions=2,
        stats={"L2/info": 0, "L3/warning": 1, "L4/error": 0},
    )


@pytest.fixture
def sample_citations():
    """Create sample CitationReport for testing."""
    return CitationReport(
        ok=True,
        total_numbers=10,
        cited_numbers=10,
        sources_used={"Per LMIS:": 8, "According to GCC-STAT:": 2},
    )


@pytest.fixture
def sample_replay_stub():
    """Replay stub fixture for audit pack writing."""
    return {
        "task": {"intent": "pattern.anomalies"},
        "routing": {},
    }


class TestAuditManifest:
    """Tests for AuditManifest dataclass."""

    def test_audit_manifest_creation(self):
        """AuditManifest should be created with required fields."""
        manifest = AuditManifest(
            audit_id="test-123",
            created_at=datetime.utcnow().isoformat(),
            request_id="req-456",
            registry_version="v1.0",
            code_version="abc123",
            data_sources=["lmis_workforce"],
            query_ids=["qid_abc123"],
            freshness={"lmis_workforce": "2024-01-15T10:00:00Z"},
            citations={"ok": True, "total_numbers": 10},
            verification={"ok": True, "issues_count": 0},
            orchestration={"routing": {}, "agents": []},
            reproducibility={"snippet": "# test", "params_hash": "hash123"},
        )

        assert manifest.audit_id == "test-123"
        assert manifest.request_id == "req-456"
        assert len(manifest.data_sources) == 1
        assert len(manifest.query_ids) == 1

    def test_audit_manifest_to_dict(self):
        """to_dict should serialize all fields."""
        manifest = AuditManifest(
            audit_id="test-123",
            created_at="2024-01-15T10:00:00Z",
            request_id="req-456",
            registry_version="v1.0",
            code_version="abc123",
            data_sources=["lmis_workforce"],
            query_ids=["qid_abc123"],
            freshness={"lmis_workforce": "2024-01-15T10:00:00Z"},
            citations={"ok": True},
            verification={"ok": True},
            orchestration={},
            reproducibility={},
        )

        result = manifest.to_dict()

        assert isinstance(result, dict)
        assert result["audit_id"] == "test-123"
        assert result["request_id"] == "req-456"
        assert "data_sources" in result
        assert "query_ids" in result

    def test_audit_manifest_from_dict(self):
        """from_dict should reconstruct manifest."""
        data = {
            "audit_id": "test-123",
            "created_at": "2024-01-15T10:00:00Z",
            "request_id": "req-456",
            "registry_version": "v1.0",
            "code_version": "abc123",
            "data_sources": ["lmis_workforce"],
            "query_ids": ["qid_abc123"],
            "freshness": {"lmis_workforce": "2024-01-15T10:00:00Z"},
            "citations": {"ok": True},
            "verification": {"ok": True},
            "orchestration": {},
            "reproducibility": {},
            "pack_paths": {},
            "digest_sha256": "",
            "hmac_sha256": None,
        }

        manifest = AuditManifest.from_dict(data)

        assert manifest.audit_id == "test-123"
        assert manifest.request_id == "req-456"

    def test_audit_manifest_immutable(self):
        """AuditManifest should be frozen (immutable)."""
        manifest = AuditManifest(
            audit_id="test-123",
            created_at="2024-01-15T10:00:00Z",
            request_id="req-456",
            registry_version="v1.0",
            code_version="abc123",
            data_sources=[],
            query_ids=[],
            freshness={},
            citations={},
            verification={},
            orchestration={},
            reproducibility={},
        )

        with pytest.raises((AttributeError, TypeError)):
            manifest.audit_id = "modified"


class TestAuditTrail:
    """Tests for AuditTrail pack generation and writing."""

    def test_audit_trail_initialization(self, tmp_path):
        """AuditTrail should create pack directory."""
        pack_dir = tmp_path / "audit_packs"
        AuditTrail(pack_dir=str(pack_dir))

        assert pack_dir.exists()
        assert pack_dir.is_dir()

    def test_generate_trail(
        self, tmp_path, sample_query_results, sample_verification, sample_citations
    ):
        """generate_trail should create complete manifest."""
        trail = AuditTrail(pack_dir=str(tmp_path))

        manifest = trail.generate_trail(
            response_md="# Test Response",
            qresults=sample_query_results,
            verification=sample_verification,
            citations=sample_citations,
            orchestration_meta={
                "routing": {"mode": "single"},
                "agents": ["test_agent"],
                "timings": {"total_ms": 100},
            },
            code_version="abc123",
            registry_version="v1.0",
            request_id="req-test",
        )

        assert manifest.audit_id  # Should be UUID
        assert manifest.request_id == "req-test"
        assert len(manifest.data_sources) == 2
        assert len(manifest.query_ids) == 2
        assert "lmis_workforce" in manifest.data_sources
        assert "lmis_sectors" in manifest.data_sources
        assert manifest.citations["ok"] is True
        assert manifest.verification["ok"] is True

    def test_write_pack_creates_structure(
        self,
        tmp_path,
        sample_query_results,
        sample_verification,
        sample_citations,
        sample_replay_stub,
    ):
        """write_pack should create complete directory structure."""
        trail = AuditTrail(pack_dir=str(tmp_path))

        manifest = trail.generate_trail(
            response_md="# Test Response",
            qresults=sample_query_results,
            verification=sample_verification,
            citations=sample_citations,
            orchestration_meta={},
            code_version="abc123",
            registry_version="v1.0",
            request_id="req-test",
        )

        final_manifest = trail.write_pack(
            manifest=manifest,
            response_md="# Test Response",
            qresults=sample_query_results,
            citations=sample_citations,
            result_report=None,
            replay_stub=sample_replay_stub,
        )

        pack_dir = tmp_path / final_manifest.audit_id

        # Check directory structure
        assert pack_dir.exists()
        assert (pack_dir / "manifest.json").exists()
        assert (pack_dir / "narrative.md").exists()
        assert (pack_dir / "evidence").exists()
        assert (pack_dir / "verification").exists()
        assert (pack_dir / "reproducibility.py").exists()
        assert (pack_dir / "sources").exists()
        assert (pack_dir / "replay.json").exists()

        # Check evidence files
        evidence_dir = pack_dir / "evidence"
        assert (evidence_dir / "qid_abc123.json").exists()
        assert (evidence_dir / "qid_def456.json").exists()

        sources_dir = pack_dir / "sources"
        assert any(sources_dir.iterdir())

        # Check verification files
        verification_dir = pack_dir / "verification"
        assert (verification_dir / "citations.json").exists()

    def test_evidence_files_handle_duplicate_query_ids(
        self,
        tmp_path,
        sample_verification,
        sample_citations,
        sample_replay_stub,
    ):
        """Duplicate query_ids should create suffixed evidence files."""
        trail = AuditTrail(pack_dir=str(tmp_path))

        dup_results = [
            QueryResult(
                query_id="qid_dup",
                rows=[Row(data={"value": 1})],
                unit="count",
                provenance=Provenance(
                    source="csv",
                    dataset_id="ds_one",
                    locator="/tmp/data.csv",
                    fields=["value"],
                ),
                freshness=Freshness(asof_date="2024-01-01", updated_at="2024-01-02T00:00:00Z"),
            ),
            QueryResult(
                query_id="qid_dup",
                rows=[Row(data={"value": 2})],
                unit="count",
                provenance=Provenance(
                    source="csv",
                    dataset_id="ds_two",
                    locator="/tmp/data.csv",
                    fields=["value"],
                ),
                freshness=Freshness(asof_date="2024-01-03", updated_at="2024-01-04T00:00:00Z"),
            ),
        ]

        manifest = trail.generate_trail(
            response_md="# Test",
            qresults=dup_results,
            verification=sample_verification,
            citations=sample_citations,
            orchestration_meta={},
            code_version="abc123",
            registry_version="v1.0",
            request_id="req-dup",
        )

        final_manifest = trail.write_pack(
            manifest=manifest,
            response_md="# Test",
            qresults=dup_results,
            citations=sample_citations,
            result_report=None,
            replay_stub=sample_replay_stub,
        )

        evidence_dir = tmp_path / final_manifest.audit_id / "evidence"
        assert (evidence_dir / "qid_dup.json").exists()
        assert (evidence_dir / "qid_dup_01.json").exists()

    def test_sources_directory_deduplicates_entries(
        self,
        tmp_path,
        sample_verification,
        sample_citations,
        sample_replay_stub,
    ):
        """Sources directory should deduplicate identical dataset/locator combos."""
        trail = AuditTrail(pack_dir=str(tmp_path))

        dup_source_results = [
            QueryResult(
                query_id="qid_src_1",
                rows=[Row(data={"value": 1})],
                unit="count",
                provenance=Provenance(
                    source="csv",
                    dataset_id="ds_shared",
                    locator="/tmp/shared.csv",
                    fields=["value"],
                ),
                freshness=Freshness(asof_date="2024-01-01", updated_at="2024-01-02T00:00:00Z"),
            ),
            QueryResult(
                query_id="qid_src_2",
                rows=[Row(data={"value": 2})],
                unit="count",
                provenance=Provenance(
                    source="csv",
                    dataset_id="ds_shared",
                    locator="/tmp/shared.csv",
                    fields=["value"],
                ),
                freshness=Freshness(asof_date="2024-01-03", updated_at="2024-01-04T00:00:00Z"),
            ),
        ]

        manifest = trail.generate_trail(
            response_md="# Test",
            qresults=dup_source_results,
            verification=sample_verification,
            citations=sample_citations,
            orchestration_meta={},
            code_version="abc123",
            registry_version="v1.0",
            request_id="req-src",
        )

        final_manifest = trail.write_pack(
            manifest=manifest,
            response_md="# Test",
            qresults=dup_source_results,
            citations=sample_citations,
            result_report=None,
            replay_stub=sample_replay_stub,
        )

        sources_dir = tmp_path / final_manifest.audit_id / "sources"
        sources = list(sources_dir.glob("*.json"))
        assert len(sources) == 1
        payload = json.loads(sources[0].read_text())
        assert sorted(payload["query_ids"]) == ["qid_src_1", "qid_src_2"]

    def test_write_pack_populates_digest(
        self,
        tmp_path,
        sample_query_results,
        sample_verification,
        sample_citations,
        sample_replay_stub,
    ):
        """write_pack should compute and store SHA-256 digest."""
        trail = AuditTrail(pack_dir=str(tmp_path))

        manifest = trail.generate_trail(
            response_md="# Test Response",
            qresults=sample_query_results,
            verification=sample_verification,
            citations=sample_citations,
            orchestration_meta={},
            code_version="abc123",
            registry_version="v1.0",
            request_id="req-test",
        )

        final_manifest = trail.write_pack(
            manifest=manifest,
            response_md="# Test Response",
            qresults=sample_query_results,
            citations=sample_citations,
            result_report=None,
            replay_stub=sample_replay_stub,
        )

        assert final_manifest.digest_sha256
        assert len(final_manifest.digest_sha256) == 64
        assert all(c in "0123456789abcdef" for c in final_manifest.digest_sha256)

    def test_write_pack_with_hmac(
        self,
        tmp_path,
        sample_query_results,
        sample_verification,
        sample_citations,
        sample_replay_stub,
    ):
        """write_pack should compute HMAC if key provided."""
        hmac_key = b"test-secret-key"
        trail = AuditTrail(pack_dir=str(tmp_path), hmac_key=hmac_key)

        manifest = trail.generate_trail(
            response_md="# Test Response",
            qresults=sample_query_results,
            verification=sample_verification,
            citations=sample_citations,
            orchestration_meta={},
            code_version="abc123",
            registry_version="v1.0",
            request_id="req-test",
        )

        final_manifest = trail.write_pack(
            manifest=manifest,
            response_md="# Test Response",
            qresults=sample_query_results,
            citations=sample_citations,
            result_report=None,
            replay_stub=sample_replay_stub,
        )

        assert final_manifest.hmac_sha256
        assert len(final_manifest.hmac_sha256) == 64

    def test_write_pack_manifest_json_valid(
        self,
        tmp_path,
        sample_query_results,
        sample_verification,
        sample_citations,
        sample_replay_stub,
    ):
        """Manifest JSON should be valid and complete."""
        trail = AuditTrail(pack_dir=str(tmp_path))

        manifest = trail.generate_trail(
            response_md="# Test Response",
            qresults=sample_query_results,
            verification=sample_verification,
            citations=sample_citations,
            orchestration_meta={},
            code_version="abc123",
            registry_version="v1.0",
            request_id="req-test",
        )

        final_manifest = trail.write_pack(
            manifest=manifest,
            response_md="# Test Response",
            qresults=sample_query_results,
            citations=sample_citations,
            result_report=None,
            replay_stub=sample_replay_stub,
        )

        manifest_path = tmp_path / final_manifest.audit_id / "manifest.json"
        manifest_data = json.loads(manifest_path.read_text())

        assert manifest_data["audit_id"] == final_manifest.audit_id
        assert "digest_sha256" in manifest_data
        assert "pack_paths" in manifest_data
        assert len(manifest_data["pack_paths"]) > 0

    def test_verify_pack_valid(
        self,
        tmp_path,
        sample_query_results,
        sample_verification,
        sample_citations,
        sample_replay_stub,
    ):
        """verify_pack should pass for unmodified pack."""
        trail = AuditTrail(pack_dir=str(tmp_path))

        manifest = trail.generate_trail(
            response_md="# Test Response",
            qresults=sample_query_results,
            verification=sample_verification,
            citations=sample_citations,
            orchestration_meta={},
            code_version="abc123",
            registry_version="v1.0",
            request_id="req-test",
        )

        final_manifest = trail.write_pack(
            manifest=manifest,
            response_md="# Test Response",
            qresults=sample_query_results,
            citations=sample_citations,
            result_report=None,
            replay_stub=sample_replay_stub,
        )

        is_valid, reasons = trail.verify_pack(final_manifest.audit_id)

        assert is_valid
        assert len(reasons) == 0

    def test_verify_pack_tampered_manifest(
        self,
        tmp_path,
        sample_query_results,
        sample_verification,
        sample_citations,
        sample_replay_stub,
    ):
        """verify_pack should fail if manifest is modified."""
        trail = AuditTrail(pack_dir=str(tmp_path))

        manifest = trail.generate_trail(
            response_md="# Test Response",
            qresults=sample_query_results,
            verification=sample_verification,
            citations=sample_citations,
            orchestration_meta={},
            code_version="abc123",
            registry_version="v1.0",
            request_id="req-test",
        )

        final_manifest = trail.write_pack(
            manifest=manifest,
            response_md="# Test Response",
            qresults=sample_query_results,
            citations=sample_citations,
            result_report=None,
            replay_stub=sample_replay_stub,
        )

        # Tamper with manifest
        manifest_path = tmp_path / final_manifest.audit_id / "manifest.json"
        manifest_data = json.loads(manifest_path.read_text())
        manifest_data["request_id"] = "tampered"
        manifest_path.write_text(json.dumps(manifest_data))

        is_valid, reasons = trail.verify_pack(final_manifest.audit_id)

        assert not is_valid
        assert len(reasons) > 0
        assert "Digest mismatch" in reasons[0]

    def test_verify_pack_missing_manifest(self, tmp_path):
        """verify_pack should fail if manifest doesn't exist."""
        trail = AuditTrail(pack_dir=str(tmp_path))

        is_valid, reasons = trail.verify_pack("nonexistent-audit-id")

        assert not is_valid
        assert len(reasons) > 0
        assert "Manifest not found" in reasons[0]

    def test_verify_pack_with_hmac_valid(
        self,
        tmp_path,
        sample_query_results,
        sample_verification,
        sample_citations,
        sample_replay_stub,
    ):
        """verify_pack should verify HMAC if key provided."""
        hmac_key = b"test-secret-key"
        trail = AuditTrail(pack_dir=str(tmp_path), hmac_key=hmac_key)

        manifest = trail.generate_trail(
            response_md="# Test Response",
            qresults=sample_query_results,
            verification=sample_verification,
            citations=sample_citations,
            orchestration_meta={},
            code_version="abc123",
            registry_version="v1.0",
            request_id="req-test",
        )

        final_manifest = trail.write_pack(
            manifest=manifest,
            response_md="# Test Response",
            qresults=sample_query_results,
            citations=sample_citations,
            result_report=None,
            replay_stub=sample_replay_stub,
        )

        is_valid, reasons = trail.verify_pack(final_manifest.audit_id)

        assert is_valid
        assert len(reasons) == 0

    def test_verify_pack_with_hmac_wrong_key(
        self,
        tmp_path,
        sample_query_results,
        sample_verification,
        sample_citations,
        sample_replay_stub,
    ):
        """verify_pack should fail with wrong HMAC key."""
        trail_write = AuditTrail(pack_dir=str(tmp_path), hmac_key=b"key1")

        manifest = trail_write.generate_trail(
            response_md="# Test Response",
            qresults=sample_query_results,
            verification=sample_verification,
            citations=sample_citations,
            orchestration_meta={},
            code_version="abc123",
            registry_version="v1.0",
            request_id="req-test",
        )

        final_manifest = trail_write.write_pack(
            manifest=manifest,
            response_md="# Test Response",
            qresults=sample_query_results,
            citations=sample_citations,
            result_report=None,
            replay_stub=sample_replay_stub,
        )

        # Verify with different key
        trail_verify = AuditTrail(pack_dir=str(tmp_path), hmac_key=b"key2")
        is_valid, reasons = trail_verify.verify_pack(final_manifest.audit_id)

        assert not is_valid
        assert any("HMAC mismatch" in r for r in reasons)
