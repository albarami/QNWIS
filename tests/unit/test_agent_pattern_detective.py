"""Unit tests for PatternDetectiveAgent."""

import pytest

from src.qnwis.agents.base import AgentReport, DataClient
from src.qnwis.agents.pattern_detective import PatternDetectiveAgent
from src.qnwis.data.deterministic.models import Freshness, Provenance, QueryResult, Row


def _sector_result(query_id: str, field: str, values: list[float]) -> QueryResult:
    rows = [
        Row(data={"sector": f"S{i+1}", field: float(value)})
        for i, value in enumerate(values)
    ]
    return QueryResult(
        query_id=query_id,
        rows=rows,
        unit="percent",
        provenance=Provenance(
            source="csv",
            dataset_id=query_id,
            locator=f"{query_id}.csv",
            fields=["sector", field],
        ),
        freshness=Freshness(asof_date="2024-01-01"),
    )


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


def test_find_correlations_fallbacks_to_spearman(monkeypatch):
    client = DataClient()
    qat_qr = _sector_result(
        "syn_qatarization_by_sector_latest",
        "qatarization_percent",
        [50.0, 50.0, 50.0],
    )
    atr_qr = _sector_result(
        "syn_attrition_by_sector_latest",
        "attrition_percent",
        [5.0, 10.0, 15.0],
    )

    def _run(query_id: str) -> QueryResult:
        if query_id == qat_qr.query_id:
            return qat_qr
        if query_id == atr_qr.query_id:
            return atr_qr
        raise AssertionError(f"Unexpected query requested: {query_id}")

    monkeypatch.setattr(client, "run", _run)
    report = PatternDetectiveAgent(client).find_correlations(method="pearson", min_sample_size=3)
    finding = report.findings[0]
    assert finding.metrics["method_used"] == "spearman"
    assert "Fallback from pearson" in finding.summary


def test_detect_anomalous_retention_validates_threshold():
    client = DataClient()
    agent = PatternDetectiveAgent(client)
    with pytest.raises(ValueError):
        agent.detect_anomalous_retention(z_threshold=0.0)


def test_best_practices_invokes_data_client_once(monkeypatch):
    client = DataClient()
    calls: list[str] = []

    res = _sector_result(
        "syn_qatarization_by_sector_latest",
        "qatarization_percent",
        [60.0, 55.0, 50.0, 45.0],
    )

    def _run(query_id: str) -> QueryResult:
        calls.append(query_id)
        return res

    monkeypatch.setattr(client, "run", _run)
    PatternDetectiveAgent(client).best_practices(metric="qatarization", top_n=3)
    assert calls == ["syn_qatarization_by_sector_latest"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
