"""
Unit tests for pattern mining core engine.

Tests PatternMiner methods and helper functions.
"""

from __future__ import annotations

from datetime import date, timedelta
from time import perf_counter

import pytest

from src.qnwis.data.deterministic.models import Freshness, Provenance, QueryResult, Row
from src.qnwis.patterns.miner import PatternFinding, PatternMiner, PatternSpec, SeriesPoint


class TestPatternMiner:
    """Test PatternMiner initialization and configuration."""

    def test_default_initialization(self):
        """Default thresholds."""
        miner = PatternMiner()
        assert miner.flat_threshold == 0.15
        assert miner.nonlinear_threshold == 0.3
        assert miner.max_cohorts == 30

    def test_custom_thresholds(self):
        """Custom threshold configuration."""
        miner = PatternMiner(flat_threshold=0.2, max_cohorts=50)
        assert miner.flat_threshold == 0.2
        assert miner.max_cohorts == 50


class TestDirectionClassification:
    """Test effect direction classification."""

    def test_flat_classification(self):
        """Effects below threshold are flat."""
        miner = PatternMiner(flat_threshold=0.15)
        assert miner._classify_direction(0.10) == "flat"
        assert miner._classify_direction(-0.10) == "flat"
        assert miner._classify_direction(0.0) == "flat"

    def test_positive_classification(self):
        """Positive effects above threshold."""
        miner = PatternMiner(flat_threshold=0.15)
        assert miner._classify_direction(0.20) == "pos"
        assert miner._classify_direction(0.75) == "pos"
        assert miner._classify_direction(1.0) == "pos"

    def test_negative_classification(self):
        """Negative effects above threshold."""
        miner = PatternMiner(flat_threshold=0.15)
        assert miner._classify_direction(-0.20) == "neg"
        assert miner._classify_direction(-0.75) == "neg"
        assert miner._classify_direction(-1.0) == "neg"

    def test_boundary_cases(self):
        """Exactly at threshold."""
        miner = PatternMiner(flat_threshold=0.15)
        # Exactly 0.15 should be pos (≥ threshold)
        assert miner._classify_direction(0.15) == "pos"
        assert miner._classify_direction(-0.15) == "neg"


class TestSeriesExtraction:
    """Test time series extraction from QueryResult."""

    def make_query_result(self, rows_data):
        """Helper to create QueryResult."""
        return QueryResult(
            query_id="test_query",
            rows=[Row(data=d) for d in rows_data],
            unit="percent",
            provenance=Provenance(
                source="csv",
                dataset_id="test",
                locator="test.csv",
                fields=["date", "value"],
            ),
            freshness=Freshness(asof_date="2024-01-01"),
        )

    def test_extract_simple_series(self):
        """Extract values within date range."""
        miner = PatternMiner()
        rows = [
            {"date": "2024-01-01", "value": 10.0},
            {"date": "2024-02-01", "value": 15.0},
            {"date": "2024-03-01", "value": 20.0},
        ]
        result = self.make_query_result(rows)

        series = miner._extract_series(
            result,
            date(2024, 1, 1),
            date(2024, 3, 1),
            None,
        )
        assert [point.value for point in series] == [10.0, 15.0, 20.0]

    def test_extract_with_sector_filter(self):
        """Filter by sector."""
        miner = PatternMiner()
        rows = [
            {"date": "2024-01-01", "value": 10.0, "sector": "Construction"},
            {"date": "2024-01-01", "value": 20.0, "sector": "Finance"},
            {"date": "2024-02-01", "value": 15.0, "sector": "Construction"},
            {"date": "2024-02-01", "value": 25.0, "sector": "Finance"},
        ]
        result = self.make_query_result(rows)

        series = miner._extract_series(
            result,
            date(2024, 1, 1),
            date(2024, 2, 1),
            "Construction",
        )
        assert [point.value for point in series] == [10.0, 15.0]

    def test_extract_with_date_filtering(self):
        """Only include dates within range."""
        miner = PatternMiner()
        rows = [
            {"date": "2023-12-01", "value": 5.0},
            {"date": "2024-01-01", "value": 10.0},
            {"date": "2024-02-01", "value": 15.0},
            {"date": "2024-03-01", "value": 20.0},
            {"date": "2024-04-01", "value": 25.0},
        ]
        result = self.make_query_result(rows)

        series = miner._extract_series(
            result,
            date(2024, 1, 1),
            date(2024, 3, 1),
            None,
        )
        assert [point.value for point in series] == [10.0, 15.0, 20.0]

    def test_extract_alternative_field_names(self):
        """Handle different value field names."""
        miner = PatternMiner()

        # Test with 'rate' field
        rows = [{"date": "2024-01-01", "rate": 10.0}]
        result = self.make_query_result(rows)
        series = miner._extract_series(result, date(2024, 1, 1), date(2024, 1, 1), None)
        assert [point.value for point in series] == [10.0]

        # Test with 'retention_rate' field
        rows = [{"date": "2024-01-01", "retention_rate": 15.0}]
        result = self.make_query_result(rows)
        series = miner._extract_series(result, date(2024, 1, 1), date(2024, 1, 1), None)
        assert [point.value for point in series] == [15.0]

    def test_extract_with_month_field(self):
        """Use 'month' instead of 'date'."""
        miner = PatternMiner()
        rows = [
            {"month": "2024-01-01", "value": 10.0},
            {"month": "2024-02-01", "value": 15.0},
        ]
        result = self.make_query_result(rows)

        series = miner._extract_series(
            result,
            date(2024, 1, 1),
            date(2024, 2, 1),
            None,
        )
        assert [point.value for point in series] == [10.0, 15.0]

    def test_extract_handles_missing_values(self):
        """Skip rows with missing values."""
        miner = PatternMiner()
        rows = [
            {"date": "2024-01-01", "value": 10.0},
            {"date": "2024-02-01"},  # No value
            {"date": "2024-03-01", "value": 20.0},
        ]
        result = self.make_query_result(rows)

        series = miner._extract_series(
            result,
            date(2024, 1, 1),
            date(2024, 3, 1),
            None,
        )
        assert [point.value for point in series] == [10.0, 20.0]

    def test_extract_sorts_by_date(self):
        """Results are sorted chronologically."""
        miner = PatternMiner()
        rows = [
            {"date": "2024-03-01", "value": 20.0},
            {"date": "2024-01-01", "value": 10.0},
            {"date": "2024-02-01", "value": 15.0},
        ]
        result = self.make_query_result(rows)

        series = miner._extract_series(
            result,
            date(2024, 1, 1),
            date(2024, 3, 1),
            None,
        )
        assert [point.value for point in series] == [10.0, 15.0, 20.0]

    def test_extract_uses_seasonally_adjusted_if_available(self):
        """Seasonally adjusted field should be captured."""
        miner = PatternMiner()
        rows = [
            {"date": "2024-01-01", "value": 10.0, "value_sa": 11.0},
            {"date": "2024-02-01", "value": 12.0, "value_sa": 12.5},
        ]
        result = self.make_query_result(rows)

        series = miner._extract_series(
            result,
            date(2024, 1, 1),
            date(2024, 2, 1),
            None,
        )
        assert [point.value for point in series] == [10.0, 12.0]
        assert [point.seasonally_adjusted for point in series] == [11.0, 12.5]


class TestSeriesAlignment:
    """Test series alignment helper."""

    @staticmethod
    def make_points(values: list[float]) -> list[SeriesPoint]:
        base = date(2024, 1, 1)
        return [
            SeriesPoint(date=base + timedelta(days=i), value=val)
            for i, val in enumerate(values)
        ]

    def test_equal_length_series(self):
        """Both series same length."""
        miner = PatternMiner()
        a = self.make_points([1.0, 2.0, 3.0])
        b = self.make_points([4.0, 5.0, 6.0])
        aligned = miner._align_series(a, b)
        assert aligned.driver_values == [1.0, 2.0, 3.0]
        assert aligned.outcome_values == [4.0, 5.0, 6.0]

    def test_first_series_longer(self):
        """First series longer, truncate to match."""
        miner = PatternMiner()
        a = self.make_points([1.0, 2.0, 3.0, 4.0, 5.0])
        b = self.make_points([10.0, 20.0, 30.0])
        aligned = miner._align_series(a, b)
        assert aligned.driver_values == [1.0, 2.0, 3.0]
        assert aligned.outcome_values == [10.0, 20.0, 30.0]

    def test_second_series_longer(self):
        """Second series longer."""
        miner = PatternMiner()
        a = self.make_points([1.0, 2.0])
        b = self.make_points([10.0, 20.0, 30.0, 40.0])
        aligned = miner._align_series(a, b)
        assert aligned.driver_values == [1.0, 2.0]
        assert aligned.outcome_values == [10.0, 20.0]

    def test_empty_series(self):
        """Handle empty series."""
        miner = PatternMiner()
        a = self.make_points([1.0, 2.0, 3.0])
        aligned = miner._align_series(a, [])
        assert aligned.driver_values == []
        assert aligned.outcome_values == []


class TestMineStableRelations:
    """Test stable relations mining (integration with metrics)."""

    def make_timeseries_result(self, dates, values, sector=None, sa_values=None):
        """Helper to create time series QueryResult."""
        rows_data = []
        for dt, val in zip(dates, values):
            row = {"date": dt.isoformat(), "value": val}
            if sector:
                row["sector"] = sector
            if sa_values is not None:
                row["value_sa"] = sa_values[len(rows_data)]
            rows_data.append(row)

        return QueryResult(
            query_id="test_ts",
            rows=[Row(data=d) for d in rows_data],
            unit="percent",
            provenance=Provenance(
                source="csv",
                dataset_id="test",
                locator="test.csv",
                fields=["date", "value"],
            ),
            freshness=Freshness(asof_date="2024-12-31"),
        )

    def test_stable_relations_with_perfect_correlation(self):
        """Strong positive driver-outcome relationship."""
        miner = PatternMiner()

        # Generate dates ending at Dec 31, 2024, going back 12 months
        end_date = date(2024, 12, 31)
        dates = [end_date - timedelta(days=30 * (11 - i)) for i in range(12)]

        # Outcome and driver with perfect correlation
        outcome_values = list(range(10, 22))  # 10, 11, 12, ..., 21
        driver_values = list(range(20, 32))   # 20, 21, 22, ..., 31

        timeseries_data = {
            "retention_rate": self.make_timeseries_result(dates, outcome_values),
            "avg_salary": self.make_timeseries_result(dates, driver_values),
        }

        spec = PatternSpec(
            outcome="retention_rate",
            drivers=["avg_salary"],
            window=12,
            min_support=12,
        )

        findings = miner.mine_stable_relations(spec, end_date, timeseries_data)

        assert len(findings) == 1
        assert findings[0].driver == "avg_salary"
        assert findings[0].effect > 0.99  # Near perfect correlation
        assert findings[0].direction == "pos"
        assert findings[0].support == 1.0  # 12/12 observations
        assert findings[0].n == 12

    def test_stable_relations_filters_flat_patterns(self):
        """Flat patterns are excluded."""
        miner = PatternMiner(flat_threshold=0.15)

        start_date = date(2024, 1, 1)
        dates = [start_date + timedelta(days=30 * i) for i in range(12)]

        # Outcome varies
        outcome_values = list(range(10, 22))
        # Driver is constant (no correlation)
        driver_values = [50.0] * 12

        timeseries_data = {
            "retention_rate": self.make_timeseries_result(dates, outcome_values),
            "avg_salary": self.make_timeseries_result(dates, driver_values),
        }

        spec = PatternSpec(
            outcome="retention_rate",
            drivers=["avg_salary"],
            window=12,
        )

        findings = miner.mine_stable_relations(spec, date(2024, 12, 31), timeseries_data)

        # Should be empty (flat pattern filtered out)
        assert len(findings) == 0

    def test_stable_relations_insufficient_support(self):
        """Skip patterns with insufficient support."""
        miner = PatternMiner()

        start_date = date(2024, 1, 1)
        dates = [start_date + timedelta(days=30 * i) for i in range(6)]  # Only 6 months

        outcome_values = list(range(10, 16))
        driver_values = list(range(20, 26))

        timeseries_data = {
            "retention_rate": self.make_timeseries_result(dates, outcome_values),
            "avg_salary": self.make_timeseries_result(dates, driver_values),
        }

        spec = PatternSpec(
            outcome="retention_rate",
            drivers=["avg_salary"],
            window=12,
            min_support=12,  # Require 12, only have 6
        )

        findings = miner.mine_stable_relations(spec, date(2024, 6, 30), timeseries_data)

        # Should be empty (insufficient support)
        assert len(findings) == 0

    def test_stable_relations_prefers_seasonally_adjusted(self):
        """Seasonally adjusted series should drive the effect."""
        miner = PatternMiner()
        end_date = date(2024, 12, 31)
        dates = [end_date - timedelta(days=30 * (11 - i)) for i in range(12)]
        outcome_values = list(range(10, 22))
        outcome_sa = [val * 1.1 for val in outcome_values]
        driver_values = [5.0] * 12  # flat raw values
        driver_sa = list(range(30, 42))  # strong SA correlation
        timeseries_data = {
            "retention_rate": self.make_timeseries_result(
                dates, outcome_values, sa_values=outcome_sa
            ),
            "avg_salary": self.make_timeseries_result(
                dates, driver_values, sa_values=driver_sa
            ),
        }
        spec = PatternSpec(
            outcome="retention_rate",
            drivers=["avg_salary"],
            window=12,
            min_support=12,
        )
        findings = miner.mine_stable_relations(spec, end_date, timeseries_data)
        assert len(findings) == 1
        assert findings[0].seasonally_adjusted is True
        assert findings[0].effect > 0.95

    def test_stable_relations_ranking_prioritizes_support(self):
        """Ranking should favor higher support before effect size."""
        miner = PatternMiner()
        end_date = date(2024, 12, 31)
        dates = [end_date - timedelta(days=30 * (11 - i)) for i in range(12)]
        outcome_values = list(range(50, 62))
        full_driver = [val * 1.2 for val in outcome_values]
        partial_driver = full_driver[:-2]  # missing last two points
        timeseries_data = {
            "retention_rate": self.make_timeseries_result(dates, outcome_values),
            "driver_full": self.make_timeseries_result(dates, full_driver),
            "driver_partial": self.make_timeseries_result(dates[:-2], partial_driver),
        }
        spec = PatternSpec(
            outcome="retention_rate",
            drivers=["driver_partial", "driver_full"],
            window=12,
            min_support=10,
        )
        findings = miner.mine_stable_relations(spec, end_date, timeseries_data)
        assert findings[0].driver == "driver_full"
        assert findings[1].driver == "driver_partial"


class TestPatternSpec:
    """Test PatternSpec dataclass."""

    def test_default_values(self):
        """Default values applied."""
        spec = PatternSpec(
            outcome="retention_rate",
            drivers=["avg_salary"],
        )
        assert spec.sector is None
        assert spec.window == 12
        assert spec.min_support == 12
        assert spec.method == "spearman"

    def test_custom_values(self):
        """Custom configuration."""
        spec = PatternSpec(
            outcome="qatarization_rate",
            drivers=["promotion_rate", "wage_spread"],
            sector="Finance",
            window=24,
            min_support=24,
            method="pearson",
        )
        assert spec.outcome == "qatarization_rate"
        assert spec.drivers == ["promotion_rate", "wage_spread"]
        assert spec.sector == "Finance"
        assert spec.window == 24
        assert spec.min_support == 24
        assert spec.method == "pearson"


class TestPatternFinding:
    """Test PatternFinding dataclass."""

    def test_finding_structure(self):
        """PatternFinding holds expected fields."""
        finding = PatternFinding(
            driver="avg_salary",
            effect=0.73,
            support=0.92,
            stability=0.85,
            direction="pos",
            cohort="Construction",
            n=18,
            seasonally_adjusted=True,
        )
        assert finding.driver == "avg_salary"
        assert finding.effect == 0.73
        assert finding.support == 0.92
        assert finding.stability == 0.85
        assert finding.direction == "pos"
        assert finding.cohort == "Construction"
        assert finding.n == 18
        assert finding.seasonally_adjusted is True

    def test_composite_score_calculation(self):
        """Composite score can be computed."""
        finding = PatternFinding(
            driver="avg_salary",
            effect=-0.60,
            support=0.80,
            stability=0.90,
            direction="neg",
            cohort="All",
            n=24,
            seasonally_adjusted=False,
        )
        composite = abs(finding.effect) * finding.support * finding.stability
        assert composite == pytest.approx(0.432, abs=1e-6)


class TestPatternMinerPerformance:
    """Micro-benchmark tests."""

    def make_timeseries_result(self, dates, values):
        rows = [{"date": dt.isoformat(), "value": val} for dt, val in zip(dates, values)]
        return QueryResult(
            query_id="perf_ts",
            rows=[Row(data=r) for r in rows],
            unit="percent",
            provenance=Provenance(
                source="csv",
                dataset_id="perf",
                locator="perf.csv",
                fields=["date", "value"],
            ),
            freshness=Freshness(asof_date="2024-12-31"),
        )

    def test_driver_screen_micro_benchmark_under_budget(self):
        """Ensure driver screening stays under 200ms for 5x4x4 scenario."""
        miner = PatternMiner()
        end_date = date(2024, 12, 31)
        base_dates = [end_date - timedelta(days=30 * (23 - i)) for i in range(24)]
        cohorts = [f"C{i}" for i in range(5)]
        windows = [3, 6, 12, 24]
        timeseries_data: dict[str, dict[str, QueryResult]] = {}
        for cohort in cohorts:
            series_map = {
                "driver": self.make_timeseries_result(base_dates, [i + 1 for i in range(24)]),
                "outcome": self.make_timeseries_result(base_dates, [i * 1.1 for i in range(24)]),
            }
            timeseries_data[cohort] = series_map

        start = perf_counter()
        miner.screen_driver_across_cohorts(
            driver="driver",
            outcome="outcome",
            cohorts=cohorts,
            end_date=end_date,
            windows=windows,
            timeseries_data=timeseries_data,
            min_support=3,
        )
        elapsed_ms = (perf_counter() - start) * 1000
        assert elapsed_ms < 200.0
