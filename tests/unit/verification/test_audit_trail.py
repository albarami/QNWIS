"""
Unit tests for audit trail generation and pack writing.

Tests AuditManifest assembly, pack directory structure, digest computation,
and integrity verification.
"""

import json
import tempfile
from pathlib import Path
from typing import List

import pytest

from src.qnwis.data.deterministic.models import (
    Freshness,
    Provenance,
    QueryResult,
    Row,
)
from src.qnwis.verification.audit_trail import AuditManifest, AuditTrail
from src.qnwis.verification.citation_enforcer import CitationReport
from src.qnwis.verification.schemas import CitationIssue, VerificationSummary


@pytest.fixture
def sample_query_results() -> List[QueryResult]:
    """Create sample QueryResult objects for testing."""
    return [
        QueryResult(
            query_id="labor_supply",
            rows=[Row(data={"year": 2023, "count": 100000})],
            unit="count",
            provenance=Provenance(
                source="csv",
                dataset_id="qnwis_labor",
                locator="/data/labor.csv",
                fields=["year", "count"],
            ),
            freshness=Freshness(
                asof_date="2023-12-31",
                updated_at="2024-01-15T10:00:00Z",
            ),
        ),
        QueryResult(
            query_id="unemployment_rate",
            rows=[Row(data={"year": 2023, "rate": 0.035})],
            unit="percent",
            provenance=Provenance(
                source="world_bank",
                dataset_id="wb_labor",
                locator="https://api.worldbank.org/v2/countries/QA/indicators/SL.UEM.TOTL.ZS",
                fields=["year", "rate"],
            ),
            freshness=Freshness(
                asof_date="2023-12-31",
                updated_at="2024-01-10T08:30:00Z",
            ),
        ),
    ]


@pytest.fixture
def sample_verification() -> VerificationSummary:
    """Create sample VerificationSummary for testing."""
    return VerificationSummary(
        ok=True,
        issues=[],
        applied_redactions=0,
        stats={"L2/ok": 5, "L3/ok": 3, "L4/ok": 2},
    )


@pytest.fixture
def sample_citations() -> CitationReport:
    """Create sample CitationReport for testing."""
    return CitationReport(
        ok=True,
        total_numbers=10,
        cited_numbers=10,
        uncited=[],
        malformed=[],
        missing_qid=[],
        sources_used={"labor_supply": 6, "unemployment_rate": 4},
        runtime_ms=12.5,
    )


@pytest.fixture
def temp_pack_dir() -> Path:
    """Create temporary directory for audit packs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


class TestAuditManifest:
    """Tests for AuditManifest dataclass."""

    def test_manifest_to_dict_and_from_dict(self) -> None:
        """Test serialization round-trip."""
        manifest = AuditManifest(
            audit_id="test-123",
            created_at="2024-01-15T10:00:00Z",
            request_id="req-456",
            registry_version="v1.0.0",
            code_version="abc123",
            data_sources=["qnwis_labor", "wb_labor"],
            query_ids=["labor_supply", "unemployment_rate"],
            freshness={"qnwis_labor": "2023-12-31"},
            citations={"ok": True, "total_numbers": 10},
            verification={"ok": True, "issues_count": 0},
            orchestration={"routing": "national_strategy"},
            reproducibility={"snippet": "# code", "params_hash": "xyz"},
        )

        # Serialize and deserialize
        manifest_dict = manifest.to_dict()
        restored = AuditManifest.from_dict(manifest_dict)

        assert restored.audit_id == manifest.audit_id
        assert restored.query_ids == manifest.query_ids
        assert restored.data_sources == manifest.data_sources


class TestAuditTrailGenerateTrail:
    """Tests for AuditTrail.generate_trail() method."""

    def test_generate_trail_collects_query_ids_sources_freshness(
        self,
        sample_query_results: List[QueryResult],
        sample_verification: VerificationSummary,
        sample_citations: CitationReport,
        temp_pack_dir: Path,
    ) -> None:
        """Test that generate_trail extracts all metadata correctly."""
        trail = AuditTrail(pack_dir=str(temp_pack_dir))

        orchestration_meta = {
            "routing": "national_strategy",
            "agents": ["pattern_detective"],
            "timings": {"total_ms": 1500},
            "params": {"query": "unemployment", "region": "Qatar"},
        }

        manifest = trail.generate_trail(
            response_md="The unemployment rate in Qatar is 3.5%.",
            qresults=sample_query_results,
            verification=sample_verification,
            citations=sample_citations,
            orchestration_meta=orchestration_meta,
            code_version="abc123",
            registry_version="v1.0.0",
            request_id="req-001",
        )

        # Check query IDs
        assert manifest.query_ids == ["labor_supply", "unemployment_rate"]

        # Check data sources (sorted, unique)
        assert set(manifest.data_sources) == {"qnwis_labor", "wb_labor"}
        assert manifest.data_sources == sorted(manifest.data_sources)

        # Check freshness
        assert "qnwis_labor" in manifest.freshness
        assert "wb_labor" in manifest.freshness
        assert manifest.freshness["qnwis_labor"] == "2024-01-15T10:00:00Z"

        # Check citations summary
        assert manifest.citations["ok"] is True
        assert manifest.citations["total_numbers"] == 10
        assert manifest.citations["cited_numbers"] == 10

        # Check verification summary
        assert manifest.verification["ok"] is True
        assert manifest.verification["issues_count"] == 0

        # Check reproducibility
        assert "snippet" in manifest.reproducibility
        assert "params_hash" in manifest.reproducibility
        assert "labor_supply" in manifest.reproducibility["snippet"]

    def test_redaction_applied_to_summaries(
        self,
        sample_query_results: List[QueryResult],
        sample_verification: VerificationSummary,
        temp_pack_dir: Path,
    ) -> None:
        """Test that PII redaction is applied to citation examples."""
        trail = AuditTrail(pack_dir=str(temp_pack_dir))

        # Create citation report with PII
        citations_with_pii = CitationReport(
            ok=False,
            total_numbers=5,
            cited_numbers=3,
            uncited=[
                CitationIssue(
                    code="UNCITED_NUMBER",
                    value_text="John Smith earned 50000",
                    message="Uncited claim about John Smith",
                    severity="warning",
                )
            ],
            malformed=[],
            missing_qid=[],
            sources_used={"labor_supply": 3},
        )

        manifest = trail.generate_trail(
            response_md="Response text",
            qresults=sample_query_results,
            verification=sample_verification,
            citations=citations_with_pii,
            orchestration_meta={},
            code_version="abc123",
            registry_version="v1.0.0",
            request_id="req-002",
        )

        # Check that uncited examples are redacted
        uncited_examples = manifest.citations.get("uncited_examples", [])
        assert len(uncited_examples) == 1

        example = uncited_examples[0]
        assert "John Smith" not in example["value_text"]
        assert "[REDACTED_NAME]" in example["value_text"]


class TestAuditTrailWritePack:
    """Tests for AuditTrail.write_pack() method."""

    def test_write_pack_writes_manifest_and_files(
        self,
        sample_query_results: List[QueryResult],
        sample_verification: VerificationSummary,
        sample_citations: CitationReport,
        temp_pack_dir: Path,
    ) -> None:
        """Test that write_pack creates all expected files."""
        trail = AuditTrail(pack_dir=str(temp_pack_dir))

        manifest = trail.generate_trail(
            response_md="The unemployment rate is 3.5%.",
            qresults=sample_query_results,
            verification=sample_verification,
            citations=sample_citations,
            orchestration_meta={},
            code_version="abc123",
            registry_version="v1.0.0",
            request_id="req-003",
        )

        final_manifest = trail.write_pack(
            manifest=manifest,
            response_md="The unemployment rate is 3.5%.",
            qresults=sample_query_results,
            citations=sample_citations,
            result_report=None,
        )

        pack_root = Path(final_manifest.pack_root)

        # Check directory structure
        assert pack_root.exists()
        assert (pack_root / "manifest.json").exists()
        assert (pack_root / "narrative.md").exists()
        assert (pack_root / "reproducibility.py").exists()
        assert (pack_root / "evidence").is_dir()
        assert (pack_root / "verification").is_dir()
        assert (pack_root / "sources").is_dir()

        # Check evidence files
        assert (pack_root / "evidence" / "labor_supply.json").exists()
        assert (pack_root / "evidence" / "unemployment_rate.json").exists()

        # Check verification files
        assert (pack_root / "verification" / "citations.json").exists()

        # Check reproducibility snippet is executable Python
        snippet_path = pack_root / "reproducibility.py"
        snippet_text = snippet_path.read_text(encoding="utf-8")
        assert "from src.qnwis.data.deterministic.api import DataAPI" in snippet_text

    def test_pack_digest_matches_verify_tool(
        self,
        sample_query_results: List[QueryResult],
        sample_verification: VerificationSummary,
        sample_citations: CitationReport,
        temp_pack_dir: Path,
    ) -> None:
        """Test that digest is computed correctly and verification passes."""
        trail = AuditTrail(pack_dir=str(temp_pack_dir))

        manifest = trail.generate_trail(
            response_md="Response text",
            qresults=sample_query_results,
            verification=sample_verification,
            citations=sample_citations,
            orchestration_meta={},
            code_version="abc123",
            registry_version="v1.0.0",
            request_id="req-004",
        )

        final_manifest = trail.write_pack(
            manifest=manifest,
            response_md="Response text",
            qresults=sample_query_results,
            citations=sample_citations,
            result_report=None,
        )

        # Check that digest was computed
        assert final_manifest.digest_sha256
        assert len(final_manifest.digest_sha256) == 64

        # Verify pack integrity
        is_valid, reasons = trail.verify_pack(final_manifest.audit_id)
        assert is_valid, f"Verification failed: {reasons}"
        assert reasons == []

    def test_write_pack_with_hmac(
        self,
        sample_query_results: List[QueryResult],
        sample_verification: VerificationSummary,
        sample_citations: CitationReport,
        temp_pack_dir: Path,
    ) -> None:
        """Test that HMAC signature is computed when key is provided."""
        hmac_key = b"test_secret_key_12345"
        trail = AuditTrail(pack_dir=str(temp_pack_dir), hmac_key=hmac_key)

        manifest = trail.generate_trail(
            response_md="Response text",
            qresults=sample_query_results,
            verification=sample_verification,
            citations=sample_citations,
            orchestration_meta={},
            code_version="abc123",
            registry_version="v1.0.0",
            request_id="req-005",
        )

        final_manifest = trail.write_pack(
            manifest=manifest,
            response_md="Response text",
            qresults=sample_query_results,
            citations=sample_citations,
            result_report=None,
        )

        # Check that HMAC was computed
        assert final_manifest.hmac_sha256 is not None
        assert len(final_manifest.hmac_sha256) == 64

        # Verify with correct key
        is_valid, reasons = trail.verify_pack(final_manifest.audit_id)
        assert is_valid, f"Verification with correct key failed: {reasons}"

        # Verify with wrong key should fail
        wrong_trail = AuditTrail(pack_dir=str(temp_pack_dir), hmac_key=b"wrong_key")
        is_valid, reasons = wrong_trail.verify_pack(final_manifest.audit_id)
        assert not is_valid
        assert any("HMAC mismatch" in reason for reason in reasons)


class TestAuditTrailVerifyPack:
    """Tests for AuditTrail.verify_pack() method."""

    def test_verify_pack_detects_tampering(
        self,
        sample_query_results: List[QueryResult],
        sample_verification: VerificationSummary,
        sample_citations: CitationReport,
        temp_pack_dir: Path,
    ) -> None:
        """Test that verification detects manifest tampering."""
        trail = AuditTrail(pack_dir=str(temp_pack_dir))

        manifest = trail.generate_trail(
            response_md="Original response",
            qresults=sample_query_results,
            verification=sample_verification,
            citations=sample_citations,
            orchestration_meta={},
            code_version="abc123",
            registry_version="v1.0.0",
            request_id="req-006",
        )

        final_manifest = trail.write_pack(
            manifest=manifest,
            response_md="Original response",
            qresults=sample_query_results,
            citations=sample_citations,
            result_report=None,
        )

        # Tamper with manifest file
        pack_root = Path(final_manifest.pack_root)
        manifest_path = pack_root / "manifest.json"
        manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest_data["code_version"] = "tampered_version"
        manifest_path.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")

        # Verification should fail
        is_valid, reasons = trail.verify_pack(final_manifest.audit_id)
        assert not is_valid
        assert len(reasons) > 0
        assert any("Digest mismatch" in reason for reason in reasons)

    def test_verify_pack_missing_manifest(
        self,
        temp_pack_dir: Path,
    ) -> None:
        """Test that verification fails gracefully for missing manifest."""
        trail = AuditTrail(pack_dir=str(temp_pack_dir))

        is_valid, reasons = trail.verify_pack("nonexistent-audit-id")
        assert not is_valid
        assert len(reasons) == 1
        assert "Manifest not found" in reasons[0]
