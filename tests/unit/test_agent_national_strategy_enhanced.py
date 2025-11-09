"""
Unit tests for NationalStrategyAgent enhanced methods.

Tests GCC benchmarking, talent competition assessment, and Vision 2030 alignment.
"""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from src.qnwis.agents.base import DataClient
from src.qnwis.agents.national_strategy import VISION_2030_TARGETS, NationalStrategyAgent
from src.qnwis.data.deterministic.models import Freshness, Provenance, QueryResult, Row


@pytest.fixture
def mock_client():
    """Create a mock DataClient for testing."""
    return Mock(spec=DataClient)


@pytest.fixture
def agent(mock_client):
    """Create NationalStrategyAgent with mock client."""
    return NationalStrategyAgent(mock_client)


class TestGCCBenchmark:
    """Test GCC benchmarking functionality."""

    def test_basic_benchmarking(self, agent, mock_client):
        """Should rank Qatar among GCC countries."""
        gcc_result = QueryResult(
            query_id="syn_unemployment_rate_gcc_latest",
            rows=[
                Row(data={"country": "Qatar", "unemployment_rate": 6.5, "year": 2023}),
                Row(data={"country": "Saudi Arabia", "unemployment_rate": 8.2, "year": 2023}),
                Row(data={"country": "UAE", "unemployment_rate": 5.1, "year": 2023}),
                Row(data={"country": "Kuwait", "unemployment_rate": 7.8, "year": 2023}),
                Row(data={"country": "Bahrain", "unemployment_rate": 6.9, "year": 2023}),
                Row(data={"country": "Oman", "unemployment_rate": 9.5, "year": 2023}),
            ],
            unit="percent",
            provenance=Provenance(source="csv", dataset_id="gcc", locator="test", fields=[]),
            freshness=Freshness(asof_date="2023-12-31"),
            warnings=[],
        )

        mock_client.run.return_value = gcc_result

        report = agent.gcc_benchmark()

        finding = report.findings[0]
        assert "gcc" in finding.title.lower()
        # Qatar @ 6.5 ranks 2nd: UAE(5.1) < Qatar(6.5) < Bahrain(6.9) < Kuwait(7.8) < SA(8.2) < Oman(9.5)
        assert finding.metrics["qatar_rank"] == 2
        assert finding.metrics["qatar_rate"] == 6.5
        assert finding.metrics["gcc_countries_count"] == 6
        assert "gcc_average" in finding.metrics

    def test_qatar_best_performer(self, agent, mock_client):
        """Should handle Qatar ranking first."""
        gcc_result = QueryResult(
            query_id="syn_unemployment_rate_gcc_latest",
            rows=[
                Row(data={"country": "Qatar", "unemployment_rate": 4.0, "year": 2023}),
                Row(data={"country": "UAE", "unemployment_rate": 5.5, "year": 2023}),
                Row(data={"country": "Saudi Arabia", "unemployment_rate": 8.0, "year": 2023}),
            ],
            unit="percent",
            provenance=Provenance(source="csv", dataset_id="gcc", locator="test", fields=[]),
            freshness=Freshness(asof_date="2023-12-31"),
            warnings=[],
        )

        mock_client.run.return_value = gcc_result

        report = agent.gcc_benchmark()

        finding = report.findings[0]
        assert finding.metrics["qatar_rank"] == 1
        assert "ranks 1/3" in finding.summary

    def test_insufficient_countries(self, agent, mock_client):
        """Should warn when too few countries available."""
        gcc_result = QueryResult(
            query_id="syn_unemployment_rate_gcc_latest",
            rows=[
                Row(data={"country": "Qatar", "unemployment_rate": 6.5, "year": 2023}),
            ],
            unit="percent",
            provenance=Provenance(source="csv", dataset_id="gcc", locator="test", fields=[]),
            freshness=Freshness(asof_date="2023-12-31"),
            warnings=[],
        )

        mock_client.run.return_value = gcc_result

        report = agent.gcc_benchmark(min_countries=3)

        assert len(report.findings) == 0
        assert "Insufficient GCC data" in report.warnings[0]

    def test_qatar_not_found(self, agent, mock_client):
        """Should handle case where Qatar data is missing."""
        gcc_result = QueryResult(
            query_id="syn_unemployment_rate_gcc_latest",
            rows=[
                Row(data={"country": "UAE", "unemployment_rate": 5.5, "year": 2023}),
                Row(data={"country": "Saudi Arabia", "unemployment_rate": 8.0, "year": 2023}),
                Row(data={"country": "Kuwait", "unemployment_rate": 7.5, "year": 2023}),
            ],
            unit="percent",
            provenance=Provenance(source="csv", dataset_id="gcc", locator="test", fields=[]),
            freshness=Freshness(asof_date="2023-12-31"),
            warnings=[],
        )

        mock_client.run.return_value = gcc_result

        report = agent.gcc_benchmark()

        finding = report.findings[0]
        assert "Qatar data not found" in finding.summary
        assert "qatar_rank" not in finding.metrics

    def test_gap_calculation(self, agent, mock_client):
        """Should calculate gap to GCC average correctly."""
        gcc_result = QueryResult(
            query_id="syn_unemployment_rate_gcc_latest",
            rows=[
                Row(data={"country": "Qatar", "unemployment_rate": 6.0, "year": 2023}),
                Row(data={"country": "UAE", "unemployment_rate": 5.0, "year": 2023}),
                Row(data={"country": "Saudi Arabia", "unemployment_rate": 9.0, "year": 2023}),
            ],
            unit="percent",
            provenance=Provenance(source="csv", dataset_id="gcc", locator="test", fields=[]),
            freshness=Freshness(asof_date="2023-12-31"),
            warnings=[],
        )

        mock_client.run.return_value = gcc_result

        report = agent.gcc_benchmark()

        finding = report.findings[0]
        # Average = (6 + 5 + 9) / 3 = 6.67
        # Gap = 6.0 - 6.67 = -0.67
        assert abs(finding.metrics["gap_to_average"] - (-0.67)) < 0.1


class TestTalentCompetitionAssessment:
    """Test talent competition assessment."""

    def test_basic_competition_assessment(self, agent, mock_client):
        """Should classify sectors by competitive pressure."""
        atr_result = QueryResult(
            query_id="syn_attrition_by_sector_latest",
            rows=[
                Row(data={"sector": "Finance", "attrition_percent": 20.0}),  # High (>1.5x avg)
                Row(data={"sector": "Energy", "attrition_percent": 8.0}),  # Low
                Row(data={"sector": "Healthcare", "attrition_percent": 12.0}),  # Moderate
                Row(data={"sector": "ICT", "attrition_percent": 10.0}),  # Average
            ],
            unit="percent",
            provenance=Provenance(source="csv", dataset_id="atr", locator="test", fields=[]),
            freshness=Freshness(asof_date="2024-12-31"),
        )

        mock_client.run.return_value = atr_result

        report = agent.talent_competition_assessment()

        finding = report.findings[0]
        assert "competition" in finding.title.lower()
        assert finding.metrics["total_sectors"] == 4
        assert finding.metrics["average_attrition"] == 12.5
        assert finding.metrics["highest_attrition_sector"] == "Finance"

    def test_high_competition_threshold(self, agent, mock_client):
        """Should identify high competition sectors correctly."""
        # Average will be 10%, high threshold is 15%
        atr_result = QueryResult(
            query_id="syn_attrition_by_sector_latest",
            rows=[
                Row(data={"sector": "A", "attrition_percent": 8.0}),
                Row(data={"sector": "B", "attrition_percent": 9.0}),
                Row(data={"sector": "C", "attrition_percent": 10.0}),
                Row(data={"sector": "D", "attrition_percent": 13.0}),
                Row(data={"sector": "E", "attrition_percent": 20.0}),  # High (>15%)
            ],
            unit="percent",
            provenance=Provenance(source="csv", dataset_id="atr", locator="test", fields=[]),
            freshness=Freshness(asof_date="2024-12-31"),
        )

        mock_client.run.return_value = atr_result

        report = agent.talent_competition_assessment()

        finding = report.findings[0]
        # Average = 12%, high threshold = 18% (1.5x)
        # Only sector E (20%) exceeds threshold
        assert finding.metrics["high_competition_sectors"] >= 1

    def test_no_data_warning(self, agent, mock_client):
        """Should warn when no valid data available."""
        empty_result = QueryResult(
            query_id="syn_attrition_by_sector_latest",
            rows=[],
            unit="percent",
            provenance=Provenance(source="csv", dataset_id="atr", locator="test", fields=[]),
            freshness=Freshness(asof_date="2024-12-31"),
        )

        mock_client.run.return_value = empty_result

        report = agent.talent_competition_assessment()

        assert len(report.findings) == 0
        assert "No valid attrition data" in report.warnings[0]


class TestVision2030Alignment:
    """Test Vision 2030 alignment tracking."""

    def test_basic_alignment_calculation(self, agent, mock_client):
        """Should calculate gap to Vision 2030 targets."""
        qat_result = QueryResult(
            query_id="syn_qatarization_by_sector_latest",
            rows=[
                Row(data={"sector": "Finance", "qataris": 100, "non_qataris": 400}),
                Row(data={"sector": "Energy", "qataris": 200, "non_qataris": 300}),
                Row(data={"sector": "Healthcare", "qataris": 150, "non_qataris": 350}),
            ],
            unit="percent",
            provenance=Provenance(source="csv", dataset_id="qat", locator="test", fields=[]),
            freshness=Freshness(asof_date="2024-12-31"),
        )

        mock_client.run.return_value = qat_result

        report = agent.vision2030_alignment(target_year=2030, current_year=2024)

        finding = report.findings[0]
        # Total: 450 Qataris, 1050 non-Qataris = 1500 total
        # Current rate: 450/1500 = 30%
        # Target: 30% (from VISION_2030_TARGETS)
        # Gap: 0
        assert abs(finding.metrics["current_qatarization"] - 30.0) < 0.5
        assert (
            finding.metrics["target_qatarization"]
            == VISION_2030_TARGETS["qatarization_private_sector"]
        )
        assert finding.metrics["years_remaining"] == 6

    def test_below_target_high_risk(self, agent, mock_client):
        """Should flag high risk when far from target."""
        qat_result = QueryResult(
            query_id="syn_qatarization_by_sector_latest",
            rows=[
                Row(data={"sector": "Finance", "qataris": 100, "non_qataris": 900}),  # 10%
            ],
            unit="percent",
            provenance=Provenance(source="csv", dataset_id="qat", locator="test", fields=[]),
            freshness=Freshness(asof_date="2024-12-31"),
        )

        mock_client.run.return_value = qat_result

        report = agent.vision2030_alignment(target_year=2030, current_year=2024)

        finding = report.findings[0]
        # Current: 10%, Target: 30%, Gap: 20 pp = 67% of target
        assert finding.metrics["gap_percentage_points"] > 15
        assert "high" in finding.summary.lower()

    def test_required_annual_growth(self, agent, mock_client):
        """Should calculate required annual growth rate."""
        qat_result = QueryResult(
            query_id="syn_qatarization_by_sector_latest",
            rows=[
                Row(data={"sector": "A", "qataris": 100, "non_qataris": 400}),  # 20%
            ],
            unit="percent",
            provenance=Provenance(source="csv", dataset_id="qat", locator="test", fields=[]),
            freshness=Freshness(asof_date="2024-12-31"),
        )

        mock_client.run.return_value = qat_result

        report = agent.vision2030_alignment(target_year=2030, current_year=2024)

        finding = report.findings[0]
        # Current: 20%, Target: 30%, Gap: 10 pp
        # Years: 6
        # Required growth: 10/6 ≈ 1.67 pp/year
        assert abs(finding.metrics["required_annual_growth"] - 1.67) < 0.1

    def test_on_track_or_exceeding(self, agent, mock_client):
        """Should recognize when on track or exceeding target."""
        qat_result = QueryResult(
            query_id="syn_qatarization_by_sector_latest",
            rows=[
                Row(data={"sector": "A", "qataris": 350, "non_qataris": 650}),  # 35% > 30% target
            ],
            unit="percent",
            provenance=Provenance(source="csv", dataset_id="qat", locator="test", fields=[]),
            freshness=Freshness(asof_date="2024-12-31"),
        )

        mock_client.run.return_value = qat_result

        report = agent.vision2030_alignment()

        finding = report.findings[0]
        assert finding.metrics["gap_percentage_points"] < 0  # Exceeding target
        assert "on_track" in finding.summary.lower()

    def test_no_data_warning(self, agent, mock_client):
        """Should warn when no employment data available."""
        empty_result = QueryResult(
            query_id="syn_qatarization_by_sector_latest",
            rows=[],
            unit="percent",
            provenance=Provenance(source="csv", dataset_id="qat", locator="test", fields=[]),
            freshness=Freshness(asof_date="2024-12-31"),
        )

        mock_client.run.return_value = empty_result

        report = agent.vision2030_alignment()

        assert len(report.findings) == 0
        assert "No valid employment data" in report.warnings[0]


class TestLegacyRun:
    """Test backward compatibility with original run() method."""

    def test_legacy_strategic_snapshot(self, agent, mock_client):
        """Original run() method should still work."""
        emp_result = QueryResult(
            query_id="q_employment_share_by_gender_2023",
            rows=[
                Row(
                    data={
                        "male_percent": 65.0,
                        "female_percent": 35.0,
                        "total_percent": 100.0,
                    }
                ),
            ],
            unit="percent",
            provenance=Provenance(source="csv", dataset_id="emp", locator="test", fields=[]),
            freshness=Freshness(asof_date="2023-12-31"),
            warnings=[],
        )

        gcc_result = QueryResult(
            query_id="q_unemployment_rate_gcc_latest",
            rows=[
                Row(data={"country": "Qatar", "unemployment_rate": 6.5, "year": 2023}),
                Row(data={"country": "UAE", "unemployment_rate": 5.0, "year": 2023}),
            ],
            unit="percent",
            provenance=Provenance(source="csv", dataset_id="gcc", locator="test", fields=[]),
            freshness=Freshness(asof_date="2023-12-31"),
            warnings=[],
        )

        mock_client.run.side_effect = [emp_result, gcc_result]

        report = agent.run()

        assert report.agent == "NationalStrategy"
        assert len(report.findings) == 1
        finding = report.findings[0]
        assert "strategic snapshot" in finding.title.lower()
        assert "employment_male_percent" in finding.metrics
        assert "gcc_unemployment_min" in finding.metrics
        assert "gcc_unemployment_max" in finding.metrics


class TestEvidenceChain:
    """Test that all methods maintain proper evidence chains."""

    def test_gcc_benchmark_evidence(self, agent, mock_client):
        """GCC benchmark should have complete evidence chain."""
        gcc_result = QueryResult(
            query_id="syn_unemployment_rate_gcc_latest",
            rows=[
                Row(data={"country": "Qatar", "unemployment_rate": 6.5, "year": 2023})
                for _ in range(3)
            ],
            unit="percent",
            provenance=Provenance(source="csv", dataset_id="gcc", locator="test", fields=[]),
            freshness=Freshness(asof_date="2023-12-31"),
            warnings=[],
        )

        mock_client.run.return_value = gcc_result

        report = agent.gcc_benchmark()

        finding = report.findings[0]
        assert len(finding.evidence) >= 2  # Original + derived
        assert any("syn_unemployment_rate_gcc_latest" in e.query_id for e in finding.evidence)
        assert any("derived_" in e.query_id for e in finding.evidence)

    def test_vision2030_evidence(self, agent, mock_client):
        """Vision 2030 should have complete evidence chain."""
        qat_result = QueryResult(
            query_id="syn_qatarization_by_sector_latest",
            rows=[Row(data={"sector": "A", "qataris": 100, "non_qataris": 400})],
            unit="percent",
            provenance=Provenance(source="csv", dataset_id="qat", locator="test", fields=[]),
            freshness=Freshness(asof_date="2024-12-31"),
        )

        mock_client.run.return_value = qat_result

        report = agent.vision2030_alignment()

        finding = report.findings[0]
        assert len(finding.evidence) >= 2
        assert any("syn_qatarization_by_sector_latest" in e.query_id for e in finding.evidence)
        assert any("vision2030_gap_analysis" in e.query_id for e in finding.evidence)
