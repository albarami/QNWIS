"""
Unit tests for LabourEconomistAgent.

Tests employment trend analysis and YoY growth computation using
deterministic test data.
"""

import pytest

from src.qnwis.agents.base import AgentReport, DataClient
from src.qnwis.agents.labour_economist import LabourEconomistAgent
from src.qnwis.data.deterministic.models import Freshness, Provenance, QueryResult, Row


def _qr_emp():
    """Generate test QueryResult for employment data."""
    return QueryResult(
        query_id="q_employment_share_by_gender_2023",
        rows=[
            Row(
                data={
                    "year": 2022,
                    "male_percent": 58.0,
                    "female_percent": 42.0,
                    "total_percent": 100.0,
                }
            ),
            Row(
                data={
                    "year": 2023,
                    "male_percent": 60.0,
                    "female_percent": 40.0,
                    "total_percent": 100.0,
                }
            ),
        ],
        unit="percent",
        provenance=Provenance(
            source="csv",
            dataset_id="employed-persons-*.csv",
            locator="x.csv",
            fields=["year", "male_percent", "female_percent", "total_percent"],
        ),
        freshness=Freshness(asof_date="2023-12-31"),
    )


def test_labour_economist_agent_initialization():
    """Verify agent can be initialized with DataClient."""
    client = DataClient()
    agent = LabourEconomistAgent(client)
    assert agent.client is client


def test_labour_economist_agent_run(monkeypatch):
    """Test full agent execution with mocked data."""
    client = DataClient()
    monkeypatch.setattr(client, "run", lambda qid: _qr_emp())
    out = LabourEconomistAgent(client).run()
    assert isinstance(out, AgentReport)
    assert out.agent == "LabourEconomist"
    assert len(out.findings) > 0


def test_labour_economist_metrics(monkeypatch):
    """Verify agent produces expected metrics."""
    client = DataClient()
    monkeypatch.setattr(client, "run", lambda qid: _qr_emp())
    out = LabourEconomistAgent(client).run()
    m = out.findings[0].metrics
    # Should contain YoY growth or latest percentages
    assert "yoy_percent" in m or "total_percent" in m
    # Verify numeric values
    for v in m.values():
        assert isinstance(v, (int, float))


def test_labour_economist_evidence(monkeypatch):
    """Verify agent includes proper provenance evidence."""
    client = DataClient()
    monkeypatch.setattr(client, "run", lambda qid: _qr_emp())
    out = LabourEconomistAgent(client).run()
    ev = out.findings[0].evidence
    assert len(ev) > 0
    assert ev[0].query_id == "q_employment_share_by_gender_2023"
    assert ev[0].dataset_id == "employed-persons-*.csv"


def test_labour_economist_with_single_row(monkeypatch):
    """Test agent handles single-row data gracefully."""
    single_row_result = QueryResult(
        query_id="q_employment_share_by_gender_2023",
        rows=[
            Row(
                data={
                    "year": 2023,
                    "male_percent": 60.0,
                    "female_percent": 40.0,
                    "total_percent": 100.0,
                }
            )
        ],
        unit="percent",
        provenance=Provenance(
            source="csv",
            dataset_id="employed-persons-*.csv",
            locator="x.csv",
            fields=["year", "male_percent", "female_percent", "total_percent"],
        ),
        freshness=Freshness(asof_date="2023-12-31"),
    )
    client = DataClient()
    monkeypatch.setattr(client, "run", lambda qid: single_row_result)
    out = LabourEconomistAgent(client).run()
    assert isinstance(out, AgentReport)
    # YoY growth should be None for single row, but metrics should exist
    m = out.findings[0].metrics
    assert len(m) > 0


def test_labour_economist_warnings_propagation(monkeypatch):
    """Verify agent propagates warnings from data layer."""
    result_with_warnings = QueryResult(
        query_id="q_employment_share_by_gender_2023",
        rows=[
            Row(
                data={
                    "year": 2023,
                    "male_percent": 60.0,
                    "female_percent": 40.0,
                    "total_percent": 100.0,
                }
            )
        ],
        unit="percent",
        provenance=Provenance(
            source="csv",
            dataset_id="employed-persons-*.csv",
            locator="x.csv",
            fields=["year", "male_percent", "female_percent", "total_percent"],
        ),
        freshness=Freshness(asof_date="2023-12-31"),
        warnings=["stale_data", "incomplete_records"],
    )
    client = DataClient()
    monkeypatch.setattr(client, "run", lambda qid: result_with_warnings)
    out = LabourEconomistAgent(client).run()
    assert "stale_data" in out.findings[0].warnings
    assert "incomplete_records" in out.findings[0].warnings


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
