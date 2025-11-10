"""Unit tests for NationalStrategyAgent."""

import pytest

from src.qnwis.agents.base import AgentReport, DataClient
from src.qnwis.agents.national_strategy import NationalStrategyAgent
from src.qnwis.data.deterministic.models import Freshness, Provenance, QueryResult, Row


def test_national_strategy_initialization():
    client = DataClient()
    agent = NationalStrategyAgent(client)
    assert agent.client is client


def test_national_strategy_run(monkeypatch):
    emp = QueryResult(
        query_id="q_employment_share_by_gender_2023",
        rows=[Row(data={"year": 2023, "male_percent": 60.0, "female_percent": 40.0, "total_percent": 100.0})],
        unit="percent",
        provenance=Provenance(
            source="csv", dataset_id="employed", locator="x.csv",
            fields=["year", "male_percent", "female_percent", "total_percent"]
        ),
        freshness=Freshness(asof_date="2023-12-31")
    )
    gcc = QueryResult(
        query_id="q_unemployment_rate_gcc_latest",
        rows=[
            Row(data={"country": "QAT", "year": 2023, "value": 0.1}),
            Row(data={"country": "ARE", "year": 2023, "value": 2.8})
        ],
        unit="percent",
        provenance=Provenance(
            source="world_bank", dataset_id="SL.UEM.TOTL.ZS",
            locator="indicator=SL.UEM.TOTL.ZS", fields=["country", "year", "value"]
        ),
        freshness=Freshness(asof_date="api")
    )
    client = DataClient()

    def _run(qid):
        return emp if qid == emp.query_id else gcc

    monkeypatch.setattr(client, "run", _run)
    rep = NationalStrategyAgent(client).run()
    assert isinstance(rep, AgentReport)
    assert "gcc_unemployment_min" in rep.findings[0].metrics


def test_national_strategy_combines_metrics(monkeypatch):
    emp = QueryResult(
        query_id="q_employment_share_by_gender_2023",
        rows=[Row(data={"year": 2023, "male_percent": 60.0, "female_percent": 40.0, "total_percent": 100.0})],
        unit="percent",
        provenance=Provenance(
            source="csv", dataset_id="employed", locator="x.csv",
            fields=["year", "male_percent", "female_percent", "total_percent"]
        ),
        freshness=Freshness(asof_date="2023-12-31")
    )
    gcc = QueryResult(
        query_id="q_unemployment_rate_gcc_latest",
        rows=[
            Row(data={"country": "QAT", "year": 2023, "value": 0.1}),
            Row(data={"country": "SAU", "year": 2023, "value": 5.4})
        ],
        unit="percent",
        provenance=Provenance(
            source="world_bank", dataset_id="SL.UEM.TOTL.ZS",
            locator="indicator=SL.UEM.TOTL.ZS", fields=["country", "year", "value"]
        ),
        freshness=Freshness(asof_date="api")
    )
    client = DataClient()

    def _run(qid):
        return emp if qid == emp.query_id else gcc

    monkeypatch.setattr(client, "run", _run)
    rep = NationalStrategyAgent(client).run()
    m = rep.findings[0].metrics
    assert any(k.startswith("employment_") for k in m)
    assert "gcc_unemployment_min" in m
    assert m["gcc_unemployment_min"] == 0.1
    assert m["gcc_unemployment_max"] == 5.4


def test_gcc_benchmark_uses_data_client(monkeypatch):
    calls: list[str] = []
    client = DataClient()
    gcc = QueryResult(
        query_id="syn_unemployment_rate_gcc_latest",
        rows=[
            Row(data={"country": "Qatar", "unemployment_rate": 1.0, "year": 2023}),
            Row(data={"country": "Oman", "unemployment_rate": 2.0, "year": 2023}),
            Row(data={"country": "Bahrain", "unemployment_rate": 3.0, "year": 2023}),
        ],
        unit="percent",
        provenance=Provenance(
            source="csv",
            dataset_id="syn_unemployment_rate_gcc_latest",
            locator="syn_unemployment_rate_gcc_latest.csv",
            fields=["country", "unemployment_rate", "year"],
        ),
        freshness=Freshness(asof_date="2024-01-01"),
    )

    def _run(query_id: str) -> QueryResult:
        calls.append(query_id)
        return gcc

    monkeypatch.setattr(client, "run", _run)
    NationalStrategyAgent(client).gcc_benchmark(min_countries=3)
    assert calls == ["syn_unemployment_rate_gcc_latest"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
