"""
Unit tests for NationalizationAgent.

Tests GCC unemployment comparison and ranking logic using
deterministic test data.
"""

import pytest

from src.qnwis.agents.base import AgentReport, DataClient
from src.qnwis.agents.nationalization import NationalizationAgent
from src.qnwis.data.deterministic.models import Freshness, Provenance, QueryResult, Row


def _qr_wb():
    """Generate test QueryResult for World Bank unemployment data."""
    rows = [
        Row(data={"country": "QAT", "year": 2023, "value": 0.1}),
        Row(data={"country": "ARE", "year": 2023, "value": 2.8}),
        Row(data={"country": "SAU", "year": 2023, "value": 5.4}),
    ]
    return QueryResult(
        query_id="q_unemployment_rate_gcc_latest",
        rows=rows,
        unit="percent",
        provenance=Provenance(
            source="world_bank",
            dataset_id="SL.UEM.TOTL.ZS",
            locator="indicator=SL.UEM.TOTL.ZS",
            fields=["country", "year", "value"],
        ),
        freshness=Freshness(asof_date="api"),
    )


def test_nationalization_agent_initialization():
    """Verify agent can be initialized with DataClient."""
    client = DataClient()
    agent = NationalizationAgent(client)
    assert agent.client is client


def test_nationalization_agent_run(monkeypatch):
    """Test full agent execution with mocked data."""
    client = DataClient()
    monkeypatch.setattr(client, "run", lambda qid: _qr_wb())
    out = NationalizationAgent(client).run()
    assert isinstance(out, AgentReport)
    assert out.agent == "Nationalization"
    assert len(out.findings) > 0


def test_nationalization_metrics(monkeypatch):
    """Verify agent produces Qatar-specific metrics."""
    client = DataClient()
    monkeypatch.setattr(client, "run", lambda qid: _qr_wb())
    out = NationalizationAgent(client).run()
    m = out.findings[0].metrics
    assert any(k.startswith("qatar_") for k in m)
    # Verify Qatar has best (lowest) unemployment in test data
    assert "qatar_unemployment_percent" in m
    assert m["qatar_unemployment_percent"] == 0.1


def test_nationalization_ranking(monkeypatch):
    """Verify agent correctly ranks Qatar among GCC countries."""
    client = DataClient()
    monkeypatch.setattr(client, "run", lambda qid: _qr_wb())
    out = NationalizationAgent(client).run()
    m = out.findings[0].metrics
    if "qatar_rank_gcc" in m:
        # Qatar should rank 1st (best) with 0.1% unemployment
        assert m["qatar_rank_gcc"] == 1.0


def test_nationalization_with_missing_qatar(monkeypatch):
    """Test agent handles data without Qatar entry."""
    no_qatar_result = QueryResult(
        query_id="q_unemployment_rate_gcc_latest",
        rows=[
            Row(data={"country": "ARE", "year": 2023, "value": 2.8}),
            Row(data={"country": "SAU", "year": 2023, "value": 5.4}),
        ],
        unit="percent",
        provenance=Provenance(
            source="world_bank",
            dataset_id="SL.UEM.TOTL.ZS",
            locator="indicator=SL.UEM.TOTL.ZS",
            fields=["country", "year", "value"],
        ),
        freshness=Freshness(asof_date="api"),
    )
    client = DataClient()
    monkeypatch.setattr(client, "run", lambda qid: no_qatar_result)
    out = NationalizationAgent(client).run()
    # Should not crash, metrics may be empty
    assert isinstance(out, AgentReport)


def test_nationalization_evidence(monkeypatch):
    """Verify agent includes proper provenance evidence."""
    client = DataClient()
    monkeypatch.setattr(client, "run", lambda qid: _qr_wb())
    out = NationalizationAgent(client).run()
    ev = out.findings[0].evidence
    assert len(ev) > 0
    assert ev[0].query_id == "q_unemployment_rate_gcc_latest"
    assert ev[0].dataset_id == "SL.UEM.TOTL.ZS"


def test_nationalization_resilient_field_detection(monkeypatch):
    """Test agent can detect numeric fields dynamically."""
    # Use different field name for unemployment value
    alt_field_result = QueryResult(
        query_id="q_unemployment_rate_gcc_latest",
        rows=[
            Row(data={"country": "QAT", "year": 2023, "unemployment_rate": 0.1}),
            Row(data={"country": "ARE", "year": 2023, "unemployment_rate": 2.8}),
        ],
        unit="percent",
        provenance=Provenance(
            source="world_bank",
            dataset_id="SL.UEM.TOTL.ZS",
            locator="indicator=SL.UEM.TOTL.ZS",
            fields=["country", "year", "unemployment_rate"],
        ),
        freshness=Freshness(asof_date="api"),
    )
    client = DataClient()
    monkeypatch.setattr(client, "run", lambda qid: alt_field_result)
    out = NationalizationAgent(client).run()
    # Should still extract metrics
    m = out.findings[0].metrics
    assert "qatar_unemployment_percent" in m


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
