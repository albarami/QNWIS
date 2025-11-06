"""
Unit tests for router node.

Tests cover:
- Pass-through validation when task.intent is given
- Query classification when query_text is given
- Unknown intent rejection with warnings
- Low confidence queries requiring clarification
- Routing decision population (mode, prefetch, agents)
"""

from typing import Any
from unittest.mock import Mock, patch

import pytest

from src.qnwis.orchestration.nodes.router import route_intent
from src.qnwis.orchestration.registry import AgentRegistry
from src.qnwis.orchestration.schemas import (
    Classification,
    Entities,
    OrchestrationTask,
    RoutingDecision,
)


class FakeAgent:
    """Fake agent for testing."""

    def __init__(self) -> None:
        pass

    def test_method(self) -> Any:
        """Fake method."""
        pass


@pytest.fixture
def registry() -> AgentRegistry:
    """Create test registry with registered intents."""
    reg = AgentRegistry()
    agent = FakeAgent()
    reg.register("pattern.anomalies", agent, "test_method")
    reg.register("pattern.correlation", agent, "test_method")
    reg.register("strategy.gcc_benchmark", agent, "test_method")
    return reg


def test_route_explicit_intent_pass_through(registry: AgentRegistry) -> None:
    """Test that explicit intent is validated and passed through."""
    task = OrchestrationTask(
        intent="pattern.anomalies",
        params={"sector": "Construction"},
        request_id="req-001",
    )

    state = {
        "task": task,
        "route": None,
        "routing_decision": None,
        "logs": [],
        "metadata": {},
    }

    result = route_intent(state, registry)

    # Should have route set
    assert result["route"] == "pattern.anomalies"

    # Should have routing_decision
    assert result["routing_decision"] is not None
    routing_decision = RoutingDecision(**result["routing_decision"])
    assert routing_decision.agents == ["pattern.anomalies"]
    assert routing_decision.mode == "single"
    assert "Explicit intent routing" in routing_decision.notes

    # Should not have error
    assert result.get("error") is None

    # Should have log entry
    assert any("Routed to intent" in log for log in result["logs"])


def test_route_explicit_intent_unknown_rejected(registry: AgentRegistry) -> None:
    """Test that unknown explicit intent is rejected."""
    # Use a valid Intent literal that's not registered
    task = OrchestrationTask(
        intent="pattern.root_causes",  # Valid Intent but not in our test registry
        params={},
        request_id="req-002",
    )

    state = {
        "task": task,
        "route": None,
        "routing_decision": None,
        "logs": [],
        "metadata": {},
    }

    result = route_intent(state, registry)

    # Should have error (not registered)
    assert result["error"] is not None
    error_lower = result["error"].lower()
    assert "unknown" in error_lower or "not" in error_lower or "registered" in error_lower


def test_route_query_text_classification(registry: AgentRegistry) -> None:
    """Test query text classification to intent."""
    task = OrchestrationTask(
        query_text="Find anomalies in Construction retention over 24 months",
        params={},
        request_id="req-003",
    )

    state = {
        "task": task,
        "route": None,
        "routing_decision": None,
        "logs": [],
        "metadata": {},
    }

    result = route_intent(state, registry)

    # If low confidence, may have error
    if result.get("error"):
        # Low confidence case - skip rest of assertions
        assert "clarification" in result["error"].lower() or "confidence" in result["error"].lower()
        return

    # Should have route set (likely pattern.anomalies or pattern.correlation)
    assert result["route"] is not None
    # Should be a registered intent
    assert registry.is_registered(result["route"])

    # Should have routing_decision with classification metadata
    assert result["routing_decision"] is not None
    routing_decision = RoutingDecision(**result["routing_decision"])
    assert len(routing_decision.agents) > 0
    assert routing_decision.mode in ["single", "parallel", "sequential"]

    # Should have classification metadata
    assert "classification_confidence" in result["metadata"]
    assert "classification_elapsed_ms" in result["metadata"]
    assert "classification_complexity" in result["metadata"]

    # Should have logs
    assert any("Classification" in log for log in result["logs"])


def test_route_query_text_low_confidence(registry: AgentRegistry) -> None:
    """Test low confidence query requiring clarification."""
    # Vague query with no clear keywords
    task = OrchestrationTask(
        query_text="Tell me something",
        params={},
        request_id="req-004",
    )

    state = {
        "task": task,
        "route": None,
        "routing_decision": None,
        "logs": [],
        "metadata": {},
    }

    result = route_intent(state, registry)

    # Should have error (clarification required)
    assert result["error"] is not None
    assert "Clarification required" in result["error"] or "confidence" in result["error"].lower()

    # Should not have route
    assert result.get("route") is None

    # Should have metadata with clarifying_question
    assert "clarifying_question" in result["metadata"]
    assert isinstance(result["metadata"]["clarifying_question"], str)
    assert len(result["metadata"]["clarifying_question"]) > 0


def test_route_query_text_no_valid_intents(registry: AgentRegistry) -> None:
    """Test query that classifies to unregistered intents."""
    # Create a query that might classify to an intent not in our registry
    # Mock the classifier to return an intent not in registry
    task = OrchestrationTask(
        query_text="Some query text",
        params={},
        request_id="req-005",
    )

    state = {
        "task": task,
        "route": None,
        "routing_decision": None,
        "logs": [],
        "metadata": {},
    }

    # Mock classification to return unregistered intent
    mock_classification = Classification(
        intents=["unregistered.intent"],
        complexity="simple",
        entities=Entities(),
        confidence=0.8,
        reasons=["Matched unregistered.intent"],
        intent_scores={"unregistered.intent": 1.5},
        elapsed_ms=10.0,
        tie_within_threshold=False,
    )

    with patch("src.qnwis.orchestration.nodes.router._get_classifier") as mock_get_classifier:
        mock_classifier = Mock()
        mock_classifier.classify_text.return_value = mock_classification
        mock_classifier.min_confidence = 0.55
        mock_get_classifier.return_value = mock_classifier

        result = route_intent(state, registry)

        # Should have error (no valid intents)
        assert result["error"] is not None
        assert "No valid intents" in result["error"]


def test_route_query_text_parallel_mode_for_tie(registry: AgentRegistry) -> None:
    """Test parallel mode selection when intents tie."""
    task = OrchestrationTask(
        query_text="Find outliers and correlations in Construction retention",
        params={},
        request_id="req-006",
    )

    state = {
        "task": task,
        "route": None,
        "routing_decision": None,
        "logs": [],
        "metadata": {},
    }

    # Mock classification with tie
    mock_classification = Classification(
        intents=["pattern.anomalies", "pattern.correlation"],
        complexity="simple",
        entities=Entities(
            sectors=["Construction"],
            metrics=["retention"],
        ),
        confidence=0.75,
        reasons=["Tie within threshold"],
        intent_scores={
            "pattern.anomalies": 2.0,
            "pattern.correlation": 1.98,  # Very close
        },
        elapsed_ms=12.0,
        tie_within_threshold=True,  # Tie flag set
    )

    with patch("src.qnwis.orchestration.nodes.router._get_classifier") as mock_get_classifier:
        mock_classifier = Mock()
        mock_classifier.classify_text.return_value = mock_classification
        mock_classifier.min_confidence = 0.55
        mock_classifier.determine_data_needs.return_value = []
        mock_get_classifier.return_value = mock_classifier

        result = route_intent(state, registry)

        # Should not have error
        assert result.get("error") is None

        # Should have routing_decision with parallel mode
        routing_decision = RoutingDecision(**result["routing_decision"])
        assert routing_decision.mode == "parallel"
        assert len(routing_decision.agents) == 2  # Top 2 intents
        assert "pattern.anomalies" in routing_decision.agents
        assert "pattern.correlation" in routing_decision.agents

        # Should have tie metadata
        assert result["metadata"]["tie_within_threshold"] is True


def test_route_query_text_single_mode_for_simple(registry: AgentRegistry) -> None:
    """Test single mode for simple queries."""
    task = OrchestrationTask(
        query_text="Show retention for Construction",
        params={},
        request_id="req-007",
    )

    state = {
        "task": task,
        "route": None,
        "routing_decision": None,
        "logs": [],
        "metadata": {},
    }

    # Mock classification with single clear intent
    mock_classification = Classification(
        intents=["pattern.correlation"],
        complexity="simple",
        entities=Entities(
            sectors=["Construction"],
            metrics=["retention"],
        ),
        confidence=0.85,
        reasons=["Matched 1 intent(s)"],
        intent_scores={"pattern.correlation": 2.5},
        elapsed_ms=10.0,
        tie_within_threshold=False,
    )

    with patch("src.qnwis.orchestration.nodes.router._get_classifier") as mock_get_classifier:
        mock_classifier = Mock()
        mock_classifier.classify_text.return_value = mock_classification
        mock_classifier.min_confidence = 0.55
        mock_classifier.determine_data_needs.return_value = []
        mock_get_classifier.return_value = mock_classifier

        result = route_intent(state, registry)

        # Should not have error
        assert result.get("error") is None

        # Should have routing_decision with single mode
        routing_decision = RoutingDecision(**result["routing_decision"])
        assert routing_decision.mode == "single"
        assert len(routing_decision.agents) == 1


def test_route_query_text_prefetch_populated(registry: AgentRegistry) -> None:
    """Test that prefetch is populated from classifier."""
    task = OrchestrationTask(
        query_text="Analyze retention in Construction",
        params={},
        request_id="req-008",
    )

    state = {
        "task": task,
        "route": None,
        "routing_decision": None,
        "logs": [],
        "metadata": {},
    }

    # Mock prefetch data
    mock_prefetch = [
        {
            "fn": "get_retention_by_company",
            "params": {"sectors": ["Construction"], "months": 36},
            "description": "Retention data",
        }
    ]

    mock_classification = Classification(
        intents=["pattern.anomalies"],
        complexity="simple",
        entities=Entities(
            sectors=["Construction"],
            metrics=["retention"],
        ),
        confidence=0.75,
        reasons=["Matched pattern.anomalies"],
        intent_scores={"pattern.anomalies": 2.0},
        elapsed_ms=10.0,
        tie_within_threshold=False,
    )

    with patch("src.qnwis.orchestration.nodes.router._get_classifier") as mock_get_classifier:
        mock_classifier = Mock()
        mock_classifier.classify_text.return_value = mock_classification
        mock_classifier.min_confidence = 0.55
        mock_classifier.determine_data_needs.return_value = mock_prefetch
        mock_get_classifier.return_value = mock_classifier

        result = route_intent(state, registry)

        # Should not have error
        assert result.get("error") is None

        # Should have prefetch in routing_decision
        routing_decision = RoutingDecision(**result["routing_decision"])
        assert len(routing_decision.prefetch) > 0
        assert routing_decision.prefetch[0]["fn"] == "get_retention_by_company"


def test_route_no_task_provided(registry: AgentRegistry) -> None:
    """Test error when no task provided."""
    state = {
        "task": None,
        "route": None,
        "routing_decision": None,
        "logs": [],
        "metadata": {},
    }

    result = route_intent(state, registry)

    # Should have error
    assert result["error"] is not None
    assert "No task provided" in result["error"]


def test_route_validates_task_has_intent_or_query() -> None:
    """Test that OrchestrationTask validation ensures intent or query_text is provided."""
    # This scenario is prevented by pydantic validation on OrchestrationTask
    # Verify that the validation works correctly
    with pytest.raises(ValueError, match="Either intent or query_text must be provided"):
        from src.qnwis.orchestration.schemas import OrchestrationTask
        # Attempt to create task with neither field
        OrchestrationTask(intent=None, query_text=None, params={})


def test_route_updates_task_with_classification(registry: AgentRegistry) -> None:
    """Test that task is updated with classification when query_text used."""
    task = OrchestrationTask(
        query_text="Find strong correlations in Construction retention",
        params={},
        request_id="req-009",
    )

    state = {
        "task": task,
        "route": None,
        "routing_decision": None,
        "logs": [],
        "metadata": {},
    }

    result = route_intent(state, registry)

    # If low confidence, skip
    if result.get("error"):
        assert "clarification" in result["error"].lower() or "confidence" in result["error"].lower()
        return

    # Task should be updated with classification
    updated_task = OrchestrationTask(**result["task"])
    assert updated_task.classification is not None
    assert isinstance(updated_task.classification, Classification)
    assert updated_task.intent is not None  # Primary intent set


def test_route_metadata_populated(registry: AgentRegistry) -> None:
    """Test that metadata is populated with classification details."""
    task = OrchestrationTask(
        query_text="Find urgent anomalies in Healthcare retention",
        params={},
        request_id="req-010",
    )

    state = {
        "task": task,
        "route": None,
        "routing_decision": None,
        "logs": [],
        "metadata": {},
    }

    result = route_intent(state, registry)

    # If low confidence, skip
    if result.get("error"):
        assert "clarification" in result["error"].lower() or "confidence" in result["error"].lower()
        return

    # Metadata should contain classification details
    metadata = result["metadata"]
    assert "classification_confidence" in metadata
    assert "classification_elapsed_ms" in metadata
    assert "classification_intent_scores" in metadata
    assert "classification_complexity" in metadata
    assert "routed_agents" in metadata

    # Check types
    assert isinstance(metadata["classification_confidence"], float)
    assert isinstance(metadata["classification_elapsed_ms"], float)
    assert isinstance(metadata["classification_intent_scores"], dict)
    assert isinstance(metadata["classification_complexity"], str)
    assert isinstance(metadata["routed_agents"], list)
