"""
Unit tests for orchestration registry.

Tests intent registration, resolution, and security controls.
"""

import pytest

from src.qnwis.orchestration.registry import AgentRegistry, UnknownIntentError


class MockAgent:
    """Mock agent for testing."""

    def analyze(self, param1: str = "default") -> str:
        """Mock analysis method."""
        return f"analyzed:{param1}"

    def process(self) -> str:
        """Mock process method."""
        return "processed"

    not_callable = "not a method"


def test_registry_register_and_resolve():
    """Test basic registration and resolution."""
    registry = AgentRegistry()
    agent = MockAgent()

    registry.register("test.analyze", agent, "analyze")

    resolved_agent, method_name = registry.resolve("test.analyze")
    assert resolved_agent is agent
    assert method_name == "analyze"


def test_registry_get_method():
    """Test getting callable method."""
    registry = AgentRegistry()
    agent = MockAgent()

    registry.register("test.analyze", agent, "analyze")

    method = registry.get_method("test.analyze")
    assert callable(method)
    assert method() == "analyzed:default"
    assert method(param1="custom") == "analyzed:custom"


def test_registry_intents():
    """Test listing intents."""
    registry = AgentRegistry()
    agent = MockAgent()

    registry.register("test.analyze", agent, "analyze")
    registry.register("test.process", agent, "process")

    intents = registry.intents()
    assert sorted(intents) == ["test.analyze", "test.process"]


def test_registry_is_registered():
    """Test checking registration status."""
    registry = AgentRegistry()
    agent = MockAgent()

    assert not registry.is_registered("test.analyze")

    registry.register("test.analyze", agent, "analyze")

    assert registry.is_registered("test.analyze")
    assert not registry.is_registered("test.unknown")


def test_registry_duplicate_registration():
    """Test that duplicate registration raises error."""
    registry = AgentRegistry()
    agent = MockAgent()

    registry.register("test.analyze", agent, "analyze")

    with pytest.raises(ValueError, match="Intent already registered"):
        registry.register("test.analyze", agent, "analyze")


def test_registry_missing_method():
    """Test that registering non-existent method raises error."""
    registry = AgentRegistry()
    agent = MockAgent()

    with pytest.raises(AttributeError, match="does not have method"):
        registry.register("test.missing", agent, "missing_method")


def test_registry_not_callable():
    """Test that registering non-callable attribute raises error."""
    registry = AgentRegistry()
    agent = MockAgent()

    with pytest.raises(TypeError, match="is not callable"):
        registry.register("test.invalid", agent, "not_callable")


def test_registry_unknown_intent():
    """Test that resolving unknown intent raises informative error."""
    registry = AgentRegistry()
    agent = MockAgent()

    registry.register("test.analyze", agent, "analyze")

    with pytest.raises(UnknownIntentError) as exc_info:
        registry.resolve("test.unknown")

    error = exc_info.value
    assert error.intent == "test.unknown"
    assert "test.analyze" in error.available
    assert "Unknown intent: test.unknown" in str(error)


def test_registry_clear():
    """Test clearing registry."""
    registry = AgentRegistry()
    agent = MockAgent()

    registry.register("test.analyze", agent, "analyze")
    assert len(registry.intents()) == 1

    registry.clear()
    assert len(registry.intents()) == 0
    assert not registry.is_registered("test.analyze")
