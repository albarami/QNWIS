"""
Unit tests for council orchestrator.

Tests deterministic multi-agent execution, verification integration,
and council report generation.
"""

import pytest

from src.qnwis.agents.base import AgentReport, DataClient, Evidence, Insight
from src.qnwis.data.deterministic.models import Freshness, Provenance, QueryResult, Row
from src.qnwis.orchestration.council import CouncilConfig, default_agents, run_council


def _mock_query_result(query_id: str) -> QueryResult:
    """Generate mock QueryResult for testing."""
    return QueryResult(
        query_id=query_id,
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
            dataset_id="test-dataset",
            locator="test.csv",
            fields=["year", "male_percent", "female_percent", "total_percent"],
        ),
        freshness=Freshness(asof_date="2023-12-31"),
    )


def test_council_config_defaults():
    """Verify CouncilConfig default values."""
    cfg = CouncilConfig()
    assert cfg.queries_dir is None
    assert cfg.ttl_s == 300


def test_council_config_custom():
    """Verify CouncilConfig with custom values."""
    cfg = CouncilConfig(queries_dir="custom/path", ttl_s=600)
    assert cfg.queries_dir == "custom/path"
    assert cfg.ttl_s == 600


def test_default_agents_creates_five():
    """Verify default_agents creates all 5 agents."""
    client = DataClient()
    agents = default_agents(client)
    assert len(agents) == 5
    # All agents should have run() method
    for agent in agents:
        assert hasattr(agent, "run")


def test_default_agents_types():
    """Verify default_agents creates correct agent types."""
    from src.qnwis.agents.labour_economist import LabourEconomistAgent
    from src.qnwis.agents.national_strategy import NationalStrategyAgent
    from src.qnwis.agents.nationalization import NationalizationAgent
    from src.qnwis.agents.pattern_detective import PatternDetectiveAgent
    from src.qnwis.agents.skills import SkillsAgent

    client = DataClient()
    agents = default_agents(client)
    agent_types = {type(a) for a in agents}
    expected_types = {
        LabourEconomistAgent,
        NationalizationAgent,
        SkillsAgent,
        PatternDetectiveAgent,
        NationalStrategyAgent,
    }
    assert agent_types == expected_types


def test_run_council_structure(monkeypatch):
    """Verify run_council returns correct structure."""

    def mock_run(self, query_id: str):
        return _mock_query_result(query_id)

    # Monkeypatch DataClient.run to return mock data
    monkeypatch.setattr("src.qnwis.agents.base.DataClient.run", mock_run)

    cfg = CouncilConfig()
    result = run_council(cfg)

    # Check top-level structure
    assert "council" in result
    assert "verification" in result

    # Check council structure
    council = result["council"]
    assert "agents" in council
    assert "findings" in council
    assert "consensus" in council
    assert "warnings" in council
    assert "min_confidence" in council
    assert isinstance(result["rate_limit_applied"], bool)

    # Check verification structure
    verification = result["verification"]
    assert isinstance(verification, dict)


def test_run_council_agent_names(monkeypatch):
    """Verify all expected agents are present in results."""

    def mock_run(self, query_id: str):
        return _mock_query_result(query_id)

    monkeypatch.setattr("src.qnwis.agents.base.DataClient.run", mock_run)

    cfg = CouncilConfig()
    result = run_council(cfg)

    expected_agents = {
        "LabourEconomist",
        "Nationalization",
        "Skills",
        "PatternDetective",
        "NationalStrategy",
    }
    actual_agents = set(result["council"]["agents"])
    assert actual_agents == expected_agents


def test_run_council_findings_format(monkeypatch):
    """Verify findings are properly formatted."""

    def mock_run(self, query_id: str):
        return _mock_query_result(query_id)

    monkeypatch.setattr("src.qnwis.agents.base.DataClient.run", mock_run)

    cfg = CouncilConfig()
    result = run_council(cfg)

    findings = result["council"]["findings"]
    assert len(findings) > 0

    # Check first finding structure
    finding = findings[0]
    assert "title" in finding
    assert "summary" in finding
    assert "metrics" in finding
    assert "evidence" in finding
    assert "warnings" in finding
    assert "confidence_score" in finding


def test_run_council_verification_format(monkeypatch):
    """Verify verification results are properly formatted."""

    def mock_run(self, query_id: str):
        return _mock_query_result(query_id)

    monkeypatch.setattr("src.qnwis.agents.base.DataClient.run", mock_run)

    cfg = CouncilConfig()
    result = run_council(cfg)

    verification = result["verification"]
    # Each agent should have a verification entry
    for agent_name in result["council"]["agents"]:
        assert agent_name in verification
        issues = verification[agent_name]
        assert isinstance(issues, list)
        # Check issue format if any exist
        for issue in issues:
            assert "level" in issue
            assert "code" in issue
            assert "detail" in issue


def test_run_council_custom_agents(monkeypatch):
    """Verify run_council accepts custom agent factory."""

    def mock_run(self, query_id: str):
        return _mock_query_result(query_id)

    monkeypatch.setattr("src.qnwis.agents.base.DataClient.run", mock_run)

    def custom_agents(client: DataClient):
        from src.qnwis.agents.labour_economist import LabourEconomistAgent

        return [LabourEconomistAgent(client)]

    cfg = CouncilConfig()
    result = run_council(cfg, make_agents=custom_agents)

    # Should only have one agent
    assert len(result["council"]["agents"]) == 1
    assert result["council"]["agents"][0] == "LabourEconomist"


def test_run_council_consensus_computed(monkeypatch):
    """Verify consensus metrics are computed."""

    def mock_run(self, query_id: str):
        return _mock_query_result(query_id)

    monkeypatch.setattr("src.qnwis.agents.base.DataClient.run", mock_run)

    cfg = CouncilConfig()
    result = run_council(cfg)

    consensus = result["council"]["consensus"]
    assert isinstance(consensus, dict)
    # With multiple agents, some metrics should have consensus
    # (exact keys depend on agent implementations)


def test_run_council_deterministic(monkeypatch):
    """Verify council execution is deterministic."""

    def mock_run(self, query_id: str):
        return _mock_query_result(query_id)

    monkeypatch.setattr("src.qnwis.agents.base.DataClient.run", mock_run)

    cfg = CouncilConfig()
    result1 = run_council(cfg)
    result2 = run_council(cfg)

    # Agent order should be identical
    assert result1["council"]["agents"] == result2["council"]["agents"]

    # Number of findings should be identical
    assert len(result1["council"]["findings"]) == len(result2["council"]["findings"])


def test_run_council_with_ttl(monkeypatch):
    """Verify TTL configuration is passed to DataClient."""

    def mock_run(self, query_id: str):
        return _mock_query_result(query_id)

    monkeypatch.setattr("src.qnwis.agents.base.DataClient.run", mock_run)

    cfg = CouncilConfig(ttl_s=600)
    result = run_council(cfg)

    # Should execute without error
    assert "council" in result


def test_run_council_warnings_collected(monkeypatch):
    """Verify warnings from all agents are collected."""

    def mock_run(self, query_id: str):
        result = _mock_query_result(query_id)
        result.warnings = ["test_warning"]
        return result

    monkeypatch.setattr("src.qnwis.agents.base.DataClient.run", mock_run)

    cfg = CouncilConfig()
    result = run_council(cfg)

    warnings = result["council"]["warnings"]
    assert isinstance(warnings, list)
    # Warnings should be deduplicated and sorted
    assert warnings == sorted(set(warnings))


def test_run_council_json_serializable(monkeypatch):
    """Verify entire result is JSON-serializable."""
    import json

    def mock_run(self, query_id: str):
        return _mock_query_result(query_id)

    monkeypatch.setattr("src.qnwis.agents.base.DataClient.run", mock_run)

    cfg = CouncilConfig()
    result = run_council(cfg)

    # Should not raise
    json_str = json.dumps(result)
    assert len(json_str) > 0

    # Round-trip should work
    parsed = json.loads(json_str)
    assert parsed["council"]["agents"] == result["council"]["agents"]
    assert parsed["rate_limit_applied"] == result["rate_limit_applied"]


def test_run_council_empty_findings_edge_case(monkeypatch):
    """Verify council handles agents with no findings."""

    def custom_agents(client: DataClient):
        class EmptyAgent:
            def __init__(self, client):
                self.client = client

            def run(self):
                return AgentReport(agent="EmptyAgent", findings=[])

        return [EmptyAgent(client)]

    cfg = CouncilConfig()
    result = run_council(cfg, make_agents=custom_agents)

    assert len(result["council"]["agents"]) == 1
    assert len(result["council"]["findings"]) == 0
    assert result["council"]["consensus"] == {}
    assert result["council"]["min_confidence"] == pytest.approx(1.0)


def test_run_council_min_confidence(monkeypatch):
    """Verify min_confidence reflects lowest insight confidence score."""

    class StaticAgent:
        def __init__(self, agent_name: str, warnings: list[str]):
            self._agent_name = agent_name
            self._warnings = warnings

        def run(self):
            insight = Insight(
                title="Test",
                summary="Summary",
                metrics={"value": 1.0},
                evidence=[
                    Evidence(
                        query_id="q",
                        dataset_id="ds",
                        locator="loc",
                        fields=["value"],
                    )
                ],
                warnings=self._warnings,
            )
            return AgentReport(agent=self._agent_name, findings=[insight])

    def custom_agents(client: DataClient):
        return [StaticAgent("A", ["warn"]), StaticAgent("B", [])]

    cfg = CouncilConfig()
    result = run_council(cfg, make_agents=custom_agents)
    assert result["council"]["min_confidence"] == pytest.approx(0.9)


def test_run_council_rate_limit_env(monkeypatch):
    """Ensure rate limit env var enforces TTL floor and response annotation."""

    original_init = DataClient.__init__
    captured: dict[str, int] = {}

    def wrapped_init(self, queries_dir=None, ttl_s=300):
        captured["ttl_s"] = ttl_s
        original_init(self, queries_dir=queries_dir, ttl_s=ttl_s)

    monkeypatch.setattr("src.qnwis.agents.base.DataClient.__init__", wrapped_init)
    monkeypatch.setenv("QNWIS_RATE_LIMIT_RPS", "2")

    class DummyAgent:
        def __init__(self, client: DataClient):
            self.client = client

        def run(self):
            return AgentReport(agent="Dummy", findings=[])

    def custom_agents(client: DataClient):
        return [DummyAgent(client)]

    cfg = CouncilConfig(ttl_s=10)
    result = run_council(cfg, make_agents=custom_agents)

    assert result["rate_limit_applied"] is True
    assert captured["ttl_s"] >= 60


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
