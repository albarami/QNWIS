"""
Unit tests for ScenarioAgent.

Tests cover:
- Agent initialization
- apply method
- compare method
- batch method
- Error handling and validation
"""

import pytest

from src.qnwis.agents.base import DataClient
from src.qnwis.agents.scenario_agent import ScenarioAgent
from src.qnwis.data.deterministic.models import (
    Freshness,
    Provenance,
    QueryResult,
    Row,
)
from src.qnwis.scenario.dsl import ScenarioSpec, Transform

STATIC_UPDATED_AT = "2024-12-31T00:00:00Z"


class MockDataClient(DataClient):
    """Deterministic stub DataClient for tests."""

    def __init__(self, baseline_data=None):
        """
        Initialize mock client.

        Args:
            baseline_data: Dict mapping query_id to list of values
        """
        self.baseline_data = baseline_data or {}

    def run(self, query_id: str) -> QueryResult:
        """Mock run method returning baseline forecast data."""
        if query_id not in self.baseline_data:
            raise ValueError(f"Query not found: {query_id}")

        values = self.baseline_data[query_id]
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
                locator="test_locator",
                fields=["yhat", "h", "lo", "hi"],
                license="Test",
            ),
            freshness=Freshness(
                asof_date="2024-12-31",
                updated_at=STATIC_UPDATED_AT,
            ),
            warnings=[],
        )


class TestScenarioAgentInit:
    """Test ScenarioAgent initialization."""

    def test_basic_initialization(self):
        """Test agent initializes with DataClient."""
        client = MockDataClient()
        agent = ScenarioAgent(client)

        assert agent.client is client

    def test_rejects_non_data_client(self):
        """ScenarioAgent should enforce DataClient-only usage."""
        with pytest.raises(TypeError, match="DataClient"):
            ScenarioAgent(object())  # type: ignore[arg-type]


class TestApplyMethod:
    """Test apply method."""

    def test_apply_basic_yaml_spec(self):
        """Test applying scenario from YAML string."""
        baseline_data = {
            "forecast_baseline_retention_construction_12m": [100.0] * 12
        }
        client = MockDataClient(baseline_data)
        agent = ScenarioAgent(client)

        yaml_spec = """
name: Retention Boost
description: 10% improvement
metric: retention
sector: Construction
horizon_months: 12
transforms:
  - type: multiplicative
    value: 0.10
    start_month: 0
"""

        narrative = agent.apply(yaml_spec, spec_format="yaml")

        assert isinstance(narrative, str)
        assert "Retention Boost" in narrative
        assert "Executive Summary" in narrative
        assert "QID=" in narrative
        assert "Scenario Forecast" in narrative

    def test_apply_with_baseline_override(self):
        """Test applying scenario with baseline override."""
        client = MockDataClient()
        agent = ScenarioAgent(client)

        # Create baseline override
        baseline = QueryResult(
            query_id="test_baseline",
            rows=[
                Row(data={"yhat": 100.0, "h": 1}),
                Row(data={"yhat": 100.0, "h": 2}),
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

        spec = ScenarioSpec(
            name="Test",
            description="Test scenario",
            metric="retention",
            horizon_months=2,
            transforms=[
                Transform(type="additive", value=10.0, start_month=0)
            ],
        )

        narrative = agent.apply(spec, baseline_override=baseline)

        assert isinstance(narrative, str)
        assert "Test" in narrative

    def test_apply_invalid_metric(self):
        """Test applying scenario with non-whitelisted metric."""
        client = MockDataClient()
        agent = ScenarioAgent(client)

        yaml_spec = """
name: Invalid Metric Test
description: Test
metric: invalid_metric
horizon_months: 12
transforms:
  - type: additive
    value: 1.0
    start_month: 0
"""

        narrative = agent.apply(yaml_spec)

        assert "Error" in narrative
        assert "not whitelisted" in narrative

    def test_apply_missing_baseline(self):
        """Test applying scenario when baseline is unavailable."""
        client = MockDataClient({})
        agent = ScenarioAgent(client)

        yaml_spec = """
name: Missing Baseline
description: Test
metric: retention
sector: Construction
horizon_months: 12
transforms:
  - type: additive
    value: 1.0
    start_month: 0
"""

        narrative = agent.apply(yaml_spec)

        assert "Error" in narrative
        assert "unavailable" in narrative or "not found" in narrative.lower()


class TestCompareMethod:
    """Test compare method."""

    def test_compare_multiple_scenarios(self):
        """Test comparing multiple scenarios."""
        baseline_data = {
            "forecast_baseline_retention_all_12m": [100.0] * 12
        }
        client = MockDataClient(baseline_data)
        agent = ScenarioAgent(client)

        scenario1 = """
name: Optimistic
description: 15% improvement
metric: retention
horizon_months: 12
transforms:
  - type: multiplicative
    value: 0.15
    start_month: 0
"""

        scenario2 = """
name: Pessimistic
description: 5% improvement
metric: retention
horizon_months: 12
transforms:
  - type: multiplicative
    value: 0.05
    start_month: 0
"""

        narrative = agent.compare([scenario1, scenario2])

        assert isinstance(narrative, str)
        assert "Scenario Comparison" in narrative
        assert "Optimistic" in narrative
        assert "Pessimistic" in narrative
        assert "Comparison Table" in narrative

    def test_compare_inconsistent_metrics(self):
        """Test comparing scenarios with different metrics."""
        client = MockDataClient()
        agent = ScenarioAgent(client)

        scenario1 = """
name: Retention
description: Test
metric: retention
horizon_months: 12
transforms:
  - type: additive
    value: 1.0
    start_month: 0
"""

        scenario2 = """
name: Salary
description: Test
metric: salary
horizon_months: 12
transforms:
  - type: additive
    value: 1.0
    start_month: 0
"""

        narrative = agent.compare([scenario1, scenario2])

        assert "Error" in narrative
        assert "Inconsistent metrics" in narrative

    def test_compare_inconsistent_horizons(self):
        """Test comparing scenarios with different horizons."""
        client = MockDataClient()
        agent = ScenarioAgent(client)

        scenario1 = """
name: Short
description: Test
metric: retention
horizon_months: 6
transforms:
  - type: additive
    value: 1.0
    start_month: 0
"""

        scenario2 = """
name: Long
description: Test
metric: retention
horizon_months: 12
transforms:
  - type: additive
    value: 1.0
    start_month: 0
"""

        narrative = agent.compare([scenario1, scenario2])

        assert "Error" in narrative
        assert "Inconsistent horizons" in narrative


class TestBatchMethod:
    """Test batch method."""

    def test_batch_multiple_sectors(self):
        """Test batch processing multiple sectors."""
        baseline_data = {
            "forecast_baseline_retention_construction_12m": [100.0] * 12,
            "forecast_baseline_retention_healthcare_12m": [80.0] * 12,
        }
        client = MockDataClient(baseline_data)
        agent = ScenarioAgent(client)

        construction_spec = """
name: Construction Boost
description: 10% improvement
metric: retention
sector: Construction
horizon_months: 12
transforms:
  - type: multiplicative
    value: 0.10
    start_month: 0
"""

        healthcare_spec = """
name: Healthcare Boost
description: 15% improvement
metric: retention
sector: Healthcare
horizon_months: 12
transforms:
  - type: multiplicative
    value: 0.15
    start_month: 0
"""

        sector_specs = {
            "Construction": construction_spec,
            "Healthcare": healthcare_spec,
        }

        narrative = agent.batch(sector_specs)

        assert isinstance(narrative, str)
        assert "Batch Scenario Processing" in narrative
        assert "Construction" in narrative
        assert "Healthcare" in narrative
        assert "National Aggregation" in narrative

    def test_batch_with_weights(self):
        """Test batch processing with custom sector weights."""
        baseline_data = {
            "forecast_baseline_retention_construction_12m": [100.0] * 12,
            "forecast_baseline_retention_healthcare_12m": [80.0] * 12,
        }
        client = MockDataClient(baseline_data)
        agent = ScenarioAgent(client)

        sector_specs = {
            "Construction": {
                "name": "Test1",
                "description": "Test",
                "metric": "retention",
                "sector": "Construction",
                "horizon_months": 12,
                "transforms": [
                    {"type": "additive", "value": 5.0, "start_month": 0}
                ],
            },
            "Healthcare": {
                "name": "Test2",
                "description": "Test",
                "metric": "retention",
                "sector": "Healthcare",
                "horizon_months": 12,
                "transforms": [
                    {"type": "additive", "value": 5.0, "start_month": 0}
                ],
            },
        }

        weights = {"Construction": 0.7, "Healthcare": 0.3}

        narrative = agent.batch(sector_specs, spec_format="dict", sector_weights=weights)

        assert isinstance(narrative, str)
        assert "Weights" in narrative
        assert "0.700" in narrative or "0.70" in narrative

    def test_batch_inconsistent_metrics(self):
        """Test batch with inconsistent metrics across sectors."""
        client = MockDataClient()
        agent = ScenarioAgent(client)

        sector_specs = {
            "Construction": {
                "name": "Test1",
                "description": "Test",
                "metric": "retention",
                "horizon_months": 12,
                "transforms": [
                    {"type": "additive", "value": 1.0, "start_month": 0}
                ],
            },
            "Healthcare": {
                "name": "Test2",
                "description": "Test",
                "metric": "salary",
                "horizon_months": 12,
                "transforms": [
                    {"type": "additive", "value": 1.0, "start_month": 0}
                ],
            },
        }

        narrative = agent.batch(sector_specs, spec_format="dict")

        assert "Error" in narrative
        assert "different metric" in narrative

    def test_batch_no_sectors(self):
        """Test batch with no sector specs."""
        client = MockDataClient()
        agent = ScenarioAgent(client)

        narrative = agent.batch({})

        assert "Error" in narrative
        assert "No sector scenarios" in narrative


class TestValidation:
    """Test validation and error handling."""

    def test_validate_metric_whitelisting(self):
        """Test metric whitelisting."""
        client = MockDataClient()
        agent = ScenarioAgent(client)

        # Valid metric
        agent._validate_metric("retention")  # Should not raise

        # Invalid metric
        with pytest.raises(ValueError, match="not whitelisted"):
            agent._validate_metric("invalid_metric")
