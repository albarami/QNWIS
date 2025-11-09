"""
Integration tests for Scenario Planner end-to-end flow.

Tests the full pipeline:
Router → ScenarioAgent → Verification → Formatting → Audit
"""

import pytest

from src.qnwis.agents.scenario_agent import ScenarioAgent
from src.qnwis.data.deterministic.models import (
    Freshness,
    Provenance,
    QueryResult,
    Row,
)
from src.qnwis.scenario.dsl import ScenarioSpec, Transform

STATIC_UPDATED_AT = "2024-12-31T00:00:00Z"


class MockDataClient:
    """Mock DataClient with realistic baseline forecasts."""

    def run(self, query_id: str):
        """Return mock baseline forecast."""
        # Generate 12 months of baseline data
        values = [100.0 + i * 2 for i in range(12)]
        rows = [
            Row(data={"yhat": v, "h": i + 1, "lo": v - 5, "hi": v + 5})
            for i, v in enumerate(values)
        ]

        return QueryResult(
            query_id=query_id,
            rows=rows,
            unit="count",
            provenance=Provenance(
                source="csv",
                dataset_id="test_baseline",
                locator="test",
                fields=["yhat", "h", "lo", "hi"],
                license="Test",
            ),
            freshness=Freshness(
                asof_date="2024-12-31",
                updated_at=STATIC_UPDATED_AT,
            ),
            warnings=[],
        )


class TestScenarioEndToEnd:
    """Test complete scenario flow."""

    def test_apply_scenario_full_pipeline(self):
        """Test scenario application through full pipeline."""
        client = MockDataClient()
        agent = ScenarioAgent(client)

        # Create scenario spec
        spec = ScenarioSpec(
            name="Retention Improvement",
            description="10% retention boost across forecast horizon",
            metric="retention",
            sector="Construction",
            horizon_months=12,
            transforms=[
                Transform(type="multiplicative", value=0.10, start_month=0)
            ],
        )

        # Apply scenario with baseline override
        baseline = client.run("forecast_baseline_retention_construction_12m")
        narrative = agent.apply(spec, baseline_override=baseline)

        # Verify narrative structure
        assert isinstance(narrative, str)
        assert "Retention Improvement" in narrative
        assert "Executive Summary" in narrative
        assert "Scenario Forecast" in narrative
        assert "QID=" in narrative
        assert "Transform Details" in narrative
        assert "Data Sources" in narrative
        assert "Reproducibility" in narrative

        # Verify citations present
        assert narrative.count("QID=") >= 2  # At least baseline + derived

    def test_compare_scenarios_full_pipeline(self):
        """Test scenario comparison through full pipeline."""
        client = MockDataClient()
        agent = ScenarioAgent(client)

        # Create multiple scenarios
        optimistic = ScenarioSpec(
            name="Optimistic",
            description="20% improvement",
            metric="retention",
            horizon_months=12,
            transforms=[
                Transform(type="multiplicative", value=0.20, start_month=0)
            ],
        )

        pessimistic = ScenarioSpec(
            name="Pessimistic",
            description="5% improvement",
            metric="retention",
            horizon_months=12,
            transforms=[
                Transform(type="multiplicative", value=0.05, start_month=0)
            ],
        )

        # Compare with baseline override
        baseline = client.run("forecast_baseline_retention_all_12m")
        narrative = agent.compare(
            [optimistic, pessimistic],
            spec_format="dict",
            baseline_override=baseline,
        )

        # Verify comparison structure
        assert isinstance(narrative, str)
        assert "Scenario Comparison" in narrative
        assert "Optimistic" in narrative
        assert "Pessimistic" in narrative
        assert "Comparison Table" in narrative
        assert narrative.count("QID=") >= 3  # Baseline + 2 scenarios

    def test_batch_scenarios_full_pipeline(self):
        """Test batch scenario processing through full pipeline."""
        client = MockDataClient()
        agent = ScenarioAgent(client)

        # Create sector scenarios
        construction = ScenarioSpec(
            name="Construction Plan",
            description="Construction sector intervention",
            metric="retention",
            sector="Construction",
            horizon_months=12,
            transforms=[
                Transform(type="multiplicative", value=0.10, start_month=0)
            ],
        )

        healthcare = ScenarioSpec(
            name="Healthcare Plan",
            description="Healthcare sector intervention",
            metric="retention",
            sector="Healthcare",
            horizon_months=12,
            transforms=[
                Transform(type="multiplicative", value=0.15, start_month=0)
            ],
        )

        sector_specs = {
            "Construction": construction,
            "Healthcare": healthcare,
        }

        weights = {"Construction": 0.6, "Healthcare": 0.4}

        # Process batch
        narrative = agent.batch(
            sector_specs,
            spec_format="dict",
            sector_weights=weights,
        )

        # Verify batch structure
        assert isinstance(narrative, str)
        assert "Batch Scenario Processing" in narrative
        assert "Construction" in narrative
        assert "Healthcare" in narrative
        assert "National Aggregation" in narrative
        assert "Weights" in narrative
        assert narrative.count("QID=") >= 3  # Multiple sector + national

    def test_scenario_with_clamping(self):
        """Test scenario with min/max clamping."""
        client = MockDataClient()
        agent = ScenarioAgent(client)

        spec = ScenarioSpec(
            name="Clamped Scenario",
            description="Test clamping",
            metric="retention",
            horizon_months=12,
            transforms=[
                Transform(type="multiplicative", value=0.50, start_month=0)
            ],
            clamp_min=100.0,
            clamp_max=150.0,
        )

        baseline = client.run("forecast_baseline_retention_all_12m")
        narrative = agent.apply(spec, baseline_override=baseline)

        assert "Clamped Scenario" in narrative
        assert "Scenario Forecast" in narrative

    def test_scenario_with_stability_warning(self):
        """Test scenario that triggers stability warning."""
        from src.qnwis.data.deterministic.models import (
            Freshness,
            Provenance,
            QueryResult,
            Row,
        )

        # Create volatile baseline
        volatile_values = [100.0, 50.0, 200.0, 30.0, 180.0, 60.0] * 2
        baseline = QueryResult(
            query_id="volatile_baseline",
            rows=[
                Row(data={"yhat": v, "h": i + 1})
                for i, v in enumerate(volatile_values)
            ],
            unit="count",
            provenance=Provenance(
                source="csv",
                dataset_id="test",
                locator="test",
                fields=["yhat", "h"],
                license="Test",
            ),
            freshness=Freshness(asof_date="2024-12-31"),
            warnings=[],
        )

        client = MockDataClient()
        agent = ScenarioAgent(client)

        spec = ScenarioSpec(
            name="Volatile Test",
            description="Test stability detection",
            metric="retention",
            horizon_months=12,
            transforms=[
                Transform(type="multiplicative", value=0.10, start_month=0)
            ],
        )

        narrative = agent.apply(spec, baseline_override=baseline)

        # Should contain stability warning
        assert "Stability Warning" in narrative or "instability" in narrative


@pytest.mark.slow
class TestScenarioPerformance:
    """Test scenario performance requirements."""

    def test_scenario_meets_sla(self):
        """Test scenario application meets <75ms SLA for 96-point series."""
        import time

        from src.qnwis.data.deterministic.models import (
            Freshness,
            Provenance,
            QueryResult,
            Row,
        )

        # Create 96-month (8-year) baseline
        values = [100.0 + i * 0.5 for i in range(96)]
        baseline = QueryResult(
            query_id="long_baseline",
            rows=[Row(data={"yhat": v, "h": i + 1}) for i, v in enumerate(values)],
            unit="count",
            provenance=Provenance(
                source="csv",
                dataset_id="test",
                locator="test",
                fields=["yhat", "h"],
                license="Test",
            ),
            freshness=Freshness(asof_date="2024-12-31"),
            warnings=[],
        )

        spec = ScenarioSpec(
            name="SLA Test",
            description="Performance test",
            metric="retention",
            horizon_months=96,
            transforms=[
                Transform(type="multiplicative", value=0.10, start_month=0),
                Transform(type="additive", value=5.0, start_month=48),
            ],
        )

        # Run multiple iterations
        latencies = []
        for _ in range(10):
            start = time.perf_counter()
            from src.qnwis.scenario.apply import apply_scenario

            _ = apply_scenario(baseline, spec)
            end = time.perf_counter()
            latencies.append((end - start) * 1000)  # Convert to ms

        # Check P95 latency
        latencies.sort()
        p95_idx = int(len(latencies) * 0.95)
        p95_latency = latencies[p95_idx]

        print(f"P95 latency: {p95_latency:.2f}ms")
        assert p95_latency < 75.0, f"P95 latency {p95_latency:.2f}ms exceeds 75ms SLA"
