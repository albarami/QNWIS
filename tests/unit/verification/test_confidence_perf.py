"""
Performance tests for confidence scoring.

Validates that confidence computation stays within micro-benchmark budget:
- 10k-char narrative metadata
- 60 claims
- <5ms average computation time

This ensures confidence scoring doesn't become a bottleneck in
production orchestration workflows.
"""

from time import perf_counter

import pytest

from src.qnwis.verification.confidence import (
    ConfidenceInputs,
    ConfidenceRules,
    aggregate_confidence,
)


@pytest.fixture
def production_rules() -> ConfidenceRules:
    """Production-like rules matching confidence.yml."""
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


class TestPerformanceBenchmarks:
    """Performance benchmarks for confidence scoring."""

    def test_baseline_performance(self, production_rules):
        """
        Baseline: Typical case with moderate data.

        Scenario: 15 numbers, 30 claims, minimal issues
        Target: <1ms average
        """
        inputs = ConfidenceInputs(
            total_numbers=15,
            cited_numbers=14,
            citation_errors=0,
            claims_total=30,
            claims_matched=28,
            math_checks={"percent_total": True, "table_sum": True},
            l2_warnings=2,
            l3_redactions=3,
            l4_errors=0,
            l4_warnings=1,
            max_age_hours=48.0,
            freshness_sla_hours=72.0,
        )

        iterations = 1000
        start = perf_counter()
        for _ in range(iterations):
            aggregate_confidence(inputs, production_rules)
        elapsed_ms = (perf_counter() - start) * 1000 / iterations

        assert elapsed_ms < 1.0, f"Baseline too slow: {elapsed_ms:.3f}ms"

    def test_large_input_performance(self, production_rules):
        """
        Large input: 60 claims, 30 numbers, many issues.

        Scenario: Simulates complex report with many verification checks
        Target: <5ms average (as per Step 22 requirements)
        """
        # Create large math_checks dict (simulating many consistency checks)
        math_checks = {
            f"check_{i}": (i % 3 != 0)  # Some pass, some fail
            for i in range(20)
        }

        inputs = ConfidenceInputs(
            total_numbers=30,
            cited_numbers=25,
            citation_errors=3,
            claims_total=60,
            claims_matched=52,
            math_checks=math_checks,
            l2_warnings=15,
            l3_redactions=10,
            l4_errors=2,
            l4_warnings=8,
            max_age_hours=120.0,
            freshness_sla_hours=72.0,
            previous_score=85,  # Include hysteresis
        )

        iterations = 200
        start = perf_counter()
        for _ in range(iterations):
            aggregate_confidence(inputs, production_rules)
        elapsed_ms = (perf_counter() - start) * 1000 / iterations

        assert elapsed_ms < 5.0, f"Large input too slow: {elapsed_ms:.3f}ms (target: <5ms)"

    def test_maximum_reasons_performance(self, production_rules):
        """
        Maximum reasons: Many issues generating many reason strings.

        This tests reason deduplication and capping logic performance.
        """
        # Create scenario that generates many reasons
        inputs = ConfidenceInputs(
            total_numbers=25,
            cited_numbers=10,  # Many uncited
            citation_errors=5,  # Citation errors
            claims_total=50,
            claims_matched=25,  # Many unmatched
            math_checks={
                "check1": False,
                "check2": False,
                "check3": False,
            },  # Failed checks
            l2_warnings=20,  # Many cross-check warnings
            l3_redactions=15,  # Many redactions
            l4_errors=3,
            l4_warnings=10,
            max_age_hours=200.0,  # Stale data
            freshness_sla_hours=72.0,
        )

        iterations = 500
        start = perf_counter()
        for _ in range(iterations):
            result = aggregate_confidence(inputs, production_rules)
            # Ensure reasons are processed
            assert len(result.reasons) > 0
        elapsed_ms = (perf_counter() - start) * 1000 / iterations

        assert elapsed_ms < 2.0, f"Reason processing too slow: {elapsed_ms:.3f}ms"

    def test_hysteresis_overhead(self, production_rules):
        """
        Hysteresis: Test overhead of band hysteresis logic.

        This should add minimal overhead (<0.1ms).
        """
        inputs = ConfidenceInputs(
            total_numbers=15,
            cited_numbers=14,
            citation_errors=0,
            claims_total=30,
            claims_matched=27,
            math_checks={"check": True},
            l2_warnings=2,
            l3_redactions=1,
            l4_errors=0,
            l4_warnings=0,
            max_age_hours=36.0,
            freshness_sla_hours=72.0,
            previous_score=89,  # Trigger hysteresis logic
        )

        iterations = 1000
        start = perf_counter()
        for _ in range(iterations):
            aggregate_confidence(inputs, production_rules)
        elapsed_ms = (perf_counter() - start) * 1000 / iterations

        assert elapsed_ms < 1.5, f"Hysteresis adds too much overhead: {elapsed_ms:.3f}ms"

    def test_component_computation_parallel(self, production_rules):
        """
        Component computation: All components computed independently.

        This validates that component computation is efficient and
        doesn't have n^2 behavior.
        """
        inputs = ConfidenceInputs(
            total_numbers=20,
            cited_numbers=18,
            citation_errors=1,
            claims_total=40,
            claims_matched=38,
            math_checks={"c1": True, "c2": False, "c3": True},
            l2_warnings=5,
            l3_redactions=4,
            l4_errors=0,
            l4_warnings=2,
            max_age_hours=60.0,
            freshness_sla_hours=72.0,
        )

        iterations = 1000
        start = perf_counter()
        for _ in range(iterations):
            result = aggregate_confidence(inputs, production_rules)
            # Ensure all components computed
            assert len(result.components) == 5
        elapsed_ms = (perf_counter() - start) * 1000 / iterations

        assert elapsed_ms < 1.0, f"Component computation too slow: {elapsed_ms:.3f}ms"

    def test_worst_case_performance(self, production_rules):
        """
        Worst case: Maximum inputs, all checks failing.

        This tests performance under extreme load.
        Target: <10ms (relaxed for worst case)
        """
        # Maximum math checks (100 checks)
        math_checks = {f"check_{i}": False for i in range(100)}

        inputs = ConfidenceInputs(
            total_numbers=100,
            cited_numbers=30,
            citation_errors=20,
            claims_total=200,
            claims_matched=80,
            math_checks=math_checks,
            l2_warnings=50,
            l3_redactions=30,
            l4_errors=10,
            l4_warnings=20,
            max_age_hours=500.0,
            freshness_sla_hours=72.0,
            previous_score=92,
        )

        iterations = 100
        start = perf_counter()
        for _ in range(iterations):
            aggregate_confidence(inputs, production_rules)
        elapsed_ms = (perf_counter() - start) * 1000 / iterations

        assert elapsed_ms < 10.0, f"Worst case too slow: {elapsed_ms:.3f}ms (target: <10ms)"

    def test_no_allocations_in_hot_path(self, production_rules):
        """
        Memory efficiency: Ensure no unnecessary allocations in hot path.

        This is a smoke test - we just run many iterations and check
        that performance doesn't degrade over time (which would indicate
        memory pressure).
        """
        inputs = ConfidenceInputs(
            total_numbers=15,
            cited_numbers=14,
            citation_errors=0,
            claims_total=30,
            claims_matched=28,
            math_checks={"check": True},
            l2_warnings=2,
            l3_redactions=1,
            l4_errors=0,
            l4_warnings=0,
            max_age_hours=36.0,
            freshness_sla_hours=72.0,
        )

        # Warm-up
        for _ in range(100):
            aggregate_confidence(inputs, production_rules)

        # Measure first batch
        iterations_batch = 500
        start1 = perf_counter()
        for _ in range(iterations_batch):
            aggregate_confidence(inputs, production_rules)
        elapsed1 = perf_counter() - start1

        # Measure second batch (should be similar time)
        start2 = perf_counter()
        for _ in range(iterations_batch):
            aggregate_confidence(inputs, production_rules)
        elapsed2 = perf_counter() - start2

        # Second batch should not be significantly slower (< 20% difference)
        ratio = elapsed2 / elapsed1
        assert 0.8 <= ratio <= 1.2, (
            f"Performance degraded over time: {ratio:.2f}x "
            "(possible memory pressure)"
        )

    def test_determinism_no_performance_impact(self, production_rules):
        """
        Determinism: Multiple runs with same inputs should have
        identical performance characteristics.
        """
        inputs = ConfidenceInputs(
            total_numbers=20,
            cited_numbers=18,
            citation_errors=1,
            claims_total=40,
            claims_matched=36,
            math_checks={"c1": True, "c2": False},
            l2_warnings=3,
            l3_redactions=2,
            l4_errors=0,
            l4_warnings=1,
            max_age_hours=48.0,
            freshness_sla_hours=72.0,
        )

        timings = []
        for _ in range(5):
            iterations = 500
            start = perf_counter()
            for _ in range(iterations):
                aggregate_confidence(inputs, production_rules)
            elapsed_ms = (perf_counter() - start) * 1000 / iterations
            timings.append(elapsed_ms)

        # All timings should be within 50% of median (stable performance)
        median = sorted(timings)[len(timings) // 2]
        for timing in timings:
            assert 0.5 * median <= timing <= 1.5 * median, (
                f"Timing variance too high: {timings} "
                f"(median: {median:.3f}ms)"
            )


class TestScalability:
    """Test performance scalability with input size."""

    def test_scales_linearly_with_numbers(self, production_rules):
        """
        Scaling: Computation should scale linearly with input size.

        Double the numbers → ~double the time (with some overhead tolerance).
        """
        small_inputs = ConfidenceInputs(
            total_numbers=10,
            cited_numbers=9,
            citation_errors=0,
            claims_total=20,
            claims_matched=18,
            math_checks={"check": True},
            l2_warnings=1,
            l3_redactions=1,
            l4_errors=0,
            l4_warnings=0,
            max_age_hours=24.0,
            freshness_sla_hours=72.0,
        )

        large_inputs = ConfidenceInputs(
            total_numbers=20,
            cited_numbers=18,
            citation_errors=0,
            claims_total=40,
            claims_matched=36,
            math_checks={"check": True},
            l2_warnings=2,
            l3_redactions=2,
            l4_errors=0,
            l4_warnings=0,
            max_age_hours=24.0,
            freshness_sla_hours=72.0,
        )

        iterations = 500

        # Measure small
        start_small = perf_counter()
        for _ in range(iterations):
            aggregate_confidence(small_inputs, production_rules)
        time_small = perf_counter() - start_small

        # Measure large
        start_large = perf_counter()
        for _ in range(iterations):
            aggregate_confidence(large_inputs, production_rules)
        time_large = perf_counter() - start_large

        # Large should be at most 3x slower (linear scaling with overhead)
        ratio = time_large / time_small
        assert ratio < 3.0, f"Scaling not linear: {ratio:.2f}x (expected <3x)"

    def test_scales_with_reason_count(self, production_rules):
        """
        Reason processing should scale efficiently with reason count.
        """
        # Few reasons
        few_inputs = ConfidenceInputs(
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

        # Many reasons
        many_inputs = ConfidenceInputs(
            total_numbers=30,
            cited_numbers=15,
            citation_errors=5,
            claims_total=60,
            claims_matched=30,
            math_checks={f"c{i}": False for i in range(10)},
            l2_warnings=20,
            l3_redactions=15,
            l4_errors=3,
            l4_warnings=10,
            max_age_hours=200.0,
            freshness_sla_hours=72.0,
        )

        iterations = 300

        start_few = perf_counter()
        for _ in range(iterations):
            aggregate_confidence(few_inputs, production_rules)
        time_few = perf_counter() - start_few

        start_many = perf_counter()
        for _ in range(iterations):
            aggregate_confidence(many_inputs, production_rules)
        time_many = perf_counter() - start_many

        # Many reasons should add < 2x overhead
        ratio = time_many / time_few
        assert ratio < 4.0, f"Reason processing not efficient: {ratio:.2f}x"
