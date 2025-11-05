"""Integration tests for LangGraph agent workflows."""

import pytest

from src.qnwis.agents.base import DataClient
from src.qnwis.agents.graphs.common import build_simple_graph
from src.qnwis.data.deterministic.models import Freshness, Provenance, QueryResult, Row


def test_graph_runs_with_deterministic_client(monkeypatch):
    def fake_res():
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

    client = DataClient()
    monkeypatch.setattr(client, "run", lambda qid: fake_res())
    graph = build_simple_graph("LabourEconomist", ["q_employment_share_by_gender_2023"], client.run)
    state = graph.invoke({})
    rep = state["report"]
    assert rep.agent == "LabourEconomist"
    assert rep.findings


def test_graph_with_multiple_queries(monkeypatch):
    results = {
        "q1": QueryResult(
            query_id="q1", rows=[Row(data={"v": 1})], unit="count",
            provenance=Provenance(source="csv", dataset_id="d1", locator="l1", fields=["v"]),
            freshness=Freshness(asof_date="2023-12-31")
        ),
        "q2": QueryResult(
            query_id="q2", rows=[Row(data={"v": 2})], unit="count",
            provenance=Provenance(source="csv", dataset_id="d2", locator="l2", fields=["v"]),
            freshness=Freshness(asof_date="2023-12-31")
        ),
    }

    def runner(qid):
        return results[qid]

    graph = build_simple_graph("TestAgent", ["q1", "q2"], runner)
    state = graph.invoke({})
    assert len(state["report"].findings) == 2


def test_graph_with_empty_results(monkeypatch):
    def fake_empty():
        return QueryResult(
            query_id="empty", rows=[], unit="count",
            provenance=Provenance(source="csv", dataset_id="d", locator="l", fields=[]),
            freshness=Freshness(asof_date="2023-12-31")
        )

    graph = build_simple_graph("EmptyAgent", ["empty"], fake_empty)
    state = graph.invoke({})
    assert state["report"].agent == "EmptyAgent"
    assert len(state["report"].findings) == 1
    assert state["report"].findings[0].summary == "No rows."


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
