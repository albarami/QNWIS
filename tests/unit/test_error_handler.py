"""
Unit tests for NSIC Error Handler - Graceful Degradation Module

Tests all failure scenarios and recovery strategies.
"""

import pytest
import asyncio
from datetime import datetime


class TestErrorHandler:
    """Test suite for NSICErrorHandler."""

    def test_import_error_handler(self):
        """Test that error handler imports correctly."""
        from src.nsic.orchestration.error_handler import (
            NSICErrorHandler,
            AnalysisState,
            FailureType,
            DegradationStrategy,
            create_error_handler,
        )
        assert NSICErrorHandler is not None
        assert AnalysisState is not None
        assert FailureType is not None
        print("[PASS] Error handler imports successfully")

    def test_create_analysis_state(self):
        """Test creating fresh analysis state."""
        from src.nsic.orchestration.error_handler import create_error_handler

        handler = create_error_handler()
        state = handler.create_state()

        assert state.base_confidence == 0.80
        assert state.confidence_reduction == 0.0
        assert state.engine_a_available is True
        assert state.engine_b_available is True
        assert state.is_degraded() is False
        print("[PASS] Analysis state created correctly")

    def test_failure_types_defined(self):
        """Test all failure types are defined."""
        from src.nsic.orchestration.error_handler import FailureType

        expected_types = [
            "ENGINE_A_TIMEOUT",
            "ENGINE_A_MID_DEBATE",
            "ENGINE_B_TIMEOUT",
            "ENGINE_B_INSTANCE_CRASH",
            "BOTH_ENGINES_FAIL",
            "EMBEDDINGS_SERVER_DOWN",
            "VERIFICATION_SERVER_DOWN",
            "KG_SERVER_DOWN",
            "EXTERNAL_API_FAILURE",
            "RAG_FAILURE",
            "DATABASE_FAILURE",
        ]

        for ft in expected_types:
            assert hasattr(FailureType, ft), f"Missing failure type: {ft}"

        print(f"[PASS] All {len(expected_types)} failure types defined")

    def test_strategies_defined_for_all_failures(self):
        """Test that every failure type has a strategy."""
        from src.nsic.orchestration.error_handler import (
            NSICErrorHandler,
            FailureType,
        )

        handler = NSICErrorHandler()

        for failure_type in FailureType:
            assert failure_type in handler.STRATEGIES, f"No strategy for {failure_type}"
            strategy = handler.STRATEGIES[failure_type]
            assert strategy.action is not None
            assert 0 <= strategy.confidence_reduction <= 1.0
            assert strategy.message_template is not None
            assert strategy.severity in ["low", "medium", "high", "critical"]

        print(f"[PASS] All {len(FailureType)} failure types have strategies")

    @pytest.mark.asyncio
    async def test_handle_engine_a_timeout(self):
        """Test handling Engine A timeout."""
        from src.nsic.orchestration.error_handler import create_error_handler

        handler = create_error_handler()
        state = handler.create_state()

        error = TimeoutError("Engine A timed out")
        state = await handler.handle_engine_a_failure(state, error)

        assert state.engine_a_available is False
        assert state.confidence_reduction == 0.25
        assert state.is_degraded() is True
        assert len(state.degradation_notes) == 1
        assert len(state.audit_trail) == 1
        assert state.audit_trail[0]["engine"] == "A"
        print("[PASS] Engine A timeout handled correctly")

    @pytest.mark.asyncio
    async def test_handle_engine_a_mid_debate(self):
        """Test handling Engine A failure mid-debate."""
        from src.nsic.orchestration.error_handler import create_error_handler

        handler = create_error_handler()
        state = handler.create_state()

        # Fail at turn 60 (past halfway of 100)
        error = Exception("Connection lost")
        state = await handler.handle_engine_a_failure(state, error, turn=60)

        assert state.engine_a_partial is True
        assert state.engine_a_completed_turns == 60
        assert state.confidence_reduction == 0.15  # Lower than full timeout
        assert "60" in state.degradation_notes[0]
        print("[PASS] Engine A mid-debate failure handled correctly")

    @pytest.mark.asyncio
    async def test_handle_engine_b_failure(self):
        """Test handling Engine B failure."""
        from src.nsic.orchestration.error_handler import create_error_handler

        handler = create_error_handler()
        state = handler.create_state()

        error = ConnectionError("DeepSeek unreachable")
        state = await handler.handle_engine_b_failure(state, error, completed_scenarios=5)

        assert state.engine_b_available is False
        assert state.engine_b_completed_scenarios == 5
        assert state.confidence_reduction == 0.20
        assert state.is_degraded() is True
        print("[PASS] Engine B failure handled correctly")

    @pytest.mark.asyncio
    async def test_handle_both_engines_failure(self):
        """Test handling both engines failing (critical)."""
        from src.nsic.orchestration.error_handler import create_error_handler

        handler = create_error_handler()
        state = handler.create_state()

        error_a = TimeoutError("Engine A down")
        error_b = ConnectionError("Engine B down")
        state = await handler.handle_both_engines_failure(state, error_a, error_b)

        assert state.engine_a_available is False
        assert state.engine_b_available is False
        assert state.confidence_reduction == 0.60
        assert abs(state.get_final_confidence() - 0.20) < 0.001  # 0.80 - 0.60 = 0.20 (minimum)
        assert state.audit_trail[0]["event"] == "critical_failure"
        print("[PASS] Both engines failure handled correctly")

    @pytest.mark.asyncio
    async def test_handle_service_failure(self):
        """Test handling supporting service failures."""
        from src.nsic.orchestration.error_handler import create_error_handler

        handler = create_error_handler()
        state = handler.create_state()

        # Test embeddings failure
        error = ConnectionError("Server down")
        state = await handler.handle_service_failure(state, "embeddings", error)
        assert state.embeddings_available is False
        assert state.confidence_reduction == 0.15

        # Test verification failure
        state2 = handler.create_state()
        state2 = await handler.handle_service_failure(state2, "verification", error)
        assert state2.verification_available is False
        assert state2.confidence_reduction == 0.20

        # Test KG failure
        state3 = handler.create_state()
        state3 = await handler.handle_service_failure(state3, "knowledge_graph", error)
        assert state3.kg_available is False
        assert state3.confidence_reduction == 0.10

        print("[PASS] Service failures handled correctly")

    @pytest.mark.asyncio
    async def test_handle_api_failure(self):
        """Test handling external API failure."""
        from src.nsic.orchestration.error_handler import create_error_handler

        handler = create_error_handler()
        state = handler.create_state()

        # Record some successes first
        state = handler.record_api_success(state, "world_bank")
        state = handler.record_api_success(state, "imf")

        # Now fail one
        error = Exception("API rate limited")
        state = await handler.handle_api_failure(state, "qatar_central_bank", error)

        assert "qatar_central_bank" in state.failed_apis
        assert len(state.successful_apis) == 2
        assert state.confidence_reduction == 0.05
        print("[PASS] API failure handled correctly")

    @pytest.mark.asyncio
    async def test_cumulative_degradation(self):
        """Test that multiple failures accumulate correctly."""
        from src.nsic.orchestration.error_handler import create_error_handler

        handler = create_error_handler()
        state = handler.create_state()

        error = Exception("Test error")

        # Multiple service failures
        state = await handler.handle_service_failure(state, "embeddings", error)  # -0.15
        state = await handler.handle_service_failure(state, "kg", error)  # -0.10
        state = await handler.handle_api_failure(state, "test_api", error)  # -0.05

        expected_reduction = 0.15 + 0.10 + 0.05
        assert abs(state.confidence_reduction - expected_reduction) < 0.001
        assert state.get_final_confidence() == 0.80 - expected_reduction

        print(f"[PASS] Cumulative degradation: {state.confidence_reduction:.2f}")

    def test_degradation_summary_generation(self):
        """Test generating degradation summary for ministerial brief."""
        from src.nsic.orchestration.error_handler import create_error_handler

        handler = create_error_handler()
        state = handler.create_state()

        # Add some degradation notes
        state.degradation_notes.append("Semantic search unavailable. Using keyword matching fallback.")
        state.degradation_notes.append("Knowledge graph unavailable. Causal chain analysis skipped.")
        state.confidence_reduction = 0.25

        summary = handler.generate_degradation_summary(state)

        assert "ANALYSIS LIMITATIONS" in summary
        assert "MEDIUM" in summary  # 0.25 > 0.15
        assert "Semantic search unavailable" in summary
        assert "Knowledge graph unavailable" in summary
        assert "80%" in summary  # base confidence
        assert "55%" in summary  # final confidence (80 - 25)

        print("[PASS] Degradation summary generated correctly")

    def test_empty_degradation_summary(self):
        """Test that no summary is generated when no degradations."""
        from src.nsic.orchestration.error_handler import create_error_handler

        handler = create_error_handler()
        state = handler.create_state()

        summary = handler.generate_degradation_summary(state)
        assert summary == ""

        print("[PASS] Empty summary for non-degraded state")

    def test_state_to_dict(self):
        """Test state serialization to dictionary."""
        from src.nsic.orchestration.error_handler import create_error_handler

        handler = create_error_handler()
        state = handler.create_state()
        state.confidence_reduction = 0.15

        state_dict = state.to_dict()

        assert state_dict["base_confidence"] == 0.80
        assert state_dict["confidence_reduction"] == 0.15
        assert state_dict["final_confidence"] == 0.65
        assert state_dict["is_degraded"] is True

        print("[PASS] State serialization works correctly")

    def test_handler_statistics(self):
        """Test error handler statistics tracking."""
        from src.nsic.orchestration.error_handler import create_error_handler

        handler = create_error_handler()
        stats = handler.get_stats()

        assert stats["total_failures_handled"] == 0
        assert "failures_by_type" in stats
        assert stats["strategies_available"] == 11

        print("[PASS] Handler statistics tracked correctly")


if __name__ == "__main__":
    # Run tests directly
    import sys

    test = TestErrorHandler()

    # Run sync tests
    test.test_import_error_handler()
    test.test_create_analysis_state()
    test.test_failure_types_defined()
    test.test_strategies_defined_for_all_failures()
    test.test_degradation_summary_generation()
    test.test_empty_degradation_summary()
    test.test_state_to_dict()
    test.test_handler_statistics()

    # Run async tests
    asyncio.run(test.test_handle_engine_a_timeout())
    asyncio.run(test.test_handle_engine_a_mid_debate())
    asyncio.run(test.test_handle_engine_b_failure())
    asyncio.run(test.test_handle_both_engines_failure())
    asyncio.run(test.test_handle_service_failure())
    asyncio.run(test.test_handle_api_failure())
    asyncio.run(test.test_cumulative_degradation())

    print("\n" + "=" * 50)
    print("ALL ERROR HANDLER TESTS PASSED")
    print("=" * 50)
