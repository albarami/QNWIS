"""Unit tests for PatternDetectiveAgent."""

import pytest

from src.qnwis.agents.base import AgentReport, DataClient
from src.qnwis.agents.pattern_detective import PatternDetectiveAgent
from src.qnwis.data.deterministic.models import Freshness, Provenance, QueryResult, Row


def _qr_consistent():
    return QueryResult(
        query_id="q_employment_share_by_gender_2023",
        rows=[Row(data={"year": 2023, "male_percent": 60.0, "female_percent": 40.0, "total_percent": 100.0})],
        unit="percent",
        provenance=Provenance(
            source="csv", dataset_id="employed", locator="x.csv",
            fields=["year", "male_percent", "female_percent", "total_percent"]
        ),
        freshness=Freshness(asof_date="2023-12-31"),
    )


def _qr_inconsistent():
    return QueryResult(
        query_id="q_employment_share_by_gender_2023",
        rows=[Row(data={"year": 2023, "male_percent": 55.0, "female_percent": 44.0, "total_percent": 100.0})],
        unit="percent",
        provenance=Provenance(
            source="csv", dataset_id="employed", locator="x.csv",
            fields=["year", "male_percent", "female_percent", "total_percent"]
        ),
        freshness=Freshness(asof_date="2023-12-31"),
    )


def test_pattern_detective_initialization():
    client = DataClient()
    agent = PatternDetectiveAgent(client)
    assert agent.client is client


def test_pattern_detective_run(monkeypatch):
    client = DataClient()
    monkeypatch.setattr(client, "run", lambda qid: _qr_consistent())
    out = PatternDetectiveAgent(client).run()
    assert isinstance(out, AgentReport)
    assert out.agent == "PatternDetective"


def test_pattern_detective_detects_inconsistency(monkeypatch):
    qr = _qr_inconsistent()
    client = DataClient()
    monkeypatch.setattr(client, "run", lambda qid: qr)
    rep = PatternDetectiveAgent(client).run()
    has_warning = any("sum_mismatch" in w for w in rep.warnings)
    has_metric = rep.findings[0].metrics.get("delta_percent") is not None
    assert has_warning or has_metric


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
