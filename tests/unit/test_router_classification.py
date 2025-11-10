"""
Tests for router classification integration.

Tests the upgraded router node with natural language query support.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.qnwis.orchestration.nodes.router import route_intent
from src.qnwis.orchestration.registry import AgentRegistry
from src.qnwis.orchestration.schemas import OrchestrationTask


@pytest.fixture
def mock_registry() -> AgentRegistry:
    """Create a mock agent registry."""
    registry = AgentRegistry()

    # Create mock agent
    mock_agent = MagicMock()
    mock_agent.detect_anomalous_retention = MagicMock(return_value="result")
    mock_agent.find_correlations = MagicMock(return_value="result")
    mock_agent.gcc_benchmark = MagicMock(return_value="result")
    mock_agent.apply = MagicMock(return_value="scenario_result")
    mock_agent.compare = MagicMock(return_value="scenario_result")
    mock_agent.batch = MagicMock(return_value="scenario_result")

    # Register intents
    registry.register("pattern.anomalies", mock_agent, "detect_anomalous_retention")
    registry.register("pattern.correlation", mock_agent, "find_correlations")
    registry.register("strategy.gcc_benchmark", mock_agent, "gcc_benchmark")
    registry.register("scenario.apply", mock_agent, "apply")
    registry.register("scenario.compare", mock_agent, "compare")
    registry.register("scenario.batch", mock_agent, "batch")

    return registry


class TestExplicitIntentRouting:
    """Test backward-compatible explicit intent routing."""

    def test_explicit_intent_success(self, mock_registry: AgentRegistry) -> None:
        """Test successful explicit intent routing."""
        task = OrchestrationTask(intent="pattern.anomalies", params={})
        state = {"task": task.model_dump(), "logs": []}

        result = route_intent(state, mock_registry)

        assert result["route"] == "pattern.anomalies"
        assert "error" not in result
        assert "routing_decision" in result
        assert result["routing_decision"]["mode"] == "single"

    def test_explicit_intent_unregistered(self, mock_registry: AgentRegistry) -> None:
        """Test error for unregistered intent."""
        # Use a valid Intent that's not in the mock registry
        task = OrchestrationTask(intent="pattern.root_causes", params={})
        state = {"task": task.model_dump(), "logs": []}

        result = route_intent(state, mock_registry)

        assert "error" in result
        assert "Unknown intent" in result["error"]

    def test_explicit_intent_with_params(self, mock_registry: AgentRegistry) -> None:
        """Test explicit intent with parameters."""
        task = OrchestrationTask(
            intent="pattern.anomalies",
            params={"sector": "Construction", "months": 24}
        )
        state = {"task": task.model_dump(), "logs": []}

        result = route_intent(state, mock_registry)

        assert result["route"] == "pattern.anomalies"
        assert "error" not in result


class TestQueryClassificationRouting:
    """Test natural language query classification routing."""

    def test_simple_query_classification(self, mock_registry: AgentRegistry) -> None:
        """Test classification of simple query."""
        task = OrchestrationTask(
            query_text="Detect unusual salary spikes and anomalies in Healthcare sector"
        )
        state = {"task": task.model_dump(), "logs": []}

        result = route_intent(state, mock_registry)

        assert "route" in result
        assert result["route"] == "pattern.anomalies"
        assert "routing_decision" in result
        assert result["routing_decision"]["mode"] == "single"
        assert "error" not in result
        assert "metadata" in result
        assert result["metadata"]["classification_confidence"] >= 0.0

    def test_correlation_query(self, mock_registry: AgentRegistry) -> None:
        """Test correlation query classification."""
        task = OrchestrationTask(
            query_text="Find correlation and relationship between salary and retention rates"
        )
        state = {"task": task.model_dump(), "logs": []}

        result = route_intent(state, mock_registry)

        assert "route" in result
        assert result["route"] == "pattern.correlation"
        assert "error" not in result

    def test_gcc_benchmark_query(self, mock_registry: AgentRegistry) -> None:
        """Test GCC benchmark query."""
        task = OrchestrationTask(
            query_text="GCC benchmark comparison: How does Qatar compare to UAE and regional countries?"
        )
        state = {"task": task.model_dump(), "logs": []}

        result = route_intent(state, mock_registry)

        assert "route" in result
        assert result["route"] == "strategy.gcc_benchmark"
        assert "error" not in result

    def test_low_confidence_query(self, mock_registry: AgentRegistry) -> None:
        """Test query with low confidence."""
        task = OrchestrationTask(
            query_text="Show me some data"
        )
        state = {"task": task.model_dump(), "logs": []}

        result = route_intent(state, mock_registry)

        # Should return error due to low confidence
        assert "error" in result
        assert "clarification required" in result["error"].lower()
        assert "metadata" in result
        assert "clarifying_question" in result["metadata"]
        assert result["metadata"]["clarifying_question"].startswith(
            "Could you clarify the primary labour market metric or sector"
        )

    def test_no_matching_intents(self, mock_registry: AgentRegistry) -> None:
        """Test query that matches no valid intents."""
        task = OrchestrationTask(
            query_text="Weather forecast for Doha"
        )
        state = {"task": task.model_dump(), "logs": []}

        result = route_intent(state, mock_registry)

        # Should have error or very low confidence
        assert "error" in result or result.get("routing_decision", {}).get("agents", []) == []

    def test_classification_updates_task(self, mock_registry: AgentRegistry) -> None:
        """Test that classification updates the task."""
        task = OrchestrationTask(
            query_text="Detect unusual retention anomalies and outliers in Construction sector"
        )
        state = {"task": task.model_dump(), "logs": []}

        result = route_intent(state, mock_registry)

        # Task should be updated with classification
        if "task" in result:
            updated_task = OrchestrationTask(**result["task"])
            assert updated_task.classification is not None
            assert updated_task.intent is not None  # Primary intent set

    def test_crisis_classification(self, mock_registry: AgentRegistry) -> None:
        """Test crisis-level query classification."""
        task = OrchestrationTask(
            query_text="Urgent: sudden spike in turnover now"
        )
        state = {"task": task.model_dump(), "logs": []}

        result = route_intent(state, mock_registry)

        if "task" in result:
            updated_task = OrchestrationTask(**result["task"])
            if updated_task.classification:
                # Crisis or complex is acceptable (urgency detected but may lack fresh time horizon)
                assert updated_task.classification.complexity in ["crisis", "complex"]


class TestRoutingDecision:
    """Test routing decision generation."""

    def test_routing_decision_single_mode(self, mock_registry: AgentRegistry) -> None:
        """Test single mode routing decision."""
        task = OrchestrationTask(
            query_text="Simple retention check"
        )
        state = {"task": task.model_dump(), "logs": []}

        result = route_intent(state, mock_registry)

        if "routing_decision" in result:
            decision = result["routing_decision"]
            assert decision["mode"] == "single"
            assert len(decision["agents"]) >= 1

    def test_routing_decision_prefetch(self, mock_registry: AgentRegistry) -> None:
        """Test prefetch specs in routing decision."""
        task = OrchestrationTask(
            query_text="Detect unusual retention in Construction"
        )
        state = {"task": task.model_dump(), "logs": []}

        result = route_intent(state, mock_registry)

        if "routing_decision" in result:
            decision = result["routing_decision"]
            # Prefetch may or may not be populated depending on intent
            assert "prefetch" in decision
            assert isinstance(decision["prefetch"], list)

    def test_routing_decision_notes(self, mock_registry: AgentRegistry) -> None:
        """Test notes in routing decision."""
        task = OrchestrationTask(
            query_text="Analyze retention patterns"
        )
        state = {"task": task.model_dump(), "logs": []}

        result = route_intent(state, mock_registry)

        if "routing_decision" in result:
            decision = result["routing_decision"]
            assert "notes" in decision
            assert isinstance(decision["notes"], list)

    def test_tie_forces_parallel_mode(self, mock_registry: AgentRegistry) -> None:
        """Test tie handling yields parallel mode with two agents."""
        task = OrchestrationTask(
            query_text="Investigate anomaly correlation patterns in labour data"
        )
        state = {"task": task.model_dump(), "logs": []}

        result = route_intent(state, mock_registry)

        if "routing_decision" in result:
            decision = result["routing_decision"]
            assert decision["mode"] == "parallel"
            assert len(decision["agents"]) == 2
            assert result["metadata"].get("tie_within_threshold") is True
            assert result["metadata"]["routed_agents"] == decision["agents"]


class TestScenarioRouting:
    """Ensure scenario intents route deterministically."""

    def test_scenario_apply_routes_single(self, mock_registry: AgentRegistry) -> None:
        """Scenario apply queries should map to scenario.apply intent."""
        task = OrchestrationTask(
            query_text="Scenario: improve Construction retention by 8% over the next 12 months"
        )
        state = {"task": task.model_dump(), "logs": []}

        result = route_intent(state, mock_registry)

        assert result["route"] == "scenario.apply"
        assert result["routing_decision"]["mode"] == "single"
        assert result["metadata"].get("tie_within_threshold") is False

    def test_scenario_compare_routes_single(self, mock_registry: AgentRegistry) -> None:
        """Scenario compare queries should not trigger ties."""
        task = OrchestrationTask(
            query_text="Compare optimistic vs pessimistic qatarization scenarios for Energy"
        )
        state = {"task": task.model_dump(), "logs": []}

        result = route_intent(state, mock_registry)

        assert result["route"] == "scenario.compare"
        assert result["routing_decision"]["mode"] == "single"
        assert result["metadata"].get("tie_within_threshold") is False

    def test_scenario_batch_routes_single(self, mock_registry: AgentRegistry) -> None:
        """Scenario batch queries should resolve to scenario.batch intent."""
        task = OrchestrationTask(
            query_text="Batch run retention scenarios for Construction, Finance, and ICT to estimate national impact"
        )
        state = {"task": task.model_dump(), "logs": []}

        result = route_intent(state, mock_registry)

        assert result["route"] == "scenario.batch"
        assert result["routing_decision"]["mode"] == "single"
        assert result["metadata"].get("tie_within_threshold") is False


class TestErrorHandling:
    """Test error handling in router."""

    def test_no_task_provided(self, mock_registry: AgentRegistry) -> None:
        """Test error when no task is provided."""
        state = {"task": None, "logs": []}

        result = route_intent(state, mock_registry)

        assert "error" in result
        assert "No task provided" in result["error"]

    def test_neither_intent_nor_query(self, mock_registry: AgentRegistry) -> None:
        """Test error when neither intent nor query_text provided."""
        # This should be caught by Pydantic validation
        with pytest.raises(ValueError, match="Either intent or query_text must be provided"):
            OrchestrationTask(params={})

    def test_both_intent_and_query(self) -> None:
        """Test that providing both intent and query_text works (intent takes precedence)."""
        # Both can be provided; intent takes precedence
        task = OrchestrationTask(
            intent="pattern.anomalies",
            query_text="Some query"
        )
        assert task.intent == "pattern.anomalies"
        assert task.query_text == "Some query"


class TestLogging:
    """Test logging functionality."""

    def test_logs_updated(self, mock_registry: AgentRegistry) -> None:
        """Test that logs are updated during routing."""
        task = OrchestrationTask(intent="pattern.anomalies", params={})
        state = {"task": task.model_dump(), "logs": []}

        result = route_intent(state, mock_registry)

        assert "logs" in result
        assert len(result["logs"]) > 0

    def test_logs_preserve_existing(self, mock_registry: AgentRegistry) -> None:
        """Test that existing logs are preserved."""
        task = OrchestrationTask(intent="pattern.anomalies", params={})
        existing_logs = ["Initial log"]
        state = {"task": task.model_dump(), "logs": existing_logs}

        result = route_intent(state, mock_registry)

        assert "logs" in result
        assert len(result["logs"]) > len(existing_logs)
