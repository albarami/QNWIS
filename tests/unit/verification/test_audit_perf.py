"""
Performance tests for audit trail generation.

Ensures audit pack generation completes within acceptable time bounds
even with large narratives and multiple QueryResults.
"""

import tempfile
import time
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
def large_narrative() -> str:
    """Generate a large narrative (~10k characters) for performance testing."""
    base_text = """
## Labor Market Analysis for Qatar

The labor market in Qatar has shown remarkable resilience in 2023.
Unemployment rates have remained stable at 3.5%, reflecting strong economic fundamentals.

### Key Findings

1. **Employment Growth**: The workforce expanded by 100,000 individuals compared to the previous year.
2. **Sectoral Distribution**: Construction and services sectors continue to dominate employment.
3. **Wage Trends**: Average wages increased by 5.2% year-over-year, outpacing inflation.
4. **Labor Force Participation**: Participation rates remained steady at 68.5%.

### Regional Context

When compared to other GCC countries, Qatar maintains competitive employment metrics:
- UAE: 4.1% unemployment
- Saudi Arabia: 5.8% unemployment
- Bahrain: 4.3% unemployment
- Kuwait: 3.9% unemployment
- Oman: 6.2% unemployment

### Policy Implications

The sustained low unemployment rate suggests that current labor policies are effective.
However, diversification efforts should continue to reduce dependency on hydrocarbon sectors.

### Data Quality and Methodology

All statistics cited in this report are derived from official government sources and
international databases. Cross-validation with World Bank indicators confirms consistency.

### Conclusion

Qatar's labor market demonstrates strong fundamentals with room for continued growth
through strategic investments in education and skills development.
"""
    # Repeat to reach ~10k characters
    repeated_text = base_text * 10
    return repeated_text[:10000]


@pytest.fixture
def multiple_query_results() -> List[QueryResult]:
    """Create 3 QueryResult objects for performance testing."""
    return [
        QueryResult(
            query_id="labor_supply",
            rows=[
                Row(data={"year": y, "count": 90000 + (y - 2020) * 5000})
                for y in range(2020, 2024)
            ],
            unit="count",
            provenance=Provenance(
                source="csv",
                dataset_id="qnwis_labor_supply",
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
                Row(data={"year": y, "rate": 0.035 + (y - 2020) * 0.001})
                for y in range(2020, 2024)
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
        QueryResult(
            query_id="wage_trends",
            rows=[
                Row(data={"year": y, "avg_wage": 5000 + (y - 2020) * 250})
                for y in range(2020, 2024)
            ],
            unit="qar",
            provenance=Provenance(
                source="csv",
                dataset_id="qnwis_wages",
                locator="/data/wages.csv",
                fields=["year", "avg_wage"],
            ),
            freshness=Freshness(
                asof_date="2023-12-31",
                updated_at="2024-01-12T14:00:00Z",
            ),
        ),
    ]


@pytest.fixture
def temp_pack_dir() -> Path:
    """Create temporary directory for performance testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


class TestAuditPerformance:
    """Performance tests for audit trail operations."""

    def test_pack_generation_with_large_narrative(
        self,
        large_narrative: str,
        multiple_query_results: List[QueryResult],
        temp_pack_dir: Path,
    ) -> None:
        """
        Test that audit pack generation completes in < 500ms for realistic workload.

        Workload:
        - 10k-character narrative
        - 3 QueryResults with multiple rows each
        - Full verification and citation reports
        """
        trail = AuditTrail(pack_dir=str(temp_pack_dir))

        verification = VerificationSummary(
            ok=True,
            issues=[],
            applied_redactions=0,
            stats={
                "L2/ok": 3,
                "L3/ok": 3,
                "L4/ok": 3,
            },
        )

        citations = CitationReport(
            ok=True,
            total_numbers=25,
            cited_numbers=25,
            sources_used={
                "labor_supply": 10,
                "unemployment_rate": 8,
                "wage_trends": 7,
            },
        )

        orchestration_meta = {
            "routing": "national_strategy",
            "agents": ["pattern_detective", "statistical_analyst"],
            "timings": {
                "query_ms": 250,
                "verification_ms": 75,
                "format_ms": 50,
                "total_ms": 375,
            },
            "params": {
                "query": "Labor market analysis for Qatar",
                "region": "Qatar",
                "year": 2023,
            },
        }

        # Measure generation time
        start_time = time.time()

        manifest = trail.generate_trail(
            response_md=large_narrative,
            qresults=multiple_query_results,
            verification=verification,
            citations=citations,
            orchestration_meta=orchestration_meta,
            code_version="perf_test_abc123",
            registry_version="v1.0.0",
            request_id="req-perf-001",
        )

        generation_time = (time.time() - start_time) * 1000  # Convert to ms

        # Measure write time
        start_time = time.time()

        final_manifest = trail.write_pack(
            manifest=manifest,
            response_md=large_narrative,
            qresults=multiple_query_results,
            citations=citations,
            result_report=None,
        )

        write_time = (time.time() - start_time) * 1000  # Convert to ms

        total_time = generation_time + write_time

        # Assertions
        assert total_time < 500, (
            f"Audit pack generation took {total_time:.2f}ms, "
            f"expected < 500ms (generation: {generation_time:.2f}ms, "
            f"write: {write_time:.2f}ms)"
        )

        # Verify pack was created correctly
        assert final_manifest.digest_sha256
        pack_path = Path(final_manifest.pack_root)
        assert pack_path.exists()
        assert (pack_path / "manifest.json").exists()
        assert (pack_path / "narrative.md").exists()

        # Verify integrity
        is_valid, reasons = trail.verify_pack(final_manifest.audit_id)
        assert is_valid, f"Pack verification failed: {reasons}"

    def test_pack_write_creates_all_files(
        self,
        large_narrative: str,
        multiple_query_results: List[QueryResult],
        temp_pack_dir: Path,
    ) -> None:
        """
        Test that all expected files are created during pack write.

        This ensures the performance test isn't skipping work.
        """
        trail = AuditTrail(pack_dir=str(temp_pack_dir))

        verification = VerificationSummary(ok=True, issues=[])
        citations = CitationReport(ok=True, total_numbers=10, cited_numbers=10)

        manifest = trail.generate_trail(
            response_md=large_narrative,
            qresults=multiple_query_results,
            verification=verification,
            citations=citations,
            orchestration_meta={},
            code_version="abc123",
            registry_version="v1.0.0",
            request_id="req-perf-002",
        )

        final_manifest = trail.write_pack(
            manifest=manifest,
            response_md=large_narrative,
            qresults=multiple_query_results,
            citations=citations,
            result_report=None,
        )

        pack_path = Path(final_manifest.pack_root)

        # Check all expected files exist
        expected_files = [
            "manifest.json",
            "narrative.md",
            "reproducibility.py",
            "evidence/labor_supply.json",
            "evidence/unemployment_rate.json",
            "evidence/wage_trends.json",
            "verification/citations.json",
        ]

        for file_path in expected_files:
            full_path = pack_path / file_path
            assert full_path.exists(), f"Expected file missing: {file_path}"

    def test_hmac_computation_overhead(
        self,
        large_narrative: str,
        multiple_query_results: List[QueryResult],
        temp_pack_dir: Path,
    ) -> None:
        """
        Test that HMAC computation adds minimal overhead (< 50ms).
        """
        hmac_key = b"performance_test_key_12345678"

        trail_with_hmac = AuditTrail(
            pack_dir=str(temp_pack_dir / "with_hmac"),
            hmac_key=hmac_key,
        )

        trail_without_hmac = AuditTrail(
            pack_dir=str(temp_pack_dir / "without_hmac"),
        )

        verification = VerificationSummary(ok=True, issues=[])
        citations = CitationReport(ok=True, total_numbers=5, cited_numbers=5)

        # Test with HMAC
        manifest = trail_with_hmac.generate_trail(
            response_md=large_narrative,
            qresults=multiple_query_results,
            verification=verification,
            citations=citations,
            orchestration_meta={},
            code_version="abc123",
            registry_version="v1.0.0",
            request_id="req-perf-003-hmac",
        )

        start_time = time.time()
        trail_with_hmac.write_pack(
            manifest=manifest,
            response_md=large_narrative,
            qresults=multiple_query_results,
            citations=citations,
            result_report=None,
        )
        time_with_hmac = (time.time() - start_time) * 1000

        # Test without HMAC
        manifest = trail_without_hmac.generate_trail(
            response_md=large_narrative,
            qresults=multiple_query_results,
            verification=verification,
            citations=citations,
            orchestration_meta={},
            code_version="abc123",
            registry_version="v1.0.0",
            request_id="req-perf-003-no-hmac",
        )

        start_time = time.time()
        trail_without_hmac.write_pack(
            manifest=manifest,
            response_md=large_narrative,
            qresults=multiple_query_results,
            citations=citations,
            result_report=None,
        )
        time_without_hmac = (time.time() - start_time) * 1000

        overhead = time_with_hmac - time_without_hmac

        # HMAC should add < 50ms overhead
        assert overhead < 50, (
            f"HMAC computation added {overhead:.2f}ms overhead, expected < 50ms"
        )
