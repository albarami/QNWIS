"""
Unit tests for coordination layer.

Tests the Coordinator, Prefetcher, and merge_results functions.
"""

import types

import pytest

from src.qnwis.agents.base import AgentReport
from src.qnwis.orchestration.coordination import Coordinator, CoordinationError
from src.qnwis.orchestration.policies import CoordinationPolicy
from src.qnwis.orchestration.merge import merge_results
from src.qnwis.orchestration.registry import AgentRegistry
from src.qnwis.orchestration.schemas import (
    Citation,
    Freshness,
    OrchestrationResult,
    ReportSection,
    Reproducibility,
)
from src.qnwis.orchestration.types import AgentCallSpec


class FakePerfCounter:
    """Deterministic perf_counter replacement that increments by a fixed step."""

    def __init__(self, step: float) -> None:
        self.value = 0.0
        self.step = step

    def __call__(self) -> float:
        self.value += self.step
        return self.value


class SequencePerfCounter:
    """Perf_counter replacement returning a predefined sequence of values."""

    def __init__(self, values: list[float], step: float = 0.0001) -> None:
        self._values = iter(values)
        self._last = 0.0
        self._step = step

    def __call__(self) -> float:
        try:
            self._last = next(self._values)
        except StopIteration:
            self._last += self._step
        return self._last


class SlowAgent:
    """Agent returning empty findings while tracking invocation count."""

    def __init__(self, name: str = "SlowAgent") -> None:
        self.name = name
        self.calls = 0

    def run(self) -> AgentReport:
        self.calls += 1
        return AgentReport(agent=self.name, findings=[], warnings=[])


class PatternAgent:
    """Agent with methods used by plan tests."""

    def __init__(self) -> None:
        self.name = "PatternAgent"

    def detect_anomalous_retention(self, **_: object) -> AgentReport:
        return AgentReport(agent=self.name, findings=[], warnings=[])

    def find_correlations(self, **_: object) -> AgentReport:
        return AgentReport(agent=self.name, findings=[], warnings=[])

    def identify_root_causes(self, **_: object) -> AgentReport:
        return AgentReport(agent=self.name, findings=[], warnings=[])


class TestCoordinator:
    """Test Coordinator planning and execution."""

    def test_plan_single_mode(self):
        """Test planning for single agent execution."""
        registry = AgentRegistry()
        policy = CoordinationPolicy()
        coordinator = Coordinator(registry, policy)
        pattern_agent = PatternAgent()
        registry.register("pattern.anomalies", pattern_agent, "detect_anomalous_retention")

        specs = [
            AgentCallSpec(
                intent="pattern.anomalies",
                method="detect_anomalous_retention",
                params={"months": 12},
            )
        ]

        waves = coordinator.plan("pattern.anomalies", specs, "single")
        assert len(waves) == 1
        assert len(waves[0]) == 1
        assert waves[0][0]["intent"] == "pattern.anomalies"

    def test_plan_parallel_mode(self):
        """Test planning for parallel execution with max_parallel limit."""
        registry = AgentRegistry()
        policy = CoordinationPolicy(max_parallel=2)
        coordinator = Coordinator(registry, policy)
        pattern_agent = PatternAgent()
        registry.register("pattern.anomalies", pattern_agent, "detect_anomalous_retention")
        registry.register("pattern.correlation", pattern_agent, "find_correlations")
        registry.register("pattern.root_causes", pattern_agent, "identify_root_causes")

        specs = [
            AgentCallSpec(
                intent="pattern.anomalies",
                method="detect_anomalous_retention",
                params={},
            ),
            AgentCallSpec(
                intent="pattern.correlation",
                method="find_correlations",
                params={},
            ),
            AgentCallSpec(
                intent="pattern.root_causes",
                method="identify_root_causes",
                params={},
            ),
        ]

        waves = coordinator.plan("pattern.anomalies", specs, "parallel")
        assert len(waves) == 2  # 3 specs with max_parallel=2 -> 2 waves
        assert len(waves[0]) == 2
        assert len(waves[1]) == 1

    def test_plan_sequential_mode(self):
        """Test planning for sequential execution."""
        registry = AgentRegistry()
        policy = CoordinationPolicy()
        coordinator = Coordinator(registry, policy)
        pattern_agent = PatternAgent()
        registry.register("pattern.anomalies", pattern_agent, "detect_anomalous_retention")
        registry.register("pattern.correlation", pattern_agent, "find_correlations")

        specs = [
            AgentCallSpec(
                intent="pattern.anomalies",
                method="detect_anomalous_retention",
                params={},
            ),
            AgentCallSpec(
                intent="pattern.correlation",
                method="find_correlations",
                params={},
            ),
        ]

        waves = coordinator.plan("pattern.anomalies", specs, "sequential")
        assert len(waves) == 2  # Each spec gets its own wave
        assert len(waves[0]) == 1
        assert len(waves[1]) == 1

    def test_plan_invalid_mode(self):
        """Test planning with invalid mode raises ValueError."""
        registry = AgentRegistry()
        policy = CoordinationPolicy()
        coordinator = Coordinator(registry, policy)
        pattern_agent = PatternAgent()
        registry.register("pattern.anomalies", pattern_agent, "detect_anomalous_retention")

        specs = [
            AgentCallSpec(
                intent="pattern.anomalies",
                method="detect_anomalous_retention",
                params={},
            )
        ]

        with pytest.raises(ValueError, match="Unknown execution mode"):
            coordinator.plan("pattern.anomalies", specs, "invalid")

    def test_plan_rejects_unregistered_method(self):
        """Specs that reference non-registered methods should raise CoordinationError."""
        registry = AgentRegistry()
        agent = SlowAgent()
        registry.register("test.intent", agent, "run")
        policy = CoordinationPolicy()
        coordinator = Coordinator(registry, policy)

        spec = AgentCallSpec(
            intent="test.intent",
            method="not_allowed",
            params={},
        )

        with pytest.raises(CoordinationError, match="Intent 'test.intent'"):
            coordinator.plan("test.intent", [spec], "single")

    def test_plan_validates_sequential_dependencies(self):
        """Ensure sequential dependencies reference existing aliases."""
        registry = AgentRegistry()
        agent_a = SlowAgent("AgentA")
        agent_b = SlowAgent("AgentB")
        registry.register("intent.a", agent_a, "run")
        registry.register("intent.b", agent_b, "run")
        policy = CoordinationPolicy()
        coordinator = Coordinator(registry, policy)

        spec1 = AgentCallSpec(intent="intent.a", method="run", params={})
        spec1["alias"] = "alpha"
        spec2 = AgentCallSpec(intent="intent.b", method="run", params={})
        spec2["alias"] = "beta"
        spec2["depends_on"] = ["unknown"]

        with pytest.raises(CoordinationError, match="unknown alias"):
            coordinator.plan("intent.a", [spec1, spec2], "sequential")


class TestCoordinatorExecution:
    """Tests focused on coordinator execution behaviour."""

    def test_execute_sequential_dependency_skip(self, monkeypatch):
        """Dependent waves should be skipped when prerequisites fail."""
        registry = AgentRegistry()
        slow_agent = SlowAgent("PrimaryAgent")
        dependent_agent = SlowAgent("DependentAgent")
        registry.register("pattern.anomalies", slow_agent, "run")
        registry.register("pattern.correlation", dependent_agent, "run")

        coordinator = Coordinator(registry, CoordinationPolicy())
        coordinator.policy = types.SimpleNamespace(
            max_parallel=1,
            per_agent_timeout_ms=1,
            total_timeout_ms=500,
        )

        fake_perf = FakePerfCounter(step=0.002)
        monkeypatch.setattr(
            "src.qnwis.orchestration.coordination.time.perf_counter",
            fake_perf,
        )

        spec1 = AgentCallSpec(intent="pattern.anomalies", method="run", params={})
        spec1["alias"] = "slow"
        spec2 = AgentCallSpec(intent="pattern.correlation", method="run", params={})
        spec2["alias"] = "dependent"
        spec2["depends_on"] = ["slow"]

        waves = coordinator.plan("pattern.anomalies", [spec1, spec2], "sequential")
        results = coordinator.execute(waves, prefetch_cache={}, mode="sequential")

        assert len(results) == 2
        slow_result, skipped_result = results

        assert slow_result.ok is False
        assert any("timeout" in warning.lower() for warning in slow_result.warnings)
        assert skipped_result.ok is False
        assert any("dependency" in warning.lower() for warning in skipped_result.warnings)
        assert skipped_result.agent_traces[0]["attempt"] == 0
        assert dependent_agent.calls == 0

    def test_execute_total_timeout_stops_remaining(self, monkeypatch):
        """Total timeout should short-circuit remaining work and emit warnings."""
        registry = AgentRegistry()
        agent_one = SlowAgent("AgentOne")
        agent_two = SlowAgent("AgentTwo")
        registry.register("pattern.anomalies", agent_one, "run")
        registry.register("pattern.correlation", agent_two, "run")

        coordinator = Coordinator(registry, CoordinationPolicy())
        coordinator.policy = types.SimpleNamespace(
            max_parallel=1,
            per_agent_timeout_ms=10,
            total_timeout_ms=6,
        )

        sequence = [
            0.0,
            0.001,
            0.0015,
            0.002,
            0.004,
            0.0045,
            0.0047,
            0.0048,
            0.0049,
            0.005,
            0.009,
            0.009,
            0.0095,
            0.0097,
        ]
        fake_perf = SequencePerfCounter(sequence)
        monkeypatch.setattr(
            "src.qnwis.orchestration.coordination.time.perf_counter",
            fake_perf,
        )

        spec1 = AgentCallSpec(intent="pattern.anomalies", method="run", params={})
        spec1["alias"] = "first"
        spec2 = AgentCallSpec(intent="pattern.correlation", method="run", params={})
        spec2["alias"] = "second"

        waves = coordinator.plan("pattern.anomalies", [spec1, spec2], "sequential")
        results = coordinator.execute(waves, prefetch_cache={}, mode="sequential")

        assert len(results) == 2
        first_result, second_result = results

        assert first_result.ok is True
        assert all("timeout" not in w.lower() for w in first_result.warnings)

        assert second_result.ok is False
        assert any("total execution timeout" in warning.lower() for warning in second_result.warnings)
        assert second_result.agent_traces[0]["success"] is False
        assert "error" in second_result.agent_traces[0]

        # Ensure the second agent was invoked exactly once before the cutoff.
        assert agent_two.calls == 1


class TestMergeResults:
    """Test deterministic result merging."""

    def test_merge_empty_raises_error(self):
        """Test that merging empty results raises ValueError."""
        with pytest.raises(ValueError, match="Cannot merge empty results"):
            merge_results([])

    def test_merge_single_result(self):
        """Test merging a single result returns it with normalized structure."""
        result = OrchestrationResult(
            ok=True,
            intent="pattern.anomalies",
            sections=[
                ReportSection(
                    title="Executive Summary",
                    body_md="Test summary",
                )
            ],
            citations=[
                Citation(
                    query_id="test_query",
                    dataset_id="test_dataset",
                    locator="test.csv",
                    fields=["field1"],
                )
            ],
            freshness={
                "test_dataset": Freshness(
                    source="test_dataset",
                    last_updated="2024-01-01T00:00:00Z",
                )
            },
            reproducibility=Reproducibility(
                method="TestAgent.test_method",
                params={},
                timestamp="2024-01-01T00:00:00Z",
            ),
        )

        merged = merge_results([result])
        assert merged.ok is True
        assert len(merged.sections) == 1
        assert merged.sections[0].title == "Executive Summary"
        assert len(merged.citations) == 1

    def test_merge_multiple_results(self):
        """Test merging multiple results combines sections and citations."""
        result1 = OrchestrationResult(
            ok=True,
            intent="pattern.anomalies",
            sections=[
                ReportSection(
                    title="Executive Summary",
                    body_md="Summary 1",
                )
            ],
            citations=[
                Citation(
                    query_id="query1",
                    dataset_id="dataset1",
                    locator="file1.csv",
                    fields=["field1"],
                )
            ],
            freshness={
                "dataset1": Freshness(
                    source="dataset1",
                    last_updated="2024-01-01T00:00:00Z",
                )
            },
            reproducibility=Reproducibility(
                method="Agent1.method1",
                params={},
                timestamp="2024-01-01T00:00:00Z",
            ),
        )

        result2 = OrchestrationResult(
            ok=True,
            intent="pattern.anomalies",
            sections=[
                ReportSection(
                    title="Key Findings",
                    body_md="Finding 1",
                )
            ],
            citations=[
                Citation(
                    query_id="query2",
                    dataset_id="dataset2",
                    locator="file2.csv",
                    fields=["field2"],
                )
            ],
            freshness={
                "dataset2": Freshness(
                    source="dataset2",
                    last_updated="2024-01-02T00:00:00Z",
                )
            },
            reproducibility=Reproducibility(
                method="Agent2.method2",
                params={},
                timestamp="2024-01-02T00:00:00Z",
            ),
        )

        merged = merge_results([result1, result2])
        assert merged.ok is True
        assert len(merged.sections) == 2
        assert len(merged.citations) == 2
        assert len(merged.freshness) == 2

    def test_merge_deduplicates_sections(self):
        """Test that duplicate sections are removed."""
        # Create sections with identical first 40 chars
        content = "This is exactly forty characters long!!" + " extra"
        result1 = OrchestrationResult(
            ok=True,
            intent="pattern.anomalies",
            sections=[
                ReportSection(
                    title="Executive Summary",
                    body_md=content,
                )
            ],
            citations=[],
            freshness={},
            reproducibility=Reproducibility(
                method="Agent1.method1",
                params={},
                timestamp="2024-01-01T00:00:00Z",
            ),
        )

        result2 = OrchestrationResult(
            ok=True,
            intent="pattern.anomalies",
            sections=[
                ReportSection(
                    title="Executive Summary",
                    body_md=content[:40] + " different ending",
                )
            ],
            citations=[],
            freshness={},
            reproducibility=Reproducibility(
                method="Agent2.method2",
                params={},
                timestamp="2024-01-02T00:00:00Z",
            ),
        )

        merged = merge_results([result1, result2])
        # Sections with same title and first 40 chars should dedupe
        assert len(merged.sections) == 1

    def test_merge_preserves_ok_status(self):
        """Test that merged ok status is all(ok) from inputs."""
        result1 = OrchestrationResult(
            ok=True,
            intent="pattern.anomalies",
            sections=[],
            citations=[],
            freshness={},
            reproducibility=Reproducibility(
                method="Agent1.method1",
                params={},
                timestamp="2024-01-01T00:00:00Z",
            ),
        )

        result2 = OrchestrationResult(
            ok=False,
            intent="pattern.anomalies",
            sections=[],
            citations=[],
            freshness={},
            reproducibility=Reproducibility(
                method="Agent2.method2",
                params={},
                timestamp="2024-01-02T00:00:00Z",
            ),
            warnings=["Something failed"],
        )

        merged = merge_results([result1, result2])
        assert merged.ok is False
        assert "Something failed" in merged.warnings

    def test_merge_freshness_range(self):
        """Freshness metadata should retain min/max timestamps."""
        result1 = OrchestrationResult(
            ok=True,
            intent="pattern.anomalies",
            sections=[],
            citations=[],
            freshness={
                "dataset1": Freshness(
                    source="dataset1",
                    last_updated="2024-01-01T00:00:00Z",
                    age_days=10,
                )
            },
            reproducibility=Reproducibility(
                method="Agent.method1",
                params={},
                timestamp="2024-01-01T00:00:00Z",
            ),
        )
        result2 = OrchestrationResult(
            ok=True,
            intent="pattern.anomalies",
            sections=[],
            citations=[],
            freshness={
                "dataset1": Freshness(
                    source="dataset1",
                    last_updated="2024-01-03T00:00:00Z",
                    age_days=2,
                )
            },
            reproducibility=Reproducibility(
                method="Agent.method2",
                params={},
                timestamp="2024-01-03T00:00:00Z",
            ),
        )

        merged = merge_results([result1, result2])
        merged_fresh = merged.freshness["dataset1"]

        assert merged_fresh.last_updated == "2024-01-03T00:00:00Z"
        assert merged_fresh.min_timestamp == "2024-01-01T00:00:00Z"
        assert merged_fresh.max_timestamp == "2024-01-03T00:00:00Z"
        assert merged_fresh.age_days == 2

    def test_merge_masks_pii_in_sections_and_warnings(self):
        """PII should be masked in merged sections and warnings."""
        result = OrchestrationResult(
            ok=True,
            intent="pattern.anomalies",
            sections=[
                ReportSection(
                    title="Warnings",
                    body_md="Contact John Smith at john.smith@example.com or call 12345678901.",
                )
            ],
            citations=[],
            freshness={},
            reproducibility=Reproducibility(
                method="Agent.method",
                params={},
                timestamp="2024-01-01T00:00:00Z",
            ),
            warnings=["John Smith <john.smith@example.com> ID 12345678901"],
        )

        merged = merge_results([result])
        warnings_body = merged.sections[0].body_md
        assert "John Smith" not in warnings_body
        assert "john.smith@example.com" not in warnings_body
        assert "12345678901" not in warnings_body
        assert "***" in warnings_body

        merged_warning = merged.warnings[0]
        assert "John" not in merged_warning
        assert "@" not in merged_warning
        assert "12345678901" not in merged_warning

    def test_merge_agent_traces_dedup_and_sort(self):
        """Agent traces should be deduplicated with deterministic ordering."""
        trace1 = {
            "intent": "pattern.anomalies",
            "agent": "AgentOne",
            "method": "run",
            "elapsed_ms": 10.0,
            "attempt": 1,
            "success": True,
            "warnings": [],
        }
        trace2 = {
            "intent": "pattern.anomalies",
            "agent": "AgentOne",
            "method": "run",
            "elapsed_ms": 15.0,
            "attempt": 2,
            "success": True,
            "warnings": [],
        }
        duplicate_trace = {**trace1, "elapsed_ms": 12.0}

        result1 = OrchestrationResult(
            ok=True,
            intent="pattern.anomalies",
            sections=[],
            citations=[],
            freshness={},
            reproducibility=Reproducibility(
                method="Agent.method1",
                params={},
                timestamp="2024-01-01T00:00:00Z",
            ),
            agent_traces=[trace1, trace2],
        )
        result2 = OrchestrationResult(
            ok=True,
            intent="pattern.anomalies",
            sections=[],
            citations=[],
            freshness={},
            reproducibility=Reproducibility(
                method="Agent.method2",
                params={},
                timestamp="2024-01-02T00:00:00Z",
            ),
            agent_traces=[duplicate_trace],
        )

        merged = merge_results([result1, result2])
        assert len(merged.agent_traces) == 2
        assert merged.agent_traces[0]["attempt"] == 1
        assert merged.agent_traces[1]["attempt"] == 2
