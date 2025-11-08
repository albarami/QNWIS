"""
Integration tests for Time Machine Agent orchestration.

Tests end-to-end workflows:
- Router correctly maps natural language to time.baseline/trend/breaks intents
- TimeMachineAgent generates complete reports with all required sections
- Reports include: Executive Summary, Tables, Citations (QIDs), Data Freshness, Reproducibility
- Derived QueryResults are properly created with audit trails
"""

from datetime import date, datetime
from pathlib import Path

import pytest

from src.qnwis.agents.time_machine import TimeMachineAgent
from src.qnwis.data.deterministic.models import (
    Freshness,
    Provenance,
    QueryResult,
    Row,
)
from src.qnwis.orchestration.classifier import QueryClassifier


def _get_classifier():
    """Helper to create a QueryClassifier with proper paths."""
    orchestration_dir = Path(__file__).resolve().parents[3] / "src" / "qnwis" / "orchestration"
    return QueryClassifier(
        catalog_path=str(orchestration_dir / "intent_catalog.yml"),
        sector_lex=str(orchestration_dir / "keywords" / "sectors.txt"),
        metric_lex=str(orchestration_dir / "keywords" / "metrics.txt"),
        min_confidence=0.55,
    )


class MockDataClient:
    """Mock DataClient for integration testing."""

    def __init__(self, series_data=None):
        """
        Initialize mock client.

        Args:
            series_data: Dict mapping query_id to list of (period, value, sector) tuples
        """
        self.series_data = series_data or {}
        self.call_log = []

    def run(self, query_id: str, params=None) -> QueryResult:
        """Mock run method with call logging."""
        self.call_log.append((query_id, params))

        if query_id not in self.series_data:
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


class TestTimeBaselineIntegration:
    """Test time.baseline intent end-to-end."""

    def test_baseline_report_complete_structure(self):
        """Test baseline report contains all required sections."""
        # Create 24 months of data with seasonal pattern
        series_data = {
            "LMIS_RETENTION_TS": [
                (f"2023-{i:02d}", 100 + (i % 3) * 5, "Construction")
                for i in range(1, 13)
            ] + [
                (f"2024-{i:02d}", 105 + (i % 3) * 5, "Construction")
                for i in range(1, 13)
            ]
        }

        client = MockDataClient(series_data)
        agent = TimeMachineAgent(client)

        report = agent.baseline_report(
            metric="retention",
            sector="Construction",
            start=date(2023, 1, 1),
            end=date(2024, 12, 31),
        )

        # Assert required sections
        assert "Executive Summary" in report
        assert "Baseline Table" in report
        assert "QID=" in report
        assert "Freshness:" in report
        assert "Reproducibility" in report or "Deterministic" in report

        # Assert original query ID is cited
        assert "LMIS_RETENTION_TS" in report

        # Assert derived QID is present (starts with derived_)
        assert "derived_" in report

    def test_baseline_uses_allowed_query_ids_only(self):
        """Test baseline report only calls allowed query IDs."""
        series_data = {
            "LMIS_RETENTION_TS": [
                (f"2023-{i:02d}", 100 + i, "Construction") for i in range(1, 13)
            ] + [
                (f"2024-{i:02d}", 110 + i, "Construction") for i in range(1, 13)
            ]
        }

        client = MockDataClient(series_data)
        agent = TimeMachineAgent(client)

        agent.baseline_report(
            metric="retention",
            sector="Construction",
            start=date(2023, 1, 1),
            end=date(2024, 12, 31),
        )

        # Verify only whitelisted query ID was called
        assert len(client.call_log) > 0
        called_qids = [qid for qid, _ in client.call_log]
        assert all(qid in agent.series_map.values() for qid in called_qids)


class TestTimeTrendIntegration:
    """Test time.trend intent end-to-end."""

    def test_trend_report_complete_structure(self):
        """Test trend report contains all required sections."""
        series_data = {
            "LMIS_QATARIZATION_TS": [
                (f"2023-{i:02d}", 50 + i, "Finance") for i in range(1, 13)
            ] + [
                (f"2024-{i:02d}", 60 + i, "Finance") for i in range(1, 13)
            ]
        }

        client = MockDataClient(series_data)
        agent = TimeMachineAgent(client)

        report = agent.trend_report(
            metric="qatarization",
            sector="Finance",
            start=date(2023, 1, 1),
            end=date(2024, 12, 31),
        )

        # Assert required sections
        assert "Trend Summary" in report or "Executive Summary" in report
        assert "Growth Rates" in report or "YoY" in report
        assert "QID=" in report
        assert "Freshness:" in report
        assert "Reproducibility" in report or "Deterministic" in report

        # Assert citations
        assert "LMIS_QATARIZATION_TS" in report
        assert "derived_" in report

    def test_trend_includes_yoy_qtq_slopes(self):
        """Test trend report includes YoY, QtQ, and slope analysis."""
        series_data = {
            "LMIS_RETENTION_TS": [
                (f"2023-{i:02d}", 100 + i * 2, "Healthcare") for i in range(1, 13)
            ] + [
                (f"2024-{i:02d}", 120 + i * 2, "Healthcare") for i in range(1, 13)
            ]
        }

        client = MockDataClient(series_data)
        agent = TimeMachineAgent(client)

        report = agent.trend_report(
            metric="retention",
            sector="Healthcare",
            start=date(2023, 1, 1),
            end=date(2024, 12, 31),
        )

        # Assert key trend metrics
        assert "YoY" in report or "year-over-year" in report
        assert "QtQ" in report or "quarter-over-quarter" in report or "QoQ" in report
        assert "slope" in report or "Slope" in report or "momentum" in report


class TestTimeBreaksIntegration:
    """Test time.breaks intent end-to-end."""

    def test_breaks_report_complete_structure(self):
        """Test breaks report contains all required sections."""
        # Create series with clear structural break
        series_data = {
            "LMIS_SALARY_TS": [
                (f"2023-{i:02d}", 5000, "IT") for i in range(1, 7)
            ] + [
                (f"2023-{i:02d}", 8000, "IT") for i in range(7, 13)  # Break at month 7
            ] + [
                (f"2024-{i:02d}", 8000, "IT") for i in range(1, 13)
            ]
        }

        client = MockDataClient(series_data)
        agent = TimeMachineAgent(client)

        report = agent.breaks_report(
            metric="salary",
            sector="IT",
            start=date(2023, 1, 1),
            end=date(2024, 12, 31),
            z_threshold=2.0,
            cusum_h=3.0,
        )

        # Assert required sections
        assert "Structural Break" in report or "Change Point" in report or "Executive Summary" in report
        assert "QID=" in report
        assert "Freshness:" in report
        assert "Audit Trail" in report or "Why Flagged" in report or "Reproducibility" in report

        # Assert citations
        assert "LMIS_SALARY_TS" in report
        assert "derived_" in report

    def test_breaks_includes_cusum_zscore_summary(self):
        """Test breaks report includes CUSUM and z-score analysis."""
        series_data = {
            "LMIS_RETENTION_TS": [
                (f"2023-{i:02d}", 80 + i, "Construction") for i in range(1, 6)
            ] + [
                (f"2023-{i:02d}", 120 + i, "Construction") for i in range(6, 13)
            ] + [
                (f"2024-{i:02d}", 120 + i, "Construction") for i in range(1, 13)
            ]
        }

        client = MockDataClient(series_data)
        agent = TimeMachineAgent(client)

        report = agent.breaks_report(
            metric="retention",
            sector="Construction",
            start=date(2023, 1, 1),
            end=date(2024, 12, 31),
            z_threshold=2.5,
            cusum_h=4.0,
        )

        # Assert detection methods are mentioned
        assert "CUSUM" in report or "cusum" in report or "change point" in report
        assert "z-score" in report or "outlier" in report or "threshold" in report


class TestRouterIntegration:
    """Test router maps natural language to time machine intents."""

    def test_router_maps_baseline_intent(self):
        """Test router identifies baseline queries."""
        queries = [
            "What is the seasonal baseline for Construction retention?",
            "Show me the normal pattern for qatarization since 2018",
            "Compute index-100 for salary trends in Finance",
            "Historical baseline for employment",
        ]

        classifier = _get_classifier()

        for query in queries:
            result = classifier.classify_text(query)
            assert "time.baseline" in result.intents, \
                f"Query '{query}' should map to time.baseline, got {result.intents}"

    def test_router_maps_trend_intent(self):
        """Test router identifies trend queries."""
        queries = [
            "What is the trend for retention?",
            "Show YoY growth for qatarization",
            "Analyze salary momentum in Finance",
            "Is employment accelerating or slowing?",
            "Quarter over quarter growth in Construction",
        ]

        classifier = _get_classifier()

        for query in queries:
            result = classifier.classify_text(query)
            assert "time.trend" in result.intents, \
                f"Query '{query}' should map to time.trend, got {result.intents}"

    def test_router_maps_breaks_intent(self):
        """Test router identifies structural break queries."""
        queries = [
            "Detect structural breaks in retention",
            "When did qatarization rates shift?",
            "Find change points in salary trends",
            "Identify disruptions in employment patterns",
            "CUSUM analysis for attrition",
        ]

        classifier = _get_classifier()

        for query in queries:
            result = classifier.classify_text(query)
            assert "time.breaks" in result.intents, \
                f"Query '{query}' should map to time.breaks, got {result.intents}"


class TestDataFreshnessAndCitations:
    """Test all reports include proper freshness and citation metadata."""

    def test_all_reports_include_freshness(self):
        """Test all report types include data freshness information."""
        series_data = {
            "LMIS_RETENTION_TS": [
                (f"2023-{i:02d}", 100 + i, "Construction") for i in range(1, 13)
            ] + [
                (f"2024-{i:02d}", 110 + i, "Construction") for i in range(1, 13)
            ]
        }

        client = MockDataClient(series_data)
        agent = TimeMachineAgent(client)

        baseline = agent.baseline_report("retention", "Construction")
        trend = agent.trend_report("retention", "Construction")
        breaks = agent.breaks_report("retention", "Construction")

        for report, report_type in [(baseline, "baseline"), (trend, "trend"), (breaks, "breaks")]:
            assert "Freshness:" in report or "as of" in report.lower(), \
                f"{report_type} report missing freshness information"
            assert "2024-12-31" in report, \
                f"{report_type} report missing expected freshness date"

    def test_all_reports_include_qid_citations(self):
        """Test all report types include QID citations."""
        series_data = {
            "LMIS_QATARIZATION_TS": [
                (f"2023-{i:02d}", 50 + i, "Finance") for i in range(1, 13)
            ] + [
                (f"2024-{i:02d}", 60 + i, "Finance") for i in range(1, 13)
            ]
        }

        client = MockDataClient(series_data)
        agent = TimeMachineAgent(client)

        baseline = agent.baseline_report("qatarization", "Finance")
        trend = agent.trend_report("qatarization", "Finance")
        breaks = agent.breaks_report("qatarization", "Finance")

        for report, report_type in [(baseline, "baseline"), (trend, "trend"), (breaks, "breaks")]:
            # Original query ID
            assert "LMIS_QATARIZATION_TS" in report, \
                f"{report_type} report missing original QID citation"

            # Derived QID
            assert "QID=" in report, \
                f"{report_type} report missing QID= citation format"
            assert "derived_" in report, \
                f"{report_type} report missing derived QID"

    def test_reports_include_reproducibility_snippets(self):
        """Test reports include reproducibility information."""
        series_data = {
            "LMIS_RETENTION_TS": [
                (f"2023-{i:02d}", 100 + i, "Healthcare") for i in range(1, 13)
            ] + [
                (f"2024-{i:02d}", 110 + i, "Healthcare") for i in range(1, 13)
            ]
        }

        client = MockDataClient(series_data)
        agent = TimeMachineAgent(client)

        baseline = agent.baseline_report("retention", "Healthcare")
        trend = agent.trend_report("retention", "Healthcare")
        breaks = agent.breaks_report("retention", "Healthcare")

        for report in [baseline, trend, breaks]:
            # Should mention reproducibility/determinism
            assert any(keyword in report.lower() for keyword in [
                "reproducib", "deterministic", "audit", "verifiable"
            ]), "Report missing reproducibility information"


class TestEndToEndWorkflow:
    """Test complete end-to-end workflow from router to final report."""

    def test_baseline_workflow_complete(self):
        """Test complete baseline workflow: classifier -> agent -> report."""
        series_data = {
            "LMIS_RETENTION_TS": [
                (f"2023-{i:02d}", 100 + i, "Construction") for i in range(1, 13)
            ] + [
                (f"2024-{i:02d}", 110 + i, "Construction") for i in range(1, 13)
            ]
        }

        client = MockDataClient(series_data)
        agent = TimeMachineAgent(client)
        classifier = _get_classifier()

        # Step 1: Classifier classifies query
        query = "What is the baseline Construction retention since 2023?"
        classification = classifier.classify_text(query)

        assert "time.baseline" in classification.intents

        # Step 2: Agent generates report
        report = agent.baseline_report(
            metric="retention",
            sector="Construction",
            start=date(2023, 1, 1),
            end=date(2024, 12, 31),
        )

        # Step 3: Verify complete report structure
        assert all(section in report for section in [
            "Executive Summary",
            "QID=",
            "Freshness:",
        ])

    def test_trend_workflow_complete(self):
        """Test complete trend workflow: classifier -> agent -> report."""
        series_data = {
            "LMIS_QATARIZATION_TS": [
                (f"2023-{i:02d}", 50 + i * 2, "Finance") for i in range(1, 13)
            ] + [
                (f"2024-{i:02d}", 70 + i * 2, "Finance") for i in range(1, 13)
            ]
        }

        client = MockDataClient(series_data)
        agent = TimeMachineAgent(client)
        classifier = _get_classifier()

        # Step 1: Classifier classifies query
        query = "Show me the YoY trend for Finance qatarization"
        classification = classifier.classify_text(query)

        assert "time.trend" in classification.intents

        # Step 2: Agent generates report
        report = agent.trend_report(
            metric="qatarization",
            sector="Finance",
            start=date(2023, 1, 1),
            end=date(2024, 12, 31),
        )

        # Step 3: Verify complete report structure
        assert all(keyword in report for keyword in ["YoY", "QID=", "Freshness:"])

    def test_breaks_workflow_complete(self):
        """Test complete breaks workflow: classifier -> agent -> report."""
        series_data = {
            "LMIS_SALARY_TS": [
                (f"2023-{i:02d}", 5000, "IT") for i in range(1, 6)
            ] + [
                (f"2023-{i:02d}", 8000, "IT") for i in range(6, 13)
            ] + [
                (f"2024-{i:02d}", 8000, "IT") for i in range(1, 13)
            ]
        }

        client = MockDataClient(series_data)
        agent = TimeMachineAgent(client)
        classifier = _get_classifier()

        # Step 1: Classifier classifies query
        query = "Detect structural breaks in IT salary trends"
        classification = classifier.classify_text(query)

        assert "time.breaks" in classification.intents

        # Step 2: Agent generates report
        report = agent.breaks_report(
            metric="salary",
            sector="IT",
            start=date(2023, 1, 1),
            end=date(2024, 12, 31),
        )

        # Step 3: Verify complete report structure
        assert "QID=" in report
        assert "Freshness:" in report


class TestErrorHandlingIntegration:
    """Test error handling in integration scenarios."""

    def test_insufficient_data_raises_clear_error(self):
        """Test clear error when insufficient data for analysis."""
        series_data = {
            "LMIS_RETENTION_TS": [
                ("2024-01", 100, "Construction"),
                ("2024-02", 110, "Construction"),
            ]
        }

        client = MockDataClient(series_data)
        agent = TimeMachineAgent(client)

        with pytest.raises(ValueError, match="Insufficient data"):
            agent.baseline_report(
                metric="retention",
                sector="Construction",
                start=date(2024, 1, 1),
                end=date(2024, 12, 31),
            )

    def test_invalid_metric_raises_clear_error(self):
        """Test clear error for invalid metric name."""
        client = MockDataClient()
        agent = TimeMachineAgent(client)

        with pytest.raises(ValueError, match="not in series_map"):
            agent.baseline_report(
                metric="invalid_metric_xyz",
                sector=None,
                start=date(2023, 1, 1),
                end=date(2024, 12, 31),
            )
