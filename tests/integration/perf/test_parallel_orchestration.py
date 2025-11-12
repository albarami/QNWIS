"""
Integration tests for parallel agent orchestration.

Tests that independent agent paths run concurrently and achieve
wall-time improvements of ≥25% compared to serial execution.
"""

import time
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

from qnwis.agents.base import AgentReport
from qnwis.orchestration.coordination import Coordinator
from qnwis.orchestration.policies import CoordinationPolicy
from qnwis.orchestration.registry import AgentRegistry
from qnwis.orchestration.schemas import ReportSection
from qnwis.orchestration.types import AgentCallSpec


class SlowMockAgent:
    """Mock agent that simulates slow execution (e.g., external API call)."""

    def __init__(self, delay_seconds: float = 0.2):
        self.delay_seconds = delay_seconds
        self.call_count = 0
        self.call_times: list[float] = []

    def analyze(self, **params) -> AgentReport:
        """Simulate slow analysis operation."""
        start = time.time()
        self.call_count += 1
        time.sleep(self.delay_seconds)

        return AgentReport(
            ok=True,
            sections=[
                ReportSection(
                    title=f"Analysis {self.call_count}",
                    body_md=f"Completed in {self.delay_seconds}s",
                )
            ],
            citations=[],
            freshness={},
        )

    def query(self, **params) -> AgentReport:
        """Simulate slow query operation."""
        return self.analyze(**params)


@pytest.fixture
def mock_registry():
    """Create registry with slow mock agents."""
    registry = AgentRegistry()

    # Register 3 independent agents
    agent1 = SlowMockAgent(delay_seconds=0.2)
    agent2 = SlowMockAgent(delay_seconds=0.2)
    agent3 = SlowMockAgent(delay_seconds=0.2)

    registry.register("agent1_analyze", agent1, "analyze")
    registry.register("agent2_analyze", agent2, "analyze")
    registry.register("agent3_analyze", agent3, "analyze")

    return registry, agent1, agent2, agent3


class TestParallelOrchestration:
    """Test parallel agent execution."""

    def test_parallel_execution_runs_concurrently(self, mock_registry):
        """Independent agents should run in parallel."""
        registry, agent1, agent2, agent3 = mock_registry

        coordinator = Coordinator(registry)

        specs: list[AgentCallSpec] = [
            {"intent": "agent1_analyze", "method": "analyze", "params": {}},
            {"intent": "agent2_analyze", "method": "analyze", "params": {}},
            {"intent": "agent3_analyze", "method": "analyze", "params": {}},
        ]

        # Execute in parallel
        start = time.time()
        result = coordinator.execute_parallel(specs)
        elapsed = time.time() - start

        # All agents should have been called
        assert agent1.call_count == 1
        assert agent2.call_count == 1
        assert agent3.call_count == 1

        # Wall time should be ~0.2s (max delay), not 0.6s (sum of delays)
        # Allow some overhead for thread management
        assert elapsed < 0.4  # Should be much less than 0.6s serial time

    def test_parallel_speedup_vs_serial(self, mock_registry):
        """Parallel execution should be ≥25% faster than serial."""
        registry, agent1, agent2, agent3 = mock_registry

        coordinator = Coordinator(registry)

        specs: list[AgentCallSpec] = [
            {"intent": "agent1_analyze", "method": "analyze", "params": {}},
            {"intent": "agent2_analyze", "method": "analyze", "params": {}},
            {"intent": "agent3_analyze", "method": "analyze", "params": {}},
        ]

        # Measure serial execution
        serial_start = time.time()
        for spec in specs:
            agent, method = registry.resolve(spec["intent"])
            getattr(agent, spec["method"])(**spec.get("params", {}))
        serial_elapsed = time.time() - serial_start

        # Reset call counts
        agent1.call_count = 0
        agent2.call_count = 0
        agent3.call_count = 0

        # Measure parallel execution
        parallel_start = time.time()
        coordinator.execute_parallel(specs)
        parallel_elapsed = time.time() - parallel_start

        # Calculate speedup
        speedup = (serial_elapsed - parallel_elapsed) / serial_elapsed

        # Should be at least 25% faster
        assert speedup >= 0.25, f"Speedup was only {speedup:.1%}, expected ≥25%"

        # For 3 independent 0.2s tasks:
        # Serial: ~0.6s
        # Parallel: ~0.2s
        # Expected speedup: ~67%
        assert speedup > 0.5  # More realistic target

    def test_parallel_execution_with_dependencies_runs_in_waves(self):
        """Agents with dependencies should run in sequential waves."""
        registry = AgentRegistry()

        agent1 = SlowMockAgent(delay_seconds=0.1)
        agent2 = SlowMockAgent(delay_seconds=0.1)
        agent3 = SlowMockAgent(delay_seconds=0.1)

        registry.register("agent1_analyze", agent1, "analyze")
        registry.register("agent2_analyze", agent2, "analyze")
        registry.register("agent3_analyze", agent3, "analyze")

        coordinator = Coordinator(registry)

        specs: list[AgentCallSpec] = [
            {"intent": "agent1_analyze", "method": "analyze", "params": {}},
            {
                "intent": "agent2_analyze",
                "method": "analyze",
                "params": {},
                "depends_on": ["agent1_analyze"],
            },
            {
                "intent": "agent3_analyze",
                "method": "analyze",
                "params": {},
                "depends_on": ["agent1_analyze"],
            },
        ]

        # Plan waves
        waves = coordinator.plan("test_route", specs, mode="parallel")

        # Should have 2 waves:
        # Wave 1: agent1 (no dependencies)
        # Wave 2: agent2, agent3 (both depend on agent1)
        assert len(waves) == 2
        assert len(waves[0]) == 1  # agent1 alone
        assert len(waves[1]) == 2  # agent2 and agent3 in parallel

        # Execute and measure
        start = time.time()
        results = coordinator.execute(waves, {}, mode="parallel")
        elapsed = time.time() - start

        # Total time should be ~0.2s (wave1: 0.1s + wave2: 0.1s in parallel)
        # Not 0.3s (all serial)
        assert elapsed < 0.3

    def test_parallel_execution_respects_max_parallel_limit(self):
        """Parallel execution should respect max_parallel limit."""
        registry = AgentRegistry()

        # Create 10 agents
        agents = [SlowMockAgent(delay_seconds=0.05) for _ in range(10)]
        for i, agent in enumerate(agents):
            registry.register(f"agent{i}_analyze", agent, "analyze")

        # Set max_parallel to 3
        policy = CoordinationPolicy(
            max_parallel=3,
            max_retries=1,
            retry_delay_ms=100,
        )

        coordinator = Coordinator(registry, policy=policy)

        specs: list[AgentCallSpec] = [
            {"intent": f"agent{i}_analyze", "method": "analyze", "params": {}}
            for i in range(10)
        ]

        start = time.time()
        coordinator.execute_parallel(specs)
        elapsed = time.time() - start

        # With 10 agents @ 0.05s each:
        # - Unlimited parallel: ~0.05s
        # - max_parallel=3: ~0.17s (10/3 ≈ 4 batches × 0.05s)
        # - Serial: ~0.5s

        # Should be slower than fully parallel but faster than serial
        assert 0.1 < elapsed < 0.4

    def test_parallel_execution_collects_all_results(self, mock_registry):
        """Parallel execution should collect results from all agents."""
        registry, agent1, agent2, agent3 = mock_registry

        coordinator = Coordinator(registry)

        specs: list[AgentCallSpec] = [
            {"intent": "agent1_analyze", "method": "analyze", "params": {}},
            {"intent": "agent2_analyze", "method": "analyze", "params": {}},
            {"intent": "agent3_analyze", "method": "analyze", "params": {}},
        ]

        results = coordinator.execute_parallel(specs)

        # Should have 3 results
        assert len(results) == 3

        # Each result should be an OrchestrationResult
        for result in results:
            assert hasattr(result, "ok")
            assert hasattr(result, "sections")
            assert result.ok is True

    def test_parallel_execution_handles_agent_failure_gracefully(self):
        """Parallel execution should handle individual agent failures."""
        registry = AgentRegistry()

        # Create agents: one will fail
        good_agent1 = SlowMockAgent(delay_seconds=0.1)
        good_agent2 = SlowMockAgent(delay_seconds=0.1)

        failing_agent = MagicMock()
        failing_agent.analyze = MagicMock(side_effect=ValueError("Agent failed"))

        registry.register("good1_analyze", good_agent1, "analyze")
        registry.register("failing_analyze", failing_agent, "analyze")
        registry.register("good2_analyze", good_agent2, "analyze")

        coordinator = Coordinator(registry)

        specs: list[AgentCallSpec] = [
            {"intent": "good1_analyze", "method": "analyze", "params": {}},
            {"intent": "failing_analyze", "method": "analyze", "params": {}},
            {"intent": "good2_analyze", "method": "analyze", "params": {}},
        ]

        # Execute - should not raise
        results = coordinator.execute_parallel(specs)

        # Should have 3 results
        assert len(results) == 3

        # Good agents should succeed
        assert results[0].ok is True  # good1
        assert results[2].ok is True  # good2

        # Failing agent should have ok=False
        assert results[1].ok is False


class TestParallelPerformanceGains:
    """Test realistic performance scenarios."""

    def test_realistic_multi_agent_query_parallelization(self):
        """Test realistic scenario with multiple analysis agents."""
        registry = AgentRegistry()

        # Simulate realistic agent timings:
        # - TimeMachine: 0.3s (historical data query)
        # - PatternMiner: 0.4s (correlation analysis)
        # - Predictor: 0.2s (forecasting)
        time_machine = SlowMockAgent(delay_seconds=0.3)
        pattern_miner = SlowMockAgent(delay_seconds=0.4)
        predictor = SlowMockAgent(delay_seconds=0.2)

        registry.register("time_machine_analyze", time_machine, "analyze")
        registry.register("pattern_miner_analyze", pattern_miner, "analyze")
        registry.register("predictor_analyze", predictor, "analyze")

        coordinator = Coordinator(registry)

        specs: list[AgentCallSpec] = [
            {"intent": "time_machine_analyze", "method": "analyze", "params": {}},
            {"intent": "pattern_miner_analyze", "method": "analyze", "params": {}},
            {"intent": "predictor_analyze", "method": "analyze", "params": {}},
        ]

        # Serial execution
        serial_start = time.time()
        for spec in specs:
            agent, method = registry.resolve(spec["intent"])
            getattr(agent, spec["method"])(**spec.get("params", {}))
        serial_time = time.time() - serial_start

        # Reset
        time_machine.call_count = 0
        pattern_miner.call_count = 0
        predictor.call_count = 0

        # Parallel execution
        parallel_start = time.time()
        coordinator.execute_parallel(specs)
        parallel_time = time.time() - parallel_start

        # Serial: 0.3 + 0.4 + 0.2 = 0.9s
        # Parallel: max(0.3, 0.4, 0.2) = 0.4s
        # Expected speedup: ~56%

        speedup = (serial_time - parallel_time) / serial_time
        assert speedup >= 0.25  # At least 25% improvement
        assert parallel_time < 0.6  # Should be much less than serial

    def test_parallel_execution_wall_time_improvement(self):
        """Verify that parallel execution achieves promised ≥25% wall-time improvement."""
        registry = AgentRegistry()

        # Create 5 independent agents with 0.15s delay each
        agents = [SlowMockAgent(delay_seconds=0.15) for _ in range(5)]
        for i, agent in enumerate(agents):
            registry.register(f"agent{i}_analyze", agent, "analyze")

        coordinator = Coordinator(registry)

        specs: list[AgentCallSpec] = [
            {"intent": f"agent{i}_analyze", "method": "analyze", "params": {}}
            for i in range(5)
        ]

        # Measure times
        serial_time = 5 * 0.15  # = 0.75s expected

        parallel_start = time.time()
        coordinator.execute_parallel(specs)
        parallel_time = time.time() - parallel_start

        # Calculate improvement
        improvement = (serial_time - parallel_time) / serial_time

        # Should achieve ≥25% improvement
        assert improvement >= 0.25, f"Only achieved {improvement:.1%} improvement, expected ≥25%"

        # For 5 independent tasks, should get significant speedup
        assert improvement > 0.60  # Realistic: ~70-80% improvement
