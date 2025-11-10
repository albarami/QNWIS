"""
Integration tests for orchestration workflow.

Tests end-to-end workflow execution with real agents (using mock data).
"""

import pytest

from src.qnwis.agents.base import AgentReport, DataClient, Insight, evidence_from
from src.qnwis.data.deterministic.models import Freshness, Provenance, QueryResult, Row
from src.qnwis.orchestration.graph import create_graph
from src.qnwis.orchestration.registry import AgentRegistry
from src.qnwis.orchestration.schemas import OrchestrationTask


class MockDataClient:
    """Mock DataClient for testing."""

    def run(self, query_id: str):
        """Return mock query result."""
        return QueryResult(
            query_id=query_id,
            rows=[
                Row(data={"sector": "Construction", "attrition_rate": 15.2}),
                Row(data={"sector": "Finance", "attrition_rate": 8.5}),
            ],
            unit="percent",
            provenance=Provenance(
                source="csv",
                dataset_id="mock_dataset",
                locator="/data/mock_dataset.csv",
                fields=["sector", "attrition_rate"],
            ),
            freshness=Freshness(
                asof_date="2025-01-01",
                updated_at="2025-01-01T00:00:00Z",
            ),
            warnings=[],
        )


class MockAgent:
    """Mock agent for testing."""

    def __init__(self, client):
        self.client = client

    def mock_method(self, **kwargs):
        """Mock analysis method."""
        query_result = self.client.run("mock.query")
        return AgentReport(
            agent="MockAgent",
            findings=[
                Insight(
                    title="Mock Finding",
                    summary="This is a mock finding for testing.",
                    metrics={"value": 42.0},
                    evidence=[evidence_from(query_result)],
                )
            ],
            warnings=[],
        )


@pytest.fixture
def mock_registry():
    """Create registry with mock agent."""
    client = MockDataClient()
    registry = AgentRegistry()

    agent = MockAgent(client)
    registry.register("pattern.anomalies", agent, "mock_method")

    return registry


def test_workflow_execution_success(mock_registry):
    """Test successful workflow execution."""
    graph = create_graph(mock_registry)

    task = OrchestrationTask(intent="pattern.anomalies", params={})

    result = graph.run(task)

    assert result is not None
    assert result.ok is True
    assert result.intent == "pattern.anomalies"
    assert len(result.sections) >= 1
    assert result.sections[0].title == "Executive Summary"


def test_workflow_unknown_intent(mock_registry):
    """Test workflow with unknown intent."""
    graph = create_graph(mock_registry)

    task = OrchestrationTask(intent="strategy.vision2030", params={})

    result = graph.run(task)

    # Should return error result, not crash
    assert result is not None
    assert result.ok is False
    assert len(result.warnings) > 0


def test_workflow_with_params(mock_registry):
    """Test workflow with parameters."""
    graph = create_graph(mock_registry)

    task = OrchestrationTask(
        intent="pattern.anomalies",
        params={"sector": "Construction", "threshold": 2.5},
    )

    result = graph.run(task)

    assert result is not None
    assert result.ok is True
    # Parameters should be in reproducibility metadata
    assert result.reproducibility.params.get("sector") == "Construction"


def test_workflow_with_request_tracking(mock_registry):
    """Test workflow preserves request tracking."""
    graph = create_graph(mock_registry)

    task = OrchestrationTask(
        intent="pattern.anomalies",
        user_id="test_user",
        request_id="TEST-001",
    )

    result = graph.run(task)

    assert result is not None
    assert result.request_id == "TEST-001"


def test_workflow_state_transitions(mock_registry):
    """Test that workflow goes through expected states."""
    graph = create_graph(mock_registry)

    task = OrchestrationTask(intent="pattern.anomalies", params={})

    # This should go: router -> invoke -> verify -> format
    result = graph.run(task)

    assert result is not None
    assert result.ok is True
    # Result should have formatted sections
    assert any(s.title == "Executive Summary" for s in result.sections)
    assert any(s.title == "Key Findings" for s in result.sections)


@pytest.mark.integration
def test_full_workflow_with_real_agents():
    """Test workflow with real agents (requires data layer)."""
    # Skip if data layer not available
    try:
        from src.qnwis.orchestration.registry import create_default_registry

        client = DataClient()
        registry = create_default_registry(client)
    except Exception:
        pytest.skip("Data layer not available")

    graph = create_graph(registry)

    # Try each registered intent
    for intent in registry.intents():
        task = OrchestrationTask(intent=intent, params={})

        result = graph.run(task)

        # Should not crash, may have warnings if data missing
        assert result is not None
        assert isinstance(result.ok, bool)
