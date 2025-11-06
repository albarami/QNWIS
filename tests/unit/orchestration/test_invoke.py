"""
Unit tests for invoke node.

Tests cover:
- Successful agent invocation with valid parameters
- Rejection of extraneous parameters
- Handling of missing required parameters
- Retry logic for transient failures
- Timeout tracking
- Metrics emission
"""

from typing import Any
from unittest.mock import Mock

from src.qnwis.agents.base import AgentReport, Evidence, Insight
from src.qnwis.orchestration.metrics import NullMetricsObserver
from src.qnwis.orchestration.nodes.invoke import invoke_agent
from src.qnwis.orchestration.registry import AgentRegistry
from src.qnwis.orchestration.schemas import OrchestrationTask


class FakePatternAgent:
    """Fake pattern detective agent for testing."""

    def __init__(self, client: Any = None, verifier: Any = None) -> None:
        self.client = client
        self.verifier = verifier
        self.call_count = 0

    def find_correlations(
        self,
        sector: str,
        months: int = 12,
    ) -> AgentReport:
        """Mock correlation analysis."""
        self.call_count += 1

        insight = Insight(
            title=f"Correlation analysis for {sector}",
            summary=f"Analyzed {sector} over {months} months",
            metrics={"correlation": 0.85, "sample_size": 100},
            evidence=[
                Evidence(
                    query_id="q_correlation",
                    dataset_id="patterns",
                    locator="data/patterns.csv",
                    fields=["sector", "metric"],
                    freshness_as_of="2024-01-01T00:00:00Z",
                )
            ],
        )

        return AgentReport(
            agent="FakePatternAgent",
            findings=[insight],
            warnings=[],
        )


class FakeStrategyAgent:
    """Fake strategy agent for testing."""

    def __init__(self, client: Any = None, verifier: Any = None) -> None:
        self.client = client
        self.verifier = verifier

    def gcc_benchmark(
        self,
        min_countries: int = 3,
    ) -> AgentReport:
        """Mock GCC benchmark."""
        insight = Insight(
            title="GCC Benchmark Analysis",
            summary=f"Benchmarked against {min_countries} countries",
            metrics={"countries_compared": min_countries},
            evidence=[
                Evidence(
                    query_id="q_gcc",
                    dataset_id="gcc_data",
                    locator="data/gcc.csv",
                    fields=["country", "metric"],
                    freshness_as_of="2024-01-01T00:00:00Z",
                )
            ],
        )

        return AgentReport(
            agent="FakeStrategyAgent",
            findings=[insight],
            warnings=[],
        )


def test_invoke_with_valid_parameters() -> None:
    """Test successful invocation with valid parameters."""
    registry = AgentRegistry()
    agent = FakePatternAgent()
    registry.register("pattern.correlation", agent, "find_correlations")

    task = OrchestrationTask(
        intent="pattern.correlation",
        params={"sector": "Construction", "months": 24},
        request_id="req-123",
    )

    state = {
        "task": task,
        "route": "pattern.correlation",
        "agent_output": None,
        "error": None,
        "logs": [],
        "metadata": {},
    }

    result = invoke_agent(state, registry, timeout_ms=30000)

    # Should have agent output
    assert result["agent_output"] is not None
    assert isinstance(result["agent_output"], AgentReport)
    assert result["agent_output"].agent == "FakePatternAgent"
    assert len(result["agent_output"].findings) == 1
    assert "Construction" in result["agent_output"].findings[0].title

    # Should not have error
    assert result["error"] is None

    # Should have execution metadata
    assert "elapsed_ms" in result["metadata"]
    assert "agent" in result["metadata"]
    assert "method" in result["metadata"]
    assert result["metadata"]["agent"] == "FakePatternAgent"
    assert result["metadata"]["method"] == "find_correlations"

    # Should have log entry
    assert any("Agent executed" in log for log in result["logs"])


def test_invoke_rejects_extraneous_parameters() -> None:
    """Test that extra parameters are rejected for methods without **kwargs."""
    registry = AgentRegistry()
    agent = FakePatternAgent()
    registry.register("pattern.correlation", agent, "find_correlations")

    task = OrchestrationTask(
        intent="pattern.correlation",
        params={
            "sector": "Construction",
            "months": 24,
            "invalid_param": "should_fail",  # Not in method signature
        },
        request_id="req-123",
    )

    state = {
        "task": task,
        "route": "pattern.correlation",
        "agent_output": None,
        "error": None,
        "logs": [],
        "metadata": {},
    }

    result = invoke_agent(state, registry)

    # Should have error
    assert result["error"] is not None
    assert "Unsupported parameters" in result["error"]
    assert "invalid_param" in result["error"]

    # Should not have output
    assert result.get("agent_output") is None


def test_invoke_handles_missing_required_parameters() -> None:
    """Test that missing required parameters are caught."""
    registry = AgentRegistry()
    agent = FakePatternAgent()
    registry.register("pattern.correlation", agent, "find_correlations")

    task = OrchestrationTask(
        intent="pattern.correlation",
        params={"months": 24},  # Missing required 'sector'
        request_id="req-123",
    )

    state = {
        "task": task,
        "route": "pattern.correlation",
        "agent_output": None,
        "error": None,
        "logs": [],
        "metadata": {},
    }

    result = invoke_agent(state, registry)

    # Should have error
    assert result["error"] is not None
    assert "Missing required parameters" in result["error"]
    assert "sector" in result["error"]


def test_invoke_uses_default_parameters() -> None:
    """Test that method defaults are used when params not provided."""
    registry = AgentRegistry()
    agent = FakePatternAgent()
    registry.register("pattern.correlation", agent, "find_correlations")

    task = OrchestrationTask(
        intent="pattern.correlation",
        params={"sector": "Construction"},  # months not provided, should use default
        request_id="req-123",
    )

    state = {
        "task": task,
        "route": "pattern.correlation",
        "agent_output": None,
        "error": None,
        "logs": [],
        "metadata": {},
    }

    result = invoke_agent(state, registry)

    # Should succeed with defaults
    assert result["error"] is None
    assert result["agent_output"] is not None
    assert isinstance(result["agent_output"], AgentReport)
    # Default months=12 should be used
    assert "12 months" in result["agent_output"].findings[0].summary


def test_invoke_handles_missing_route() -> None:
    """Test that invoke handles missing route gracefully."""
    registry = AgentRegistry()

    task = OrchestrationTask(
        intent="pattern.correlation",
        params={},
    )

    state = {
        "task": task,
        "route": None,  # No route set
        "agent_output": None,
        "error": None,
        "logs": [],
        "metadata": {},
    }

    result = invoke_agent(state, registry)

    # Should have error
    assert result["error"] is not None
    assert "No route available for invocation" in result["error"]


def test_invoke_handles_missing_task() -> None:
    """Test that invoke handles missing task gracefully."""
    registry = AgentRegistry()

    state = {
        "task": None,  # No task
        "route": "pattern.correlation",
        "agent_output": None,
        "error": None,
        "logs": [],
        "metadata": {},
    }

    result = invoke_agent(state, registry)

    # Should have error
    assert result["error"] is not None
    assert "No task available for invocation" in result["error"]


def test_invoke_with_metrics_observer() -> None:
    """Test that invoke emits metrics correctly."""
    observer = Mock(spec=NullMetricsObserver)

    registry = AgentRegistry()
    agent = FakeStrategyAgent()
    registry.register("strategy.gcc_benchmark", agent, "gcc_benchmark")

    task = OrchestrationTask(
        intent="strategy.gcc_benchmark",
        params={"min_countries": 4},
    )

    state = {
        "task": task,
        "route": "strategy.gcc_benchmark",
        "agent_output": None,
        "error": None,
        "logs": [],
        "metadata": {},
    }

    result = invoke_agent(state, registry, observer=observer)

    # Should succeed
    assert result["error"] is None

    # Should emit metrics
    observer.increment.assert_called()
    observer.timing.assert_called()

    # Check for success metric
    success_calls = [
        call for call in observer.increment.call_args_list if "agent.invoke.success" in str(call)
    ]
    assert len(success_calls) > 0


def test_invoke_retries_transient_errors() -> None:
    """Test retry logic for transient failures."""

    class FailingAgent:
        """Agent that fails on first call, succeeds on retry."""

        def __init__(self) -> None:
            self.call_count = 0

        def flaky_method(self) -> AgentReport:
            """Method that fails first time."""
            self.call_count += 1
            if self.call_count == 1:
                raise ConnectionError("Temporary network issue")

            insight = Insight(
                title="Success after retry",
                summary="This succeeded on retry",
                metrics={"retries": 1},
                evidence=[
                    Evidence(
                        query_id="q_retry",
                        dataset_id="test_data",
                        locator="data/test.csv",
                        fields=["field1"],
                        freshness_as_of="2024-01-01T00:00:00Z",
                    )
                ],
            )

            return AgentReport(
                agent="FailingAgent",
                findings=[insight],
                warnings=[],
            )

    registry = AgentRegistry()
    agent = FailingAgent()
    registry.register("test.flaky", agent, "flaky_method")

    task = OrchestrationTask(intent="test.flaky", params={})

    state = {
        "task": task,
        "route": "test.flaky",
        "agent_output": None,
        "error": None,
        "logs": [],
        "metadata": {},
    }

    result = invoke_agent(
        state,
        registry,
        max_retries=1,
        transient_exceptions=["ConnectionError"],
    )

    # Should succeed after retry
    assert result["error"] is None
    assert result["agent_output"] is not None
    assert agent.call_count == 2  # First call + 1 retry

    # Should have attempt metadata
    assert result["metadata"]["attempts"] == 2


def test_invoke_fails_after_max_retries() -> None:
    """Test that invoke fails after exhausting retries."""

    class AlwaysFailingAgent:
        """Agent that always fails."""

        def always_fails(self) -> AgentReport:
            """Method that always fails."""
            raise ConnectionError("Persistent network issue")

    registry = AgentRegistry()
    agent = AlwaysFailingAgent()
    registry.register("test.always_fail", agent, "always_fails")

    task = OrchestrationTask(intent="test.always_fail", params={})

    state = {
        "task": task,
        "route": "test.always_fail",
        "agent_output": None,
        "error": None,
        "logs": [],
        "metadata": {},
    }

    result = invoke_agent(
        state,
        registry,
        max_retries=1,
        transient_exceptions=["ConnectionError"],
    )

    # Should have error after retries
    assert result["error"] is not None
    assert "ConnectionError" in result["error"]
    assert "Persistent network issue" in result["error"]

    # Should have attempt logs
    assert any("Attempt" in log for log in result["logs"])


def test_invoke_tracks_timeout_exceeded() -> None:
    """Test that invoke tracks when timeout is exceeded (but doesn't enforce it)."""
    registry = AgentRegistry()
    agent = FakeStrategyAgent()
    registry.register("strategy.gcc_benchmark", agent, "gcc_benchmark")

    task = OrchestrationTask(
        intent="strategy.gcc_benchmark",
        params={"min_countries": 3},
    )

    state = {
        "task": task,
        "route": "strategy.gcc_benchmark",
        "agent_output": None,
        "error": None,
        "logs": [],
        "metadata": {},
    }

    # Set very low timeout to ensure warning
    result = invoke_agent(state, registry, timeout_ms=1)

    # Should still succeed (timeout not enforced)
    assert result["error"] is None
    assert result["agent_output"] is not None

    # Should have metadata about elapsed time
    assert "elapsed_ms" in result["metadata"]


def test_invoke_with_all_optional_parameters() -> None:
    """Test invoking method with all optional parameters."""
    registry = AgentRegistry()
    agent = FakeStrategyAgent()
    registry.register("strategy.gcc_benchmark", agent, "gcc_benchmark")

    task = OrchestrationTask(
        intent="strategy.gcc_benchmark",
        params={},  # All params optional
    )

    state = {
        "task": task,
        "route": "strategy.gcc_benchmark",
        "agent_output": None,
        "error": None,
        "logs": [],
        "metadata": {},
    }

    result = invoke_agent(state, registry)

    # Should succeed with all defaults
    assert result["error"] is None
    assert result["agent_output"] is not None
