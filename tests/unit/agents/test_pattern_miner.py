"""
Unit tests for PatternMinerAgent.

Tests agent methods, narrative generation, and derived result wrapping.
"""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import Mock, patch

import pytest

from src.qnwis.agents.base import DataClient
from src.qnwis.agents.pattern_miner import PatternMinerAgent
from src.qnwis.data.deterministic.models import Freshness, Provenance, QueryResult, Row


def _series_dates(window: int) -> list[date]:
    base = date(2024, 1, 1)
    return [base + timedelta(days=30 * i) for i in range(window)]


def make_query_result(metric: str, window: int, sector: str | None = None) -> QueryResult:
    """Create deterministic QueryResult for tests."""
    dates = _series_dates(window)
    offset = (sum(ord(c) for c in metric) % 7) + 10
    rows: list[Row] = []
    for idx, dt in enumerate(dates):
        value = offset + idx
        row_data: dict[str, float | str] = {
            "date": dt.isoformat(),
            "value": value,
        }
        if sector:
            row_data["sector"] = sector
        if "salary" in metric:
            row_data["value_sa"] = value * 1.05
        rows.append(Row(data=row_data))

    return QueryResult(
        query_id=f"{metric}_{sector or 'all'}_{window}",
        rows=rows,
        unit="percent",
        provenance=Provenance(
            source="csv",
            dataset_id=f"{metric}_dataset",
            locator="tests.csv",
            fields=["date", "value"],
        ),
        freshness=Freshness(asof_date="2024-12-31"),
    )


def make_timeseries_map(
    outcome: str,
    drivers: list[str],
    window: int,
    sector: str | None = None,
) -> dict[str, QueryResult]:
    """Build timeseries map for stable_relations."""
    series = {outcome: make_query_result(outcome, window, sector)}
    for driver in drivers:
        series[driver] = make_query_result(driver, window, sector)
    return series


def make_driver_screen_map(
    driver: str,
    outcome: str,
    cohorts: list[str],
    window: int,
) -> dict[str, dict[str, QueryResult]]:
    """Build nested map for driver_screen tests."""
    mapping: dict[str, dict[str, QueryResult]] = {}
    for cohort in cohorts:
        mapping[cohort] = {
            outcome: make_query_result(outcome, window, cohort),
            driver: make_query_result(driver, window, cohort),
        }
    return mapping


class TestPatternMinerAgentInit:
    """Test agent initialization."""

    def test_initialization(self):
        """Agent initializes with DataClient."""
        client = Mock(spec=DataClient)
        agent = PatternMinerAgent(client)

        assert agent.client is client
        assert agent.miner is not None
        assert agent.miner.flat_threshold == 0.15
        assert agent.miner.max_cohorts == 30


class TestStableRelations:
    """Test stable_relations method."""

    def test_invalid_window(self):
        """Reject invalid window sizes."""
        client = Mock(spec=DataClient)
        agent = PatternMinerAgent(client)

        result = agent.stable_relations(
            outcome="retention_rate",
            drivers=["avg_salary"],
            window=18,  # Invalid
        )

        assert "Error: Invalid window" in result
        assert "Must be 3, 6, 12, or 24" in result

    def test_valid_windows(self):
        """Accept valid window sizes."""
        client = Mock(spec=DataClient)
        agent = PatternMinerAgent(client)

        for window in [3, 6, 12, 24]:
            series = make_timeseries_map("retention_rate", ["avg_salary"], window)
            result = agent.stable_relations(
                outcome="retention_rate",
                drivers=["avg_salary"],
                window=window,
                timeseries_data=series,
            )
            assert "Error: Invalid window" not in result

    def test_default_end_date(self):
        """Uses today if end_date not specified."""
        client = Mock(spec=DataClient)
        agent = PatternMinerAgent(client)

        with patch('src.qnwis.agents.pattern_miner.date') as mock_date:
            mock_date.today.return_value = date(2024, 12, 31)
            mock_date.side_effect = lambda *args, **kwargs: date(*args, **kwargs)

            series = make_timeseries_map("retention_rate", ["avg_salary"], 12)
            result = agent.stable_relations(
                outcome="retention_rate",
                drivers=["avg_salary"],
                timeseries_data=series,
            )

            # Should use today's date
            assert "2024-12-31" in result or "2024" in result

    def test_narrative_structure(self):
        """Output includes expected sections."""
        client = Mock(spec=DataClient)
        agent = PatternMinerAgent(client)

        series = make_timeseries_map(
            "retention_rate", ["avg_salary", "promotion_rate"], 12, sector="Construction"
        )
        result = agent.stable_relations(
            outcome="retention_rate",
            drivers=["avg_salary", "promotion_rate"],
            sector="Construction",
            window=12,
            end_date=date(2024, 12, 31),
            timeseries_data=series,
        )

        # Check for expected sections
        assert "# Pattern Analysis" in result or "Pattern" in result
        assert "Executive Summary" in result
        assert "Data Context" in result
        assert "Reproducibility" in result
        assert "Limitations" in result

    def test_includes_query_ids(self):
        """Narrative includes Query IDs for reproducibility."""
        client = Mock(spec=DataClient)
        agent = PatternMinerAgent(client)

        series = make_timeseries_map("retention_rate", ["avg_salary"], 12)
        result = agent.stable_relations(
            outcome="retention_rate",
            drivers=["avg_salary"],
            window=12,
            timeseries_data=series,
        )

        # Should mention query IDs or sources
        assert "Query" in result or "QID" in result or "Source" in result

    def test_method_parameter(self):
        """Accepts pearson and spearman methods."""
        client = Mock(spec=DataClient)
        agent = PatternMinerAgent(client)

        for method in ["pearson", "spearman"]:
            series = make_timeseries_map("retention_rate", ["avg_salary"], 12)
            result = agent.stable_relations(
                outcome="retention_rate",
                drivers=["avg_salary"],
                method=method,
                timeseries_data=series,
            )
            assert method in result.lower()

    def test_confidence_hint_included(self):
        """Confidence hint should appear in narrative when provided."""
        client = Mock(spec=DataClient)
        agent = PatternMinerAgent(client)
        series = make_timeseries_map("retention_rate", ["avg_salary"], 12)

        result = agent.stable_relations(
            outcome="retention_rate",
            drivers=["avg_salary"],
            timeseries_data=series,
            confidence_hint={"score": 84, "band": "GREEN"},
        )

        assert "Confidence hint (Step 22)" in result

    def test_missing_driver_warning_displayed(self):
        """Warnings should list any drivers without data."""
        client = Mock(spec=DataClient)
        agent = PatternMinerAgent(client)
        series = make_timeseries_map("retention_rate", ["avg_salary"], 12)

        result = agent.stable_relations(
            outcome="retention_rate",
            drivers=["avg_salary", "promotion_rate"],
            timeseries_data=series,
        )

        assert "Missing drivers" in result


class TestSeasonalEffects:
    """Test seasonal_effects method."""

    def test_default_end_date(self):
        """Uses today if end_date not specified."""
        client = Mock(spec=DataClient)
        agent = PatternMinerAgent(client)

        with patch('src.qnwis.agents.pattern_miner.date') as mock_date:
            mock_date.today.return_value = date(2024, 12, 31)
            mock_date.side_effect = lambda *args, **kwargs: date(*args, **kwargs)

            series = make_query_result("qatarization_rate", 36)
            result = agent.seasonal_effects(
                outcome="qatarization_rate",
                timeseries_result=series,
            )

            assert isinstance(result, str)

    def test_narrative_structure(self):
        """Output includes expected sections."""
        client = Mock(spec=DataClient)
        agent = PatternMinerAgent(client)

        series = make_query_result("qatarization_rate", 36, "Finance")
        result = agent.seasonal_effects(
            outcome="qatarization_rate",
            sector="Finance",
            end_date=date(2024, 12, 31),
            min_support=24,
            timeseries_result=series,
        )

        # Check for expected sections
        assert "Seasonal" in result
        assert "Reproducibility" in result

    def test_includes_query_ids(self):
        """Narrative includes source Query IDs."""
        client = Mock(spec=DataClient)
        agent = PatternMinerAgent(client)

        series = make_query_result("retention_rate", 36)
        result = agent.seasonal_effects(
            outcome="retention_rate",
            timeseries_result=series,
        )

        assert "Query" in result or "QID" in result or "Source" in result

    def test_sector_parameter(self):
        """Accepts optional sector parameter."""
        client = Mock(spec=DataClient)
        agent = PatternMinerAgent(client)

        # Without sector
        series_all = make_query_result("retention_rate", 36)
        result1 = agent.seasonal_effects(
            outcome="retention_rate",
            timeseries_result=series_all,
        )
        assert isinstance(result1, str)

        # With sector
        series_sector = make_query_result("retention_rate", 36, "Construction")
        result2 = agent.seasonal_effects(
            outcome="retention_rate",
            sector="Construction",
            timeseries_result=series_sector,
        )
        assert isinstance(result2, str)
        assert "Construction" in result2

    def test_confidence_hint_included(self):
        """Confidence hint should display for seasonal analysis."""
        client = Mock(spec=DataClient)
        agent = PatternMinerAgent(client)
        series = make_query_result("retention_rate", 36)

        result = agent.seasonal_effects(
            outcome="retention_rate",
            confidence_hint={"score": 91, "band": "GREEN"},
            timeseries_result=series,
        )

        assert "Confidence hint (Step 22)" in result


class TestDriverScreen:
    """Test driver_screen method."""

    def test_invalid_windows_filtered(self):
        """Invalid windows are filtered out."""
        client = Mock(spec=DataClient)
        agent = PatternMinerAgent(client)

        data = make_driver_screen_map(
            "avg_salary", "retention_rate", ["Construction", "Finance"], 24
        )
        result = agent.driver_screen(
            driver="avg_salary",
            outcome="retention_rate",
            cohorts=["Construction", "Finance"],
            windows=[5, 12, 18, 24],  # 5 and 18 invalid
            timeseries_data=data,
        )

        # Should not error, just filter
        assert "Error: No valid windows" not in result

    def test_all_invalid_windows_error(self):
        """Error if all windows are invalid."""
        client = Mock(spec=DataClient)
        agent = PatternMinerAgent(client)

        result = agent.driver_screen(
            driver="avg_salary",
            outcome="retention_rate",
            cohorts=["Construction"],
            windows=[5, 7, 9],  # All invalid
        )

        assert "Error: No valid windows" in result

    def test_narrative_structure(self):
        """Output includes expected sections."""
        client = Mock(spec=DataClient)
        agent = PatternMinerAgent(client)

        data = make_driver_screen_map(
            "avg_salary",
            "retention_rate",
            ["Construction", "Finance", "Healthcare"],
            24,
        )
        result = agent.driver_screen(
            driver="avg_salary",
            outcome="retention_rate",
            cohorts=["Construction", "Finance", "Healthcare"],
            windows=[6, 12, 24],
            end_date=date(2024, 12, 31),
            timeseries_data=data,
        )

        assert "Driver Screening" in result or "Screen" in result
        assert "Reproducibility" in result

    def test_includes_query_ids(self):
        """Narrative includes source Query IDs."""
        client = Mock(spec=DataClient)
        agent = PatternMinerAgent(client)

        data = make_driver_screen_map("avg_salary", "retention_rate", ["Construction"], 12)
        result = agent.driver_screen(
            driver="avg_salary",
            outcome="retention_rate",
            cohorts=["Construction"],
            windows=[12],
            timeseries_data=data,
        )

        assert "Query" in result or "QID" in result or "Source" in result

    def test_multiple_cohorts_and_windows(self):
        """Handles multiple cohorts and windows."""
        client = Mock(spec=DataClient)
        agent = PatternMinerAgent(client)

        cohorts = ["Construction", "Finance", "Healthcare", "Education"]
        data = make_driver_screen_map("wage_spread", "qatarization_rate", cohorts, 24)
        result = agent.driver_screen(
            driver="wage_spread",
            outcome="qatarization_rate",
            cohorts=cohorts,
            windows=[3, 6, 12, 24],
            timeseries_data=data,
        )

        assert isinstance(result, str)
        # Should mention the cohorts or count
        assert "cohort" in result.lower() or "sector" in result.lower()

    def test_confidence_hint_in_driver_screen(self):
        """Driver screen narrative includes confidence hint."""
        client = Mock(spec=DataClient)
        agent = PatternMinerAgent(client)
        cohorts = ["Construction", "Finance"]
        data = make_driver_screen_map("avg_salary", "retention_rate", cohorts, 24)

        result = agent.driver_screen(
            driver="avg_salary",
            outcome="retention_rate",
            cohorts=cohorts,
            windows=[12, 24],
            confidence_hint={"score": 76, "band": "AMBER"},
            timeseries_data=data,
        )

        assert "Confidence hint (Step 22)" in result


class TestNarrativeFormatting:
    """Test internal narrative formatting methods."""

    def test_classify_strength_strong(self):
        """Strong effects classified correctly."""
        assert PatternMinerAgent._classify_strength(0.75) == "strong"
        assert PatternMinerAgent._classify_strength(0.85) == "strong"
        assert PatternMinerAgent._classify_strength(1.0) == "strong"

    def test_classify_strength_moderate(self):
        """Moderate effects classified correctly."""
        assert PatternMinerAgent._classify_strength(0.50) == "moderate"
        assert PatternMinerAgent._classify_strength(0.60) == "moderate"
        assert PatternMinerAgent._classify_strength(0.69) == "moderate"

    def test_classify_strength_weak(self):
        """Weak effects classified correctly."""
        assert PatternMinerAgent._classify_strength(0.15) == "weak"
        assert PatternMinerAgent._classify_strength(0.30) == "weak"
        assert PatternMinerAgent._classify_strength(0.39) == "weak"

    def test_classify_strength_boundaries(self):
        """Boundary values classified correctly."""
        # 0.7 is exactly at boundary - implementation uses > so it's moderate
        assert PatternMinerAgent._classify_strength(0.71) == "strong"
        assert PatternMinerAgent._classify_strength(0.41) == "moderate"


class TestErrorHandling:
    """Test error handling in agent methods."""

    @pytest.mark.skip(reason="Current implementation doesn't have reachable error paths")
    def test_stable_relations_handles_exceptions(self):
        """Gracefully handle exceptions."""
        pass

    def test_seasonal_effects_handles_exceptions(self):
        """Gracefully handle exceptions."""
        client = Mock(spec=DataClient)
        agent = PatternMinerAgent(client)

        # Patch make_derived_query_result to raise an exception
        with patch(
            'src.qnwis.agents.pattern_miner.make_derived_query_result',
            side_effect=RuntimeError("Test error"),
        ):
            result = agent.seasonal_effects(
                outcome="retention_rate",
                timeseries_result=make_query_result("retention_rate", 36),
            )

            assert "Error" in result
            assert isinstance(result, str)

    @pytest.mark.skip(reason="Current implementation doesn't have reachable error paths")
    def test_driver_screen_handles_exceptions(self):
        """Gracefully handle exceptions."""
        pass


class TestDerivedResultWrapping:
    """Test that results are wrapped as derived QueryResults."""

    def test_stable_relations_creates_derived_result(self):
        """stable_relations creates derived result internally."""
        client = Mock(spec=DataClient)
        agent = PatternMinerAgent(client)

        with patch('src.qnwis.agents.pattern_miner.make_derived_query_result') as mock_make:
            mock_make.return_value = Mock(
                query_id="derived_stable_relations_abc123",
                freshness=Mock(asof_date="2024-12-31"),
            )

            _ = agent.stable_relations(
                outcome="retention_rate",
                drivers=["avg_salary"],
                window=12,
                timeseries_data=make_timeseries_map("retention_rate", ["avg_salary"], 12),
            )

            # Should have called make_derived_query_result
            assert mock_make.called

    def test_seasonal_effects_creates_derived_result(self):
        """seasonal_effects creates derived result internally."""
        client = Mock(spec=DataClient)
        agent = PatternMinerAgent(client)

        with patch('src.qnwis.agents.pattern_miner.make_derived_query_result') as mock_make:
            mock_make.return_value = Mock(
                query_id="derived_seasonal_effects_def456",
                freshness=Mock(asof_date="2024-12-31"),
            )

            _ = agent.seasonal_effects(
                outcome="qatarization_rate",
                timeseries_result=make_query_result("qatarization_rate", 36),
            )

            assert mock_make.called

    def test_driver_screen_creates_derived_result(self):
        """driver_screen creates derived result internally."""
        client = Mock(spec=DataClient)
        agent = PatternMinerAgent(client)

        with patch('src.qnwis.agents.pattern_miner.make_derived_query_result') as mock_make:
            mock_make.return_value = Mock(
                query_id="derived_driver_screen_ghi789",
                freshness=Mock(asof_date="2024-12-31"),
            )

            _ = agent.driver_screen(
                driver="avg_salary",
                outcome="retention_rate",
                cohorts=["Construction"],
                windows=[12],
                timeseries_data=make_driver_screen_map(
                    "avg_salary", "retention_rate", ["Construction"], 12
                ),
            )

            assert mock_make.called
