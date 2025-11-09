"""
Unit tests for scenario application transforms.

Tests cover:
- Individual transform functions (additive, multiplicative, growth_override, clamp)
- apply_scenario function
- cascade_sector_to_national function
- Edge cases and error handling
"""

import pytest

from src.qnwis.data.deterministic.models import (
    Freshness,
    Provenance,
    QueryResult,
    Row,
)
from src.qnwis.scenario.apply import (
    apply_additive,
    apply_clamp,
    apply_growth_override,
    apply_multiplicative,
    apply_scenario,
    apply_transform,
    cascade_sector_to_national,
)
from src.qnwis.scenario.dsl import ScenarioSpec, Transform

STATIC_UPDATED_AT = "2024-12-31T00:00:00Z"


class TestIndividualTransforms:
    """Test individual transform functions."""

    def test_apply_additive(self):
        """Test additive transform."""
        values = [100.0, 105.0, 110.0]
        result = apply_additive(values, shift=10.0, start=1, end=2)
        assert result == [100.0, 115.0, 120.0]

    def test_apply_additive_no_end(self):
        """Test additive transform with no end (applies to all remaining)."""
        values = [100.0, 105.0, 110.0, 115.0]
        result = apply_additive(values, shift=5.0, start=2, end=None)
        assert result == [100.0, 105.0, 115.0, 120.0]

    def test_apply_multiplicative(self):
        """Test multiplicative transform."""
        values = [100.0, 100.0, 100.0]
        result = apply_multiplicative(values, rate=0.10, start=0, end=1)
        # First two values should be increased by 10%
        assert result == pytest.approx([110.0, 110.0, 100.0])

    def test_apply_growth_override(self):
        """Test growth override transform."""
        values = [100.0, 100.0, 100.0, 100.0]
        result = apply_growth_override(values, target_rate=0.05, start=1, end=3)
        # Starting from values[0]=100, grow at 5% per month
        expected = [100.0, 100.0, 105.0, 110.25]
        assert result == pytest.approx(expected)

    def test_apply_clamp(self):
        """Test clamp transform."""
        values = [50.0, 100.0, 150.0]
        result = apply_clamp(values, min_val=60.0, max_val=140.0)
        assert result == [60.0, 100.0, 140.0]

    def test_apply_clamp_min_only(self):
        """Test clamp with min only."""
        values = [10.0, 50.0, 100.0]
        result = apply_clamp(values, min_val=30.0, max_val=None)
        assert result == [30.0, 50.0, 100.0]

    def test_apply_clamp_max_only(self):
        """Test clamp with max only."""
        values = [10.0, 50.0, 100.0]
        result = apply_clamp(values, min_val=None, max_val=60.0)
        assert result == [10.0, 50.0, 60.0]


class TestApplyTransform:
    """Test apply_transform dispatcher function."""

    def test_apply_transform_additive(self):
        """Test apply_transform with additive type."""
        values = [100.0, 100.0, 100.0]
        transform = Transform(type="additive", value=10.0, start_month=0)
        result = apply_transform(values, transform)
        assert result == [110.0, 110.0, 110.0]

    def test_apply_transform_multiplicative(self):
        """Test apply_transform with multiplicative type."""
        values = [100.0, 100.0]
        transform = Transform(type="multiplicative", value=0.20, start_month=1)
        result = apply_transform(values, transform)
        assert result == pytest.approx([100.0, 120.0])

    def test_apply_transform_unknown_type(self):
        """Test apply_transform with unknown type raises error."""
        values = [100.0]
        # Create a valid transform but then monkey-patch the type to test error handling
        transform = Transform(type="additive", value=1.0, start_month=0)
        # Bypass Pydantic validation by accessing __dict__ directly
        object.__setattr__(transform, "type", "unknown_type")

        with pytest.raises(ValueError, match="Unknown transform type"):
            apply_transform(values, transform)


class TestApplyScenario:
    """Test apply_scenario function."""

    def _make_baseline(self, values: list[float], value_field: str = "yhat") -> QueryResult:
        """Helper to create baseline QueryResult."""
        rows = [Row(data={value_field: v, "h": i + 1}) for i, v in enumerate(values)]
        return QueryResult(
            query_id="baseline_forecast",
            rows=rows,
            unit="count",
            provenance=Provenance(
                source="csv",
                dataset_id="test",
                locator="test",
                fields=[value_field, "h"],
                license="Test",
            ),
            freshness=Freshness(
                asof_date="2024-12-31",
                updated_at=STATIC_UPDATED_AT,
            ),
            warnings=[],
        )

    def test_apply_scenario_basic(self):
        """Test basic scenario application."""
        baseline = self._make_baseline([100.0, 100.0, 100.0])
        spec = ScenarioSpec(
            name="Test",
            description="Test scenario",
            metric="retention",
            horizon_months=3,
            transforms=[
                Transform(type="multiplicative", value=0.10, start_month=0)
            ],
        )

        result = apply_scenario(baseline, spec)

        assert result.query_id.startswith("derived_scenario_application")
        assert len(result.rows) == 3
        assert result.rows[0].data["baseline"] == 100.0
        assert result.rows[0].data["adjusted"] == pytest.approx(110.0)
        assert result.rows[0].data["delta"] == pytest.approx(10.0)
        assert result.rows[0].data["delta_pct"] == pytest.approx(10.0)

    def test_apply_scenario_with_date_labels(self):
        """Test scenario application with date labels."""
        baseline = self._make_baseline([100.0, 100.0])
        spec = ScenarioSpec(
            name="Test",
            description="Test",
            metric="retention",
            horizon_months=2,
            transforms=[
                Transform(type="additive", value=5.0, start_month=0)
            ],
        )
        date_labels = ["2024-01", "2024-02"]

        result = apply_scenario(baseline, spec, date_labels=date_labels)

        assert result.rows[0].data["period"] == "2024-01"
        assert result.rows[1].data["period"] == "2024-02"

    def test_apply_scenario_with_clamping(self):
        """Test scenario with final clamping."""
        baseline = self._make_baseline([50.0, 100.0, 150.0])
        spec = ScenarioSpec(
            name="Test",
            description="Test",
            metric="retention",
            horizon_months=3,
            transforms=[
                Transform(type="multiplicative", value=0.50, start_month=0)
            ],
            clamp_min=80.0,
            clamp_max=120.0,
        )

        result = apply_scenario(baseline, spec)

        # After 50% increase: [75, 150, 225], then clamped to [80, 120, 120]
        assert result.rows[0].data["adjusted"] == pytest.approx(80.0)
        assert result.rows[1].data["adjusted"] == pytest.approx(120.0)
        assert result.rows[2].data["adjusted"] == pytest.approx(120.0)

    def test_apply_scenario_empty_baseline(self):
        """Test scenario application with empty baseline raises error."""
        baseline = self._make_baseline([])
        spec = ScenarioSpec(
            name="Test",
            description="Test",
            metric="retention",
            horizon_months=12,
            transforms=[
                Transform(type="additive", value=1.0, start_month=0)
            ],
        )

        with pytest.raises(ValueError, match="no rows"):
            apply_scenario(baseline, spec)

    def test_apply_scenario_missing_value_field(self):
        """Test scenario with missing value field raises error."""
        rows = [Row(data={"wrong_field": 100.0})]
        baseline = QueryResult(
            query_id="test",
            rows=rows,
            unit="count",
            provenance=Provenance(
                source="csv",
                dataset_id="test",
                locator="test",
                fields=["wrong_field"],
                license="Test",
            ),
            freshness=Freshness(asof_date="2024-12-31"),
            warnings=[],
        )
        spec = ScenarioSpec(
            name="Test",
            description="Test",
            metric="retention",
            horizon_months=1,
            transforms=[
                Transform(type="additive", value=1.0, start_month=0)
            ],
        )

        with pytest.raises(ValueError, match="must contain"):
            apply_scenario(baseline, spec)

    def test_apply_scenario_sequential_transforms(self):
        """Test scenario with multiple transforms applied sequentially."""
        baseline = self._make_baseline([100.0, 100.0])
        spec = ScenarioSpec(
            name="Test",
            description="Test",
            metric="retention",
            horizon_months=2,
            transforms=[
                Transform(type="multiplicative", value=0.10, start_month=0),
                Transform(type="additive", value=5.0, start_month=0),
            ],
        )

        result = apply_scenario(baseline, spec)

        # First: 100 * 1.10 = 110
        # Then: 110 + 5 = 115
        assert result.rows[0].data["adjusted"] == pytest.approx(115.0)


class TestCascadeSectorToNational:
    """Test cascade_sector_to_national function."""

    def _make_sector_result(
        self, sector: str, values: list[float]
    ) -> QueryResult:
        """Helper to create sector QueryResult."""
        rows = [Row(data={"adjusted": v, "h": i + 1}) for i, v in enumerate(values)]
        return QueryResult(
            query_id=f"scenario_{sector}",
            rows=rows,
            unit="count",
            provenance=Provenance(
                source="csv",
                dataset_id=sector,
                locator="test",
                fields=["adjusted", "h"],
                license="Test",
            ),
            freshness=Freshness(asof_date="2024-12-31"),
            warnings=[],
        )

    def test_cascade_equal_weights(self):
        """Test cascading with equal weights."""
        sector_results = {
            "Construction": self._make_sector_result("Construction", [100.0, 110.0]),
            "Healthcare": self._make_sector_result("Healthcare", [80.0, 90.0]),
        }

        national = cascade_sector_to_national(sector_results)

        assert len(national.rows) == 2
        # Equal weights: (100 + 80) / 2 = 90
        assert national.rows[0].data["adjusted"] == pytest.approx(90.0)
        # (110 + 90) / 2 = 100
        assert national.rows[1].data["adjusted"] == pytest.approx(100.0)

    def test_cascade_custom_weights(self):
        """Test cascading with custom weights."""
        sector_results = {
            "Construction": self._make_sector_result("Construction", [100.0]),
            "Healthcare": self._make_sector_result("Healthcare", [80.0]),
        }
        weights = {"Construction": 0.7, "Healthcare": 0.3}

        national = cascade_sector_to_national(sector_results, weights)

        # 100 * 0.7 + 80 * 0.3 = 70 + 24 = 94
        assert national.rows[0].data["adjusted"] == pytest.approx(94.0)

    def test_cascade_empty_sectors_error(self):
        """Test cascading with no sectors raises error."""
        with pytest.raises(ValueError, match="No sector results"):
            cascade_sector_to_national({})

    def test_cascade_inconsistent_horizons_error(self):
        """Test cascading with inconsistent horizons raises error."""
        sector_results = {
            "Construction": self._make_sector_result("Construction", [100.0]),
            "Healthcare": self._make_sector_result("Healthcare", [80.0, 90.0]),
        }

        with pytest.raises(ValueError, match="Inconsistent horizons"):
            cascade_sector_to_national(sector_results)
