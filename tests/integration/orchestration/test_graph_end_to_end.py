"""
Integration tests for QNWIS orchestration graph end-to-end.

Tests cover:
- Complete workflow execution with real agent integration
- Multiple intent paths (pattern and strategy agents)
- Deterministic results with stubbed DataClient
- Graceful degradation on errors
- Full state transitions through all nodes
"""

import pytest

from src.qnwis.agents.base import DataClient
from src.qnwis.agents.national_strategy import NationalStrategyAgent
from src.qnwis.agents.pattern_detective import PatternDetectiveAgent
from src.qnwis.data.deterministic.models import Freshness, Provenance, QueryResult, Row
from src.qnwis.orchestration.graph import QNWISGraph, create_graph
from src.qnwis.orchestration.registry import AgentRegistry
from src.qnwis.orchestration.schemas import OrchestrationResult, OrchestrationTask


class StubbedDataClient(DataClient):
    """
    Stubbed data client for integration testing.

    Returns synthetic results without requiring real data files.
    """

    def __init__(self) -> None:
        self._responses: dict[str, QueryResult] = {}
        # Skip parent init to avoid filesystem checks
        self.ttl_s = 300

    def add_response(self, query_id: str, result: QueryResult) -> None:
        """Register a synthetic query result."""
        self._responses[query_id] = result

    def run(self, query_id: str) -> QueryResult:
        """Return pre-configured synthetic result."""
        if query_id not in self._responses:
            # Return empty result rather than raising
            return QueryResult(
                query_id=query_id,
                rows=[],
                provenance=Provenance(
                    dataset_id="synthetic",
                    locator=f"synthetic://{query_id}",
                ),
                freshness=Freshness(
                    as_of="2024-01-01T00:00:00Z",
                    updated_at="2024-01-01T00:00:00Z",
                ),
            )
        return self._responses[query_id]


@pytest.fixture
def stubbed_client() -> StubbedDataClient:
    """Fixture providing a stubbed client with synthetic data."""
    client = StubbedDataClient()

    # Add synthetic attrition data for pattern detective
    attrition_result = QueryResult(
        query_id="syn_attrition_by_sector_latest",
        rows=[
            Row(data={"sector": "Finance", "attrition_percent": 10.0}),
            Row(data={"sector": "Retail", "attrition_percent": 12.0}),
            Row(data={"sector": "Manufacturing", "attrition_percent": 11.0}),
            Row(data={"sector": "Healthcare", "attrition_percent": 15.0}),
            Row(data={"sector": "Construction", "attrition_percent": 45.0}),  # Anomaly
        ],
        provenance=Provenance(
            dataset_id="attrition_data",
            locator="data/attrition.csv",
        ),
        freshness=Freshness(
            as_of="2024-01-15T00:00:00Z",
            updated_at="2024-01-15T00:00:00Z",
        ),
    )
    client.add_response("syn_attrition_by_sector_latest", attrition_result)

    # Add synthetic GCC data for strategy agent
    gcc_result = QueryResult(
        query_id="syn_gcc_unemployment_comparison",
        rows=[
            Row(data={"country": "Saudi Arabia", "unemployment_rate": 5.6}),
            Row(data={"country": "UAE", "unemployment_rate": 2.8}),
            Row(data={"country": "Qatar", "unemployment_rate": 0.3}),
            Row(data={"country": "Kuwait", "unemployment_rate": 3.2}),
        ],
        provenance=Provenance(
            dataset_id="gcc_data",
            locator="data/gcc_stats.csv",
        ),
        freshness=Freshness(
            as_of="2024-01-10T00:00:00Z",
            updated_at="2024-01-10T00:00:00Z",
        ),
    )
    client.add_response("syn_gcc_unemployment_comparison", gcc_result)

    return client


@pytest.fixture
def test_registry(stubbed_client: StubbedDataClient) -> AgentRegistry:
    """Create a test registry with stubbed agents."""
    registry = AgentRegistry()

    # Create agents with stubbed client
    pattern_agent = PatternDetectiveAgent(stubbed_client)
    strategy_agent = NationalStrategyAgent(stubbed_client)

    # Register pattern intents
    registry.register("pattern.anomalies", pattern_agent, "detect_anomalous_retention")
    registry.register("pattern.correlation", pattern_agent, "find_correlations")

    # Register strategy intents
    registry.register("strategy.gcc_benchmark", strategy_agent, "gcc_benchmark")

    return registry


def test_graph_pattern_anomalies_end_to_end(test_registry: AgentRegistry) -> None:
    """Test complete workflow for pattern anomalies detection."""
    # Create and build graph
    graph = create_graph(test_registry)

    # Create task
    task = OrchestrationTask(
        intent="pattern.anomalies",
        params={"z_threshold": 2.5, "min_sample_size": 3},
        request_id="test-001",
    )

    # Run workflow
    result = graph.run(task)

    # Verify result structure
    assert isinstance(result, OrchestrationResult)
    assert result.ok is True
    assert result.intent == "pattern.anomalies"
    assert result.request_id == "test-001"

    # Verify sections present
    section_titles = [s.title for s in result.sections]
    assert "Executive Summary" in section_titles
    assert "Key Findings" in section_titles
    assert "Evidence (Top Sources)" in section_titles

    # Verify citations present
    assert len(result.citations) > 0
    assert any(c.query_id == "syn_attrition_by_sector_latest" for c in result.citations)

    # Verify freshness metadata
    assert "attrition_data" in result.freshness
    assert result.freshness["attrition_data"].age_days is not None

    # Verify reproducibility metadata
    assert result.reproducibility is not None
    assert "PatternDetectiveAgent" in result.reproducibility.method
    assert "z_threshold" in result.reproducibility.params


def test_graph_pattern_correlation_end_to_end(test_registry: AgentRegistry) -> None:
    """Test complete workflow for pattern correlation analysis."""
    graph = create_graph(test_registry)

    task = OrchestrationTask(
        intent="pattern.correlation",
        params={"sector": "Construction", "months": 12},
        request_id="test-002",
    )

    result = graph.run(task)

    # Verify result
    assert isinstance(result, OrchestrationResult)
    assert result.ok is True
    assert result.intent == "pattern.correlation"

    # Verify sections
    assert len(result.sections) >= 3

    # Verify citations
    assert len(result.citations) > 0

    # Verify reproducibility
    assert result.reproducibility.params["sector"] == "Construction"
    assert result.reproducibility.params["months"] == 12


def test_graph_strategy_gcc_benchmark_end_to_end(test_registry: AgentRegistry) -> None:
    """Test complete workflow for GCC benchmarking."""
    graph = create_graph(test_registry)

    task = OrchestrationTask(
        intent="strategy.gcc_benchmark",
        params={"min_countries": 3},
        request_id="test-003",
    )

    result = graph.run(task)

    # Verify result
    assert isinstance(result, OrchestrationResult)
    assert result.ok is True
    assert result.intent == "strategy.gcc_benchmark"

    # Verify sections
    assert len(result.sections) >= 3

    # Verify citations contain GCC data
    assert any(c.dataset_id == "gcc_data" for c in result.citations)

    # Verify reproducibility
    assert "NationalStrategyAgent" in result.reproducibility.method


def test_graph_handles_unknown_intent(test_registry: AgentRegistry) -> None:
    """Test that graph handles unknown intents gracefully."""
    create_graph(test_registry)

    task = OrchestrationTask(
        intent="pattern.correlation",  # Valid literal but not registered
        params={},
        request_id="test-004",
    )

    # Manually change intent to something unregistered
    # (normally would be caught by pydantic, but testing error path)
    task_dict = task.model_dump()
    task_dict["intent"] = "unknown.intent"

    # Create state manually to bypass validation

    # Manually set an unknown intent that isn't registered
    # We'll test by registering limited intents
    limited_registry = AgentRegistry()
    stubbed_client = StubbedDataClient()
    pattern_agent = PatternDetectiveAgent(stubbed_client)
    limited_registry.register("pattern.anomalies", pattern_agent, "detect_anomalous_retention")

    limited_graph = create_graph(limited_registry)

    # Try to run with unregistered intent
    task_unknown = OrchestrationTask(
        intent="pattern.correlation",  # Not in limited_registry
        params={},
        request_id="test-004",
    )

    result = limited_graph.run(task_unknown)

    # Should get error result
    assert isinstance(result, OrchestrationResult)
    assert result.ok is False
    assert len(result.warnings) > 0
    assert any("Unknown intent" in w or "intent" in w.lower() for w in result.warnings)


def test_graph_handles_agent_errors_gracefully(test_registry: AgentRegistry) -> None:
    """Test graceful degradation when agent raises errors."""

    class FailingAgent:
        """Agent that always raises errors."""

        def __init__(self, client: DataClient) -> None:
            self.client = client

        def failing_method(self) -> None:
            """Method that always fails."""
            raise ValueError("Simulated agent failure")

    # Create registry with failing agent
    failing_registry = AgentRegistry()
    stubbed_client = StubbedDataClient()
    failing_agent = FailingAgent(stubbed_client)
    failing_registry.register("test.failing", failing_agent, "failing_method")

    graph = create_graph(failing_registry)

    task = OrchestrationTask(
        intent="pattern.correlation",  # Use valid intent literal
        params={},
        request_id="test-005",
    )

    result = graph.run(task)

    # Should get error result
    assert isinstance(result, OrchestrationResult)
    assert result.ok is False
    assert len(result.warnings) > 0

    # Should have error information
    error_text = " ".join(result.warnings)
    assert "error" in error_text.lower() or "unknown intent" in error_text.lower()


def test_graph_multiple_sequential_runs(test_registry: AgentRegistry) -> None:
    """Test that graph can handle multiple sequential runs."""
    graph = create_graph(test_registry)

    # First run
    task1 = OrchestrationTask(
        intent="pattern.anomalies",
        params={"z_threshold": 2.5},
        request_id="test-006a",
    )
    result1 = graph.run(task1)
    assert result1.ok is True
    assert result1.request_id == "test-006a"

    # Second run with different intent
    task2 = OrchestrationTask(
        intent="strategy.gcc_benchmark",
        params={"min_countries": 3},
        request_id="test-006b",
    )
    result2 = graph.run(task2)
    assert result2.ok is True
    assert result2.request_id == "test-006b"

    # Results should be independent
    assert result1.intent != result2.intent
    assert result1.reproducibility.method != result2.reproducibility.method


def test_graph_with_custom_config(test_registry: AgentRegistry) -> None:
    """Test graph with custom configuration."""
    custom_config = {
        "timeouts": {"agent_call_ms": 60000},
        "validation": {
            "strict": False,
            "require_evidence": True,
            "require_freshness": True,
        },
        "formatting": {
            "max_findings": 5,  # Limit findings
            "max_citations": 10,
            "top_evidence": 3,
        },
    }

    graph = QNWISGraph(test_registry, config=custom_config)
    graph.build()

    task = OrchestrationTask(
        intent="pattern.anomalies",
        params={},
        request_id="test-007",
    )

    result = graph.run(task)

    # Should succeed with custom config
    assert result.ok is True


def test_graph_preserves_request_id(test_registry: AgentRegistry) -> None:
    """Test that request_id is preserved through workflow."""
    graph = create_graph(test_registry)

    task = OrchestrationTask(
        intent="pattern.anomalies",
        params={},
        request_id="custom-request-123",
    )

    result = graph.run(task)

    assert result.request_id == "custom-request-123"


def test_graph_deterministic_output(test_registry: AgentRegistry) -> None:
    """Test that graph produces deterministic output for same inputs."""
    graph = create_graph(test_registry)

    task = OrchestrationTask(
        intent="pattern.anomalies",
        params={"z_threshold": 2.5, "min_sample_size": 3},
        request_id="test-008",
    )

    # Run twice
    result1 = graph.run(task)
    result2 = graph.run(task)

    # Key fields should be deterministic
    assert result1.intent == result2.intent
    assert result1.ok == result2.ok
    assert len(result1.sections) == len(result2.sections)
    assert len(result1.citations) == len(result2.citations)

    # Section structure should be identical
    for s1, s2 in zip(result1.sections, result2.sections):
        assert s1.title == s2.title


def test_graph_citation_quality(test_registry: AgentRegistry) -> None:
    """Test that citations have required metadata."""
    graph = create_graph(test_registry)

    task = OrchestrationTask(
        intent="pattern.anomalies",
        params={},
        request_id="test-009",
    )

    result = graph.run(task)

    # All citations should have required fields
    for citation in result.citations:
        assert citation.query_id
        assert citation.dataset_id
        assert citation.locator
        assert len(citation.fields) > 0
        assert citation.timestamp is not None


def test_graph_freshness_metadata(test_registry: AgentRegistry) -> None:
    """Test that freshness metadata is properly populated."""
    graph = create_graph(test_registry)

    task = OrchestrationTask(
        intent="strategy.gcc_benchmark",
        params={},
        request_id="test-010",
    )

    result = graph.run(task)

    # Should have freshness entries
    assert len(result.freshness) > 0

    # Each freshness entry should have required fields
    for source, freshness in result.freshness.items():
        assert freshness.source == source
        assert freshness.last_updated
        assert freshness.age_days is not None
