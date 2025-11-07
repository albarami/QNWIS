"""
Unit tests for result verification engine.

Tests numeric claim extraction, binding, tolerances, and math consistency checks.
"""

import pytest

from src.qnwis.data.deterministic.models import (
    Freshness,
    Provenance,
    QueryResult,
    Row,
)
from src.qnwis.verification.number_extractors import extract_numeric_claims
from src.qnwis.verification.result_verifier import (
    bind_claim_to_sources,
    check_math_consistency,
    verify_numbers,
)
from src.qnwis.verification.schemas import NumericClaim


class TestNumericClaimExtraction:
    """Test numeric claim extraction from narrative text."""

    def test_extract_simple_integer(self):
        """Test extraction of simple integer count."""
        text = "Per LMIS: There are 1234 employees."
        claims = extract_numeric_claims(text)

        assert len(claims) == 1
        assert claims[0].value == 1234.0
        assert claims[0].unit == "count"
        assert claims[0].citation_prefix == "Per LMIS:"

    def test_extract_percentage(self):
        """Test extraction of percentage value."""
        text = "According to GCC-STAT: Growth was 15.5%"
        claims = extract_numeric_claims(text)

        assert len(claims) == 1
        assert claims[0].value == 15.5
        assert claims[0].unit == "percent"
        assert claims[0].citation_prefix == "According to GCC-STAT:"

    def test_extract_currency(self):
        """Test extraction of currency value."""
        text = "Per LMIS: Average salary is 5,000 QAR"
        claims = extract_numeric_claims(text)

        assert len(claims) == 1
        assert claims[0].value == 5000.0
        assert claims[0].unit == "currency"
        # value_text includes the unit if present
        assert "5,000" in claims[0].value_text

    def test_extract_with_query_id(self):
        """Test extraction with query ID detection."""
        text = "Per LMIS: 1234 records (QID:lmis_001)"
        claims = extract_numeric_claims(text)

        assert len(claims) == 1
        assert claims[0].query_id == "lmis_001"
        assert claims[0].source_family == "LMIS"

    def test_ignore_years(self):
        """Test that years are ignored."""
        text = "In 2023, there were 1234 employees"
        claims = extract_numeric_claims(text, ignore_years=True)

        # Should only extract 1234, not 2023
        assert len(claims) == 1
        assert claims[0].value == 1234.0

    def test_ignore_small_numbers(self):
        """Test filtering of small numbers."""
        text = "0.5% growth"
        claims = extract_numeric_claims(text, ignore_below=1.0)

        # 0.5 is below threshold
        assert len(claims) == 0

    def test_multiple_claims(self):
        """Test extraction of multiple claims."""
        text = """
        Per LMIS: Total workforce is 10,000 employees (QID:lmis_001).
        According to GCC-STAT: Growth rate is 5.5% (QID:gcc_002).
        """
        claims = extract_numeric_claims(text)

        assert len(claims) == 2
        assert claims[0].value == 10000.0
        assert claims[0].source_family == "LMIS"
        assert claims[1].value == 5.5
        assert claims[1].source_family == "GCC-STAT"

    def test_extract_handles_commas_signs_and_currency(self):
        """Ensure parser handles 1,234, 87.5%, +2.3 pp, and QAR 18,500."""
        text = (
            "Per LMIS: 1,234 workers joined (+2.3 pp vs 2023). "
            "According to GCC-STAT: Retention hit 87.5%. "
            "Pay reached QAR 18,500."
        )

        claims = extract_numeric_claims(text)
        assert len(claims) == 4
        values = [c.value for c in claims]
        assert 1234.0 in values
        assert 2.3 in values  # percentage points
        assert 87.5 in values
        assert 18500.0 in values


class TestClaimBinding:
    """Test claim binding to QueryResult sources."""

    def test_bind_by_exact_query_id(self):
        """Test binding with exact query_id match."""
        claim = NumericClaim(
            value_text="1234",
            value=1234.0,
            unit="count",
            span=(0, 4),
            sentence="Test",
            query_id="lmis_001",
        )

        qr = QueryResult(
            query_id="lmis_001",
            rows=[Row(data={}) for _ in range(1234)],
            unit="count",
            provenance=Provenance(
                source="csv",
                dataset_id="lmis_employees",
                locator="test.csv",
                fields=["count"],
            ),
            freshness=Freshness(asof_date="2024-01-01"),
        )

        tolerances = {"abs_epsilon": 0.5, "rel_epsilon": 0.01, "prefer_query_id": True}
        binding = bind_claim_to_sources(claim, [qr], tolerances)

        assert binding.matched
        assert binding.matched_source_qid == "lmis_001"
        assert binding.matched_location == "row_count"

    def test_bind_by_source_family(self):
        """Test binding by source_family when QID not specified."""
        claim = NumericClaim(
            value_text="1234",
            value=1234.0,
            unit="count",
            span=(0, 4),
            sentence="Test",
            source_family="LMIS",
        )

        qr = QueryResult(
            query_id="lmis_001",
            rows=[Row(data={}) for _ in range(1234)],
            unit="count",
            provenance=Provenance(
                source="csv",
                dataset_id="lmis_employees",
                locator="test.csv",
                fields=["count"],
            ),
            freshness=Freshness(asof_date="2024-01-01"),
        )

        tolerances = {"abs_epsilon": 0.5, "rel_epsilon": 0.01, "prefer_query_id": False}
        binding = bind_claim_to_sources(claim, [qr], tolerances)

        assert binding.matched

    def test_bind_data_field_match(self):
        """Test binding to data field value."""
        claim = NumericClaim(
            value_text="5000",
            value=5000.0,
            unit="currency",
            span=(0, 4),
            sentence="Test",
            query_id="lmis_001",
        )

        qr = QueryResult(
            query_id="lmis_001",
            rows=[Row(data={"avg_salary": 5000.0})],
            unit="qar",
            provenance=Provenance(
                source="csv",
                dataset_id="lmis_salaries",
                locator="test.csv",
                fields=["avg_salary"],
            ),
            freshness=Freshness(asof_date="2024-01-01"),
        )

        tolerances = {"abs_epsilon": 0.5, "rel_epsilon": 0.01, "prefer_query_id": True}
        binding = bind_claim_to_sources(claim, [qr], tolerances)

        assert binding.matched
        assert "avg_salary" in binding.matched_location

    def test_percentage_normalization(self):
        """Test percentage value normalization (0.15 vs 15.0)."""
        claim = NumericClaim(
            value_text="15%",
            value=15.0,
            unit="percent",
            span=(0, 3),
            sentence="Test",
            query_id="lmis_001",
        )

        # Data stored as [0, 1] range
        qr = QueryResult(
            query_id="lmis_001",
            rows=[Row(data={"growth_rate": 0.15})],
            unit="percent",
            provenance=Provenance(
                source="csv",
                dataset_id="lmis_growth",
                locator="test.csv",
                fields=["growth_rate"],
            ),
            freshness=Freshness(asof_date="2024-01-01"),
        )

        tolerances = {"abs_epsilon": 0.5, "rel_epsilon": 0.01, "prefer_query_id": True}
        binding = bind_claim_to_sources(claim, [qr], tolerances)

        assert binding.matched

    def test_rounding_tolerance(self):
        """Test rounding tolerance for near-matches."""
        claim = NumericClaim(
            value_text="1234",
            value=1234.0,
            unit="count",
            span=(0, 4),
            sentence="Test",
            query_id="lmis_001",
        )

        # Actual value is 1234.4 (rounds to 1234)
        qr = QueryResult(
            query_id="lmis_001",
            rows=[Row(data={"count": 1234.4})],
            unit="count",
            provenance=Provenance(
                source="csv",
                dataset_id="lmis_count",
                locator="test.csv",
                fields=["count"],
            ),
            freshness=Freshness(asof_date="2024-01-01"),
        )

        tolerances = {"abs_epsilon": 0.5, "rel_epsilon": 0.01, "prefer_query_id": True}
        binding = bind_claim_to_sources(claim, [qr], tolerances)

        assert binding.matched

    def test_no_match_when_outside_tolerance(self):
        """Test that claims outside tolerance are not matched."""
        claim = NumericClaim(
            value_text="1234",
            value=1234.0,
            unit="count",
            span=(0, 4),
            sentence="Test",
            query_id="lmis_001",
        )

        # Actual value is 1236 (outside ±0.5 tolerance)
        qr = QueryResult(
            query_id="lmis_001",
            rows=[Row(data={"count": 1236.0})],
            unit="count",
            provenance=Provenance(
                source="csv",
                dataset_id="lmis_count",
                locator="test.csv",
                fields=["count"],
            ),
            freshness=Freshness(asof_date="2024-01-01"),
        )

        # Disable relative tolerance to ensure absolute check fails
        tolerances = {"abs_epsilon": 0.5, "rel_epsilon": 0.0, "prefer_query_id": True}
        binding = bind_claim_to_sources(claim, [qr], tolerances)

        assert not binding.matched

    def test_segment_aware_binding_prefers_matching_row(self):
        """Rows narrowed to matching sector when sentence mentions it."""
        claim = NumericClaim(
            value_text="500",
            value=500.0,
            unit="count",
            span=(0, 3),
            sentence="Per LMIS: Energy sector employment reached 500 (QID:lmis_seg)",
            query_id="lmis_seg",
        )

        rows = [
            Row(data={"sector": "Finance", "headcount": 500.0}),
            Row(data={"sector": "Energy", "headcount": 500.0}),
        ]
        qr = QueryResult(
            query_id="lmis_seg",
            rows=rows,
            unit="count",
            provenance=Provenance(
                source="csv",
                dataset_id="lmis_segments",
                locator="segments.csv",
                fields=["sector", "headcount"],
            ),
            freshness=Freshness(asof_date="2024-01-01"),
        )

        tolerances = {
            "abs_epsilon": 0.5,
            "rel_epsilon": 0.01,
            "prefer_query_id": True,
            "segment_fields": ["sector"],
        }
        binding = bind_claim_to_sources(claim, [qr], tolerances)

        assert binding.matched
        assert binding.matched_location == "data[1].headcount"

    def test_ambiguous_sources_without_query_id(self):
        """Multiple sources with same value should flag ambiguity."""
        claim = NumericClaim(
            value_text="1234",
            value=1234.0,
            unit="count",
            span=(0, 4),
            sentence="Per LMIS: 1234 workers were surveyed.",
        )

        qr_a = QueryResult(
            query_id="lmis_a",
            rows=[Row(data={}) for _ in range(1234)],
            unit="count",
            provenance=Provenance(
                source="csv",
                dataset_id="lmis_a",
                locator="a.csv",
                fields=["count"],
            ),
            freshness=Freshness(asof_date="2024-01-01"),
        )
        qr_b = QueryResult(
            query_id="lmis_b",
            rows=[Row(data={}) for _ in range(1234)],
            unit="count",
            provenance=Provenance(
                source="csv",
                dataset_id="lmis_b",
                locator="b.csv",
                fields=["count"],
            ),
            freshness=Freshness(asof_date="2024-01-01"),
        )

        tolerances = {"abs_epsilon": 0.5, "rel_epsilon": 0.01}
        binding = bind_claim_to_sources(claim, [qr_a, qr_b], tolerances)

        assert not binding.matched
        assert binding.ambiguous
        assert binding.failure_reason == "AMBIGUOUS_SOURCE"
        assert set(binding.candidate_qids) == {"lmis_a", "lmis_b"}

    def test_derived_share_recomputation_flags_inconsistency(self):
        """Derived bindings recompute share-of-total using stored rows."""
        claim = NumericClaim(
            value_text="10%",
            value=10.0,
            unit="percent",
            span=(0, 3),
            sentence="Per LMIS: Finance qatarization is 10% (QID:derived_qat)",
            query_id="derived_qat",
        )

        row = Row(
            data={
                "segment": "Finance",
                "qataris": 200,
                "non_qataris": 800,
                "qatarization_percent": 10.0,  # incorrect derived value
            }
        )
        qr = QueryResult(
            query_id="derived_qat",
            rows=[row],
            unit="percent",
            provenance=Provenance(
                source="csv",
                dataset_id="derived_qatarization",
                locator="derived.csv",
                fields=["segment", "qataris", "non_qataris", "qatarization_percent"],
            ),
            freshness=Freshness(asof_date="2024-01-01"),
        )

        tolerances = {
            "abs_epsilon": 0.5,
            "rel_epsilon": 0.01,
            "prefer_query_id": True,
            "derived_share_check_enabled": True,
            "derived_share_min_components": 2,
        }

        binding = bind_claim_to_sources(claim, [qr], tolerances)

        assert binding.matched
        assert binding.derived_consistent is False
        assert binding.derived_recomputed_value == pytest.approx(20.0)


class TestMathConsistency:
    """Test math consistency checks."""

    def test_percentage_sum_passes(self):
        """Test percentage bullet group that sums to 100%."""
        narrative = """
        - 45% in construction
        - 30% in services
        - 25% in manufacturing
        """

        tolerances = {"epsilon_pct": 0.5, "sum_to_100": True}
        checks, _ = check_math_consistency(narrative, tolerances)

        assert len(checks) > 0
        assert all(checks.values())  # All checks pass

    def test_percentage_sum_fails(self):
        """Test percentage bullet group that doesn't sum to 100%."""
        narrative = """
        - 45% in construction
        - 30% in services
        - 20% in manufacturing
        """
        # Sums to 95%, outside 0.5% tolerance

        tolerances = {"epsilon_pct": 0.5, "sum_to_100": True}
        checks, _ = check_math_consistency(narrative, tolerances)

        assert len(checks) > 0
        assert not all(checks.values())  # At least one check fails

    def test_percentage_sum_within_tolerance(self):
        """Test percentage sum within rounding tolerance."""
        narrative = """
        - 33.4% in sector A
        - 33.3% in sector B
        - 33.3% in sector C
        """
        # Sums to 100.0%, should pass

        tolerances = {"epsilon_pct": 0.5, "sum_to_100": True}
        checks, _ = check_math_consistency(narrative, tolerances)

        assert len(checks) > 0
        assert all(checks.values())

    def test_no_checks_when_disabled(self):
        """Test that no checks run when sum_to_100 is disabled."""
        narrative = """
        - 50% increase
        - 30% decrease
        """

        tolerances = {"epsilon_pct": 0.5, "sum_to_100": False}
        checks, _ = check_math_consistency(narrative, tolerances)

        assert len(checks) == 0

    def test_markdown_table_total_mismatch(self):
        """Verify Markdown table totals are validated."""
        narrative = """
        | Sector | Workers |
        | ------ | ------- |
        | Energy | 1000    |
        | Finance| 2000    |
        | Total  | 3500    |
        """

        tolerances = {"abs_epsilon": 0.5, "sum_to_100": True}
        checks, details = check_math_consistency(narrative, tolerances)

        assert checks
        failing = [name for name, passed in checks.items() if not passed]
        assert failing, "Expected table total check to fail"
        fail_name = failing[0]
        assert "table_total" in fail_name
        assert details[fail_name]["expected"] == 3500.0
        assert details[fail_name]["sum"] == 3000.0


class TestVerifyNumbers:
    """Integration tests for full verification flow."""

    def test_verify_all_claims_matched(self):
        """Test verification when all claims match."""
        narrative = "Per LMIS: There are 1234 employees (QID:lmis_001)."

        qr = QueryResult(
            query_id="lmis_001",
            rows=[Row(data={}) for _ in range(1234)],
            unit="count",
            provenance=Provenance(
                source="csv",
                dataset_id="lmis_employees",
                locator="test.csv",
                fields=["count"],
            ),
            freshness=Freshness(asof_date="2024-01-01"),
        )

        tolerances = {
            "abs_epsilon": 0.5,
            "rel_epsilon": 0.01,
            "prefer_query_id": True,
            "require_citation_first": True,
            "ignore_numbers_below": 1.0,
        }

        report = verify_numbers(narrative, [qr], tolerances)

        assert report.ok
        assert report.claims_total == 1
        assert report.claims_matched == 1
        assert len(report.issues) == 0

    def test_verify_uncited_claim_error(self):
        """Test that uncited claims trigger errors."""
        narrative = "There are 1234 employees."  # No citation

        qr = QueryResult(
            query_id="lmis_001",
            rows=[Row(data={}) for _ in range(1234)],
            unit="count",
            provenance=Provenance(
                source="csv",
                dataset_id="lmis_employees",
                locator="test.csv",
                fields=["count"],
            ),
            freshness=Freshness(asof_date="2024-01-01"),
        )

        tolerances = {
            "abs_epsilon": 0.5,
            "rel_epsilon": 0.01,
            "require_citation_first": True,
            "ignore_numbers_below": 1.0,
        }

        report = verify_numbers(narrative, [qr], tolerances)

        assert not report.ok
        assert len(report.issues) > 0
        assert any(i.code == "CLAIM_UNCITED" for i in report.issues)

    def test_verify_claim_not_found(self):
        """Test that unmatched claims trigger errors."""
        narrative = "Per LMIS: There are 9999 employees (QID:lmis_001)."

        qr = QueryResult(
            query_id="lmis_001",
            rows=[Row(data={}) for _ in range(1234)],  # Different value
            unit="count",
            provenance=Provenance(
                source="csv",
                dataset_id="lmis_employees",
                locator="test.csv",
                fields=["count"],
            ),
            freshness=Freshness(asof_date="2024-01-01"),
        )

        tolerances = {
            "abs_epsilon": 0.5,
            "rel_epsilon": 0.01,
            "prefer_query_id": True,
            "require_citation_first": True,
            "ignore_numbers_below": 1.0,
        }

        report = verify_numbers(narrative, [qr], tolerances)

        assert not report.ok
        assert len(report.issues) > 0
        assert any(i.code == "CLAIM_NOT_FOUND" for i in report.issues)

    def test_verify_with_math_checks(self):
        """Test verification with math consistency checks."""
        narrative = """
        Per LMIS: Employment breakdown (QID:lmis_001):
        - 45% in construction
        - 30% in services
        - 24% in manufacturing
        """
        # Sums to 99%, outside tolerance

        qr = QueryResult(
            query_id="lmis_001",
            rows=[Row(data={"sector": "test"})],
            unit="percent",
            provenance=Provenance(
                source="csv",
                dataset_id="lmis_sectors",
                locator="test.csv",
                fields=["sector"],
            ),
            freshness=Freshness(asof_date="2024-01-01"),
        )

        tolerances = {
            "abs_epsilon": 0.5,
            "rel_epsilon": 0.01,
            "epsilon_pct": 0.5,
            "sum_to_100": True,
            "prefer_query_id": True,
            "require_citation_first": True,
            "ignore_numbers_below": 1.0,
        }

        report = verify_numbers(narrative, [qr], tolerances)

        # Math check should fail
        assert not report.ok
        assert any(i.code == "MATH_INCONSISTENT" for i in report.issues)
        assert report.math_check_details

    def test_verify_ambiguous_sources_surface_warning(self):
        """Ambiguous sources without QID emit warning."""
        narrative = "Per LMIS: 2,500 workers joined."
        qr_a = QueryResult(
            query_id="lmis_a",
            rows=[Row(data={}) for _ in range(2500)],
            unit="count",
            provenance=Provenance(
                source="csv",
                dataset_id="a",
                locator="a.csv",
                fields=["count"],
            ),
            freshness=Freshness(asof_date="2024-01-01"),
        )
        qr_b = QueryResult(
            query_id="lmis_b",
            rows=[Row(data={}) for _ in range(2500)],
            unit="count",
            provenance=Provenance(
                source="csv",
                dataset_id="b",
                locator="b.csv",
                fields=["count"],
            ),
            freshness=Freshness(asof_date="2024-01-01"),
        )
        tolerances = {"abs_epsilon": 0.5, "rel_epsilon": 0.01, "require_citation_first": False}
        report = verify_numbers(narrative, [qr_a, qr_b], tolerances)

        assert any(issue.code == "AMBIGUOUS_SOURCE" for issue in report.issues)

    def test_verify_rounding_mismatch_hint_included(self):
        """Rounding mismatches include fix-it hints."""
        narrative = "Per LMIS: 1,000 jobs (QID:lmis_round)."
        qr = QueryResult(
            query_id="lmis_round",
            rows=[Row(data={"jobs": 1000.8})],
            unit="count",
            provenance=Provenance(
                source="csv",
                dataset_id="rounding",
                locator="round.csv",
                fields=["jobs"],
            ),
            freshness=Freshness(asof_date="2024-01-01"),
        )
        tolerances = {
            "abs_epsilon": 0.5,
            "rel_epsilon": 0.0,
            "prefer_query_id": True,
            "require_citation_first": True,
        }
        report = verify_numbers(narrative, [qr], tolerances)

        mismatch = next(i for i in report.issues if i.code == "ROUNDING_MISMATCH")
        assert "hint" in mismatch.details

    def test_verify_derived_share_inconsistency(self):
        """Derived share mismatch surfaces as error even if data matched."""
        narrative = "Per LMIS: Finance qatarization is 10% (QID:derived_qat)."
        qr = QueryResult(
            query_id="derived_qat",
            rows=[
                Row(
                    data={
                        "segment": "Finance",
                        "qataris": 200,
                        "non_qataris": 800,
                        "qatarization_percent": 10.0,
                    }
                )
            ],
            unit="percent",
            provenance=Provenance(
                source="csv",
                dataset_id="derived_qatarization",
                locator="derived.csv",
                fields=["segment", "qataris", "non_qataris", "qatarization_percent"],
            ),
            freshness=Freshness(asof_date="2024-01-01"),
        )
        tolerances = {
            "abs_epsilon": 0.5,
            "rel_epsilon": 0.01,
            "prefer_query_id": True,
            "require_citation_first": True,
            "derived_share_check_enabled": True,
        }
        report = verify_numbers(narrative, [qr], tolerances)

        issues = [i for i in report.issues if i.code == "ROUNDING_MISMATCH"]
        assert issues
        assert issues[0].severity == "error"

    def test_verify_runtime_budget_under_five_seconds(self):
        """Runtime metric recorded and within budget for large narratives."""
        base_sentence = "Per LMIS: Headcount is 1000 (QID:lmis_speed)."
        narrative = " ".join(base_sentence for _ in range(400))  # ~14k chars
        qr = QueryResult(
            query_id="lmis_speed",
            rows=[Row(data={}) for _ in range(1000)],
            unit="count",
            provenance=Provenance(
                source="csv",
                dataset_id="speed",
                locator="speed.csv",
                fields=["count"],
            ),
            freshness=Freshness(asof_date="2024-01-01"),
        )
        tolerances = {
            "abs_epsilon": 0.5,
            "rel_epsilon": 0.01,
            "prefer_query_id": True,
            "require_citation_first": True,
        }
        report = verify_numbers(narrative, [qr], tolerances)

        assert report.runtime_ms is not None
        assert report.runtime_ms < 5000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
