"""
Unit tests for the orchestration invoke node.
"""

from __future__ import annotations

from src.qnwis.orchestration.metrics import NullMetricsObserver
from src.qnwis.orchestration.nodes.invoke import invoke_agent
from src.qnwis.orchestration.registry import AgentRegistry
from src.qnwis.orchestration.schemas import OrchestrationTask


class SampleAgent:
    """Agent with a strict signature."""

    def run(self, required: int) -> str:
        """Return a formatted value."""
        return f"value:{required}"


class KwargsAgent:
    """Agent that accepts arbitrary keyword arguments."""

    def __init__(self) -> None:
        self.seen: dict[str, object] = {}

    def run(self, **kwargs: object) -> dict[str, object]:
        """Echo the kwargs for verification."""
        self.seen = dict(kwargs)
        return kwargs


class FlakyAgent:
    """Agent that fails once with a transient error."""

    def __init__(self) -> None:
        self.calls = 0

    def run(self) -> str:
        """Raise TimeoutError on first call, succeed afterwards."""
        self.calls += 1
        if self.calls == 1:
            raise TimeoutError("Transient failure")
        return "ok"


def _make_state(task: OrchestrationTask) -> dict:
    """Helper to build a workflow state dict."""
    return {
        "task": task,
        "route": task.intent,
        "logs": [],
        "metadata": {},
    }


def test_invoke_rejects_unknown_params() -> None:
    """Invoke node should reject parameters outside the method signature."""
    registry = AgentRegistry()
    agent = SampleAgent()
    registry.register("pattern.anomalies", agent, "run")

    task = OrchestrationTask(intent="pattern.anomalies", params={"required": 1, "extra": "nope"})
    state = _make_state(task)

    result_state = invoke_agent(
        state,
        registry,
        timeout_ms=1000,
        observer=NullMetricsObserver(),
        max_retries=0,
    )

    assert "error" in result_state
    assert "Unsupported parameters" in result_state["error"]


def test_invoke_allows_var_kwargs() -> None:
    """Methods that accept **kwargs should receive the provided parameters."""
    registry = AgentRegistry()
    agent = KwargsAgent()
    registry.register("pattern.correlation", agent, "run")

    params = {"sector": "Construction", "threshold": 2.5}
    task = OrchestrationTask(intent="pattern.correlation", params=params)
    state = _make_state(task)

    result_state = invoke_agent(
        state,
        registry,
        timeout_ms=1000,
        observer=NullMetricsObserver(),
        max_retries=0,
    )

    assert "error" not in result_state
    assert result_state["agent_output"] == params
    assert agent.seen == params


def test_invoke_retries_transient_error() -> None:
    """Transient errors should be retried once when configured."""
    registry = AgentRegistry()
    agent = FlakyAgent()
    registry.register("pattern.root_causes", agent, "run")

    task = OrchestrationTask(intent="pattern.root_causes", params={})
    state = _make_state(task)

    result_state = invoke_agent(
        state,
        registry,
        timeout_ms=1000,
        observer=NullMetricsObserver(),
        max_retries=1,
        transient_exceptions=("TimeoutError",),
    )

    assert "error" not in result_state
    assert result_state["agent_output"] == "ok"
    assert agent.calls == 2
    assert result_state["metadata"]["attempts"] == 2
