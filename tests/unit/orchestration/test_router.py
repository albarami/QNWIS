"""
Unit tests for router node.

Tests cover:
- Successful routing for known intents
- Rejection of unknown intents with helpful error messages
- Handling of missing task in state
- Error propagation in state
"""


from src.qnwis.orchestration.nodes.router import route_intent
from src.qnwis.orchestration.registry import AgentRegistry
from src.qnwis.orchestration.schemas import OrchestrationTask


class MockAgent:
    """Mock agent for testing."""

    def test_method(self) -> dict[str, str]:
        """Mock method."""
        return {"status": "ok"}


def test_router_accepts_known_intent() -> None:
    """Test that router successfully routes known intents."""
    registry = AgentRegistry()
    agent = MockAgent()
    registry.register("test.intent", agent, "test_method")

    task = OrchestrationTask(
        intent="test.intent",
        params={"param1": "value1"},
        request_id="req-123",
    )

    state = {
        "task": task,
        "route": None,
        "agent_output": None,
        "error": None,
        "logs": [],
        "metadata": {},
    }

    result = route_intent(state, registry)

    # Should have route set
    assert result["route"] == "test.intent"
    assert result["error"] is None

    # Should have log entry
    assert len(result["logs"]) == 1
    assert "Routed to intent: test.intent" in result["logs"][0]


def test_router_rejects_unknown_intent_with_help() -> None:
    """Test that router rejects unknown intents with helpful message."""
    registry = AgentRegistry()
    agent = MockAgent()
    registry.register("known.intent1", agent, "test_method")
    registry.register("known.intent2", agent, "test_method")

    task = OrchestrationTask(
        intent="pattern.correlation",  # Not registered
        params={},
        request_id="req-456",
    )

    state = {
        "task": task,
        "route": None,
        "agent_output": None,
        "error": None,
        "logs": [],
        "metadata": {},
    }

    result = route_intent(state, registry)

    # Should have error set
    assert result["error"] is not None
    assert "Unknown intent: pattern.correlation" in result["error"]
    assert "known.intent1" in result["error"]
    assert "known.intent2" in result["error"]

    # Route should not be set
    assert result.get("route") is None

    # Should have error log
    assert any("ERROR" in log for log in result["logs"])


def test_router_handles_missing_task() -> None:
    """Test that router handles missing task gracefully."""
    registry = AgentRegistry()

    state = {
        "task": None,
        "route": None,
        "agent_output": None,
        "error": None,
        "logs": [],
        "metadata": {},
    }

    result = route_intent(state, registry)

    # Should have error set
    assert result["error"] is not None
    assert "No task provided to router" in result["error"]

    # Should have error log
    assert len(result["logs"]) == 1
    assert "ERROR" in result["logs"][0]


def test_router_preserves_existing_logs() -> None:
    """Test that router preserves existing logs in state."""
    registry = AgentRegistry()
    agent = MockAgent()
    registry.register("test.intent", agent, "test_method")

    task = OrchestrationTask(intent="test.intent", params={})

    state = {
        "task": task,
        "route": None,
        "agent_output": None,
        "error": None,
        "logs": ["Previous log entry 1", "Previous log entry 2"],
        "metadata": {},
    }

    result = route_intent(state, registry)

    # Should preserve previous logs
    assert len(result["logs"]) == 3
    assert result["logs"][0] == "Previous log entry 1"
    assert result["logs"][1] == "Previous log entry 2"
    assert "Routed to intent" in result["logs"][2]


def test_router_handles_unexpected_exceptions() -> None:
    """Test that router handles unexpected exceptions gracefully."""

    class BrokenRegistry:
        """Mock registry that raises unexpected errors."""

        def is_registered(self, intent: str) -> bool:
            raise RuntimeError("Unexpected registry error")

    registry = BrokenRegistry()

    task = OrchestrationTask(intent="test.intent", params={})

    state = {
        "task": task,
        "route": None,
        "agent_output": None,
        "error": None,
        "logs": [],
        "metadata": {},
    }

    result = route_intent(state, registry)  # type: ignore[arg-type]

    # Should have error set
    assert result["error"] is not None
    assert "Routing failed" in result["error"]
    assert "RuntimeError" in result["error"]

    # Should have error log
    assert any("ERROR" in log for log in result["logs"])


def test_router_preserves_metadata() -> None:
    """Test that router preserves existing metadata."""
    registry = AgentRegistry()
    agent = MockAgent()
    registry.register("test.intent", agent, "test_method")

    task = OrchestrationTask(intent="test.intent", params={})

    state = {
        "task": task,
        "route": None,
        "agent_output": None,
        "error": None,
        "logs": [],
        "metadata": {"existing_key": "existing_value"},
    }

    result = route_intent(state, registry)

    # Should preserve metadata
    assert result["metadata"]["existing_key"] == "existing_value"


def test_router_validates_task_intent_field() -> None:
    """Test that router uses task.intent for validation."""
    registry = AgentRegistry()
    agent = MockAgent()
    registry.register("registered.intent", agent, "test_method")

    task = OrchestrationTask(
        intent="registered.intent",
        params={},
    )

    state = {
        "task": task,
        "route": None,
        "agent_output": None,
        "error": None,
        "logs": [],
        "metadata": {},
    }

    result = route_intent(state, registry)

    # Should successfully route
    assert result["route"] == "registered.intent"
    assert result["error"] is None
