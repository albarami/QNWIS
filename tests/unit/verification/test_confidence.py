"""
Unit tests for confidence scoring engine.

Tests cover:
- Component score computation (citation, numbers, cross, privacy, freshness)
- Aggregation logic with weighted averaging
- Edge cases (zero values, insufficient evidence, extreme penalties)
- Configuration validation (weight sum)
- Determinism and monotonicity properties
- Stability guards (small-n smoothing, hysteresis, penalty caps)
- Performance budget (<5ms per computation)
"""

from dataclasses import replace
from time import perf_counter

import pytest

from src.qnwis.verification.confidence import (
    ConfidenceInputs,
    ConfidenceRules,
    aggregate_confidence,
    compute_component_citation,
    compute_component_cross,
    compute_component_freshness,
    compute_component_numbers,
    compute_component_privacy,
)

PENALTY_CAP = 0.5
SMALL_SAMPLE_THRESHOLD = 3


@pytest.fixture
def default_rules() -> ConfidenceRules:
    """Default scoring rules mirroring config."""
    return ConfidenceRules(
        w_citation=0.25,
        w_numbers=0.40,
        w_cross=0.10,
        w_privacy=0.10,
        w_freshness=0.15,
        penalty_math_fail=15.0,
        penalty_l2_per_item=3.0,
        penalty_redaction_per_item=1.0,
        penalty_freshness_per_10h=2.0,
        min_score_on_insufficient=60,
        bands={"GREEN": 90, "AMBER": 75, "RED": 0},
        penalty_cap_fraction=0.5,
        max_reason_count=8,
        enable_hysteresis=True,
        hysteresis_tolerance=4,
        min_support_numbers=3,
        min_support_claims=3,
    )


class TestComponentCitation:
    """Test citation component scoring."""

    def test_perfect_citation_coverage(self):
        """All numbers cited, no errors → 100."""
        score, reasons = compute_component_citation(
            total_numbers=10,
            cited_numbers=10,
            errors=0,
            small_sample_threshold=SMALL_SAMPLE_THRESHOLD,
            max_penalty_fraction=PENALTY_CAP,
        )
        assert score == 100.0
        assert "All 10 claims properly cited" in reasons

    def test_partial_citation_coverage(self):
        """50% cited, no errors → 50."""
        score, reasons = compute_component_citation(
            total_numbers=10,
            cited_numbers=5,
            errors=0,
            small_sample_threshold=SMALL_SAMPLE_THRESHOLD,
            max_penalty_fraction=PENALTY_CAP,
        )
        assert score == 50.0
        assert "Uncited claims: 5/10" in reasons

    def test_citation_with_errors(self):
        """Errors force strong penalty."""
        score, reasons = compute_component_citation(
            total_numbers=10,
            cited_numbers=10,
            errors=3,
            small_sample_threshold=SMALL_SAMPLE_THRESHOLD,
            max_penalty_fraction=PENALTY_CAP,
        )
        assert score == 50.0  # Penalty capped at 50% of component
        assert "Citation errors detected: 3 (-50.0)" in reasons

    def test_no_numbers(self):
        """No numbers → 100 (perfect score for empty set)."""
        score, reasons = compute_component_citation(
            total_numbers=0,
            cited_numbers=0,
            errors=0,
            small_sample_threshold=SMALL_SAMPLE_THRESHOLD,
            max_penalty_fraction=PENALTY_CAP,
        )
        assert score == 100.0
        assert "No numeric claims detected" in reasons

    def test_small_sample_guard(self):
        """Single number guard blends toward neutral score."""
        score, reasons = compute_component_citation(
            total_numbers=1,
            cited_numbers=0,
            errors=0,
            small_sample_threshold=SMALL_SAMPLE_THRESHOLD,
            max_penalty_fraction=PENALTY_CAP,
        )
        assert score > 60.0  # Guard softens otherwise 0 score
        assert any("Small sample guard" in reason for reason in reasons)


class TestComponentNumbers:
    """Test numbers/result verification component scoring."""

    def test_all_claims_matched(self):
        """All claims match source data → 100."""
        score, reasons = compute_component_numbers(
            claims_total=20,
            claims_matched=20,
            math_checks={"percent_total": True, "table_sum": True},
            penalty_math_fail=15.0,
            small_sample_threshold=SMALL_SAMPLE_THRESHOLD,
            max_penalty_fraction=PENALTY_CAP,
        )
        assert score == 100.0
        assert "All 20 claims verified" in reasons

    def test_partial_claims_matched(self):
        """50% matched → 50."""
        score, reasons = compute_component_numbers(
            claims_total=20,
            claims_matched=10,
            math_checks={},
            penalty_math_fail=15.0,
            small_sample_threshold=SMALL_SAMPLE_THRESHOLD,
            max_penalty_fraction=PENALTY_CAP,
        )
        assert score == 50.0
        assert "Unmatched claims: 10/20" in reasons

    def test_math_check_failure(self):
        """Failed math check applies penalty."""
        score, reasons = compute_component_numbers(
            claims_total=20,
            claims_matched=20,
            math_checks={"percent_total": False},
            penalty_math_fail=15.0,
            small_sample_threshold=SMALL_SAMPLE_THRESHOLD,
            max_penalty_fraction=PENALTY_CAP,
        )
        assert score == 85.0  # 100 - 15
        assert "Math checks failed (1): percent_total (-15.0)" in reasons

    def test_no_claims(self):
        """No claims → 100."""
        score, reasons = compute_component_numbers(
            claims_total=0,
            claims_matched=0,
            math_checks={},
            penalty_math_fail=15.0,
            small_sample_threshold=SMALL_SAMPLE_THRESHOLD,
            max_penalty_fraction=PENALTY_CAP,
        )
        assert score == 100.0
        assert "No claims to verify" in reasons

    def test_small_sample_guard(self):
        """Guard dampens penalty when very few claims exist."""
        score, reasons = compute_component_numbers(
            claims_total=1,
            claims_matched=0,
            math_checks={},
            penalty_math_fail=15.0,
            small_sample_threshold=SMALL_SAMPLE_THRESHOLD,
            max_penalty_fraction=PENALTY_CAP,
        )
        assert score > 0.0  # Would be 0 without guard
        assert any("Small sample guard" in reason for reason in reasons)


class TestComponentCross:
    """Test cross-source validation component scoring."""

    def test_no_warnings(self):
        """No cross-check warnings -> 100."""
        score, reasons = compute_component_cross(
            l2_warnings=0,
            penalty_per_item=3.0,
            max_penalty_fraction=PENALTY_CAP,
        )
        assert score == 100.0
        assert "No cross-source discrepancies" in reasons

    def test_multiple_warnings(self):
        """Five warnings apply deductions."""
        score, reasons = compute_component_cross(
            l2_warnings=5,
            penalty_per_item=3.0,
            max_penalty_fraction=PENALTY_CAP,
        )
        assert score == 85.0
        assert "Cross-check warnings: 5 (-15.0)" in reasons

    def test_penalty_cap(self):
        """Large penalty cannot remove more than 50%."""
        score, _ = compute_component_cross(
            l2_warnings=500,
            penalty_per_item=10.0,
            max_penalty_fraction=PENALTY_CAP,
        )
        assert score >= 50.0


class TestComponentPrivacy:
    """Test privacy component scoring."""

    def test_no_redactions(self):
        """No PII -> 100."""
        score, reasons = compute_component_privacy(
            redactions=0,
            penalty_per_item=1.0,
            max_penalty_fraction=PENALTY_CAP,
        )
        assert score == 100.0
        assert "No PII detected" in reasons

    def test_redactions_penalized(self):
        """Many redactions reduce score."""
        score, reasons = compute_component_privacy(
            redactions=10,
            penalty_per_item=1.0,
            max_penalty_fraction=PENALTY_CAP,
        )
        assert score == 90.0
        assert "PII redactions applied: 10 (-10.0)" in reasons


class TestComponentFreshness:
    """Test freshness component scoring."""

    def test_within_sla(self):
        """Data within SLA stays 100."""
        score, reasons = compute_component_freshness(
            max_age_hours=48.0,
            sla_hours=72.0,
            penalty_per_10h=2.0,
            max_penalty_fraction=PENALTY_CAP,
        )
        assert score == 100.0
        assert "Data age within SLA: 48.0h" in reasons

    def test_freshness_penalty(self):
        """Stale data taxed per bucket."""
        score, reasons = compute_component_freshness(
            max_age_hours=120.0,
            sla_hours=72.0,
            penalty_per_10h=2.0,
            max_penalty_fraction=PENALTY_CAP,
        )
        assert score == pytest.approx(90.4)
        assert "exceeds SLA" in " ".join(reasons)

    def test_very_stale_data(self):
        """Very stale data stays non-negative due to clamp."""
        score, _ = compute_component_freshness(
            max_age_hours=500.0,
            sla_hours=72.0,
            penalty_per_10h=2.0,
            max_penalty_fraction=PENALTY_CAP,
        )
        assert score >= 0.0


class TestAggregation:
    """Test weighted aggregation of component scores."""

    def test_all_perfect(self, default_rules):
        """All components perfect → 100, GREEN."""
        inputs = ConfidenceInputs(
            total_numbers=10,
            cited_numbers=10,
            citation_errors=0,
            claims_total=20,
            claims_matched=20,
            math_checks={"percent_total": True},
            l2_warnings=0,
            l3_redactions=0,
            l4_errors=0,
            l4_warnings=0,
            max_age_hours=24.0,
            freshness_sla_hours=72.0,
        )

        result = aggregate_confidence(inputs, default_rules)

        assert result.score == 100
        assert result.band == "GREEN"
        assert all(v == 100.0 for v in result.components.values())

    def test_insufficient_evidence(self, default_rules):
        """No numbers and no claims → floor score."""
        inputs = ConfidenceInputs(
            total_numbers=0,
            cited_numbers=0,
            citation_errors=0,
            claims_total=0,
            claims_matched=0,
            math_checks={},
            l2_warnings=0,
            l3_redactions=0,
            l4_errors=0,
            l4_warnings=0,
            max_age_hours=0.0,
            freshness_sla_hours=72.0,
        )

        result = aggregate_confidence(inputs, default_rules)

        assert result.score == 60
        assert result.band == "RED"
        assert any("Insufficient evidence" in r for r in result.reasons)

    def test_weighted_average(self, default_rules):
        """Weighted averaging produces expected score."""
        inputs = ConfidenceInputs(
            total_numbers=10,
            cited_numbers=5,  # 50% → citation = 50
            citation_errors=0,
            claims_total=20,
            claims_matched=10,  # 50% → numbers = 50
            math_checks={},
            l2_warnings=0,  # cross = 100
            l3_redactions=0,  # privacy = 100
            l4_errors=0,
            l4_warnings=0,
            max_age_hours=24.0,  # freshness = 100
            freshness_sla_hours=72.0,
        )

        result = aggregate_confidence(inputs, default_rules)

        # Expected: 0.25*50 + 0.40*50 + 0.10*100 + 0.10*100 + 0.15*100
        #         = 12.5 + 20 + 10 + 10 + 15 = 67.5 → 68 (rounded)
        assert result.score == 68
        assert result.band == "RED"

    def test_band_thresholds(self, default_rules):
        """Scores map to correct bands."""
        # GREEN threshold
        inputs_green = ConfidenceInputs(
            total_numbers=10,
            cited_numbers=10,
            citation_errors=0,
            claims_total=20,
            claims_matched=19,  # 95% → very high
            math_checks={},
            l2_warnings=0,
            l3_redactions=0,
            l4_errors=0,
            l4_warnings=0,
            max_age_hours=24.0,
            freshness_sla_hours=72.0,
        )

        result_green = aggregate_confidence(inputs_green, default_rules)
        assert result_green.score >= 90
        assert result_green.band == "GREEN"

        # AMBER threshold
        inputs_amber = ConfidenceInputs(
            total_numbers=10,
            cited_numbers=10,
            citation_errors=0,
            claims_total=20,
            claims_matched=15,  # 75% → medium
            math_checks={},
            l2_warnings=5,
            l3_redactions=5,
            l4_errors=0,
            l4_warnings=0,
            max_age_hours=24.0,
            freshness_sla_hours=72.0,
        )

        result_amber = aggregate_confidence(inputs_amber, default_rules)
        assert 75 <= result_amber.score < 90
        assert result_amber.band == "AMBER"

    def test_determinism(self, default_rules):
        """Same inputs produce same score every time."""
        inputs = ConfidenceInputs(
            total_numbers=10,
            cited_numbers=8,
            citation_errors=1,
            claims_total=20,
            claims_matched=16,
            math_checks={"check1": True, "check2": False},
            l2_warnings=2,
            l3_redactions=3,
            l4_errors=0,
            l4_warnings=1,
            max_age_hours=80.0,
            freshness_sla_hours=72.0,
        )

        result1 = aggregate_confidence(inputs, default_rules)
        result2 = aggregate_confidence(inputs, default_rules)

        assert result1.score == result2.score
        assert result1.band == result2.band
        assert result1.components == result2.components
        assert result1.reasons == result2.reasons

    def test_weights_validation(self):
        """Invalid weights raise ValueError."""
        bad_rules = ConfidenceRules(
            w_citation=0.25,
            w_numbers=0.40,
            w_cross=0.10,
            w_privacy=0.10,
            w_freshness=0.10,  # Sum = 0.95 (invalid)
            penalty_math_fail=15.0,
            penalty_l2_per_item=3.0,
            penalty_redaction_per_item=1.0,
            penalty_freshness_per_10h=2.0,
            min_score_on_insufficient=60,
            bands={"GREEN": 90, "AMBER": 75, "RED": 0},
            penalty_cap_fraction=0.5,
            max_reason_count=8,
            enable_hysteresis=True,
            hysteresis_tolerance=4,
            min_support_numbers=3,
            min_support_claims=3,
        )

        inputs = ConfidenceInputs()

        with pytest.raises(ValueError, match="Weights must sum to 1.0"):
            aggregate_confidence(inputs, bad_rules)

    def test_reasons_deduplicated(self, default_rules):
        """Reasons are unique and sorted."""
        inputs = ConfidenceInputs(
            total_numbers=10,
            cited_numbers=10,
            citation_errors=0,
            claims_total=20,
            claims_matched=20,
            math_checks={},
            l2_warnings=0,
            l3_redactions=0,
            l4_errors=0,
            l4_warnings=0,
            max_age_hours=24.0,
            freshness_sla_hours=72.0,
        )

        result = aggregate_confidence(inputs, default_rules)

        # Reasons should be unique
        assert len(result.reasons) == len(set(result.reasons))
        # Reasons should be sorted
        assert result.reasons == sorted(result.reasons)

    def test_reason_cap_enforced(self, default_rules):
        """Reason list is capped and summarizes overflow."""
        noisy_rules = replace(default_rules, max_reason_count=2)
        inputs = ConfidenceInputs(
            total_numbers=10,
            cited_numbers=2,
            citation_errors=4,
            claims_total=10,
            claims_matched=5,
            math_checks={"sum": False},
            l2_warnings=10,
            l3_redactions=10,
            l4_errors=0,
            l4_warnings=0,
            max_age_hours=200.0,
            freshness_sla_hours=72.0,
        )

        result = aggregate_confidence(inputs, noisy_rules)

        assert len(result.reasons) == 2
        assert result.reasons[-1].startswith("...")

    def test_band_hysteresis_respects_previous_score(self, default_rules):
        """Band stays stable when delta below hysteresis tolerance."""
        hysteresis_rules = replace(default_rules, hysteresis_tolerance=5, enable_hysteresis=True)
        inputs = ConfidenceInputs(
            total_numbers=10,
            cited_numbers=9,  # Slightly reduced coverage
            citation_errors=0,
            claims_total=20,
            claims_matched=18,
            math_checks={},
            l2_warnings=2,
            l3_redactions=2,
            l4_errors=0,
            l4_warnings=0,
            max_age_hours=24.0,
            freshness_sla_hours=72.0,
            previous_score=89,
        )

        result = aggregate_confidence(inputs, hysteresis_rules)
        assert result.band == "AMBER"  # Remains previous band
        assert any("Band hysteresis applied" in reason for reason in result.reasons)

    def test_dashboard_payload_exposes_metrics(self, default_rules):
        """Dashboard payload mirrors core metrics."""
        inputs = ConfidenceInputs(
            total_numbers=8,
            cited_numbers=6,
            citation_errors=0,
            claims_total=8,
            claims_matched=7,
            math_checks={},
            l2_warnings=1,
            l3_redactions=2,
            l4_errors=0,
            l4_warnings=0,
            max_age_hours=36.0,
            freshness_sla_hours=72.0,
        )

        result = aggregate_confidence(inputs, default_rules)

        payload = result.dashboard_payload
        assert payload["score"] == result.score
        assert payload["band"] == result.band
        assert pytest.approx(payload["coverage"], rel=1e-3) == result.coverage
        assert pytest.approx(payload["freshness"], rel=1e-3) == result.freshness


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_extreme_penalties_floor_at_zero(self, default_rules):
        """Excessive penalties floor component scores at 0."""
        inputs = ConfidenceInputs(
            total_numbers=10,
            cited_numbers=0,
            citation_errors=10,  # Heavy penalty
            claims_total=20,
            claims_matched=0,
            math_checks={"c1": False, "c2": False},
            l2_warnings=100,  # Excessive
            l3_redactions=200,
            l4_errors=0,
            l4_warnings=0,
            max_age_hours=1000.0,  # Very stale
            freshness_sla_hours=72.0,
        )

        result = aggregate_confidence(inputs, default_rules)

        # Score should be low but not negative
        assert 0 <= result.score <= 100
        assert result.band == "RED"

    def test_zero_everything(self, default_rules):
        """All zeros → insufficient evidence floor."""
        inputs = ConfidenceInputs()  # All defaults (zeros)

        result = aggregate_confidence(inputs, default_rules)

        assert result.score == 60  # Floor for insufficient evidence
        assert result.band == "RED"

    def test_rounding_consistency(self, default_rules):
        """Score always rounded to nearest integer."""
        # Create inputs that yield fractional score
        inputs = ConfidenceInputs(
            total_numbers=3,
            cited_numbers=2,  # 66.67%
            citation_errors=0,
            claims_total=3,
            claims_matched=2,  # 66.67%
            math_checks={},
            l2_warnings=0,
            l3_redactions=0,
            l4_errors=0,
            l4_warnings=0,
            max_age_hours=24.0,
            freshness_sla_hours=72.0,
        )

        result = aggregate_confidence(inputs, default_rules)

        # Score must be integer
        assert isinstance(result.score, int)
        assert 0 <= result.score <= 100


class TestMonotonicity:
    """Test that better inputs never decrease score."""

    def test_more_citations_never_decrease(self, default_rules):
        """Increasing cited_numbers should not decrease score."""
        base = ConfidenceInputs(
            total_numbers=10,
            cited_numbers=5,
            citation_errors=0,
            claims_total=20,
            claims_matched=20,
            math_checks={},
            l2_warnings=0,
            l3_redactions=0,
            l4_errors=0,
            l4_warnings=0,
            max_age_hours=24.0,
            freshness_sla_hours=72.0,
        )

        better = ConfidenceInputs(
            total_numbers=10,
            cited_numbers=8,  # More cited
            citation_errors=0,
            claims_total=20,
            claims_matched=20,
            math_checks={},
            l2_warnings=0,
            l3_redactions=0,
            l4_errors=0,
            l4_warnings=0,
            max_age_hours=24.0,
            freshness_sla_hours=72.0,
        )

        score_base = aggregate_confidence(base, default_rules).score
        score_better = aggregate_confidence(better, default_rules).score

        assert score_better >= score_base

    def test_fresher_data_never_decrease(self, default_rules):
        """Fresher data should not decrease score."""
        base = ConfidenceInputs(
            total_numbers=10,
            cited_numbers=10,
            citation_errors=0,
            claims_total=20,
            claims_matched=20,
            math_checks={},
            l2_warnings=0,
            l3_redactions=0,
            l4_errors=0,
            l4_warnings=0,
            max_age_hours=100.0,
            freshness_sla_hours=72.0,
        )

        better = ConfidenceInputs(
            total_numbers=10,
            cited_numbers=10,
            citation_errors=0,
            claims_total=20,
            claims_matched=20,
            math_checks={},
            l2_warnings=0,
            l3_redactions=0,
            l4_errors=0,
            l4_warnings=0,
            max_age_hours=50.0,  # Fresher
            freshness_sla_hours=72.0,
        )

        score_base = aggregate_confidence(base, default_rules).score
        score_better = aggregate_confidence(better, default_rules).score

        assert score_better >= score_base

    def test_more_verified_claims_increase(self, default_rules):
        """Improved claim matching should not reduce score."""
        base = ConfidenceInputs(
            total_numbers=10,
            cited_numbers=10,
            citation_errors=0,
            claims_total=20,
            claims_matched=10,
            math_checks={"totals": True},
            l2_warnings=0,
            l3_redactions=0,
            l4_errors=0,
            l4_warnings=0,
            max_age_hours=24.0,
            freshness_sla_hours=72.0,
        )

        better = replace(base, claims_matched=20)

        base_score = aggregate_confidence(base, default_rules).score
        better_score = aggregate_confidence(better, default_rules).score
        assert better_score >= base_score

    def test_fewer_cross_warnings_increase(self, default_rules):
        """Reducing Layer 2 warnings should not reduce score."""
        base = ConfidenceInputs(
            total_numbers=10,
            cited_numbers=10,
            citation_errors=0,
            claims_total=20,
            claims_matched=20,
            math_checks={},
            l2_warnings=10,
            l3_redactions=0,
            l4_errors=0,
            l4_warnings=0,
            max_age_hours=24.0,
            freshness_sla_hours=72.0,
        )

        better = replace(base, l2_warnings=0)

        base_score = aggregate_confidence(base, default_rules).score
        better_score = aggregate_confidence(better, default_rules).score
        assert better_score >= base_score


class TestPerformance:
    """Ensure confidence computation stays within micro-benchmark budget."""

    def test_micro_benchmark(self, default_rules):
        """Average runtime per call must stay below 5ms."""
        inputs = ConfidenceInputs(
            total_numbers=12,
            cited_numbers=11,
            citation_errors=0,
            claims_total=18,
            claims_matched=17,
            math_checks={"totals": True},
            l2_warnings=1,
            l3_redactions=1,
            l4_errors=0,
            l4_warnings=0,
            max_age_hours=36.0,
            freshness_sla_hours=72.0,
        )

        iterations = 400
        start = perf_counter()
        for _ in range(iterations):
            aggregate_confidence(inputs, default_rules)
        elapsed_ms = (perf_counter() - start) * 1000 / iterations

        assert elapsed_ms < 5.0, f"Average runtime too slow: {elapsed_ms:.2f}ms"
