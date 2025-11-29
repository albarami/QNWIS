"""
Test Phase 9: Integration with Timing

Tests for:
- DualEngineOrchestrator
- TimingLogger
- Engine-level timing for all stages

Gate: pytest tests/test_phase9_integration.py -v
"""

import pytest
import sys
import os
import time
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestTimingLogger:
    """Tests for TimingLogger module."""
    
    def test_timing_logger_creation(self):
        """Test TimingLogger can be created."""
        from src.nsic.orchestration.timing_logger import TimingLogger
        
        timing = TimingLogger()
        assert timing is not None
        
        stats = timing.get_stats()
        assert stats["total_entries"] == 0
        assert stats["scenarios_count"] == 0
    
    def test_timing_context_manager(self):
        """Test timing via context manager."""
        from src.nsic.orchestration.timing_logger import TimingLogger, Stage
        
        timing = TimingLogger()
        
        with timing.time_stage(Stage.EMBEDDING_GENERATION, "test_scenario"):
            time.sleep(0.02)  # 20ms
        
        report = timing.get_report("test_scenario")
        assert report is not None
        assert report.total_time_ms >= 15  # At least 15ms
        assert len(report.entries) == 1
        assert report.entries[0].stage == Stage.EMBEDDING_GENERATION
    
    def test_timing_manual_start_end(self):
        """Test manual timing with start/end."""
        from src.nsic.orchestration.timing_logger import TimingLogger, Stage
        
        timing = TimingLogger()
        
        timing.start_stage(Stage.VERIFICATION, "manual_test")
        time.sleep(0.01)
        entry = timing.end_stage(Stage.VERIFICATION, "manual_test")
        
        assert entry is not None
        assert entry.duration_ms >= 5
    
    def test_timing_multiple_stages(self):
        """Test timing multiple stages for same scenario."""
        from src.nsic.orchestration.timing_logger import TimingLogger, Stage
        
        timing = TimingLogger()
        
        with timing.time_stage(Stage.CONTEXT_RETRIEVAL, "multi"):
            time.sleep(0.01)
        
        with timing.time_stage(Stage.ENGINE_B, "multi"):
            time.sleep(0.01)
        
        with timing.time_stage(Stage.VERIFICATION, "multi"):
            time.sleep(0.01)
        
        report = timing.get_report("multi")
        assert report is not None
        assert len(report.entries) == 3
        assert report.total_time_ms >= 20
    
    def test_timing_stage_summary(self):
        """Test stage summary aggregation."""
        from src.nsic.orchestration.timing_logger import TimingLogger, Stage
        
        timing = TimingLogger()
        
        # Time same stage for different scenarios
        with timing.time_stage(Stage.ENGINE_B, "scenario_1"):
            time.sleep(0.01)
        
        with timing.time_stage(Stage.ENGINE_B, "scenario_2"):
            time.sleep(0.01)
        
        summary = timing.get_stage_summary()
        assert Stage.ENGINE_B.value in summary
        assert summary[Stage.ENGINE_B.value]["count"] == 2
        assert summary[Stage.ENGINE_B.value]["avg_ms"] >= 5
    
    def test_global_timing_logger(self):
        """Test global timing logger functions."""
        from src.nsic.orchestration.timing_logger import (
            get_timing_logger, reset_timing_logger
        )
        
        reset_timing_logger()
        logger1 = get_timing_logger()
        logger2 = get_timing_logger()
        
        # Should be same instance
        assert logger1 is logger2
        
        reset_timing_logger()
        logger3 = get_timing_logger()
        
        # Should be new instance after reset
        assert logger1 is not logger3


class TestDualEngineOrchestrator:
    """Tests for DualEngineOrchestrator module."""
    
    def test_orchestrator_creation(self):
        """Test DualEngineOrchestrator can be created."""
        from src.nsic.orchestration.dual_engine_orchestrator import (
            create_dual_engine_orchestrator, DualEngineOrchestrator
        )
        
        orchestrator = create_dual_engine_orchestrator()
        assert orchestrator is not None
        assert isinstance(orchestrator, DualEngineOrchestrator)
    
    def test_orchestrator_has_engine_b(self):
        """Test orchestrator has Engine B."""
        from src.nsic.orchestration.dual_engine_orchestrator import (
            create_dual_engine_orchestrator
        )
        
        orchestrator = create_dual_engine_orchestrator()
        assert orchestrator.engine_b is not None
    
    def test_orchestrator_has_timing(self):
        """Test orchestrator has TimingLogger."""
        from src.nsic.orchestration.dual_engine_orchestrator import (
            create_dual_engine_orchestrator
        )
        
        orchestrator = create_dual_engine_orchestrator()
        assert orchestrator.timing is not None
    
    def test_orchestrator_health_check(self):
        """Test orchestrator health check."""
        from src.nsic.orchestration.dual_engine_orchestrator import (
            create_dual_engine_orchestrator
        )
        
        orchestrator = create_dual_engine_orchestrator()
        health = orchestrator.health_check()
        
        assert health["orchestrator"] == "healthy"
        assert "engine_b" in health
        assert health["timing_logger"] == "active"
    
    def test_orchestrator_stats(self):
        """Test orchestrator stats structure."""
        from src.nsic.orchestration.dual_engine_orchestrator import (
            create_dual_engine_orchestrator
        )
        
        orchestrator = create_dual_engine_orchestrator()
        stats = orchestrator.get_stats()
        
        assert "scenarios_processed" in stats
        assert "engine_a_runs" in stats
        assert "engine_b_runs" in stats
        assert "arbitrations" in stats
        assert "total_time_ms" in stats
        assert "avg_time_per_scenario_ms" in stats
    
    def test_orchestrator_timing_summary(self):
        """Test orchestrator timing summary."""
        from src.nsic.orchestration.dual_engine_orchestrator import (
            create_dual_engine_orchestrator
        )
        
        orchestrator = create_dual_engine_orchestrator()
        summary = orchestrator.get_timing_summary()
        
        assert "stage_summary" in summary
        assert "timing_stats" in summary


class TestDualEngineResult:
    """Tests for DualEngineResult dataclass."""
    
    def test_result_creation(self):
        """Test DualEngineResult can be created."""
        from src.nsic.orchestration.dual_engine_orchestrator import DualEngineResult
        
        result = DualEngineResult(
            scenario_id="test_001",
            scenario_name="Test Scenario",
            domain="economic",
        )
        
        assert result.scenario_id == "test_001"
        assert result.confidence == 0.0
        assert result.final_content == ""
    
    def test_result_to_dict(self):
        """Test DualEngineResult.to_dict()."""
        from src.nsic.orchestration.dual_engine_orchestrator import DualEngineResult
        
        result = DualEngineResult(
            scenario_id="test_001",
            scenario_name="Test Scenario",
            domain="economic",
            final_content="Test content",
            confidence=0.85,
        )
        
        data = result.to_dict()
        
        assert data["scenario_id"] == "test_001"
        assert data["confidence"] == 0.85
        assert data["final_content_length"] == len("Test content")


class TestStageEnum:
    """Tests for Stage enum."""
    
    def test_all_stages_defined(self):
        """Test all required stages are defined."""
        from src.nsic.orchestration.timing_logger import Stage
        
        required_stages = [
            "scenario_load",
            "context_retrieval",
            "embedding_generation",
            "knowledge_graph",
            "engine_a",
            "engine_b",
            "verification",
            "arbitration",
            "synthesis",
            "total",
        ]
        
        stage_values = [s.value for s in Stage]
        
        for stage in required_stages:
            assert stage in stage_values, f"Missing stage: {stage}"


class TestModuleExports:
    """Tests for module exports."""
    
    def test_orchestration_exports(self):
        """Test orchestration package exports."""
        from src.nsic.orchestration import (
            DualEngineOrchestrator,
            DualEngineResult,
            create_dual_engine_orchestrator,
            TimingLogger,
            Stage,
            TimingEntry,
            ScenarioTimingReport,
            get_timing_logger,
            reset_timing_logger,
        )
        
        # All imports should succeed
        assert DualEngineOrchestrator is not None
        assert TimingLogger is not None
        assert Stage is not None


# Integration test (requires DeepSeek server running)
@pytest.mark.skipif(
    not os.environ.get("RUN_INTEGRATION_TESTS"),
    reason="Integration tests disabled"
)
class TestIntegration:
    """Integration tests requiring live services."""
    
    def test_deepseek_health(self):
        """Test DeepSeek server is healthy."""
        from src.nsic.orchestration import create_dual_engine_orchestrator
        
        orchestrator = create_dual_engine_orchestrator()
        health = orchestrator.health_check()
        
        assert health["engine_b"]["deepseek"]["status"] == "healthy"

