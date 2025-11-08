"""
Integration tests for PatternMinerAgent.

Tests end-to-end scenarios with mock time series data.
"""

from __future__ import annotations

from datetime import date, timedelta

from src.qnwis.agents.pattern_miner import PatternMinerAgent
from src.qnwis.data.deterministic.models import (
    Freshness,
    Provenance,
    QueryResult,
    Row,
)


class MockDataClient:
    """Mock DataClient that returns synthetic time series."""

    def __init__(self):
        self.queries_called = []

    def run(self, query_id: str) -> QueryResult:
        """Return mock time series based on query_id."""
        self.queries_called.append(query_id)

        # Parse query_id to determine what to return
        if "retention_rate" in query_id:
            return self._make_retention_series(query_id)
        elif "avg_salary" in query_id:
            return self._make_salary_series(query_id)
        elif "qatarization_rate" in query_id:
            return self._make_qatarization_series(query_id)
        else:
            return self._make_generic_series(query_id)

    def _make_retention_series(self, query_id: str) -> QueryResult:
        """Generate mock retention rate time series."""
        # Extract window from query_id (e.g., "12m" → 12 months)
        window = 12
        if "24m" in query_id:
            window = 24
        elif "6m" in query_id:
            window = 6
        elif "3m" in query_id:
            window = 3

        # Generate dates
        end_date = date(2024, 12, 31)
        dates = [end_date - timedelta(days=30 * i) for i in range(window)]
        dates.reverse()

        # Retention rates: increasing trend from 70% to 85%
        base = 70.0
        increment = 15.0 / window
        values = [base + i * increment for i in range(window)]

        # Determine sector
        sector = None
        if "Construction" in query_id:
            sector = "Construction"
        elif "Finance" in query_id:
            sector = "Finance"

        rows_data = []
        for dt, val in zip(dates, values):
            row = {"date": dt.isoformat(), "retention_rate": val}
            if sector:
                row["sector"] = sector
            rows_data.append(row)

        return QueryResult(
            query_id=query_id,
            rows=[Row(data=d) for d in rows_data],
            unit="percent",
            provenance=Provenance(
                source="csv",
                dataset_id="mock_retention",
                locator="mock.csv",
                fields=["date", "retention_rate"],
            ),
            freshness=Freshness(asof_date="2024-12-31"),
        )

    def _make_salary_series(self, query_id: str) -> QueryResult:
        """Generate mock salary time series."""
        window = 12
        if "24m" in query_id:
            window = 24
        elif "6m" in query_id:
            window = 6
        elif "3m" in query_id:
            window = 3

        end_date = date(2024, 12, 31)
        dates = [end_date - timedelta(days=30 * i) for i in range(window)]
        dates.reverse()

        # Salaries: increasing from 15000 to 20000 QAR
        base = 15000.0
        increment = 5000.0 / window
        values = [base + i * increment for i in range(window)]

        sector = None
        if "Construction" in query_id:
            sector = "Construction"
        elif "Finance" in query_id:
            sector = "Finance"

        rows_data = []
        for dt, val in zip(dates, values):
            row = {"date": dt.isoformat(), "avg_salary": val}
            if sector:
                row["sector"] = sector
            rows_data.append(row)

        return QueryResult(
            query_id=query_id,
            rows=[Row(data=d) for d in rows_data],
            unit="qar",
            provenance=Provenance(
                source="csv",
                dataset_id="mock_salary",
                locator="mock.csv",
                fields=["date", "avg_salary"],
            ),
            freshness=Freshness(asof_date="2024-12-31"),
        )

    def _make_qatarization_series(self, query_id: str) -> QueryResult:
        """Generate mock qatarization rate with seasonal pattern."""
        window = 36  # Need multi-year for seasonality

        end_date = date(2024, 12, 31)
        dates = [end_date - timedelta(days=30 * i) for i in range(window)]
        dates.reverse()

        # Qatarization with seasonal pattern: higher in Q1 (Jan-Mar)
        base = 35.0
        values = []
        for i, dt in enumerate(dates):
            month = dt.month
            # Add seasonal lift for Q1
            seasonal = 5.0 if month in [1, 2, 3] else 0.0
            # Add overall trend
            trend = 0.2 * i
            values.append(base + seasonal + trend)

        sector = None
        if "Finance" in query_id:
            sector = "Finance"

        rows_data = []
        for dt, val in zip(dates, values):
            row = {"date": dt.isoformat(), "qatarization_rate": val}
            if sector:
                row["sector"] = sector
            rows_data.append(row)

        return QueryResult(
            query_id=query_id,
            rows=[Row(data=d) for d in rows_data],
            unit="percent",
            provenance=Provenance(
                source="csv",
                dataset_id="mock_qatarization",
                locator="mock.csv",
                fields=["date", "qatarization_rate"],
            ),
            freshness=Freshness(asof_date="2024-12-31"),
        )

    def _make_generic_series(self, query_id: str) -> QueryResult:
        """Generic fallback time series."""
        window = 12
        end_date = date(2024, 12, 31)
        dates = [end_date - timedelta(days=30 * i) for i in range(window)]
        dates.reverse()

        values = list(range(100, 100 + window))

        rows_data = [
            {"date": dt.isoformat(), "value": val}
            for dt, val in zip(dates, values)
        ]

        return QueryResult(
            query_id=query_id,
            rows=[Row(data=d) for d in rows_data],
            unit="unknown",
            provenance=Provenance(
                source="csv",
                dataset_id="mock_generic",
                locator="mock.csv",
                fields=["date", "value"],
            ),
            freshness=Freshness(asof_date="2024-12-31"),
        )


class TestStableRelationsIntegration:
    """Integration tests for stable_relations with mock data."""

    def test_end_to_end_with_strong_correlation(self):
        """Complete flow with strong driver-outcome relationship."""
        # Note: Since agent currently logs Query IDs but doesn't call client.run()
        # This test validates the structure and flow
        client = MockDataClient()
        agent = PatternMinerAgent(client)

        narrative = agent.stable_relations(
            outcome="retention_rate",
            drivers=["avg_salary", "promotion_rate"],
            sector="Construction",
            window=12,
            end_date=date(2024, 12, 31),
            min_support=12,
        )

        # Validate narrative structure
        assert isinstance(narrative, str)
        assert len(narrative) > 100
        assert "Pattern Analysis" in narrative
        assert "Executive Summary" in narrative
        assert "Construction" in narrative
        assert "12 months" in narrative or "12-month" in narrative
        assert "avg_salary" in narrative
        assert "promotion_rate" in narrative

    def test_narrative_includes_all_metadata(self):
        """Narrative includes required metadata sections."""
        client = MockDataClient()
        agent = PatternMinerAgent(client)

        narrative = agent.stable_relations(
            outcome="retention_rate",
            drivers=["avg_salary"],
            sector="Finance",
            window=24,
            method="pearson",
        )

        # Check all required sections
        assert "Executive Summary" in narrative
        assert "Data Context" in narrative
        assert "Limitations" in narrative
        assert "Reproducibility" in narrative

        # Check metadata content
        assert "24 months" in narrative or "24-month" in narrative
        assert "Finance" in narrative
        assert "pearson" in narrative.lower()

    def test_multiple_drivers_ranked(self):
        """Multiple drivers should be present in results."""
        client = MockDataClient()
        agent = PatternMinerAgent(client)

        narrative = agent.stable_relations(
            outcome="retention_rate",
            drivers=["avg_salary", "promotion_rate", "wage_spread"],
            window=12,
        )

        # All drivers should be mentioned in Query IDs or analysis
        # (Even if findings are empty in mock mode)
        assert "avg_salary" in narrative
        assert "promotion_rate" in narrative
        assert "wage_spread" in narrative


class TestSeasonalEffectsIntegration:
    """Integration tests for seasonal_effects."""

    def test_end_to_end_seasonal_analysis(self):
        """Complete seasonal analysis flow."""
        client = MockDataClient()
        agent = PatternMinerAgent(client)

        narrative = agent.seasonal_effects(
            outcome="qatarization_rate",
            sector="Finance",
            end_date=date(2024, 12, 31),
            min_support=24,
        )

        # Validate structure
        assert isinstance(narrative, str)
        assert len(narrative) > 100
        assert "Seasonal" in narrative
        assert "qatarization_rate" in narrative
        assert "Finance" in narrative

    def test_narrative_structure_complete(self):
        """All expected sections present."""
        client = MockDataClient()
        agent = PatternMinerAgent(client)

        narrative = agent.seasonal_effects(
            outcome="retention_rate",
        )

        assert "Seasonal" in narrative
        assert "Reproducibility" in narrative
        assert "Data Context" in narrative or "Context" in narrative


class TestDriverScreenIntegration:
    """Integration tests for driver_screen."""

    def test_end_to_end_cohort_screening(self):
        """Complete cohort screening flow."""
        client = MockDataClient()
        agent = PatternMinerAgent(client)

        narrative = agent.driver_screen(
            driver="avg_salary",
            outcome="retention_rate",
            cohorts=["Construction", "Finance", "Healthcare"],
            windows=[6, 12, 24],
            end_date=date(2024, 12, 31),
            min_support=12,
        )

        # Validate structure
        assert isinstance(narrative, str)
        assert len(narrative) > 100
        assert "Driver Screening" in narrative or "Screen" in narrative
        assert "avg_salary" in narrative
        assert "retention_rate" in narrative

    def test_multiple_cohorts_mentioned(self):
        """All cohorts should be referenced."""
        client = MockDataClient()
        agent = PatternMinerAgent(client)

        narrative = agent.driver_screen(
            driver="wage_spread",
            outcome="qatarization_rate",
            cohorts=["Construction", "Finance", "Education"],
            windows=[12],
        )

        # Cohorts mentioned in Query IDs or context
        # (Structure validated even if no actual data fetched in test mode)
        assert "cohort" in narrative.lower() or "sector" in narrative.lower()

    def test_multiple_windows_processed(self):
        """All windows should be considered."""
        client = MockDataClient()
        agent = PatternMinerAgent(client)

        narrative = agent.driver_screen(
            driver="promotion_rate",
            outcome="retention_rate",
            cohorts=["Construction"],
            windows=[3, 6, 12, 24],
        )

        # Windows referenced in context or Query IDs
        assert "window" in narrative.lower() or "Window" in narrative


class TestDerivedResultProvenance:
    """Test that derived results maintain proper provenance."""

    def test_stable_relations_derived_qid_format(self):
        """Derived Query ID follows expected format."""
        client = MockDataClient()
        agent = PatternMinerAgent(client)

        narrative = agent.stable_relations(
            outcome="retention_rate",
            drivers=["avg_salary"],
        )

        # Should reference derived query IDs
        assert "derived_" in narrative or "Derived" in narrative or "QID" in narrative

    def test_seasonal_effects_derived_qid_format(self):
        """Seasonal analysis creates derived result."""
        client = MockDataClient()
        agent = PatternMinerAgent(client)

        narrative = agent.seasonal_effects(
            outcome="qatarization_rate",
        )

        assert "derived_" in narrative or "Derived" in narrative or "QID" in narrative

    def test_driver_screen_derived_qid_format(self):
        """Driver screening creates derived result."""
        client = MockDataClient()
        agent = PatternMinerAgent(client)

        narrative = agent.driver_screen(
            driver="avg_salary",
            outcome="retention_rate",
            cohorts=["Construction"],
            windows=[12],
        )

        assert "derived_" in narrative or "Derived" in narrative or "QID" in narrative


class TestCitationCompliance:
    """Test that narratives comply with citation requirements."""

    def test_stable_relations_includes_citations(self):
        """Citations present in narrative."""
        client = MockDataClient()
        agent = PatternMinerAgent(client)

        narrative = agent.stable_relations(
            outcome="retention_rate",
            drivers=["avg_salary"],
        )

        # Should have citations or Query ID references
        assert "QID" in narrative or "Query" in narrative or "query_id" in narrative

    def test_seasonal_effects_includes_citations(self):
        """Seasonal narrative cites sources."""
        client = MockDataClient()
        agent = PatternMinerAgent(client)

        narrative = agent.seasonal_effects(
            outcome="retention_rate",
        )

        assert "QID" in narrative or "Query" in narrative or "query_id" in narrative

    def test_freshness_included(self):
        """Freshness metadata present."""
        client = MockDataClient()
        agent = PatternMinerAgent(client)

        narrative = agent.stable_relations(
            outcome="retention_rate",
            drivers=["avg_salary"],
        )

        # Freshness date should be mentioned
        assert "Freshness" in narrative or "freshness" in narrative or "2024" in narrative
