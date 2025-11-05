"""
Unit tests for agent base classes and data structures.

These tests verify that core abstractions are correctly defined and that
agents do not contain any SQL or network calls.
"""

import importlib
import inspect

import pytest

from src.qnwis.agents.base import (
    AgentReport,
    DataClient,
    Evidence,
    Insight,
    MissingQueryDefinitionError,
    evidence_from,
)
from src.qnwis.data.deterministic.models import Freshness, Provenance, QueryResult, Row


def test_dataclasses_exist():
    """Verify all core data structures are defined."""
    assert Evidence is not None
    assert Insight is not None
    assert AgentReport is not None


def test_evidence_structure():
    """Verify Evidence dataclass has correct fields."""
    ev = Evidence(
        query_id="test_q", dataset_id="test_ds", locator="test.csv", fields=["a", "b"]
    )
    assert ev.query_id == "test_q"
    assert ev.dataset_id == "test_ds"
    assert ev.locator == "test.csv"
    assert ev.fields == ["a", "b"]


def test_insight_structure():
    """Verify Insight dataclass has correct fields and defaults."""
    insight = Insight(title="Test", summary="Test summary")
    assert insight.title == "Test"
    assert insight.summary == "Test summary"
    assert insight.metrics == {}
    assert insight.evidence == []
    assert insight.warnings == []
    assert insight.confidence_score == 1.0


def test_insight_with_data():
    """Verify Insight with full data."""
    ev = Evidence(query_id="q1", dataset_id="ds1", locator="loc1", fields=["f1"])
    insight = Insight(
        title="Full Test",
        summary="Summary",
        metrics={"value": 42.0},
        evidence=[ev],
        warnings=["warn1"],
    )
    assert insight.metrics["value"] == 42.0
    assert len(insight.evidence) == 1
    assert insight.warnings == ["warn1"]
    assert insight.confidence_score == 0.9


def test_insight_confidence_floor():
    """Confidence score is floored at 0.5 regardless of warnings volume."""
    warnings = [f"warn{i}" for i in range(10)]
    insight = Insight(title="Many warnings", summary="desc", warnings=warnings)
    assert insight.confidence_score == 0.5


def test_agent_report_structure():
    """Verify AgentReport dataclass has correct fields."""
    report = AgentReport(agent="TestAgent", findings=[])
    assert report.agent == "TestAgent"
    assert report.findings == []
    assert report.warnings == []


def test_data_client_initialization():
    """Verify DataClient can be initialized without crashing."""
    client = DataClient()
    assert client.ttl_s == 300
    assert client.registry is not None


def test_evidence_from_helper():
    """Verify evidence_from helper creates Evidence from QueryResult."""
    qr = QueryResult(
        query_id="test_query",
        rows=[Row(data={"field1": 1, "field2": 2})],
        unit="count",
        provenance=Provenance(
            source="csv",
            dataset_id="test_dataset",
            locator="test.csv",
            fields=["field1", "field2"],
        ),
        freshness=Freshness(asof_date="2023-12-31"),
    )
    ev = evidence_from(qr)
    assert ev.query_id == "test_query"
    assert ev.dataset_id == "test_dataset"
    assert ev.locator == "test.csv"
    assert "field1" in ev.fields
    assert "field2" in ev.fields


def test_evidence_from_empty_result():
    """Verify evidence_from handles empty results gracefully."""
    qr = QueryResult(
        query_id="empty_query",
        rows=[],
        unit="count",
        provenance=Provenance(
            source="csv", dataset_id="empty_dataset", locator="empty.csv", fields=[]
        ),
        freshness=Freshness(asof_date="2023-12-31"),
    )
    ev = evidence_from(qr)
    assert ev.query_id == "empty_query"
    assert ev.fields == []


def test_no_sql_strings_in_agents():
    """
    Critical security test: ensure no direct SQL/psycopg usage in agents.

    This test scans the source code of all agent modules to verify that
    they do not contain SQL strings or database client imports.
    """
    for name in (
        "labour_economist",
        "nationalization",
        "skills",
        "pattern_detective",
        "national_strategy",
    ):
        m = importlib.import_module(f"src.qnwis.agents.{name}")
        src = inspect.getsource(m)
        # Check for SQL keywords
        assert "SELECT " not in src, f"{name} contains SELECT statement"
        assert "INSERT " not in src, f"{name} contains INSERT statement"
        assert "UPDATE " not in src, f"{name} contains UPDATE statement"
        assert "DELETE " not in src, f"{name} contains DELETE statement"
        # Check for database libraries
        assert "psycopg" not in src, f"{name} imports psycopg"
        assert "engine.execute" not in src, f"{name} uses engine.execute"
        assert "sqlalchemy" not in src.lower(), f"{name} imports sqlalchemy"


def test_no_network_calls_in_agents():
    """
    Verify agents don't make direct network calls.

    This test ensures agents don't bypass the deterministic layer by
    importing HTTP clients or making direct API calls.
    """
    for name in (
        "labour_economist",
        "nationalization",
        "skills",
        "pattern_detective",
        "national_strategy",
    ):
        m = importlib.import_module(f"src.qnwis.agents.{name}")
        src = inspect.getsource(m)
        # Check for HTTP libraries
        assert "requests." not in src, f"{name} uses requests library"
        assert "httpx." not in src, f"{name} uses httpx library"
        assert "urllib" not in src, f"{name} uses urllib"


def test_data_client_guards():
    """Verify DataClient enforces deterministic access patterns."""
    client = DataClient()
    # Should not crash when registry is empty (test mode)
    assert hasattr(client, "run")
    assert hasattr(client, "registry")


def test_numeric_fields_helper():
    """Test _numeric_fields helper extracts numeric field names."""
    from src.qnwis.agents.base import _numeric_fields
    rows = [
        Row(data={"name": "test", "value": 42, "percent": 10.5}),
        Row(data={"name": "test2", "value": 100, "count": 5}),
    ]
    fields = _numeric_fields(rows)
    assert "value" in fields
    assert "percent" in fields
    assert "count" in fields
    assert "name" not in fields


def test_numeric_fields_with_empty():
    """Test _numeric_fields handles empty input."""
    from src.qnwis.agents.base import _numeric_fields
    assert _numeric_fields([]) == []


def test_metric_from_rows():
    """Test metric_from_rows extracts last numeric value."""
    from src.qnwis.agents.base import metric_from_rows
    rows = [
        Row(data={"value": 10}),
        Row(data={"value": 20}),
        Row(data={"value": 30}),
    ]
    assert metric_from_rows(rows, "value") == 30.0


def test_metric_from_rows_missing_key():
    """Test metric_from_rows returns 0.0 for missing key."""
    from src.qnwis.agents.base import metric_from_rows
    rows = [Row(data={"other": 10})]
    assert metric_from_rows(rows, "missing") == 0.0


def test_metric_from_rows_non_numeric():
    """Test metric_from_rows ignores non-numeric values."""
    from src.qnwis.agents.base import metric_from_rows
    rows = [
        Row(data={"value": "text"}),
        Row(data={"value": 42}),
    ]
    assert metric_from_rows(rows, "value") == 42.0


def test_data_client_custom_ttl():
    """Verify DataClient respects custom TTL."""
    client = DataClient(ttl_s=600)
    assert client.ttl_s == 600


def test_data_client_custom_queries_dir():
    """Verify DataClient accepts custom queries directory."""
    client = DataClient(queries_dir="custom/path")
    # Should initialize without crashing
    assert client.registry is not None


def test_data_client_missing_query_raises():
    """DataClient raises a helpful error when a query definition is missing."""
    client = DataClient(queries_dir="nonexistent/path")
    with pytest.raises(MissingQueryDefinitionError):
        client.run("q_missing")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
