"""
Unit tests for AgentRegistry.

Tests cover:
- Successful registration and resolution
- Duplicate registration rejection
- Unknown intent errors with helpful messages
- Method validation (existence and callability)
"""

import pytest

from src.qnwis.orchestration.registry import (
    AgentRegistry,
    UnknownIntentError,
)


class FakeAgent:
    """Mock agent for testing."""

    def __init__(self, name: str = "FakeAgent") -> None:
        self.name = name
        self.calls: list[tuple[str, dict]] = []

    def do_analysis(self, **kwargs: object) -> dict[str, object]:
        """Mock analysis method."""
        self.calls.append(("do_analysis", kwargs))
        return {"result": "success", "agent": self.name}

    def another_method(self) -> str:
        """Another mock method."""
        self.calls.append(("another_method", {}))
        return "called"

    not_callable_attr = "I am not callable"  # noqa: RUF012


def test_register_and_resolve_ok() -> None:
    """Test successful registration and resolution."""
    registry = AgentRegistry()
    agent = FakeAgent("TestAgent")

    # Register intent
    registry.register("test.intent", agent, "do_analysis")

    # Verify registration succeeded
    assert registry.is_registered("test.intent")
    assert "test.intent" in registry.intents()

    # Resolve intent
    resolved_agent, method_name = registry.resolve("test.intent")
    assert resolved_agent is agent
    assert method_name == "do_analysis"

    # Get callable method
    method = registry.get_method("test.intent")
    assert callable(method)
    assert method is agent.do_analysis


def test_duplicate_registration_rejected() -> None:
    """Test that duplicate registrations raise ValueError."""
    registry = AgentRegistry()
    agent = FakeAgent()

    # First registration succeeds
    registry.register("duplicate.intent", agent, "do_analysis")

    # Second registration should fail
    with pytest.raises(ValueError) as exc_info:
        registry.register("duplicate.intent", agent, "another_method")

    assert "Intent already registered: duplicate.intent" in str(exc_info.value)


def test_unknown_intent_raises() -> None:
    """Test that unknown intents raise UnknownIntentError with helpful message."""
    registry = AgentRegistry()
    agent = FakeAgent()

    # Register a few intents
    registry.register("known.intent1", agent, "do_analysis")
    registry.register("known.intent2", agent, "another_method")

    # Try to resolve unknown intent
    with pytest.raises(UnknownIntentError) as exc_info:
        registry.resolve("unknown.intent")

    error = exc_info.value
    assert error.intent == "unknown.intent"
    assert "known.intent1" in error.available
    assert "known.intent2" in error.available
    assert "Unknown intent: unknown.intent" in str(error)
    assert "known.intent1" in str(error)


def test_register_nonexistent_method_raises() -> None:
    """Test that registering a nonexistent method raises AttributeError."""
    registry = AgentRegistry()
    agent = FakeAgent()

    with pytest.raises(AttributeError) as exc_info:
        registry.register("bad.intent", agent, "nonexistent_method")

    assert "does not have method: nonexistent_method" in str(exc_info.value)


def test_register_noncallable_attribute_raises() -> None:
    """Test that registering a non-callable attribute raises TypeError."""
    registry = AgentRegistry()
    agent = FakeAgent()

    with pytest.raises(TypeError) as exc_info:
        registry.register("bad.intent", agent, "not_callable_attr")

    assert "is not callable" in str(exc_info.value)


def test_intents_returns_sorted_list() -> None:
    """Test that intents() returns a sorted list of registered intents."""
    registry = AgentRegistry()
    agent = FakeAgent()

    registry.register("zebra.intent", agent, "do_analysis")
    registry.register("alpha.intent", agent, "another_method")
    registry.register("beta.intent", agent, "do_analysis")

    intents = registry.intents()
    assert intents == ["alpha.intent", "beta.intent", "zebra.intent"]


def test_clear_removes_all_registrations() -> None:
    """Test that clear() removes all registrations."""
    registry = AgentRegistry()
    agent = FakeAgent()

    registry.register("intent1", agent, "do_analysis")
    registry.register("intent2", agent, "another_method")

    assert len(registry.intents()) == 2

    registry.clear()

    assert len(registry.intents()) == 0
    assert not registry.is_registered("intent1")
    assert not registry.is_registered("intent2")


def test_multiple_agents_different_intents() -> None:
    """Test registering multiple agents with different intents."""
    registry = AgentRegistry()
    agent1 = FakeAgent("Agent1")
    agent2 = FakeAgent("Agent2")

    registry.register("agent1.method1", agent1, "do_analysis")
    registry.register("agent1.method2", agent1, "another_method")
    registry.register("agent2.method1", agent2, "do_analysis")

    # Verify all registered
    assert len(registry.intents()) == 3

    # Verify resolution returns correct agents
    resolved1, _ = registry.resolve("agent1.method1")
    resolved2, _ = registry.resolve("agent2.method1")
    assert resolved1 is agent1
    assert resolved2 is agent2


def test_get_method_unknown_intent_raises() -> None:
    """Test that get_method raises UnknownIntentError for unknown intents."""
    registry = AgentRegistry()
    agent = FakeAgent()

    registry.register("known.intent", agent, "do_analysis")

    with pytest.raises(UnknownIntentError):
        registry.get_method("unknown.intent")
