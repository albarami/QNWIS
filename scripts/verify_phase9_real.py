#!/usr/bin/env python3
"""
Verify Phase 9: Dual-Engine Orchestrator + Timing Logger
NO MOCKS. REAL INTEGRATION.
"""

import sys
import os
import asyncio
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    print("=" * 60)
    print("PHASE 9 VERIFICATION: DUAL-ENGINE ORCHESTRATOR")
    print("=" * 60)
    
    errors = []
    
    # Test 1: Timing Logger Module
    print("\n[1] Timing Logger...")
    try:
        from src.nsic.orchestration.timing_logger import (
            TimingLogger, Stage, TimingEntry, ScenarioTimingReport,
            get_timing_logger, reset_timing_logger
        )
        
        # Test context manager timing
        timing = TimingLogger()
        with timing.time_stage(Stage.EMBEDDING_GENERATION, "test"):
            time.sleep(0.01)
        
        report = timing.get_report("test")
        assert report is not None, "No report generated"
        assert report.total_time_ms >= 10, "Timing not recorded"
        
        # Test manual start/end
        timing.start_stage(Stage.VERIFICATION, "test2")
        time.sleep(0.01)
        timing.end_stage(Stage.VERIFICATION, "test2")
        
        stats = timing.get_stats()
        assert stats["total_entries"] == 2, "Entry count wrong"
        
        print("  ✅ TimingLogger: context manager, manual, stats all working")
        
    except Exception as e:
        errors.append(f"TimingLogger: {e}")
        print(f"  ❌ TimingLogger: {e}")
    
    # Test 2: Dual-Engine Orchestrator Creation
    print("\n[2] DualEngineOrchestrator Creation...")
    try:
        from src.nsic.orchestration.dual_engine_orchestrator import (
            DualEngineOrchestrator, DualEngineResult, create_dual_engine_orchestrator
        )
        
        orchestrator = create_dual_engine_orchestrator()
        assert orchestrator is not None
        assert orchestrator.engine_b is not None
        assert orchestrator.timing is not None
        
        print("  ✅ Orchestrator created with all components")
        
    except Exception as e:
        errors.append(f"DualEngineOrchestrator creation: {e}")
        print(f"  ❌ DualEngineOrchestrator creation: {e}")
    
    # Test 3: Health Check - Must be HEALTHY not degraded
    print("\n[3] Health Check (must be HEALTHY)...")
    try:
        health = orchestrator.health_check()
        
        print(f"  Orchestrator: {health['orchestrator']}")
        assert health['orchestrator'] == 'healthy', "Orchestrator not healthy"
        
        engine_b_status = health['engine_b']['deepseek']['status']
        print(f"  Engine B (DeepSeek): {engine_b_status}")
        assert engine_b_status == 'healthy', f"DeepSeek must be healthy, got: {engine_b_status}"
        
        print(f"  Timing Logger: {health['timing_logger']}")
        print("  ✅ All components HEALTHY")
        
    except Exception as e:
        errors.append(f"Health check: {e}")
        print(f"  ❌ Health check: {e}")
    
    # Test 4: DeepSeek Direct Inference
    print("\n[4] DeepSeek Direct Inference...")
    try:
        client = orchestrator.engine_b.client
        response = client.chat([
            {"role": "user", "content": "Calculate: 15 * 7 = ?"}
        ])
        
        assert response is not None
        assert len(response.content) > 0
        assert response.total_time_ms > 0
        
        print(f"  ✅ Response: {response.content[:80]}...")
        print(f"  ✅ Time: {response.total_time_ms:.0f}ms")
        
    except Exception as e:
        errors.append(f"DeepSeek inference: {e}")
        print(f"  ❌ DeepSeek inference: {e}")
    
    # Test 5: Scenario Loading
    print("\n[5] Scenario Loading...")
    try:
        from src.nsic.scenarios import ScenarioLoader
        loader = ScenarioLoader("scenarios")
        loader.load_all()
        scenarios = loader.get_all()
        
        assert len(scenarios) > 0, "No scenarios loaded"
        print(f"  ✅ Loaded {len(scenarios)} scenarios")
        
        for s in scenarios[:3]:
            print(f"     - {s.id}: {s.name[:40]}...")
            
    except Exception as e:
        errors.append(f"Scenario loading: {e}")
        print(f"  ❌ Scenario loading: {e}")
    
    # Test 6: Integration Points
    print("\n[6] Integration Points...")
    try:
        # RAG
        rag = orchestrator.engine_b.rag
        assert rag is not None
        print("  ✅ RAG connector loaded")
        
        # Database
        db = orchestrator.engine_b.db
        assert db is not None
        print("  ✅ Database loaded")
        
        # Causal Graph
        graph = orchestrator.engine_b.graph
        assert graph is not None
        print("  ✅ Causal Graph loaded")
        
        # Verifier
        verifier = orchestrator.engine_b.verifier
        assert verifier is not None
        print("  ✅ Verifier loaded")
        
    except Exception as e:
        errors.append(f"Integration points: {e}")
        print(f"  ❌ Integration points: {e}")
    
    # Test 7: Orchestrator Stats
    print("\n[7] Orchestrator Stats...")
    try:
        stats = orchestrator.get_stats()
        
        print(f"  Scenarios processed: {stats['scenarios_processed']}")
        print(f"  Engine B runs: {stats['engine_b_runs']}")
        print(f"  Total time: {stats['total_time_ms']:.1f}ms")
        
        assert 'engine_b_stats' in stats
        print("  ✅ Stats structure valid")
        
    except Exception as e:
        errors.append(f"Stats: {e}")
        print(f"  ❌ Stats: {e}")
    
    # Summary
    print("\n" + "=" * 60)
    if errors:
        print(f"❌ PHASE 9 VERIFICATION FAILED: {len(errors)} errors")
        for err in errors:
            print(f"  - {err}")
        return 1
    else:
        print("✅ PHASE 9 VERIFICATION COMPLETE")
        print("   - TimingLogger: ✅")
        print("   - DualEngineOrchestrator: ✅")
        print("   - Health Check: ✅ HEALTHY")
        print("   - DeepSeek Inference: ✅")
        print("   - Scenario Loading: ✅")
        print("   - Integration Points: ✅")
        print("   - Stats: ✅")
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

