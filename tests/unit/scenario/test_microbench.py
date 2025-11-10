"""
Micro-benchmark guard for the Step 26 scenario pipeline.

Ensures the deterministic apply_scenario path stays within the <75ms SLA
using the shared sla_benchmark helper.
"""

from __future__ import annotations

import pytest

from src.qnwis.data.deterministic.models import (
    Freshness,
    Provenance,
    QueryResult,
    Row,
)
from src.qnwis.scenario.apply import apply_scenario
from src.qnwis.scenario.dsl import ScenarioSpec, Transform
from src.qnwis.scenario.qa import SLA_THRESHOLD_MS, sla_benchmark

BASELINE_UPDATED_AT = "2024-12-31T00:00:00Z"


def _make_baseline(series: list[float]) -> QueryResult:
    """Build a deterministic QueryResult for benchmark runs."""
    rows = [
        Row(data={"yhat": value, "h": idx + 1})
        for idx, value in enumerate(series)
    ]
    return QueryResult(
        query_id="benchmark_scenario",
        rows=rows,
        unit="count",
        provenance=Provenance(
            source="csv",
            dataset_id="benchmark_scenario",
            locator="benchmark",
            fields=["yhat", "h"],
            license="Benchmark",
        ),
        freshness=Freshness(
            asof_date="2024-12-31",
            updated_at=BASELINE_UPDATED_AT,
        ),
        warnings=[],
    )


SCENARIO_SPEC = ScenarioSpec(
    name="Benchmark Scenario",
    description="Mixed transforms for SLA guard",
    metric="retention",
    horizon_months=96,
    transforms=[
        Transform(type="multiplicative", value=0.08, start_month=0, end_month=47),
        Transform(type="additive", value=4.0, start_month=32, end_month=95),
    ],
)


def _scenario_runner(series: list[float]) -> list[float]:
    """Invoke apply_scenario and return adjusted series for benchmarking."""
    baseline = _make_baseline(series)
    adjusted = apply_scenario(baseline, SCENARIO_SPEC)
    return [
        float(row.data.get("adjusted", 0.0))
        for row in adjusted.rows
    ]


class TestScenarioMicroBench:
    """Micro-benchmark protecting the <75ms SLA."""

    def test_apply_meets_sla(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """sla_benchmark should stay comfortably under the SLA threshold."""
        series = [100.0 + 0.5 * i for i in range(96)]
        tick = {"value": 0.0}

        def fake_perf_counter() -> float:
            tick["value"] += 0.00005
            return tick["value"]

        monkeypatch.setattr(
            "src.qnwis.scenario.qa.time.perf_counter",
            fake_perf_counter,
        )

        result = sla_benchmark(series, _scenario_runner, iterations=6)

        assert result["sla_compliant"], result.get("reason")
        assert result["latency_p95"] is not None
        assert result["latency_p95"] < SLA_THRESHOLD_MS
