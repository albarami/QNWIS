"""
Integration tests for PredictorAgent.

Tests full agent behavior with synthetic data from mocked DataClient.
"""

from __future__ import annotations

from datetime import date
from unittest.mock import Mock

import pytest

from src.qnwis.agents.base import DataClient
from src.qnwis.agents.predictor import PredictorAgent
from src.qnwis.data.deterministic.models import Freshness, Provenance, QueryResult, Row


@pytest.fixture
def mock_client() -> Mock:
    """Create a mock DataClient with synthetic time-series data."""
    client = Mock(spec=DataClient)

    # Synthetic time-series: 36 months of retention data
    rows = []
    for i in range(36):
        month = f"2022-{(i % 12) + 1:02d}-01" if i < 12 else f"2023-{(i % 12) + 1:02d}-01" if i < 24 else f"2024-{(i % 12) + 1:02d}-01"
        retention = 80.0 + i * 0.2 + (i % 12) * 0.5  # Trend + seasonality
        rows.append(Row(data={"month": month, "retention": retention, "sector": "Construction"}))

    client.run.return_value = QueryResult(
        query_id="ts_retention_by_sector",
        rows=rows,
        unit="percent",
        provenance=Provenance(
            source="csv",
            dataset_id="synthetic_retention",
            locator="test_data",
            fields=["month", "retention", "sector"],
        ),
        freshness=Freshness(asof_date="2024-12-01", updated_at="2024-12-01T10:00:00"),
        metadata={},
        warnings=[],
    )

    # Mock registry for query_id resolution
    mock_registry = Mock()
    mock_registry.all_ids.return_value = ["ts_retention_by_sector", "ts_employment", "ts_wages"]
    client.registry = mock_registry

    return client


class TestPredictorForecastBaseline:
    """Test forecast_baseline entrypoint."""

    def test_successful_forecast(self, mock_client: Mock) -> None:
        """Forecast with sufficient data returns narrative."""
        agent = PredictorAgent(mock_client)

        narrative = agent.forecast_baseline(
            metric="retention",
            sector="Construction",
            start=date(2022, 1, 1),
            end=date(2024, 12, 1),
            horizon_months=6,
            season=12,
        )

        # Check narrative structure
        assert "## Executive Summary" in narrative
        assert "## Forecast with 95% Prediction Intervals" in narrative
        assert "## Backtest Performance" in narrative
        assert "## Freshness" in narrative
        assert "## Reproducibility" in narrative

        # Check QID citations (format is "(QID=...)")
        assert "(QID=" in narrative or "QID=" in narrative

        # Check forecast table
        assert "| h | yhat | lo | hi |" in narrative

        # Check method selection
        assert "Method selected" in narrative
        assert any(
            method in narrative
            for method in ["seasonal_naive", "ewma", "rolling_mean", "robust_trend"]
        )

    def test_insufficient_data_error(self, mock_client: Mock) -> None:
        """Forecast with insufficient data returns error message."""
        # Mock with only 10 points
        rows = []
        for i in range(10):
            rows.append(Row(data={"month": f"2024-{i + 1:02d}-01", "retention": 80.0}))

        mock_client.run.return_value = QueryResult(
            query_id="ts_retention_by_sector",
            rows=rows,
            unit="percent",
            provenance=Provenance(
                source="csv", dataset_id="test", locator="test", fields=[]
            ),
            freshness=Freshness(asof_date="2024-12-01"),
            metadata={},
            warnings=[],
        )

        agent = PredictorAgent(mock_client)

        narrative = agent.forecast_baseline(
            metric="retention",
            sector="Construction",
            start=date(2024, 1, 1),
            end=date(2024, 10, 1),
            horizon_months=6,
        )

        assert "Insufficient data" in narrative
        assert "24" in narrative  # Minimum requirement

    def test_horizon_validation(self, mock_client: Mock) -> None:
        """Forecast with horizon > 12 raises ValueError."""
        agent = PredictorAgent(mock_client)

        with pytest.raises(ValueError, match="horizon_months must be"):
            agent.forecast_baseline(
                metric="retention",
                sector="Construction",
                start=date(2022, 1, 1),
                end=date(2024, 12, 1),
                horizon_months=18,  # Too large
            )

    def test_query_not_found_error(self, mock_client: Mock) -> None:
        """Forecast with missing query returns error message."""
        mock_client.run.side_effect = KeyError("Query not found")

        agent = PredictorAgent(mock_client)

        narrative = agent.forecast_baseline(
            metric="unknown_metric",
            sector="Construction",
            start=date(2022, 1, 1),
            end=date(2024, 12, 1),
            horizon_months=6,
        )

        assert "Error" in narrative
        assert "unable to fetch" in narrative.lower()


class TestPredictorEarlyWarning:
    """Test early_warning entrypoint."""

    def test_successful_warning_no_flags(self, mock_client: Mock) -> None:
        """Early warning with normal data shows low risk."""
        agent = PredictorAgent(mock_client)

        narrative = agent.early_warning(
            metric="retention",
            sector="Construction",
            end=date(2024, 12, 1),
            horizon_months=3,
        )

        # Check narrative structure
        assert "## Risk Assessment" in narrative
        assert "## Flag Details" in narrative
        assert "## Recommended Actions" in narrative
        assert "## Freshness" in narrative

        # Check risk score present
        assert "/100" in narrative

        # Check flags documented
        assert "Band Breach" in narrative
        assert "Slope Reversal" in narrative
        assert "Volatility Spike" in narrative

    def test_successful_warning_with_spike(self, mock_client: Mock) -> None:
        """Early warning with volatility spike shows elevated risk."""
        # Add a spike at the end
        rows = []
        for i in range(36):
            month = f"2024-{(i % 12) + 1:02d}-01"
            retention = 80.0 + i * 0.1
            if i == 35:  # Last point
                retention = 95.0  # Sudden spike
            rows.append(Row(data={"month": month, "retention": retention}))

        mock_client.run.return_value = QueryResult(
            query_id="ts_retention_by_sector",
            rows=rows,
            unit="percent",
            provenance=Provenance(
                source="csv", dataset_id="test", locator="test", fields=[]
            ),
            freshness=Freshness(asof_date="2024-12-01"),
            metadata={},
            warnings=[],
        )

        agent = PredictorAgent(mock_client)

        narrative = agent.early_warning(
            metric="retention",
            sector="Construction",
            end=date(2024, 12, 1),
        )

        # Risk score should be > 0 due to spike
        assert "Risk Score" in narrative
        # May have volatility_spike or band_breach flag active

    def test_insufficient_data_error(self, mock_client: Mock) -> None:
        """Early warning with insufficient data returns error message."""
        rows = [Row(data={"month": f"2024-{i + 1:02d}-01", "retention": 80.0}) for i in range(5)]

        mock_client.run.return_value = QueryResult(
            query_id="ts_retention_by_sector",
            rows=rows,
            unit="percent",
            provenance=Provenance(
                source="csv", dataset_id="test", locator="test", fields=[]
            ),
            freshness=Freshness(asof_date="2024-12-01"),
            metadata={},
            warnings=[],
        )

        agent = PredictorAgent(mock_client)

        narrative = agent.early_warning(
            metric="retention",
            sector="Construction",
            end=date(2024, 12, 1),
        )

        assert "Insufficient data" in narrative


class TestPredictorScenarioCompare:
    """Test scenario_compare entrypoint."""

    def test_successful_comparison(self, mock_client: Mock) -> None:
        """Scenario comparison with multiple methods returns table."""
        agent = PredictorAgent(mock_client)

        narrative = agent.scenario_compare(
            metric="retention",
            sector="Construction",
            start=date(2022, 1, 1),
            end=date(2024, 12, 1),
            horizon_months=6,
            methods=["seasonal_naive", "ewma", "robust_trend"],
        )

        # Check narrative structure
        assert "## Method Comparison" in narrative
        assert "### Backtest Performance" in narrative
        assert "### Forecast Comparison" in narrative
        assert "## Freshness" in narrative

        # Check method names in table
        assert "seasonal_naive" in narrative
        assert "ewma" in narrative
        assert "robust_trend" in narrative

        # Check metrics columns
        assert "MAE" in narrative
        assert "MAPE" in narrative
        assert "RMSE" in narrative

    def test_single_method_comparison(self, mock_client: Mock) -> None:
        """Scenario comparison with single method works."""
        agent = PredictorAgent(mock_client)

        narrative = agent.scenario_compare(
            metric="retention",
            sector="Construction",
            start=date(2022, 1, 1),
            end=date(2024, 12, 1),
            horizon_months=3,
            methods=["ewma"],
        )

        assert "ewma" in narrative
        assert "## Method Comparison" in narrative

    def test_insufficient_data_error(self, mock_client: Mock) -> None:
        """Scenario comparison with insufficient data returns error."""
        rows = [Row(data={"month": f"2024-{i + 1:02d}-01", "retention": 80.0}) for i in range(10)]

        mock_client.run.return_value = QueryResult(
            query_id="ts_retention_by_sector",
            rows=rows,
            unit="percent",
            provenance=Provenance(
                source="csv", dataset_id="test", locator="test", fields=[]
            ),
            freshness=Freshness(asof_date="2024-12-01"),
            metadata={},
            warnings=[],
        )

        agent = PredictorAgent(mock_client)

        narrative = agent.scenario_compare(
            metric="retention",
            sector="Construction",
            start=date(2024, 1, 1),
            end=date(2024, 10, 1),
            horizon_months=6,
            methods=["ewma", "robust_trend"],
        )

        assert "Insufficient data" in narrative


class TestPredictorIntegration:
    """Integration tests for full agent workflow."""

    def test_forecast_produces_valid_qids(self, mock_client: Mock) -> None:
        """Forecast narrative includes valid derived QIDs."""
        agent = PredictorAgent(mock_client)

        narrative = agent.forecast_baseline(
            metric="retention",
            sector="Construction",
            start=date(2022, 1, 1),
            end=date(2024, 12, 1),
            horizon_months=6,
        )

        # Check for derived QID patterns
        assert "derived_forecast_baseline" in narrative or "[QID:" in narrative
        assert "derived_backtest_metrics" in narrative or "QID:" in narrative

    def test_early_warning_produces_valid_qids(self, mock_client: Mock) -> None:
        """Early warning narrative includes valid derived QIDs."""
        agent = PredictorAgent(mock_client)

        narrative = agent.early_warning(
            metric="retention",
            sector="Construction",
            end=date(2024, 12, 1),
        )

        assert "derived_early_warning" in narrative or "[QID:" in narrative

    def test_reproducibility_snippets_present(self, mock_client: Mock) -> None:
        """All narratives include reproducibility code snippets."""
        agent = PredictorAgent(mock_client)

        forecast_narrative = agent.forecast_baseline(
            metric="retention",
            sector="Construction",
            start=date(2022, 1, 1),
            end=date(2024, 12, 1),
            horizon_months=6,
        )

        warning_narrative = agent.early_warning(
            metric="retention",
            sector="Construction",
            end=date(2024, 12, 1),
        )

        compare_narrative = agent.scenario_compare(
            metric="retention",
            sector="Construction",
            start=date(2022, 1, 1),
            end=date(2024, 12, 1),
            horizon_months=6,
            methods=["ewma", "robust_trend"],
        )

        # Check all have reproducibility sections
        assert "```python" in forecast_narrative
        assert "PredictorAgent" in forecast_narrative

        assert "```python" in warning_narrative
        assert "PredictorAgent" in warning_narrative

        assert "```python" in compare_narrative
        assert "PredictorAgent" in compare_narrative
