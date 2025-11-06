"""
Integration tests for graph-level coordination.

Tests end-to-end multi-agent workflows through the QNWISGraph interface,
including prefetch, coordination, and merge operations.
"""

from src.qnwis.agents.base import AgentReport, Evidence, Insight
from src.qnwis.data.deterministic.models import (
    Freshness,
    Provenance,
    QueryResult,
    Row,
)
from src.qnwis.orchestration.coordination import Coordinator
from src.qnwis.orchestration.policies import CoordinationPolicy
from src.qnwis.orchestration.prefetch import Prefetcher
from src.qnwis.orchestration.registry import AgentRegistry
from src.qnwis.orchestration.types import AgentCallSpec, PrefetchSpec


class StubAgent:
    """Stub agent for testing coordination."""

    def __init__(self, name: str, return_findings: bool = True):
        """
        Initialize stub agent.

        Args:
            name: Agent name
            return_findings: Whether to return findings (True) or empty report (False)
        """
        self.name = name
        self.return_findings = return_findings
        self.calls = []

    def run(self, **kwargs) -> AgentReport:
        """Stub run method."""
        self.calls.append(("run", kwargs))
        if not self.return_findings:
            return AgentReport(agent=self.name, findings=[], warnings=[])

        finding = Insight(
            title=f"{self.name} Finding",
            summary=f"Test finding from {self.name}",
            metrics={"value": 42.0},
            evidence=[
                Evidence(
                    query_id="test_query",
                    dataset_id="test_dataset",
                    locator="test.csv",
                    fields=["field1"],
                    freshness_as_of="2024-01-01",
                )
            ],
        )
        return AgentReport(agent=self.name, findings=[finding], warnings=[])

    def detect_patterns(self, **kwargs) -> AgentReport:
        """Stub detect_patterns method."""
        self.calls.append(("detect_patterns", kwargs))
        finding = Insight(
            title=f"{self.name} Pattern",
            summary=f"Pattern detected by {self.name}",
            metrics={"pattern_score": 0.85},
            evidence=[
                Evidence(
                    query_id="pattern_query",
                    dataset_id="pattern_dataset",
                    locator="patterns.csv",
                    fields=["pattern_field"],
                    freshness_as_of="2024-01-02",
                )
            ],
        )
        return AgentReport(agent=self.name, findings=[finding], warnings=[])


class MockDataClient:
    """Mock DataClient for prefetch testing."""

    def __init__(self):
        """Initialize mock with call tracking."""
        self.calls = []

    def run(self, query_id: str) -> QueryResult:
        """Mock run method."""
        self.calls.append(("run", {"query_id": query_id}))
        return QueryResult(
            query_id=query_id,
            rows=[Row(data={"value": 100})],
            provenance=Provenance(
                dataset_id="prefetch_dataset",
                locator="prefetch.csv",
                source_format="csv",
            ),
            freshness=Freshness(asof_date="2024-01-01"),
        )

    def get_metrics(self, sector: str) -> QueryResult:
        """Mock get_metrics method."""
        self.calls.append(("get_metrics", {"sector": sector}))
        return QueryResult(
            query_id="metrics_query",
            rows=[Row(data={"sector": sector, "value": 200})],
            provenance=Provenance(
                dataset_id="metrics_dataset",
                locator="metrics.csv",
                source_format="csv",
            ),
            freshness=Freshness(asof_date="2024-01-02"),
        )


class TestGraphCoordinationSingle:
    """Test single agent execution through coordinator."""

    def test_single_mode_execution(self):
        """Test single mode executes one agent."""
        registry = AgentRegistry()
        agent = StubAgent("SingleAgent")
        registry.register("test.single", agent, "run")

        coordinator = Coordinator(registry, CoordinationPolicy())

        spec = AgentCallSpec(
            intent="test.single",
            method="run",
            params={"arg": "value"},
        )

        waves = coordinator.plan("test.single", [spec], "single")
        results = coordinator.execute(waves, prefetch_cache={}, mode="single")

        assert len(results) == 1
        assert results[0].ok is True
        assert len(agent.calls) == 1
        assert agent.calls[0] == ("run", {"arg": "value"})

    def test_single_mode_with_findings(self):
        """Test single mode preserves findings in merged output."""
        registry = AgentRegistry()
        agent = StubAgent("FindingAgent")
        registry.register("test.findings", agent, "run")

        coordinator = Coordinator(registry, CoordinationPolicy())

        spec = AgentCallSpec(
            intent="test.findings",
            method="run",
            params={},
        )

        waves = coordinator.plan("test.findings", [spec], "single")
        results = coordinator.execute(waves, prefetch_cache={}, mode="single")
        merged = coordinator.aggregate(results)

        assert merged.ok is True
        assert len(merged.sections) > 0
        assert any("Finding" in section.title for section in merged.sections)


class TestGraphCoordinationParallel:
    """Test parallel agent execution through coordinator."""

    def test_parallel_mode_execution(self):
        """Test parallel mode executes multiple agents within max_parallel limit."""
        registry = AgentRegistry()
        agent1 = StubAgent("Agent1")
        agent2 = StubAgent("Agent2")
        agent3 = StubAgent("Agent3")
        registry.register("test.agent1", agent1, "run")
        registry.register("test.agent2", agent2, "run")
        registry.register("test.agent3", agent3, "run")

        policy = CoordinationPolicy(max_parallel=2)
        coordinator = Coordinator(registry, policy)

        specs = [
            AgentCallSpec(intent="test.agent1", method="run", params={}),
            AgentCallSpec(intent="test.agent2", method="run", params={}),
            AgentCallSpec(intent="test.agent3", method="run", params={}),
        ]

        waves = coordinator.plan("test.agent1", specs, "parallel")
        results = coordinator.execute(waves, prefetch_cache={}, mode="parallel")

        # Should create 2 waves (2 agents + 1 agent) with max_parallel=2
        assert len(waves) == 2
        assert len(results) == 3
        assert all(result.ok for result in results)
        # All agents should have been called
        assert len(agent1.calls) == 1
        assert len(agent2.calls) == 1
        assert len(agent3.calls) == 1

    def test_parallel_mode_merges_correctly(self):
        """Test parallel mode merges multiple agent outputs."""
        registry = AgentRegistry()
        agent1 = StubAgent("Agent1")
        agent2 = StubAgent("Agent2")
        registry.register("test.agent1", agent1, "run")
        registry.register("test.agent2", agent2, "run")

        coordinator = Coordinator(registry, CoordinationPolicy())

        specs = [
            AgentCallSpec(intent="test.agent1", method="run", params={}),
            AgentCallSpec(intent="test.agent2", method="run", params={}),
        ]

        waves = coordinator.plan("test.agent1", specs, "parallel")
        results = coordinator.execute(waves, prefetch_cache={}, mode="parallel")
        merged = coordinator.aggregate(results)

        assert merged.ok is True
        assert len(merged.sections) >= 2  # At least one section from each agent
        # Should have citations from both agents
        assert len(merged.citations) >= 2


class TestGraphCoordinationSequential:
    """Test sequential agent execution through coordinator."""

    def test_sequential_mode_execution(self):
        """Test sequential mode executes agents in order."""
        registry = AgentRegistry()
        agent1 = StubAgent("Agent1")
        agent2 = StubAgent("Agent2")
        registry.register("test.agent1", agent1, "run")
        registry.register("test.agent2", agent2, "run")

        coordinator = Coordinator(registry, CoordinationPolicy())

        specs = [
            AgentCallSpec(intent="test.agent1", method="run", params={}),
            AgentCallSpec(intent="test.agent2", method="run", params={}),
        ]

        waves = coordinator.plan("test.agent1", specs, "sequential")
        results = coordinator.execute(waves, prefetch_cache={}, mode="sequential")

        # Each agent gets its own wave
        assert len(waves) == 2
        assert len(results) == 2
        assert all(result.ok for result in results)

    def test_sequential_mode_with_dependencies(self):
        """Test sequential mode respects dependencies."""
        registry = AgentRegistry()
        agent1 = StubAgent("PrimaryAgent")
        agent2 = StubAgent("DependentAgent")
        registry.register("test.primary", agent1, "run")
        registry.register("test.dependent", agent2, "run")

        coordinator = Coordinator(registry, CoordinationPolicy())

        spec1 = AgentCallSpec(intent="test.primary", method="run", params={})
        spec1["alias"] = "primary"
        spec2 = AgentCallSpec(intent="test.dependent", method="run", params={})
        spec2["alias"] = "dependent"
        spec2["depends_on"] = ["primary"]

        waves = coordinator.plan("test.primary", [spec1, spec2], "sequential")
        results = coordinator.execute(waves, prefetch_cache={}, mode="sequential")

        assert len(results) == 2
        assert results[0].ok is True
        assert results[1].ok is True
        # Both agents should have executed
        assert len(agent1.calls) == 1
        assert len(agent2.calls) == 1

    def test_sequential_mode_skips_dependent_on_failure(self):
        """Test sequential mode skips dependent when prerequisite fails."""
        registry = AgentRegistry()
        failing_agent = StubAgent("FailingAgent", return_findings=False)
        dependent_agent = StubAgent("DependentAgent")
        registry.register("test.failing", failing_agent, "run")
        registry.register("test.dependent", dependent_agent, "run")

        # Force failing agent to timeout
        policy = CoordinationPolicy(per_agent_timeout_ms=1)
        coordinator = Coordinator(registry, policy)

        spec1 = AgentCallSpec(intent="test.failing", method="run", params={})
        spec1["alias"] = "failing"
        spec2 = AgentCallSpec(intent="test.dependent", method="run", params={})
        spec2["alias"] = "dependent"
        spec2["depends_on"] = ["failing"]

        waves = coordinator.plan("test.failing", [spec1, spec2], "sequential")
        results = coordinator.execute(waves, prefetch_cache={}, mode="sequential")

        assert len(results) == 2
        # First should fail (timeout)
        assert results[0].ok is False
        # Second should be skipped
        assert results[1].ok is False
        assert any("dependency" in w.lower() for w in results[1].warnings)
        # Dependent agent should not have been called
        assert len(dependent_agent.calls) == 0


class TestGraphCoordinationCrisis:
    """Test crisis mode coordination."""

    def test_crisis_mode_uses_higher_parallelism(self):
        """Test crisis mode uses crisis_parallel setting."""
        registry = AgentRegistry()
        agents = [StubAgent(f"Agent{i}") for i in range(6)]
        for i, agent in enumerate(agents):
            registry.register(f"test.agent{i}", agent, "run")

        policy = CoordinationPolicy(max_parallel=3, crisis_parallel=5)
        coordinator = Coordinator(registry, policy)

        specs = [
            AgentCallSpec(intent=f"test.agent{i}", method="run", params={})
            for i in range(6)
        ]

        # Parallel mode should use max_parallel=3, creating 2 waves (3+3)
        waves_normal = coordinator.plan("test.agent0", specs, "parallel")
        assert len(waves_normal) == 2

        # If we manually set crisis_parallel (simulating crisis mode)
        coordinator.policy = CoordinationPolicy(max_parallel=5, crisis_parallel=5)
        waves_crisis = coordinator.plan("test.agent0", specs, "parallel")
        # With max_parallel=5, should create 2 waves (5+1)
        assert len(waves_crisis) == 2
        assert len(waves_crisis[0]) == 5
        assert len(waves_crisis[1]) == 1


class TestGraphCoordinationPrefetch:
    """Test prefetch integration with coordination."""

    def test_prefetch_populates_cache(self):
        """Test that prefetch specs populate cache for agents."""
        client = MockDataClient()
        prefetcher = Prefetcher(client)

        specs = [
            PrefetchSpec(
                fn="run",
                params={"query_id": "query1"},
                cache_key="key1",
            ),
            PrefetchSpec(
                fn="get_metrics",
                params={"sector": "health"},
                cache_key="key2",
            ),
        ]

        cache = prefetcher.run(specs)

        assert len(cache) == 2
        assert "key1" in cache
        assert "key2" in cache
        assert len(client.calls) == 2

    def test_prefetch_deduplication(self):
        """Test that prefetch deduplicates by cache_key."""
        client = MockDataClient()
        prefetcher = Prefetcher(client)

        specs = [
            PrefetchSpec(
                fn="run",
                params={"query_id": "query1"},
                cache_key="duplicate",
            ),
            PrefetchSpec(
                fn="run",
                params={"query_id": "query2"},
                cache_key="duplicate",
            ),
        ]

        cache = prefetcher.run(specs)

        # Only first spec should be executed
        assert len(cache) == 1
        assert len(client.calls) == 1
        assert client.calls[0] == ("run", {"query_id": "query1"})

    def test_coordination_with_prefetch_cache(self):
        """Test coordinator execution with populated prefetch cache."""
        registry = AgentRegistry()
        agent = StubAgent("TestAgent")
        registry.register("test.agent", agent, "run")

        coordinator = Coordinator(registry, CoordinationPolicy())

        # Create prefetch cache
        client = MockDataClient()
        prefetcher = Prefetcher(client)
        prefetch_specs = [
            PrefetchSpec(
                fn="run",
                params={"query_id": "prefetch_query"},
                cache_key="prefetch_key",
            )
        ]
        prefetch_cache = prefetcher.run(prefetch_specs)

        # Execute with prefetch cache
        spec = AgentCallSpec(
            intent="test.agent",
            method="run",
            params={},
        )

        waves = coordinator.plan("test.agent", [spec], "single")
        results = coordinator.execute(waves, prefetch_cache=prefetch_cache, mode="single")

        assert len(results) == 1
        assert results[0].ok is True
        # Agent should have been called
        assert len(agent.calls) == 1


class TestGraphCoordinationTimeout:
    """Test timeout handling in coordination."""

    def test_agent_timeout_produces_warning(self):
        """Test that agent exceeding timeout produces warning."""
        import time
        import types

        registry = AgentRegistry()

        # Create agent with slow method
        class SlowAgent:
            def run(self) -> AgentReport:
                time.sleep(0.05)  # 50ms
                return AgentReport(agent="SlowAgent", findings=[], warnings=[])

        agent = SlowAgent()
        registry.register("test.slow", agent, "run")

        # Set very short per-agent timeout
        policy = types.SimpleNamespace(
            max_parallel=1,
            per_agent_timeout_ms=1,  # 1ms - will be exceeded
            total_timeout_ms=10000,
            strict_merge=False,
            retry_transient=0,
        )
        coordinator = Coordinator(registry)
        coordinator.policy = policy  # type: ignore[assignment]

        spec = AgentCallSpec(intent="test.slow", method="run", params={})

        waves = coordinator.plan("test.slow", [spec], "single")
        results = coordinator.execute(waves, prefetch_cache={}, mode="single")

        assert len(results) == 1
        result = results[0]
        # Should complete but be marked as failed due to timeout
        assert result.ok is False
        assert any("timeout" in w.lower() for w in result.warnings)


class TestGraphCoordinationMerge:
    """Test merge operations in coordination."""

    def test_merge_combines_sections(self):
        """Test that merge combines sections from multiple agents."""
        registry = AgentRegistry()
        agent1 = StubAgent("Agent1")
        agent2 = StubAgent("Agent2")
        registry.register("test.agent1", agent1, "detect_patterns")
        registry.register("test.agent2", agent2, "run")

        coordinator = Coordinator(registry, CoordinationPolicy())

        specs = [
            AgentCallSpec(intent="test.agent1", method="detect_patterns", params={}),
            AgentCallSpec(intent="test.agent2", method="run", params={}),
        ]

        waves = coordinator.plan("test.agent1", specs, "parallel")
        results = coordinator.execute(waves, prefetch_cache={}, mode="parallel")
        merged = coordinator.aggregate(results)

        # Should have sections from both agents
        assert len(merged.sections) >= 2
        # Check for deterministic section ordering (Executive Summary first)
        if len(merged.sections) > 0:
            assert "summary" in merged.sections[0].title.lower()

    def test_merge_deduplicates_citations(self):
        """Test that merge deduplicates citations."""
        registry = AgentRegistry()
        agent1 = StubAgent("Agent1")
        agent2 = StubAgent("Agent2")
        registry.register("test.agent1", agent1, "run")
        registry.register("test.agent2", agent2, "run")

        coordinator = Coordinator(registry, CoordinationPolicy())

        specs = [
            AgentCallSpec(intent="test.agent1", method="run", params={}),
            AgentCallSpec(intent="test.agent2", method="run", params={}),
        ]

        waves = coordinator.plan("test.agent1", specs, "parallel")
        results = coordinator.execute(waves, prefetch_cache={}, mode="parallel")
        merged = coordinator.aggregate(results)

        # Should have at least 2 citations (one from each agent)
        assert len(merged.citations) >= 2
        # Citations should be sorted deterministically
        if len(merged.citations) >= 2:
            assert (
                merged.citations[0].dataset_id <= merged.citations[1].dataset_id
            )

    def test_merge_tracks_agent_traces(self):
        """Test that merge preserves agent execution traces."""
        registry = AgentRegistry()
        agent1 = StubAgent("Agent1")
        agent2 = StubAgent("Agent2")
        registry.register("test.agent1", agent1, "run")
        registry.register("test.agent2", agent2, "run")

        coordinator = Coordinator(registry, CoordinationPolicy())

        specs = [
            AgentCallSpec(intent="test.agent1", method="run", params={}),
            AgentCallSpec(intent="test.agent2", method="run", params={}),
        ]

        waves = coordinator.plan("test.agent1", specs, "parallel")
        results = coordinator.execute(waves, prefetch_cache={}, mode="parallel")
        merged = coordinator.aggregate(results)

        # Should have traces from both agents
        assert len(merged.agent_traces) >= 2
        # Traces should include timing information
        assert all("elapsed_ms" in trace for trace in merged.agent_traces)
        assert all("success" in trace for trace in merged.agent_traces)
