"""
Unit tests for TimeMachineAgent.

Tests cover:
- Agent initialization
- Baseline report generation
- Trend report generation
- Breaks report generation
- Error handling and validation
"""

from datetime import date, datetime

import pytest

from src.qnwis.agents.time_machine import TimeMachineAgent
from src.qnwis.data.deterministic.models import (
    Freshness,
    Provenance,
    QueryResult,
    Row,
)


class MockDataClient:
    """Mock DataClient for testing."""

    def __init__(self, series_data=None):
        """
        Initialize mock client.
        
        Args:
            series_data: Dict mapping query_id to list of (period, value) tuples
        """
        self.series_data = series_data or {}

    def run(self, query_id: str) -> QueryResult:
        """Mock run method returning synthetic time-series data."""
        if query_id not in self.series_data:
            # Return empty result
            return QueryResult(
                query_id=query_id,
                rows=[],
                unit="count",
                provenance=Provenance(
                    source="csv",
                    dataset_id="test_dataset",
                    locator="test_locator",
                    fields=["period", "value"],
                    license="Test",
                ),
                freshness=Freshness(
                    asof_date="2024-12-31",
                    updated_at=datetime.now().isoformat(),
                ),
                warnings=[],
            )

        # Generate rows from series data
        rows = []
        for entry in self.series_data[query_id]:
            if len(entry) == 3:
                period, value, sector = entry
            else:
                period, value = entry
                sector = "Construction"
            rows.append(
                Row(
                    data={
                        "period": period,
                        "value": value,
                        "sector": sector,
                    }
                )
            )

        return QueryResult(
            query_id=query_id,
            rows=rows,
            unit="count",
            provenance=Provenance(
                source="csv",
                dataset_id="test_dataset",
                locator="test_locator",
                fields=["period", "value", "sector"],
                license="Test",
            ),
            freshness=Freshness(
                asof_date="2024-12-31",
                updated_at=datetime.now().isoformat(),
            ),
            warnings=[],
        )


class TestTimeMachineAgentInit:
    """Test TimeMachineAgent initialization."""

    def test_basic_initialization(self):
        """Test agent initializes with default series map."""
        client = MockDataClient()
        agent = TimeMachineAgent(client)

        assert agent.client is client
        assert isinstance(agent.series_map, dict)
        assert "retention" in agent.series_map

    def test_custom_series_map(self):
        """Test agent initializes with custom series map."""
        client = MockDataClient()
        custom_map = {"custom_metric": "CUSTOM_QUERY_ID"}
        agent = TimeMachineAgent(client, series_map=custom_map)

        assert agent.series_map == custom_map


class TestBaselineReport:
    """Test baseline_report method."""

    def test_baseline_report_basic(self):
        """Test baseline report with valid data."""
        # Create 24 months of data
        series_data = {
            "LMIS_RETENTION_TS": [
                (f"2023-{i:02d}", 100 + i) for i in range(1, 13)
            ]
            + [(f"2024-{i:02d}", 110 + i) for i in range(1, 13)]
        }

        client = MockDataClient(series_data)
        agent = TimeMachineAgent(client)

        report = agent.baseline_report(
            metric="retention",
            sector=None,
            start=date(2023, 1, 1),
            end=date(2024, 12, 31),
        )

        assert isinstance(report, str)
        assert "Executive Summary" in report
        assert "Baseline Table" in report
        assert "QID=" in report
        assert "Freshness:" in report

    def test_baseline_report_with_sector(self):
        """Test baseline report with sector filter."""
        series_data = {
            "LMIS_RETENTION_TS": [
                (f"2023-{i:02d}", 100 + i) for i in range(1, 13)
            ]
        }

        client = MockDataClient(series_data)
        agent = TimeMachineAgent(client)

        report = agent.baseline_report(
            metric="retention",
            sector="Construction",
            start=date(2023, 1, 1),
            end=date(2023, 12, 31),
        )

        assert isinstance(report, str)
        assert "QID=" in report

    def test_baseline_report_insufficient_data(self):
        """Test baseline report with insufficient data."""
        # Only 2 months of data (need 12)
        series_data = {
            "LMIS_RETENTION_TS": [
                ("2024-01", 100),
                ("2024-02", 110),
            ]
        }

        client = MockDataClient(series_data)
        agent = TimeMachineAgent(client)

        with pytest.raises(ValueError, match="Insufficient data"):
            agent.baseline_report(
                metric="retention",
                sector=None,
                start=date(2024, 1, 1),
                end=date(2024, 12, 31),
            )

    def test_baseline_report_sector_fallback(self):
        """Baseline report should fallback to economy-wide factors when sector is short."""
        construction_rows = [
            (f"2024-{i:02d}", 100 + i, "Construction") for i in range(1, 7)
        ]
        finance_rows = []
        for year, months in ((2024, range(1, 13)), (2025, range(1, 7))):
            for month in months:
                finance_rows.append((f"{year}-{month:02d}", 200 + month, "Finance"))

        series_data = {"LMIS_RETENTION_TS": construction_rows + finance_rows}

        client = MockDataClient(series_data)
        agent = TimeMachineAgent(client)

        report = agent.baseline_report(
            metric="retention",
            sector="Construction",
            start=date(2024, 1, 1),
            end=date(2025, 6, 30),
        )

        assert "Economy-wide fallback seasonal pattern" in report

    def test_baseline_report_invalid_metric(self):
        """Test baseline report with invalid metric."""
        client = MockDataClient()
        agent = TimeMachineAgent(client)

        with pytest.raises(ValueError, match="not in series_map"):
            agent.baseline_report(
                metric="invalid_metric",
                sector=None,
                start=date(2023, 1, 1),
                end=date(2024, 12, 31),
            )

    def test_baseline_report_default_dates(self):
        """Test baseline report with default dates."""
        series_data = {
            "LMIS_RETENTION_TS": [
                (f"2023-{i:02d}", 100 + i) for i in range(1, 13)
            ]
            + [(f"2024-{i:02d}", 110 + i) for i in range(1, 13)]
        }

        client = MockDataClient(series_data)
        agent = TimeMachineAgent(client)

        # Should use default dates (2 years ago to today)
        report = agent.baseline_report(metric="retention", sector=None)

        assert isinstance(report, str)


class TestTrendReport:
    """Test trend_report method."""

    def test_trend_report_basic(self):
        """Test trend report with valid data."""
        series_data = {
            "LMIS_QATARIZATION_TS": [
                (f"2023-{i:02d}", 50 + i) for i in range(1, 13)
            ]
            + [(f"2024-{i:02d}", 60 + i) for i in range(1, 13)]
        }

        client = MockDataClient(series_data)
        agent = TimeMachineAgent(client)

        report = agent.trend_report(
            metric="qatarization",
            sector=None,
            start=date(2023, 1, 1),
            end=date(2024, 12, 31),
        )

        assert isinstance(report, str)
        assert "Trend Summary" in report
        assert "Growth Rates" in report
        assert "YoY %" in report
        assert "QID=" in report

    def test_trend_report_includes_slopes(self):
        """Test trend report includes slope analysis."""
        series_data = {
            "LMIS_RETENTION_TS": [
                (f"2023-{i:02d}", 100 + i * 2) for i in range(1, 13)
            ]
        }

        client = MockDataClient(series_data)
        agent = TimeMachineAgent(client)

        report = agent.trend_report(
            metric="retention",
            sector=None,
            start=date(2023, 1, 1),
            end=date(2023, 12, 31),
        )

        assert "Slope Analysis" in report
        assert "month slope" in report

    def test_trend_report_insufficient_data(self):
        """Test trend report with insufficient data."""
        series_data = {
            "LMIS_RETENTION_TS": [
                ("2024-01", 100),
                ("2024-02", 110),
            ]
        }

        client = MockDataClient(series_data)
        agent = TimeMachineAgent(client)

        with pytest.raises(ValueError, match="Insufficient data"):
            agent.trend_report(
                metric="retention",
                sector=None,
                start=date(2024, 1, 1),
                end=date(2024, 12, 31),
            )

    def test_trend_report_confidence_hint(self):
        """Trend report should surface confidence hints from Step 22."""
        series_data = {
            "LMIS_RETENTION_TS": [
                (f"2023-{i:02d}", 100 + i) for i in range(1, 13)
            ]
            + [(f"2024-{i:02d}", 110 + i) for i in range(1, 13)]
        }

        client = MockDataClient(series_data)
        agent = TimeMachineAgent(client)

        report = agent.trend_report(
            metric="retention",
            sector=None,
            start=date(2023, 1, 1),
            end=date(2024, 12, 31),
            confidence_hint={"score": 0.82, "band": "GREEN"},
        )

        assert "Confidence hint (Step 22): 82/100 (GREEN)." in report


class TestBreaksReport:
    """Test breaks_report method."""

    def test_breaks_report_basic(self):
        """Test breaks report with valid data."""
        # Create series with clear break
        series_data = {
            "LMIS_SALARY_TS": [
                (f"2023-{i:02d}", 5000) for i in range(1, 7)
            ]
            + [(f"2023-{i:02d}", 8000) for i in range(7, 13)]  # Jump at month 7
            + [(f"2024-{i:02d}", 8000) for i in range(1, 13)]
        }

        client = MockDataClient(series_data)
        agent = TimeMachineAgent(client)

        report = agent.breaks_report(
            metric="salary",
            sector=None,
            start=date(2023, 1, 1),
            end=date(2024, 12, 31),
            z_threshold=2.0,
            cusum_h=3.0,
        )

        assert isinstance(report, str)
        assert "Structural Break" in report
        assert "QID=" in report
        assert "Audit Trail" in report
        assert "Why Flagged" in report

    def test_breaks_report_custom_thresholds(self):
        """Test breaks report with custom thresholds."""
        series_data = {
            "LMIS_RETENTION_TS": [
                (f"2023-{i:02d}", 80 + i) for i in range(1, 13)
            ]
        }

        client = MockDataClient(series_data)
        agent = TimeMachineAgent(client)

        report = agent.breaks_report(
            metric="retention",
            sector=None,
            start=date(2023, 1, 1),
            end=date(2023, 12, 31),
            z_threshold=3.0,
            cusum_h=6.0,
        )

        assert isinstance(report, str)
        assert "threshold=3.0" in report
        assert "h=6.0" in report

    def test_breaks_report_insufficient_data(self):
        """Test breaks report with insufficient data."""
        series_data = {
            "LMIS_RETENTION_TS": [
                ("2024-01", 100),
                ("2024-02", 110),
            ]
        }

        client = MockDataClient(series_data)
        agent = TimeMachineAgent(client)

        with pytest.raises(ValueError, match="Insufficient data"):
            agent.breaks_report(
                metric="retention",
                sector=None,
                start=date(2024, 1, 1),
                end=date(2024, 12, 31),
            )


class TestFetchSeries:
    """Test _fetch_series internal method."""

    def test_fetch_series_basic(self):
        """Test basic series fetching."""
        series_data = {
            "LMIS_RETENTION_TS": [
                (f"2024-{i:02d}", 100 + i) for i in range(1, 13)
            ]
        }

        client = MockDataClient(series_data)
        agent = TimeMachineAgent(client)

        result, values, dates = agent._fetch_series(
            metric="retention",
            sector=None,
            start=date(2024, 1, 1),
            end=date(2024, 12, 31),
        )

        assert isinstance(result, QueryResult)
        assert len(values) == 12
        assert len(dates) == 12

    def test_fetch_series_date_filtering(self):
        """Test series fetching with date filtering."""
        series_data = {
            "LMIS_RETENTION_TS": [
                (f"2023-{i:02d}", 100 + i) for i in range(1, 13)
            ]
            + [(f"2024-{i:02d}", 110 + i) for i in range(1, 13)]
        }

        client = MockDataClient(series_data)
        agent = TimeMachineAgent(client)

        # Fetch only 2024 data
        result, values, dates = agent._fetch_series(
            metric="retention",
            sector=None,
            start=date(2024, 1, 1),
            end=date(2024, 12, 31),
        )

        assert len(values) == 12
        assert all("2024" in d for d in dates)

    def test_fetch_series_invalid_metric(self):
        """Test fetch_series with invalid metric."""
        client = MockDataClient()
        agent = TimeMachineAgent(client)

        with pytest.raises(ValueError, match="not in series_map"):
            agent._fetch_series(
                metric="invalid",
                sector=None,
                start=date(2024, 1, 1),
                end=date(2024, 12, 31),
            )

    def test_fetch_series_no_data(self):
        """Test fetch_series when no data returned."""
        client = MockDataClient()  # No series_data
        agent = TimeMachineAgent(client)

        with pytest.raises(ValueError, match="No data returned"):
            agent._fetch_series(
                metric="retention",
                sector=None,
                start=date(2024, 1, 1),
                end=date(2024, 12, 31),
            )


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_series_map(self):
        """Test agent with empty series map."""
        client = MockDataClient()
        agent = TimeMachineAgent(client, series_map={})

        with pytest.raises(ValueError, match="not in series_map"):
            agent.baseline_report("any_metric", None)

    def test_report_methods_return_strings(self):
        """Test all report methods return strings."""
        series_data = {
            "LMIS_RETENTION_TS": [
                (f"2023-{i:02d}", 100 + i) for i in range(1, 13)
            ]
            + [(f"2024-{i:02d}", 110 + i) for i in range(1, 13)]
        }

        client = MockDataClient(series_data)
        agent = TimeMachineAgent(client)

        baseline = agent.baseline_report("retention", None)
        trend = agent.trend_report("retention", None)
        breaks = agent.breaks_report("retention", None)

        assert isinstance(baseline, str)
        assert isinstance(trend, str)
        assert isinstance(breaks, str)

    def test_reports_include_citations(self):
        """Test all reports include query ID citations."""
        series_data = {
            "LMIS_RETENTION_TS": [
                (f"2023-{i:02d}", 100 + i) for i in range(1, 13)
            ]
            + [(f"2024-{i:02d}", 110 + i) for i in range(1, 13)]
        }

        client = MockDataClient(series_data)
        agent = TimeMachineAgent(client)

        baseline = agent.baseline_report("retention", None)
        trend = agent.trend_report("retention", None)
        breaks = agent.breaks_report("retention", None)

        # All should include QID citations
        assert "QID=" in baseline
        assert "QID=" in trend
        assert "QID=" in breaks

        # All should include original query ID
        assert "LMIS_RETENTION_TS" in baseline
        assert "LMIS_RETENTION_TS" in trend
        assert "LMIS_RETENTION_TS" in breaks
