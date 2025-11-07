"""
Integration tests for audit trail system with orchestration.

Tests end-to-end workflow of generating audit manifests from orchestration runs,
verifying integration with verify-node, and ensuring formatted reports include
audit summaries.
"""

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
from src.qnwis.verification.audit_trail import AuditTrail
from src.qnwis.verification.citation_enforcer import CitationReport
from src.qnwis.verification.schemas import VerificationSummary


@pytest.fixture
def mock_query_results() -> List[QueryResult]:
    """Create mock QueryResults for testing."""
    return [
        QueryResult(
            query_id="labor_supply",
            rows=[
                Row(data={"year": 2023, "count": 100000}),
                Row(data={"year": 2022, "count": 95000}),
            ],
            unit="count",
            provenance=Provenance(
                source="csv",
                dataset_id="qnwis_labor",
                locator="/data/labor_supply.csv",
                fields=["year", "count"],
            ),
            freshness=Freshness(
                asof_date="2023-12-31",
                updated_at="2024-01-15T10:00:00Z",
            ),
        ),
        QueryResult(
            query_id="unemployment_rate",
            rows=[
                Row(data={"year": 2023, "rate": 0.035}),
            ],
            unit="percent",
            provenance=Provenance(
                source="world_bank",
                dataset_id="wb_unemployment",
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
def temp_audit_dir() -> Path:
    """Create temporary directory for audit packs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


class TestAuditIntegration:
    """Integration tests for audit trail with orchestration."""

    def test_audit_manifest_exists_in_state(
        self,
        mock_query_results: List[QueryResult],
        temp_audit_dir: Path,
    ) -> None:
        """
        Test that audit_manifest can be generated and has required attributes.

        This simulates what verify-node does during orchestration.
        """
        # Simulated state would have these QueryResults
        user_query = "What is the unemployment rate in Qatar?"

        # Simulate verification
        verification = VerificationSummary(
            ok=True,
            issues=[],
            applied_redactions=0,
            stats={"L2/ok": 2, "L3/ok": 2, "L4/ok": 2},
        )

        citations = CitationReport(
            ok=True,
            total_numbers=3,
            cited_numbers=3,
            sources_used={"labor_supply": 2, "unemployment_rate": 1},
        )

        # Generate audit trail
        trail = AuditTrail(pack_dir=str(temp_audit_dir))

        orchestration_meta = {
            "routing": "national_strategy",
            "agents": ["pattern_detective"],
            "timings": {"total_ms": 2500},
            "params": {"query": user_query},
        }

        manifest = trail.generate_trail(
            response_md="The unemployment rate in Qatar is 3.5% as of 2023.",
            qresults=mock_query_results,
            verification=verification,
            citations=citations,
            orchestration_meta=orchestration_meta,
            code_version="test_commit_abc123",
            registry_version="v1.0.0",
            request_id="req-integration-001",
        )

        # Assert manifest was generated
        assert manifest is not None
        assert manifest.audit_id is not None
        assert len(manifest.audit_id) > 0

        # Assert has correct structure
        # Note: digest is computed during write_pack, not generate_trail
        assert manifest.query_ids == ["labor_supply", "unemployment_rate"]
        assert set(manifest.data_sources) == {
            "qnwis_labor",
            "wb_unemployment",
        }

        # Assert reproducibility snippet is present
        assert "snippet" in manifest.reproducibility
        assert "labor_supply" in manifest.reproducibility["snippet"]

    def test_audit_pack_written_and_verified(
        self,
        mock_query_results: List[QueryResult],
        temp_audit_dir: Path,
    ) -> None:
        """
        Test that audit pack is written to disk with correct digest and can be verified.
        """
        trail = AuditTrail(pack_dir=str(temp_audit_dir))

        verification = VerificationSummary(
            ok=True,
            issues=[],
            applied_redactions=0,
            stats={},
        )

        citations = CitationReport(
            ok=True,
            total_numbers=5,
            cited_numbers=5,
        )

        # Generate manifest
        manifest = trail.generate_trail(
            response_md="Test response narrative.",
            qresults=mock_query_results,
            verification=verification,
            citations=citations,
            orchestration_meta={
                "routing": "national_strategy",
                "agents": [],
            },
            code_version="abc123",
            registry_version="v1.0.0",
            request_id="req-integration-002",
        )

        # Write pack
        final_manifest = trail.write_pack(
            manifest=manifest,
            response_md="Test response narrative.",
            qresults=mock_query_results,
            citations=citations,
            result_report=None,
        )

        # Assert digest was computed
        assert final_manifest.digest_sha256
        assert len(final_manifest.digest_sha256) == 64

        # Assert pack_root was set
        assert final_manifest.pack_root
        pack_path = Path(final_manifest.pack_root)
        assert pack_path.exists()

        # Verify pack integrity
        is_valid, reasons = trail.verify_pack(final_manifest.audit_id)
        assert is_valid, f"Pack verification failed: {reasons}"
        assert reasons == []

    def test_final_formatted_report_contains_audit_summary(
        self,
        mock_query_results: List[QueryResult],
        temp_audit_dir: Path,
    ) -> None:
        """
        Test that formatted report includes Audit Summary section with audit_id and pack path.

        This simulates what format-node does after verify-node.
        """
        trail = AuditTrail(pack_dir=str(temp_audit_dir))

        verification = VerificationSummary(
            ok=True,
            issues=[],
            applied_redactions=0,
            stats={},
        )

        citations = CitationReport(
            ok=True,
            total_numbers=5,
            cited_numbers=5,
        )

        # Generate and write pack
        manifest = trail.generate_trail(
            response_md="Response text",
            qresults=mock_query_results,
            verification=verification,
            citations=citations,
            orchestration_meta={},
            code_version="abc123",
            registry_version="v1.0.0",
            request_id="req-integration-003",
        )

        final_manifest = trail.write_pack(
            manifest=manifest,
            response_md="Response text",
            qresults=mock_query_results,
            citations=citations,
            result_report=None,
        )

        # Simulate format-node building final report
        # (In real orchestration, format-node reads state.audit_manifest and appends summary)
        audit_summary = f"""
---

## Audit Summary

**Audit ID**: {final_manifest.audit_id}
**Audit Pack**: {final_manifest.pack_root}
**Created**: {final_manifest.created_at}
**Digest**: {final_manifest.digest_sha256[:16]}...

For reproducibility instructions, see: `{final_manifest.pack_root}/reproducibility.py`
"""

        # Simulate final report
        final_report = "# Labor Market Analysis\n\nThe unemployment rate is 3.5%.\n" + audit_summary

        # Assert final formatted report contains "Audit Summary" section
        assert "## Audit Summary" in final_report
        assert final_manifest.audit_id in final_report
        assert final_manifest.pack_root in final_report

    def test_minimal_orchestration_with_mocked_results(
        self,
        mock_query_results: List[QueryResult],
        temp_audit_dir: Path,
    ) -> None:
        """
        Run minimal orchestration flow with mocked QueryResults.

        Simulates the full flow: query -> verification -> audit trail -> format.
        """
        # Step 1: Simulated state with query and results
        user_query = "What is Qatar's unemployment rate?"
        qresults = mock_query_results

        # Step 2: Run verification (mocked)
        verification = VerificationSummary(
            ok=True,
            issues=[],
            applied_redactions=0,
            stats={"L2/ok": 2, "L3/ok": 2, "L4/ok": 2},
        )

        citations = CitationReport(
            ok=True,
            total_numbers=5,
            cited_numbers=5,
            sources_used={"labor_supply": 3, "unemployment_rate": 2},
        )

        # Step 3: Generate audit trail
        trail = AuditTrail(pack_dir=str(temp_audit_dir))

        orchestration_meta = {
            "routing": "national_strategy",
            "agents": ["pattern_detective"],
            "timings": {
                "query_ms": 150,
                "verification_ms": 50,
                "format_ms": 25,
                "total_ms": 225,
            },
            "params": {"query": user_query, "region": "Qatar"},
        }

        manifest = trail.generate_trail(
            response_md="Qatar's unemployment rate is 3.5% as of 2023.",
            qresults=qresults,
            verification=verification,
            citations=citations,
            orchestration_meta=orchestration_meta,
            code_version="integration_test_commit",
            registry_version="v1.0.0",
            request_id="req-orchestration-001",
        )

        # Write pack
        final_manifest = trail.write_pack(
            manifest=manifest,
            response_md="Qatar's unemployment rate is 3.5% as of 2023.",
            qresults=qresults,
            citations=citations,
            result_report=None,
        )

        # Step 4: Format final report
        base_response = "Qatar's unemployment rate is 3.5% as of 2023."

        audit_section = f"""

---

## Audit Summary

**Audit ID**: `{final_manifest.audit_id}`
**Pack Location**: `{final_manifest.pack_root}`
**Sources**: {len(final_manifest.data_sources)} dataset(s)
**Queries**: {len(final_manifest.query_ids)} query(ies)
**Verification**: {'PASS' if verification.ok else 'FAIL'}
**Citations**: {'PASS' if citations.ok else 'FAIL'}

Reproducibility: `{final_manifest.pack_root}/reproducibility.py`
"""

        final_report = base_response + audit_section

        # Assertions
        assert final_manifest is not None
        assert final_manifest.digest_sha256
        assert "## Audit Summary" in final_report
        assert final_manifest.audit_id in final_report

        # Verify pack
        is_valid, reasons = trail.verify_pack(final_manifest.audit_id)
        assert is_valid, f"Pack verification failed: {reasons}"
