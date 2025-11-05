"""
Unit tests for SkillsAgent.

Tests skills pipeline analysis using gender distribution as a proxy metric.
"""

import pytest

from src.qnwis.agents.base import AgentReport, DataClient
from src.qnwis.agents.skills import SkillsAgent
from src.qnwis.data.deterministic.models import Freshness, Provenance, QueryResult, Row


def _qr_skills():
    """Generate test QueryResult for skills/employment data."""
    return QueryResult(
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
            dataset_id="employed",
            locator="x.csv",
            fields=["year", "male_percent", "female_percent", "total_percent"],
        ),
        freshness=Freshness(asof_date="2023-12-31"),
    )


def test_skills_agent_initialization():
    """Verify agent can be initialized with DataClient."""
    client = DataClient()
    agent = SkillsAgent(client)
    assert agent.client is client


def test_skills_agent_run(monkeypatch):
    """Test full agent execution with mocked data."""
    client = DataClient()
    monkeypatch.setattr(client, "run", lambda qid: _qr_skills())
    out = SkillsAgent(client).run()
    assert isinstance(out, AgentReport)
    assert out.agent == "Skills"
    assert len(out.findings) > 0


def test_skills_metrics(monkeypatch):
    """Verify agent extracts gender distribution metrics."""
    qr = _qr_skills()
    client = DataClient()
    monkeypatch.setattr(client, "run", lambda qid: qr)
    out = SkillsAgent(client).run()
    m = out.findings[0].metrics
    assert m.get("female_percent") == 40.0
    assert m.get("male_percent") == 60.0
    assert m.get("total_percent") == 100.0


def test_skills_title_and_summary(monkeypatch):
    """Verify agent produces correct title and summary."""
    client = DataClient()
    monkeypatch.setattr(client, "run", lambda qid: _qr_skills())
    out = SkillsAgent(client).run()
    finding = out.findings[0]
    assert "Gender distribution" in finding.title or "gender" in finding.title.lower()
    assert len(finding.summary) > 0


def test_skills_evidence(monkeypatch):
    """Verify agent includes proper provenance evidence."""
    client = DataClient()
    monkeypatch.setattr(client, "run", lambda qid: _qr_skills())
    out = SkillsAgent(client).run()
    ev = out.findings[0].evidence
    assert len(ev) > 0
    assert ev[0].query_id == "q_employment_share_by_gender_2023"


def test_skills_with_empty_data(monkeypatch):
    """Test agent handles empty result gracefully."""
    empty_result = QueryResult(
        query_id="q_employment_share_by_gender_2023",
        rows=[],
        unit="percent",
        provenance=Provenance(
            source="csv", dataset_id="employed", locator="x.csv", fields=[]
        ),
        freshness=Freshness(asof_date="2023-12-31"),
    )
    client = DataClient()
    monkeypatch.setattr(client, "run", lambda qid: empty_result)
    out = SkillsAgent(client).run()
    assert isinstance(out, AgentReport)
    # Metrics should be empty
    m = out.findings[0].metrics
    assert len(m) == 0


def test_skills_with_partial_data(monkeypatch):
    """Test agent handles rows with missing fields."""
    partial_result = QueryResult(
        query_id="q_employment_share_by_gender_2023",
        rows=[Row(data={"year": 2023, "male_percent": 60.0})],  # Missing female_percent
        unit="percent",
        provenance=Provenance(
            source="csv",
            dataset_id="employed",
            locator="x.csv",
            fields=["year", "male_percent"],
        ),
        freshness=Freshness(asof_date="2023-12-31"),
    )
    client = DataClient()
    monkeypatch.setattr(client, "run", lambda qid: partial_result)
    out = SkillsAgent(client).run()
    m = out.findings[0].metrics
    # Should extract available fields
    assert m.get("male_percent") == 60.0
    # Missing fields should not be present
    assert "female_percent" not in m or m["female_percent"] is None


def test_skills_warnings_propagation(monkeypatch):
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
            dataset_id="employed",
            locator="x.csv",
            fields=["year", "male_percent", "female_percent", "total_percent"],
        ),
        freshness=Freshness(asof_date="2023-12-31"),
        warnings=["data_quality_issue"],
    )
    client = DataClient()
    monkeypatch.setattr(client, "run", lambda qid: result_with_warnings)
    out = SkillsAgent(client).run()
    assert "data_quality_issue" in out.findings[0].warnings


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
