"""
Unit tests for National Strategy Agent.

Tests GCC benchmarking, talent competition assessment, and Vision 2030 alignment
with graceful degradation when data sources are unavailable.
"""

from __future__ import annotations

import pytest

from src.qnwis.agents.base import DataClient
from src.qnwis.agents.national_strategy import VISION_2030_TARGETS, NationalStrategyAgent
from src.qnwis.data.deterministic.models import Freshness, Provenance, QueryResult, Row


class FakeDataClient(DataClient):
    """Fake client that returns synthetic distributions without file dependencies."""

    def __init__(self) -> None:
        self._responses: dict[str, QueryResult] = {}
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
def fake_client_gcc() -> FakeDataClient:
    """Fixture providing GCC unemployment data."""
    client = FakeDataClient()

    gcc_result = QueryResult(
        query_id="syn_unemployment_rate_gcc_latest",
        rows=[
            Row(data={"country": "Qatar", "unemployment_rate": 0.3, "year": 2023}),
            Row(data={"country": "UAE", "unemployment_rate": 2.5, "year": 2023}),
            Row(data={"country": "Kuwait", "unemployment_rate": 3.2, "year": 2023}),
            Row(data={"country": "Saudi Arabia", "unemployment_rate": 5.6, "year": 2023}),
            Row(data={"country": "Bahrain", "unemployment_rate": 4.1, "year": 2023}),
            Row(data={"country": "Oman", "unemployment_rate": 3.8, "year": 2023}),
        ],
        unit="percent",
        provenance=Provenance(
            source="csv",
            dataset_id="gcc_unemployment",
            locator="gcc_unemployment.csv",
            fields=["country", "unemployment_rate", "year"],
        ),
        freshness=Freshness(asof_date="2024-01-01"),
    )
    client.add_response("syn_unemployment_rate_gcc_latest", gcc_result)

    return client


@pytest.fixture
def fake_client_full() -> FakeDataClient:
    """Fixture providing all required datasets for full testing."""
    client = FakeDataClient()

    # GCC data
    gcc_result = QueryResult(
        query_id="syn_unemployment_rate_gcc_latest",
        rows=[
            Row(data={"country": "Qatar", "unemployment_rate": 0.3, "year": 2023}),
            Row(data={"country": "UAE", "unemployment_rate": 2.5, "year": 2023}),
            Row(data={"country": "Kuwait", "unemployment_rate": 3.2, "year": 2023}),
            Row(data={"country": "Saudi Arabia", "unemployment_rate": 5.6, "year": 2023}),
        ],
        unit="percent",
        provenance=Provenance(source="csv", dataset_id="gcc", locator="gcc.csv", fields=["country", "unemployment_rate", "year"]),
        freshness=Freshness(asof_date="2024-01-01"),
    )
    client.add_response("syn_unemployment_rate_gcc_latest", gcc_result)

    # Attrition data for talent competition
    atr_result = QueryResult(
        query_id="syn_attrition_by_sector_latest",
        rows=[
            Row(data={"sector": "Finance", "attrition_percent": 12.0}),
            Row(data={"sector": "Retail", "attrition_percent": 25.0}),  # High
            Row(data={"sector": "Manufacturing", "attrition_percent": 13.0}),
            Row(data={"sector": "Healthcare", "attrition_percent": 15.0}),
            Row(data={"sector": "Education", "attrition_percent": 11.0}),
            Row(data={"sector": "Construction", "attrition_percent": 30.0}),  # Very high
        ],
        unit="percent",
        provenance=Provenance(source="csv", dataset_id="attrition", locator="atr.csv", fields=["sector", "attrition_percent"]),
        freshness=Freshness(asof_date="2024-01-01"),
    )
    client.add_response("syn_attrition_by_sector_latest", atr_result)

    # Qatarization data for Vision 2030
    qat_result = QueryResult(
        query_id="syn_qatarization_by_sector_latest",
        rows=[
            Row(data={"sector": "Finance", "qatarization_percent": 20.0, "qataris": 200, "non_qataris": 800}),
            Row(data={"sector": "Retail", "qatarization_percent": 15.0, "qataris": 150, "non_qataris": 850}),
            Row(data={"sector": "Manufacturing", "qatarization_percent": 18.0, "qataris": 180, "non_qataris": 820}),
            Row(data={"sector": "Healthcare", "qatarization_percent": 22.0, "qataris": 220, "non_qataris": 780}),
        ],
        unit="percent",
        provenance=Provenance(source="csv", dataset_id="qat", locator="qat.csv", fields=["sector", "qatarization_percent", "qataris", "non_qataris"]),
        freshness=Freshness(asof_date="2024-01-01"),
    )
    client.add_response("syn_qatarization_by_sector_latest", qat_result)

    return client


def test_gcc_benchmark_with_and_without_connectors(fake_client_gcc: FakeDataClient) -> None:
    """Test GCC benchmarking gracefully degrades; still cites sources."""
    agent = NationalStrategyAgent(fake_client_gcc)

    report = agent.gcc_benchmark(min_countries=3)

    assert len(report.findings) == 1
    insight = report.findings[0]

    assert "GCC unemployment benchmarking" in insight.title

    # Should find Qatar as rank 1 (lowest unemployment = best)
    assert insight.metrics["gcc_countries_count"] == 6
    assert insight.metrics["qatar_rank"] == 1
    assert insight.metrics["qatar_rate"] == 0.3
    assert "gcc_average" in insight.metrics

    # Gap should be negative (Qatar below average)
    assert insight.metrics["gap_to_average"] < 0

    # Verify evidence includes original and derived query IDs
    assert len(insight.evidence) == 2
    query_ids = [e.query_id for e in insight.evidence]
    assert "syn_unemployment_rate_gcc_latest" in query_ids
    assert any("derived_" in qid for qid in query_ids)

    # Summary mentions ranking
    assert "Qatar ranks 1/" in insight.summary or "ranks 1" in insight.summary


def test_talent_competition_includes_all_citations(fake_client_full: FakeDataClient) -> None:
    """Test talent competition assessment includes LMIS + external + derived citations."""
    agent = NationalStrategyAgent(fake_client_full)

    report = agent.talent_competition_assessment(focus_metric="attrition_percent")

    assert len(report.findings) == 1
    insight = report.findings[0]

    assert "Talent competition assessment" in insight.title

    # Should classify sectors by competition level
    avg_atr = (12.0 + 25.0 + 13.0 + 15.0 + 11.0 + 30.0) / 6  # = 17.67
    avg_atr * 1.5  # = 26.5
    # High competition: Retail (25.0 < 26.5) NO, Construction (30.0 > 26.5) YES
    # So 1 sector with high competition (Construction only)

    assert insight.metrics["total_sectors"] == 6
    assert insight.metrics["high_competition_sectors"] == 1  # Only Construction
    assert "average_attrition" in insight.metrics
    assert insight.metrics["highest_attrition_sector"] == "Construction"

    # Verify evidence includes source and derived result
    assert len(insight.evidence) == 2
    query_ids = [e.query_id for e in insight.evidence]
    assert "syn_attrition_by_sector_latest" in query_ids
    assert any("derived_" in qid for qid in query_ids)


def test_vision2030_alignment_targets_and_gaps(fake_client_full: FakeDataClient) -> None:
    """Test Vision 2030 alignment calculates traffic-light, numeric deltas, Query IDs."""
    agent = NationalStrategyAgent(fake_client_full)

    report = agent.vision2030_alignment(target_year=2030, current_year=2024)

    assert len(report.findings) == 1
    insight = report.findings[0]

    assert "Vision 2030 qatarization alignment" in insight.title

    # Current qatarization: (200+150+180+220) / (200+800+150+850+180+820+220+780) = 750 / 4000 = 18.75%
    # Target: 30% (private sector target)
    # Gap: 30 - 18.75 = 11.25 pp
    # Gap %: (11.25 / 30) * 100 = 37.5% (high risk)
    # Required annual growth: 11.25 / 6 years = 1.875 pp/year

    assert insight.metrics["current_qatarization"] == 18.75
    assert insight.metrics["target_qatarization"] == VISION_2030_TARGETS["qatarization_private_sector"]
    assert insight.metrics["gap_percentage_points"] == 11.25
    assert insight.metrics["years_remaining"] == 6
    assert round(insight.metrics["required_annual_growth"], 2) == 1.88

    # Verify evidence includes source and derived gap analysis
    assert len(insight.evidence) == 2
    query_ids = [e.query_id for e in insight.evidence]
    assert "syn_qatarization_by_sector_latest" in query_ids
    assert any("derived_" in qid for qid in query_ids)

    # Summary mentions risk level
    assert "risk" in insight.summary.lower()


def test_gcc_benchmark_insufficient_countries() -> None:
    """Test graceful handling when insufficient GCC countries."""
    client = FakeDataClient()

    # Only 1 country (below min_countries=3)
    result = QueryResult(
        query_id="syn_unemployment_rate_gcc_latest",
        rows=[
            Row(data={"country": "Qatar", "unemployment_rate": 0.3, "year": 2023}),
        ],
        unit="percent",
        provenance=Provenance(source="csv", dataset_id="test", locator="test.csv", fields=["country", "unemployment_rate"]),
        freshness=Freshness(asof_date="2024-01-01"),
    )
    client.add_response("syn_unemployment_rate_gcc_latest", result)

    agent = NationalStrategyAgent(client)
    report = agent.gcc_benchmark(min_countries=3)

    # Should return empty findings with warning
    assert len(report.findings) == 0
    assert len(report.warnings) == 1
    assert "Insufficient GCC data" in report.warnings[0]


def test_talent_competition_empty_data() -> None:
    """Test talent competition with no valid attrition data."""
    client = FakeDataClient()

    # Empty result
    result = QueryResult(
        query_id="syn_attrition_by_sector_latest",
        rows=[],
        unit="percent",
        provenance=Provenance(source="csv", dataset_id="test", locator="test.csv", fields=["sector", "attrition_percent"]),
        freshness=Freshness(asof_date="2024-01-01"),
    )
    client.add_response("syn_attrition_by_sector_latest", result)

    agent = NationalStrategyAgent(client)
    report = agent.talent_competition_assessment(focus_metric="attrition_percent")

    # Should return empty findings with warning
    assert len(report.findings) == 0
    assert len(report.warnings) == 1
    assert "No valid attrition data" in report.warnings[0]


def test_vision2030_empty_employment_data() -> None:
    """Test Vision 2030 alignment with no valid employment data."""
    client = FakeDataClient()

    # Empty result
    result = QueryResult(
        query_id="syn_qatarization_by_sector_latest",
        rows=[],
        unit="percent",
        provenance=Provenance(source="csv", dataset_id="test", locator="test.csv", fields=["sector", "qatarization_percent"]),
        freshness=Freshness(asof_date="2024-01-01"),
    )
    client.add_response("syn_qatarization_by_sector_latest", result)

    agent = NationalStrategyAgent(client)
    report = agent.vision2030_alignment(target_year=2030, current_year=2024)

    # Should return empty findings with warning
    assert len(report.findings) == 0
    assert len(report.warnings) == 1
    assert "No valid employment data" in report.warnings[0]


def test_vision2030_on_track_scenario() -> None:
    """Test Vision 2030 when already exceeding target (on_track risk level)."""
    client = FakeDataClient()

    # High qatarization already exceeding 30% target
    result = QueryResult(
        query_id="syn_qatarization_by_sector_latest",
        rows=[
            Row(data={"sector": "A", "qatarization_percent": 35.0, "qataris": 350, "non_qataris": 650}),
            Row(data={"sector": "B", "qatarization_percent": 40.0, "qataris": 400, "non_qataris": 600}),
        ],
        unit="percent",
        provenance=Provenance(source="csv", dataset_id="test", locator="test.csv", fields=["sector", "qatarization_percent", "qataris", "non_qataris"]),
        freshness=Freshness(asof_date="2024-01-01"),
    )
    client.add_response("syn_qatarization_by_sector_latest", result)

    agent = NationalStrategyAgent(client)
    report = agent.vision2030_alignment(target_year=2030, current_year=2024)

    assert len(report.findings) == 1
    insight = report.findings[0]

    # Current: (350+400) / (350+650+400+600) = 750 / 2000 = 37.5% (above 30% target)
    assert insight.metrics["current_qatarization"] == 37.5
    assert insight.metrics["gap_percentage_points"] < 0  # Already exceeded

    # Summary should mention on_track or that target is met
    assert "on_track" in insight.summary.lower() or "risk_level: on_track" in str(insight.metrics)
