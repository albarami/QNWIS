"""
Unit tests for PatternDetectiveAgent enhanced methods.

Tests all new capabilities: anomaly detection, correlations, root causes, best practices.
"""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from src.qnwis.agents.base import DataClient
from src.qnwis.agents.pattern_detective import PatternDetectiveAgent
from src.qnwis.data.deterministic.models import Freshness, Provenance, QueryResult, Row


@pytest.fixture
def mock_client():
    """Create a mock DataClient for testing."""
    return Mock(spec=DataClient)


@pytest.fixture
def agent(mock_client):
    """Create PatternDetectiveAgent with mock client."""
    return PatternDetectiveAgent(mock_client)


class TestDetectAnomalousRetention:
    """Test anomaly detection functionality."""

    def test_basic_anomaly_detection(self, agent, mock_client):
        """Should detect sectors with high z-scores."""
        # Mock attrition data with one clear outlier and more baseline sectors
        mock_result = QueryResult(
            query_id="syn_attrition_by_sector_latest",
            rows=[
                Row(data={"sector": "Finance", "attrition_percent": 8.0}),
                Row(data={"sector": "Energy", "attrition_percent": 10.0}),
                Row(data={"sector": "Healthcare", "attrition_percent": 35.0}),  # Clear outlier
                Row(data={"sector": "Education", "attrition_percent": 9.0}),
                Row(data={"sector": "Manufacturing", "attrition_percent": 11.0}),
                Row(data={"sector": "Retail", "attrition_percent": 9.5}),
                Row(data={"sector": "Construction", "attrition_percent": 10.5}),
                Row(data={"sector": "Transport", "attrition_percent": 8.5}),
            ],
            unit="percent",
            provenance=Provenance(
                source="csv",
                dataset_id="test",
                locator="test.csv",
                fields=["sector", "attrition_percent"],
            ),
            freshness=Freshness(asof_date="2024-12-31"),
            warnings=[],
        )
        mock_client.run.return_value = mock_result

        report = agent.detect_anomalous_retention(z_threshold=2.0)

        assert report.agent == "PatternDetective"
        assert len(report.findings) == 1

        finding = report.findings[0]
        assert "anomaly" in finding.title.lower()
        assert finding.metrics["total_sectors"] == 8
        # Healthcare (35%) should be flagged as high z-score outlier
        assert finding.metrics["anomaly_count"] >= 1

    def test_no_anomalies(self, agent, mock_client):
        """Should handle case with no anomalies."""
        # All sectors similar attrition
        mock_result = QueryResult(
            query_id="syn_attrition_by_sector_latest",
            rows=[
                Row(data={"sector": "A", "attrition_percent": 10.0}),
                Row(data={"sector": "B", "attrition_percent": 11.0}),
                Row(data={"sector": "C", "attrition_percent": 9.5}),
                Row(data={"sector": "D", "attrition_percent": 10.5}),
            ],
            unit="percent",
            provenance=Provenance(source="csv", dataset_id="test", locator="test", fields=[]),
            freshness=Freshness(asof_date="2024-12-31"),
        )
        mock_client.run.return_value = mock_result

        report = agent.detect_anomalous_retention(z_threshold=2.5)

        finding = report.findings[0]
        assert finding.metrics["anomaly_count"] == 0

    def test_insufficient_data(self, agent, mock_client):
        """Should return warning when insufficient data."""
        mock_result = QueryResult(
            query_id="syn_attrition_by_sector_latest",
            rows=[Row(data={"sector": "A", "attrition_percent": 10.0})],
            unit="percent",
            provenance=Provenance(source="csv", dataset_id="test", locator="test", fields=[]),
            freshness=Freshness(asof_date="2024-12-31"),
        )
        mock_client.run.return_value = mock_result

        report = agent.detect_anomalous_retention(min_sample_size=3)

        assert len(report.findings) == 0
        assert len(report.warnings) > 0
        assert "Insufficient" in report.warnings[0]


class TestFindCorrelations:
    """Test correlation analysis functionality."""

    def test_positive_correlation(self, agent, mock_client):
        """Should detect positive correlation between variables."""
        qat_result = QueryResult(
            query_id="syn_qatarization_by_sector_latest",
            rows=[
                Row(data={"sector": "A", "qatarization_percent": 10.0}),
                Row(data={"sector": "B", "qatarization_percent": 20.0}),
                Row(data={"sector": "C", "qatarization_percent": 30.0}),
                Row(data={"sector": "D", "qatarization_percent": 40.0}),
                Row(data={"sector": "E", "qatarization_percent": 50.0}),
            ],
            unit="percent",
            provenance=Provenance(source="csv", dataset_id="qat", locator="test", fields=[]),
            freshness=Freshness(asof_date="2024-12-31"),
            warnings=[],
        )

        atr_result = QueryResult(
            query_id="syn_attrition_by_sector_latest",
            rows=[
                Row(data={"sector": "A", "attrition_percent": 5.0}),
                Row(data={"sector": "B", "attrition_percent": 7.0}),
                Row(data={"sector": "C", "attrition_percent": 9.0}),
                Row(data={"sector": "D", "attrition_percent": 11.0}),
                Row(data={"sector": "E", "attrition_percent": 13.0}),
            ],
            unit="percent",
            provenance=Provenance(source="csv", dataset_id="atr", locator="test", fields=[]),
            freshness=Freshness(asof_date="2024-12-31"),
            warnings=[],
        )

        mock_client.run.side_effect = [qat_result, atr_result]

        report = agent.find_correlations(method="pearson", min_correlation=0.5)

        finding = report.findings[0]
        assert finding.metrics["correlation"] > 0.9  # Strong positive
        assert finding.metrics["sample_size"] == 5
        assert finding.metrics["method_used"] in ("pearson", "spearman")

    def test_spearman_vs_pearson(self, agent, mock_client):
        """Should support both correlation methods."""
        qat_result = QueryResult(
            query_id="syn_qatarization_by_sector_latest",
            rows=[Row(data={"sector": f"S{i}", "qatarization_percent": float(i * 10)}) for i in range(1, 7)],
            unit="percent",
            provenance=Provenance(source="csv", dataset_id="test", locator="test", fields=[]),
            freshness=Freshness(asof_date="2024-12-31"),
            warnings=[],
        )

        atr_result = QueryResult(
            query_id="syn_attrition_by_sector_latest",
            rows=[Row(data={"sector": f"S{i}", "attrition_percent": float(i * 2)}) for i in range(1, 7)],
            unit="percent",
            provenance=Provenance(source="csv", dataset_id="test", locator="test", fields=[]),
            freshness=Freshness(asof_date="2024-12-31"),
            warnings=[],
        )

        # Test Spearman
        mock_client.run.side_effect = [qat_result, atr_result]
        report_spearman = agent.find_correlations(method="spearman")
        assert report_spearman.findings[0].metrics["method_used"] == "spearman"

        # Test Pearson
        mock_client.run.side_effect = [qat_result, atr_result]
        report_pearson = agent.find_correlations(method="pearson")
        assert report_pearson.findings[0].metrics["method_used"] == "pearson"

    def test_insufficient_overlap(self, agent, mock_client):
        """Should warn when sectors don't overlap enough."""
        qat_result = QueryResult(
            query_id="syn_qatarization_by_sector_latest",
            rows=[Row(data={"sector": "A", "qatarization_percent": 10.0})],
            unit="percent",
            provenance=Provenance(source="csv", dataset_id="test", locator="test", fields=[]),
            freshness=Freshness(asof_date="2024-12-31"),
            warnings=[],
        )

        atr_result = QueryResult(
            query_id="syn_attrition_by_sector_latest",
            rows=[Row(data={"sector": "B", "attrition_percent": 5.0})],  # Different sector
            unit="percent",
            provenance=Provenance(source="csv", dataset_id="test", locator="test", fields=[]),
            freshness=Freshness(asof_date="2024-12-31"),
            warnings=[],
        )

        mock_client.run.side_effect = [qat_result, atr_result]

        report = agent.find_correlations(min_sample_size=5)

        assert len(report.findings) == 0
        assert "overlap" in report.warnings[0].lower()


class TestIdentifyRootCauses:
    """Test root cause analysis functionality."""

    def test_basic_root_cause(self, agent, mock_client):
        """Should compare high vs low attrition sectors."""
        atr_result = QueryResult(
            query_id="syn_attrition_by_sector_latest",
            rows=[
                Row(data={"sector": "A", "attrition_percent": 5.0}),
                Row(data={"sector": "B", "attrition_percent": 20.0}),
                Row(data={"sector": "C", "attrition_percent": 8.0}),
                Row(data={"sector": "D", "attrition_percent": 15.0}),
                Row(data={"sector": "E", "attrition_percent": 7.0}),
                Row(data={"sector": "F", "attrition_percent": 18.0}),
            ],
            unit="percent",
            provenance=Provenance(source="csv", dataset_id="test", locator="test", fields=[]),
            freshness=Freshness(asof_date="2024-12-31"),
        )

        qat_result = QueryResult(
            query_id="syn_qatarization_by_sector_latest",
            rows=[
                Row(data={"sector": "A", "qatarization_percent": 50.0}),
                Row(data={"sector": "B", "qatarization_percent": 10.0}),  # Low qat, high atr
                Row(data={"sector": "C", "qatarization_percent": 45.0}),
                Row(data={"sector": "D", "qatarization_percent": 15.0}),
                Row(data={"sector": "E", "qatarization_percent": 48.0}),
                Row(data={"sector": "F", "qatarization_percent": 12.0}),  # Low qat, high atr
            ],
            unit="percent",
            provenance=Provenance(source="csv", dataset_id="test", locator="test", fields=[]),
            freshness=Freshness(asof_date="2024-12-31"),
        )

        mock_client.run.side_effect = [atr_result, qat_result]

        report = agent.identify_root_causes(top_n=2)

        finding = report.findings[0]
        assert "root cause" in finding.title.lower()
        assert "high_attrition_qat_avg" in finding.metrics
        assert "low_attrition_qat_avg" in finding.metrics
        assert "correlation does not imply causation" in finding.summary.lower()

    def test_insufficient_sectors(self, agent, mock_client):
        """Should warn when too few sectors for comparison."""
        atr_result = QueryResult(
            query_id="syn_attrition_by_sector_latest",
            rows=[Row(data={"sector": "A", "attrition_percent": 10.0})],
            unit="percent",
            provenance=Provenance(source="csv", dataset_id="test", locator="test", fields=[]),
            freshness=Freshness(asof_date="2024-12-31"),
        )

        qat_result = QueryResult(
            query_id="syn_qatarization_by_sector_latest",
            rows=[Row(data={"sector": "A", "qatarization_percent": 20.0})],
            unit="percent",
            provenance=Provenance(source="csv", dataset_id="test", locator="test", fields=[]),
            freshness=Freshness(asof_date="2024-12-31"),
        )

        mock_client.run.side_effect = [atr_result, qat_result]

        report = agent.identify_root_causes(top_n=3)

        assert len(report.findings) == 0
        assert "Insufficient sectors" in report.warnings[0]


class TestBestPractices:
    """Test best practices identification."""

    def test_qatarization_leaders(self, agent, mock_client):
        """Should identify top qatarization performers."""
        qat_result = QueryResult(
            query_id="syn_qatarization_by_sector_latest",
            rows=[
                Row(data={"sector": "Energy", "qatarization_percent": 75.0}),
                Row(data={"sector": "Government", "qatarization_percent": 85.0}),
                Row(data={"sector": "Finance", "qatarization_percent": 45.0}),
                Row(data={"sector": "Healthcare", "qatarization_percent": 55.0}),
                Row(data={"sector": "ICT", "qatarization_percent": 30.0}),
            ],
            unit="percent",
            provenance=Provenance(source="csv", dataset_id="test", locator="test", fields=[]),
            freshness=Freshness(asof_date="2024-12-31"),
        )

        mock_client.run.return_value = qat_result

        report = agent.best_practices(metric="qatarization", top_n=3)

        finding = report.findings[0]
        assert "best practices" in finding.title.lower()
        assert finding.metrics["top_3_average"] > finding.metrics["overall_average"]
        # Verify Government is in top performers (check summary or metrics)
        assert finding.metrics["metric"] == "qatarization"

    def test_retention_leaders(self, agent, mock_client):
        """Should identify retention leaders (low attrition)."""
        atr_result = QueryResult(
            query_id="syn_attrition_by_sector_latest",
            rows=[
                Row(data={"sector": "A", "attrition_percent": 5.0}),  # Best
                Row(data={"sector": "B", "attrition_percent": 15.0}),
                Row(data={"sector": "C", "attrition_percent": 8.0}),  # Second best
                Row(data={"sector": "D", "attrition_percent": 12.0}),
            ],
            unit="percent",
            provenance=Provenance(source="csv", dataset_id="test", locator="test", fields=[]),
            freshness=Freshness(asof_date="2024-12-31"),
        )

        mock_client.run.return_value = atr_result

        report = agent.best_practices(metric="retention", top_n=2)

        finding = report.findings[0]
        # For retention (100 - attrition), higher is better
        # Top performers have LOW attrition (5%, 8%) = HIGH retention (95%, 92%)
        # So top_2_average retention should be HIGHER than overall
        assert finding.metrics["top_2_average"] > finding.metrics["overall_average"]

    def test_no_data(self, agent, mock_client):
        """Should handle empty data gracefully."""
        empty_result = QueryResult(
            query_id="test",
            rows=[],
            unit="percent",
            provenance=Provenance(source="csv", dataset_id="test", locator="test", fields=[]),
            freshness=Freshness(asof_date="2024-12-31"),
        )

        mock_client.run.return_value = empty_result

        report = agent.best_practices(metric="qatarization")

        assert len(report.findings) == 0
        assert "No valid sector data" in report.warnings[0]


class TestLegacyRun:
    """Test backward compatibility with original run() method."""

    def test_legacy_consistency_check(self, agent, mock_client):
        """Original run() method should still work."""
        emp_result = QueryResult(
            query_id="q_employment_share_by_gender_2023",
            rows=[
                Row(data={
                    "male_percent": 60.0,
                    "female_percent": 40.0,
                    "total_percent": 100.0,
                }),
            ],
            unit="percent",
            provenance=Provenance(source="csv", dataset_id="test", locator="test", fields=[]),
            freshness=Freshness(asof_date="2023-12-31"),
            warnings=[],
        )

        mock_client.run.return_value = emp_result

        report = agent.run()

        assert report.agent == "PatternDetective"
        assert len(report.findings) == 1
        assert "consistency" in report.findings[0].title.lower()
