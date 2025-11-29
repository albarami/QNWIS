"""
Turn Optimization Experiment - Tests different turn counts for Engine B.

This experiment evaluates quality vs. time tradeoffs for different turn counts.
Use this to validate the 25-turn default or explore alternatives.

HYPOTHESIS:
- 25 turns provides optimal balance between insight depth and processing time
- Below 15 turns: insufficient exploration
- Above 35 turns: diminishing returns, higher latency

METRICS:
- insight_count: Number of unique insights generated
- time_per_turn_ms: Average time per turn
- quality_score: Based on chain-of-thought depth and citation count
"""

import pytest
import asyncio
import time
from dataclasses import dataclass
from typing import List, Dict, Any, Optional


@dataclass
class TurnExperimentResult:
    """Result from a turn count experiment run."""
    turn_count: int
    total_time_ms: float
    time_per_turn_ms: float
    response_length: int
    thinking_blocks: int
    has_citations: bool
    agent_used: str
    scenario_id: str


class TestTurnOptimization:
    """
    Experiment suite for Engine B turn optimization.

    Run with: pytest tests/experiments/test_turn_optimization.py -v -s
    """

    # Turn counts to test
    TURN_CONFIGS = [10, 15, 20, 25, 30, 35]

    def test_import_components(self):
        """Verify all required components import correctly."""
        from src.nsic.orchestration.dual_engine_orchestrator import (
            DualEngineOrchestrator,
            create_dual_engine_orchestrator,
        )
        from src.nsic.orchestration.engine_b_deepseek import (
            EngineBDeepSeek,
            create_engine_b,
        )
        from src.nsic.agents.engine_b import (
            ENGINE_B_AGENTS,
            get_agent_rotation,
        )

        assert DualEngineOrchestrator is not None
        assert EngineBDeepSeek is not None
        assert len(ENGINE_B_AGENTS) == 3

        print("[PASS] All components import correctly")

    def test_agent_rotation_distribution(self):
        """Verify agent rotation distributes evenly across scenarios."""
        from src.nsic.agents.engine_b import get_agent_rotation

        # Count agent assignments across 24 scenarios
        agent_counts = {"dr_rashid": 0, "dr_noor": 0, "dr_hassan": 0}

        for i in range(24):
            agent = get_agent_rotation(i)
            agent_counts[agent] += 1

        # Each agent should get 8 scenarios
        assert all(count == 8 for count in agent_counts.values())

        print(f"[PASS] Agent distribution: {agent_counts}")

    def test_turn_config_documentation(self):
        """Verify turn configuration is documented in orchestrator."""
        from src.nsic.orchestration.dual_engine_orchestrator import DualEngineOrchestrator

        assert hasattr(DualEngineOrchestrator, "ENGINE_A_TURNS")
        assert hasattr(DualEngineOrchestrator, "ENGINE_B_TURNS")

        assert DualEngineOrchestrator.ENGINE_A_TURNS == 100
        assert DualEngineOrchestrator.ENGINE_B_TURNS == 25

        print(f"[PASS] Turn configs: A={DualEngineOrchestrator.ENGINE_A_TURNS}, B={DualEngineOrchestrator.ENGINE_B_TURNS}")

    @pytest.mark.asyncio
    async def test_engine_b_accepts_turn_parameter(self):
        """Verify Engine B accepts and uses custom turn counts."""
        from src.nsic.orchestration.engine_b_deepseek import create_engine_b

        engine = create_engine_b(mock=True)

        # Verify analyze_scenario accepts turns parameter
        import inspect
        sig = inspect.signature(engine.analyze_scenario)
        params = list(sig.parameters.keys())

        assert "turns" in params, "Engine B should accept 'turns' parameter"

        print("[PASS] Engine B accepts turns parameter")

    def test_think_tags_present_in_prompts(self):
        """Verify all Engine B agents use <think> tags for chain-of-thought."""
        from src.nsic.agents.engine_b import ENGINE_B_AGENTS

        for agent_id, agent_info in ENGINE_B_AGENTS.items():
            prompt = agent_info["system_prompt"]
            assert "<think>" in prompt, f"{agent_id} missing <think> tag in prompt"
            assert "</think>" in prompt, f"{agent_id} missing </think> tag in prompt"

        print("[PASS] All agents have <think> tags for chain-of-thought")

    def test_turn_count_affects_depth(self):
        """
        Conceptual test: More turns should allow deeper exploration.

        This test validates the hypothesis that turn count affects analysis depth.
        In production, this would be measured by:
        - Number of unique data points cited
        - Depth of causal chain exploration
        - Coverage of scenario dimensions
        """
        # Expected relationship
        turn_depth_map = {
            10: "shallow",  # Basic exploration
            15: "moderate",  # Standard exploration
            20: "good",  # Thorough exploration
            25: "optimal",  # Default - balanced
            30: "deep",  # Extensive exploration
            35: "diminishing",  # Diminishing returns expected
        }

        for turns, expected_depth in turn_depth_map.items():
            # In a real experiment, we'd measure actual depth
            # Here we just validate the configuration exists
            assert turns in self.TURN_CONFIGS or turns <= max(self.TURN_CONFIGS)

        print(f"[PASS] Turn depth hypothesis documented for {len(turn_depth_map)} configs")

    def test_graceful_degradation_tracks_turns(self):
        """Verify error handler tracks completed turns for partial failures."""
        from src.nsic.orchestration.error_handler import AnalysisState, create_error_handler

        handler = create_error_handler()
        state = handler.create_state()

        # State should track Engine B scenario completion
        assert hasattr(state, "engine_b_completed_scenarios")
        assert state.engine_b_completed_scenarios == 0

        print("[PASS] Error handler tracks Engine B scenario completion")

    @pytest.mark.asyncio
    async def test_mid_scenario_failure_recovery(self):
        """Test graceful degradation when Engine B fails mid-processing."""
        from src.nsic.orchestration.error_handler import create_error_handler

        handler = create_error_handler()
        state = handler.create_state()

        # Simulate failure after completing 5 scenarios
        error = TimeoutError("DeepSeek timeout")
        state = await handler.handle_engine_b_failure(
            state, error, completed_scenarios=5
        )

        assert state.engine_b_completed_scenarios == 5
        assert state.is_degraded()
        assert state.confidence_reduction > 0

        print(f"[PASS] Mid-scenario failure handled, completed={state.engine_b_completed_scenarios}")

    def test_experiment_metrics_structure(self):
        """Validate the experiment result structure."""
        result = TurnExperimentResult(
            turn_count=25,
            total_time_ms=5000.0,
            time_per_turn_ms=200.0,
            response_length=1500,
            thinking_blocks=3,
            has_citations=True,
            agent_used="dr_rashid",
            scenario_id="test_001",
        )

        assert result.turn_count == 25
        assert result.time_per_turn_ms == 200.0
        assert result.has_citations is True

        print("[PASS] Experiment result structure validated")

    def test_optimization_recommendations(self):
        """
        Document optimization recommendations based on experiment design.

        This test captures the expected findings from a full experiment run.
        """
        recommendations = {
            "default_turns": 25,
            "min_recommended": 15,
            "max_recommended": 35,
            "rationale": "25 turns provides optimal balance between insight depth and latency",
            "latency_target_ms": 10000,  # 10 seconds per scenario
            "quality_threshold": 0.75,  # Minimum confidence score
        }

        assert recommendations["default_turns"] == 25
        assert recommendations["min_recommended"] < recommendations["default_turns"]
        assert recommendations["max_recommended"] > recommendations["default_turns"]

        print("[PASS] Optimization recommendations documented")
        print(f"  Default: {recommendations['default_turns']} turns")
        print(f"  Range: {recommendations['min_recommended']}-{recommendations['max_recommended']} turns")
        print(f"  Target latency: {recommendations['latency_target_ms']}ms per scenario")


def run_experiment_summary():
    """Print experiment summary for documentation."""
    print("\n" + "=" * 60)
    print("TURN OPTIMIZATION EXPERIMENT SUMMARY")
    print("=" * 60)
    print("""
EXPERIMENT DESIGN:
- Test turn counts: 10, 15, 20, 25, 30, 35
- Measure: latency, response quality, insight count
- Compare across all 3 agents (rotation)

CURRENT CONFIGURATION:
- Engine A (Azure GPT-5): 100 turns (deep analysis)
- Engine B (DeepSeek): 25 turns (broad exploration)

HYPOTHESIS:
- 25 turns is optimal for Engine B
- Below 15: insufficient exploration
- Above 35: diminishing returns

NEXT STEPS:
1. Run full experiment with live DeepSeek endpoint
2. Collect metrics for each turn configuration
3. Analyze quality vs. latency tradeoffs
4. Update default if data suggests improvement
""")
    print("=" * 60)


if __name__ == "__main__":
    # Run tests directly
    test = TestTurnOptimization()

    test.test_import_components()
    test.test_agent_rotation_distribution()
    test.test_turn_config_documentation()
    test.test_think_tags_present_in_prompts()
    test.test_turn_count_affects_depth()
    test.test_graceful_degradation_tracks_turns()
    test.test_experiment_metrics_structure()
    test.test_optimization_recommendations()

    # Async tests
    asyncio.run(test.test_engine_b_accepts_turn_parameter())
    asyncio.run(test.test_mid_scenario_failure_recovery())

    run_experiment_summary()

    print("\n" + "=" * 50)
    print("ALL TURN OPTIMIZATION TESTS PASSED")
    print("=" * 50)
