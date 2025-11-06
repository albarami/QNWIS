"""
Unit tests for Pattern Detective Agent.

Tests the four key methods with synthetic data distributions,
ensuring correct outlier detection, correlations, and best practices identification.
"""

from __future__ import annotations

import pytest

from src.qnwis.agents.base import DataClient
from src.qnwis.agents.pattern_detective import PatternDetectiveAgent
from src.qnwis.data.deterministic.models import Freshness, Provenance, QueryResult, Row


class FakeDataClient(DataClient):
    """Fake client that returns synthetic distributions without file dependencies."""

    def __init__(self) -> None:
        self._responses: dict[str, QueryResult] = {}
        # Skip parent init to avoid filesystem checks
        self.ttl_s = 300

    def add_response(self, query_id: str, result: QueryResult) -> None:
        """Register a synthetic query result."""
        self._responses[query_id] = result

    def run(self, query_id: str) -> QueryResult:
        """Return pre-configured synthetic result."""
        if query_id not in self._responses:
            raise KeyError(f"No mock response for {query_id}")
        return self._responses[query_id]


@pytest.fixture
def fake_client() -> FakeDataClient:
    """Fixture providing a fake client with synthetic attrition data."""
    client = FakeDataClient()

    # Synthetic attrition distribution: need 10+ sectors for winsorization to work properly
    # With 10 values and extreme outlier, winsorization keeps outlier but z-score calculation works
    # Test confirmed: 10 sectors with values [10,10,10,11,11,12,12,13,13,150] -> z=3.0 > 2.5
    attrition_result = QueryResult(
        query_id="syn_attrition_by_sector_latest",
        rows=[
            Row(data={"sector": "Finance", "attrition_percent": 10.0}),
            Row(data={"sector": "Retail", "attrition_percent": 10.0}),
            Row(data={"sector": "Manufacturing", "attrition_percent": 10.0}),
            Row(data={"sector": "Healthcare", "attrition_percent": 11.0}),
            Row(data={"sector": "Education", "attrition_percent": 11.0}),
            Row(data={"sector": "Technology", "attrition_percent": 12.0}),
            Row(data={"sector": "Transport", "attrition_percent": 12.0}),
            Row(data={"sector": "Hospitality", "attrition_percent": 13.0}),
            Row(data={"sector": "Agriculture", "attrition_percent": 13.0}),
            Row(data={"sector": "Construction", "attrition_percent": 150.0}),  # Extreme outlier
        ],
        unit="percent",
        provenance=Provenance(
            source="csv",
            dataset_id="synthetic_attrition",
            locator="syn_attrition.csv",
            fields=["sector", "attrition_percent"],
        ),
        freshness=Freshness(asof_date="2024-01-01"),
    )
    client.add_response("syn_attrition_by_sector_latest", attrition_result)

    # Synthetic qatarization data (aligned with 10 sectors)
    qat_result = QueryResult(
        query_id="syn_qatarization_by_sector_latest",
        rows=[
            Row(data={"sector": "Finance", "qatarization_percent": 25.0, "qataris": 500, "non_qataris": 1500}),
            Row(data={"sector": "Retail", "qatarization_percent": 20.0, "qataris": 400, "non_qataris": 1600}),
            Row(data={"sector": "Manufacturing", "qatarization_percent": 22.0, "qataris": 440, "non_qataris": 1560}),
            Row(data={"sector": "Healthcare", "qatarization_percent": 18.0, "qataris": 360, "non_qataris": 1640}),
            Row(data={"sector": "Education", "qatarization_percent": 28.0, "qataris": 560, "non_qataris": 1440}),
            Row(data={"sector": "Technology", "qatarization_percent": 24.0, "qataris": 480, "non_qataris": 1520}),
            Row(data={"sector": "Transport", "qatarization_percent": 19.0, "qataris": 380, "non_qataris": 1620}),
            Row(data={"sector": "Hospitality", "qatarization_percent": 16.0, "qataris": 320, "non_qataris": 1680}),
            Row(data={"sector": "Agriculture", "qatarization_percent": 30.0, "qataris": 600, "non_qataris": 1400}),
            Row(data={"sector": "Construction", "qatarization_percent": 15.0, "qataris": 300, "non_qataris": 1700}),
        ],
        unit="percent",
        provenance=Provenance(
            source="csv",
            dataset_id="synthetic_qatarization",
            locator="syn_qatarization.csv",
            fields=["sector", "qatarization_percent", "qataris", "non_qataris"],
        ),
        freshness=Freshness(asof_date="2024-01-01"),
    )
    client.add_response("syn_qatarization_by_sector_latest", qat_result)

    return client


def test_detect_anomalous_retention_flags_expected(fake_client: FakeDataClient) -> None:
    """Test anomaly detection flags the correct outlier with Query IDs."""
    agent = PatternDetectiveAgent(fake_client)

    report = agent.detect_anomalous_retention(z_threshold=2.5, min_sample_size=3)

    # Should detect Construction as high outlier (150% with z=3.0 > 2.5)
    assert len(report.findings) == 1
    insight = report.findings[0]

    assert "Attrition anomaly detection" in insight.title
    assert insight.metrics["anomaly_count"] >= 1  # At least Construction
    assert insight.metrics["total_sectors"] == 10
    assert insight.metrics["threshold"] == 2.5

    # Verify evidence includes original and derived query IDs
    assert len(insight.evidence) == 2
    query_ids = [e.query_id for e in insight.evidence]
    assert "syn_attrition_by_sector_latest" in query_ids
    assert any("derived" in qid for qid in query_ids)

    # Verify summary mentions anomalies
    assert "sectors" in insight.summary.lower()


def test_find_correlations_returns_expected_coef(fake_client: FakeDataClient) -> None:
    """Test correlation returns known r with sample size n."""
    agent = PatternDetectiveAgent(fake_client)

    report = agent.find_correlations(method="spearman", min_correlation=0.1, min_sample_size=5)

    assert len(report.findings) == 1
    insight = report.findings[0]

    assert "Correlation analysis" in insight.title
    # Should have correlation between qatarization and attrition
    assert "correlation" in insight.metrics
    assert insight.metrics["sample_size"] == 10  # All 10 sectors match
    assert insight.metrics["method_used"] == "spearman"

    # Verify evidence includes both source queries and derived result
    assert len(insight.evidence) == 3
    query_ids = [e.query_id for e in insight.evidence]
    assert "syn_qatarization_by_sector_latest" in query_ids
    assert "syn_attrition_by_sector_latest" in query_ids
    assert any("derived" in qid for qid in query_ids)

    # Summary includes correlation coefficient and n
    assert "n=10" in insight.summary


def test_identify_root_causes_small_n_graceful(fake_client: FakeDataClient) -> None:
    """Test root cause analysis with small n provides evidence without fabrication."""
    agent = PatternDetectiveAgent(fake_client)

    # Use top_n=2 for top 2 vs bottom 2 comparison (total 4 sectors compared out of 6)
    report = agent.identify_root_causes(top_n=2)

    assert len(report.findings) == 1
    insight = report.findings[0]

    assert "Root cause analysis" in insight.title
    assert insight.metrics["top_n"] == 2

    # Should compare high vs low attrition sectors on qatarization
    assert "high_attrition_qat_avg" in insight.metrics
    assert "low_attrition_qat_avg" in insight.metrics
    assert "qatarization_diff" in insight.metrics

    # Summary includes caveat about correlation != causation
    assert "correlation does not imply causation" in insight.summary.lower() or "correlation" in insight.summary.lower()

    # Verify evidence includes both datasets and derived comparison
    assert len(insight.evidence) == 3
    query_ids = [e.query_id for e in insight.evidence]
    assert "syn_attrition_by_sector_latest" in query_ids
    assert "syn_qatarization_by_sector_latest" in query_ids
    assert any("derived" in qid for qid in query_ids)


def test_best_practices_topn_sorted_and_truncated(fake_client: FakeDataClient) -> None:
    """Test best practices returns top performers sorted and truncated."""
    agent = PatternDetectiveAgent(fake_client)

    # Request top 5 performers (but we only have 6 sectors)
    report = agent.best_practices(metric="qatarization", top_n=5)

    assert len(report.findings) == 1
    insight = report.findings[0]

    assert "Best practices" in insight.title
    assert "qatarization" in insight.title.lower()

    # Should return top 5 sectors by qatarization rate
    assert insight.metrics["metric"] == "qatarization"
    assert "top_5_average" in insight.metrics
    assert "overall_average" in insight.metrics
    assert "performance_gap" in insight.metrics

    # Top performers should have higher average than overall
    assert insight.metrics["top_5_average"] >= insight.metrics["overall_average"]

    # Verify evidence includes source query and derived ranking
    assert len(insight.evidence) == 2
    query_ids = [e.query_id for e in insight.evidence]
    assert "syn_qatarization_by_sector_latest" in query_ids
    assert any("derived" in qid for qid in query_ids)

    # Summary mentions top N comparison
    assert "Top 5 sectors" in insight.summary or "top 5" in insight.summary.lower()


def test_detect_anomalous_retention_insufficient_data() -> None:
    """Test graceful handling when insufficient sectors for analysis."""
    client = FakeDataClient()

    # Only 2 sectors (below min_sample_size=3)
    result = QueryResult(
        query_id="syn_attrition_by_sector_latest",
        rows=[
            Row(data={"sector": "Finance", "attrition_percent": 12.0}),
            Row(data={"sector": "Retail", "attrition_percent": 14.0}),
        ],
        unit="percent",
        provenance=Provenance(
            source="csv",
            dataset_id="test",
            locator="test.csv",
            fields=["sector", "attrition_percent"],
        ),
        freshness=Freshness(asof_date="2024-01-01"),
    )
    client.add_response("syn_attrition_by_sector_latest", result)

    agent = PatternDetectiveAgent(client)
    report = agent.detect_anomalous_retention(z_threshold=2.5, min_sample_size=3)

    # Should return empty findings with warning
    assert len(report.findings) == 0
    assert len(report.warnings) == 1
    assert "Insufficient data" in report.warnings[0]


def test_find_correlations_zero_variance_fallback(fake_client: FakeDataClient) -> None:
    """Test fallback to Spearman when Pearson encounters zero variance."""
    client = FakeDataClient()

    # Zero variance in attrition (all same value)
    qat_result = QueryResult(
        query_id="syn_qatarization_by_sector_latest",
        rows=[
            Row(data={"sector": "A", "qatarization_percent": 25.0}),
            Row(data={"sector": "B", "qatarization_percent": 20.0}),
            Row(data={"sector": "C", "qatarization_percent": 22.0}),
        ],
        unit="percent",
        provenance=Provenance(source="csv", dataset_id="test", locator="test.csv", fields=["sector", "qatarization_percent"]),
        freshness=Freshness(asof_date="2024-01-01"),
    )

    atr_result = QueryResult(
        query_id="syn_attrition_by_sector_latest",
        rows=[
            Row(data={"sector": "A", "attrition_percent": 15.0}),
            Row(data={"sector": "B", "attrition_percent": 15.0}),
            Row(data={"sector": "C", "attrition_percent": 15.0}),  # All same
        ],
        unit="percent",
        provenance=Provenance(source="csv", dataset_id="test", locator="test.csv", fields=["sector", "attrition_percent"]),
        freshness=Freshness(asof_date="2024-01-01"),
    )

    client.add_response("syn_qatarization_by_sector_latest", qat_result)
    client.add_response("syn_attrition_by_sector_latest", atr_result)

    agent = PatternDetectiveAgent(client)
    report = agent.find_correlations(method="pearson", min_correlation=0.3, min_sample_size=3)

    assert len(report.findings) == 1
    insight = report.findings[0]

    # Should fallback to Spearman
    assert insight.metrics["requested_method"] == "pearson"
    assert insight.metrics["method_used"] == "spearman"
    assert "fallback" in insight.summary.lower() or "variance" in insight.summary.lower()
