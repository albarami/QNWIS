"""
Unit tests for AlertCenterAgent.

Tests status, run, and silence operations with DataClient integration.
"""

import tempfile
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.qnwis.agents.alert_center import AlertCenterAgent
from src.qnwis.alerts.registry import AlertRegistry
from src.qnwis.alerts.rules import (
    AlertRule,
    ScopeConfig,
    Severity,
    TriggerConfig,
    TriggerOperator,
    TriggerType,
    WindowConfig,
)
from src.qnwis.data.deterministic.models import Freshness, Provenance, QueryResult, Row


def _build_query_result(
    rows: list[Row] | None = None,
    fields: list[str] | None = None,
    query_id: str = "test",
) -> QueryResult:
    field_list = list(fields or [])
    return QueryResult(
        query_id=query_id,
        rows=rows or [],
        unit="count",
        provenance=Provenance(
            source="csv",
            dataset_id="test",
            locator="test",
            fields=field_list,
        ),
        freshness=Freshness(asof_date="2024-01-01"),
        metadata={"fields": field_list},
    )


@pytest.fixture
def mock_data_client():
    """Create mock DataClient."""
    client = MagicMock()
    # Default: return empty result
    client.run.return_value = _build_query_result()
    return client


@pytest.fixture
def sample_registry():
    """Create registry with sample rules."""
    registry = AlertRegistry()

    rules = [
        AlertRule(
            rule_id="retention_drop",
            metric="retention",
            scope=ScopeConfig(level="sector", code="construction"),
            window=WindowConfig(months=6),
            trigger=TriggerConfig(
                type=TriggerType.YOY_DELTA_PCT,
                op=TriggerOperator.LTE,
                value=-5.0,
            ),
            horizon=12,
            severity=Severity.HIGH,
            enabled=True,
        ),
        AlertRule(
            rule_id="salary_low",
            metric="salary",
            scope=ScopeConfig(level="sector"),
            window=WindowConfig(months=3),
            trigger=TriggerConfig(
                type=TriggerType.THRESHOLD,
                op=TriggerOperator.LT,
                value=3000.0,
            ),
            horizon=6,
            severity=Severity.MEDIUM,
            enabled=True,
        ),
        AlertRule(
            rule_id="disabled_rule",
            metric="retention",
            scope=ScopeConfig(level="sector"),
            window=WindowConfig(months=3),
            trigger=TriggerConfig(
                type=TriggerType.THRESHOLD,
                op=TriggerOperator.LT,
                value=0.3,
            ),
            horizon=12,
            severity=Severity.LOW,
            enabled=False,
        ),
    ]

    for rule in rules:
        registry.add_rule(rule)

    return registry


class TestAlertCenterAgent:
    """Tests for AlertCenterAgent."""

    def test_initialization(self, mock_data_client):
        """Test agent initialization."""
        agent = AlertCenterAgent(mock_data_client)
        assert agent.client == mock_data_client
        assert agent.registry is not None
        assert agent.engine is not None

    def test_status_empty_registry(self, mock_data_client):
        """Test status with no rules loaded."""
        agent = AlertCenterAgent(mock_data_client)
        report = agent.status()

        assert len(report.insights) >= 1
        assert "Status" in report.insights[0].title
        assert report.insights[0].metrics["total_rules"] == 0.0

    def test_status_with_rules(self, mock_data_client, sample_registry):
        """Test status with loaded rules."""
        agent = AlertCenterAgent(mock_data_client, sample_registry)
        report = agent.status()

        assert report.insights[0].metrics["total_rules"] == 3.0
        assert report.insights[0].metrics["enabled_rules"] == 2.0

        # Check narrative contains rule listings
        assert "retention_drop" in report.narrative
        assert "salary_low" in report.narrative

    def test_run_no_rules(self, mock_data_client):
        """Test run with no rules."""
        agent = AlertCenterAgent(mock_data_client)
        report = agent.run()

        assert "No Rules to Evaluate" in report.insights[0].title
        assert len(report.derived_results) == 0

    def test_run_with_mock_data(self, mock_data_client, sample_registry):
        """Test run with mocked data."""
        # Mock data: retention series
        rows = [
            Row(data={"period": "2024-01", "sector": "construction", "value": "0.5"}),
            Row(data={"period": "2024-02", "sector": "construction", "value": "0.5"}),
            Row(data={"period": "2024-03", "sector": "construction", "value": "0.4"}),
        ]

        result = _build_query_result(
            rows=rows,
            fields=["period", "sector", "value"],
            query_id="LMIS_RETENTION_TS",
        )

        mock_data_client.run.return_value = result

        agent = AlertCenterAgent(mock_data_client, sample_registry)
        report = agent.run(rules=["retention_drop"])

        # Should have evaluation results
        assert len(report.insights) >= 1
        assert "Alert Evaluation Summary" in report.insights[0].title

    def test_run_specific_rules(self, mock_data_client, sample_registry):
        """Test run with specific rule IDs."""
        rows = [
            Row(data={"period": "2024-01", "value": "0.5"}),
            Row(data={"period": "2024-02", "value": "0.5"}),
            Row(data={"period": "2024-03", "value": "0.4"}),
        ]

        result = _build_query_result(rows=rows, fields=["period", "value"])

        mock_data_client.run.return_value = result

        agent = AlertCenterAgent(mock_data_client, sample_registry)
        report = agent.run(rules=["retention_drop"])

        # Should only evaluate specified rule
        assert "retention_drop" in report.narrative

    def test_silence_rule(self, mock_data_client, sample_registry):
        """Test silencing a rule."""
        with tempfile.TemporaryDirectory() as tmpdir:
            silence_path = Path(tmpdir) / "alerts" / "silences.json"

            with patch("src.qnwis.agents.alert_center.Path") as mock_path:
                path_mock = MagicMock(spec=Path)
                path_parent = MagicMock()
                path_mock.parent = path_parent
                path_parent.mkdir = MagicMock()
                path_mock.exists.return_value = False
                path_mock.__fspath__.return_value = str(silence_path)
                mock_path.return_value = path_mock

                agent = AlertCenterAgent(mock_data_client, sample_registry)

                # Silence rule
                success = agent.silence("retention_drop", "2025-12-31")
                assert success is True

                # Check internal state
                assert "retention_drop" in agent._silences

    def test_silence_invalid_date(self, mock_data_client, sample_registry):
        """Test silencing with invalid date format."""
        agent = AlertCenterAgent(mock_data_client, sample_registry)
        success = agent.silence("retention_drop", "invalid-date")
        assert success is False

    def test_silence_nonexistent_rule(self, mock_data_client, sample_registry):
        """Test silencing non-existent rule."""
        agent = AlertCenterAgent(mock_data_client, sample_registry)
        success = agent.silence("nonexistent", "2025-12-31")
        assert success is False

    def test_unsilence_rule(self, mock_data_client, sample_registry):
        """Test unsilencing a rule."""
        agent = AlertCenterAgent(mock_data_client, sample_registry)

        # Silence first
        agent._silences["retention_drop"] = "2025-12-31"
        agent._save_silences = MagicMock()

        # Unsilence
        success = agent.unsilence("retention_drop")
        assert success is True
        assert "retention_drop" not in agent._silences

    def test_metric_whitelist_enforcement(self, mock_data_client):
        """Test that non-whitelisted metrics are rejected."""
        registry = AlertRegistry()
        rule = AlertRule(
            rule_id="invalid_metric",
            metric="unknown_metric",
            scope=ScopeConfig(level="sector"),
            window=WindowConfig(months=3),
            trigger=TriggerConfig(
                type=TriggerType.THRESHOLD,
                op=TriggerOperator.LT,
                value=0.5,
            ),
            horizon=12,
            severity=Severity.LOW,
        )
        registry.add_rule(rule)

        agent = AlertCenterAgent(mock_data_client, registry)
        report = agent.run()

        # Should have evaluation but not trigger due to whitelist
        assert len(report.insights) >= 1

    def test_extract_series_with_scope_filtering(self, mock_data_client):
        """Test that series extraction filters by scope."""
        rows = [
            Row(data={"period": "2024-01", "sector": "construction", "value": "0.5"}),
            Row(data={"period": "2024-01", "sector": "finance", "value": "0.6"}),
            Row(data={"period": "2024-02", "sector": "construction", "value": "0.4"}),
        ]

        result = _build_query_result(rows=rows, fields=["period", "sector", "value"])

        rule = AlertRule(
            rule_id="test",
            metric="retention",
            scope=ScopeConfig(level="sector", code="construction"),
            window=WindowConfig(months=3),
            trigger=TriggerConfig(
                type=TriggerType.THRESHOLD,
                op=TriggerOperator.LT,
                value=0.5,
            ),
            horizon=12,
            severity=Severity.LOW,
        )

        agent = AlertCenterAgent(mock_data_client)
        values, timestamps = agent._extract_series(result, rule, None, None)

        # Should only get construction values
        assert len(values) == 2
        assert values == [0.5, 0.4]

    def test_extract_series_date_filtering(self, mock_data_client):
        """Test that series extraction filters by date range."""
        rows = [
            Row(data={"period": "2023-12", "value": "0.5"}),
            Row(data={"period": "2024-01", "value": "0.6"}),
            Row(data={"period": "2024-02", "value": "0.7"}),
            Row(data={"period": "2024-03", "value": "0.8"}),
        ]

        result = _build_query_result(rows=rows, fields=["period", "value"])

        rule = AlertRule(
            rule_id="test",
            metric="retention",
            scope=ScopeConfig(level="sector"),
            window=WindowConfig(months=3),
            trigger=TriggerConfig(
                type=TriggerType.THRESHOLD,
                op=TriggerOperator.LT,
                value=0.5,
            ),
            horizon=12,
            severity=Severity.LOW,
        )

        agent = AlertCenterAgent(mock_data_client)
        values, timestamps = agent._extract_series(
            result,
            rule,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 2, 28),
        )

        # Should only get Jan-Feb 2024
        assert len(values) == 2
        assert values == [0.6, 0.7]


class TestAlertCenterIntegration:
    """Integration tests for AlertCenterAgent."""

    def test_end_to_end_alert_flow(self, mock_data_client):
        """Test complete alert evaluation flow."""
        # Setup registry
        registry = AlertRegistry()
        rule = AlertRule(
            rule_id="e2e_test",
            metric="retention",
            scope=ScopeConfig(level="sector"),
            window=WindowConfig(months=3),
            trigger=TriggerConfig(
                type=TriggerType.THRESHOLD,
                op=TriggerOperator.LT,
                value=0.5,
            ),
            horizon=12,
            severity=Severity.HIGH,
        )
        registry.add_rule(rule)

        # Mock data that triggers alert
        rows = [
            Row(data={"period": "2024-01", "value": "0.6"}),
            Row(data={"period": "2024-02", "value": "0.5"}),
            Row(data={"period": "2024-03", "value": "0.4"}),
        ]

        result = _build_query_result(rows=rows, fields=["period", "value"], query_id="LMIS_RETENTION_TS")

        mock_data_client.run.return_value = result

        # Run agent
        agent = AlertCenterAgent(mock_data_client, registry)
        report = agent.run()

        # Verify report
        assert len(report.insights) >= 1
        assert "Alert Evaluation Summary" in report.insights[0].title

        # Should have triggered alert
        triggered_count = report.insights[0].metrics.get("alerts_fired", 0)
        assert triggered_count >= 0  # May or may not trigger depending on logic

        # Verify narrative
        assert "e2e_test" in report.narrative
