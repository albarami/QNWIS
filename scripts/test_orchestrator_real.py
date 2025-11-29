#!/usr/bin/env python3
"""
Test Dual-Engine Orchestrator with REAL components.
NO MOCKS.
"""

import sys
import os
import asyncio
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    print("=" * 60)
    print("DUAL-ENGINE ORCHESTRATOR - REAL TEST")
    print("=" * 60)
    
    # Test 1: Imports
    print("\n[1] Testing imports...")
    from src.nsic.orchestration import (
        DualEngineOrchestrator,
        create_dual_engine_orchestrator,
        TimingLogger,
        create_timing_logger,
    )
    print("  ✅ All orchestration modules import")
    
    # Test 2: Timing Logger
    print("\n[2] Testing TimingLogger...")
    timing = create_timing_logger("test_scenario")
    
    import time
    with timing.track("embedding"):
        time.sleep(0.01)  # 10ms
    
    with timing.track("engine_a"):
        time.sleep(0.02)  # 20ms
    
    with timing.track("engine_b"):
        time.sleep(0.015)  # 15ms
    
    timing.complete()
    report = timing.get_report()
    
    print(f"  ✅ Scenario: {report['scenario_id']}")
    print(f"  ✅ Total time: {report['total_ms']:.1f}ms")
    print(f"  ✅ Breakdown: embedding={report['breakdown']['embedding_ms']:.1f}ms, "
          f"engine_a={report['breakdown']['engine_a_ms']:.1f}ms, "
          f"engine_b={report['breakdown']['engine_b_ms']:.1f}ms")
    
    # Test 3: Create Orchestrator
    print("\n[3] Creating Orchestrator...")
    orchestrator = create_dual_engine_orchestrator()
    print("  ✅ Orchestrator created")
    
    # Test 4: Load a scenario
    print("\n[4] Loading scenario...")
    from src.nsic.scenarios import ScenarioLoader
    loader = ScenarioLoader("scenarios")
    loader.load_all()
    scenarios = loader.get_all()
    
    if not scenarios:
        print("  ❌ No scenarios found!")
        return 1
    
    scenario = scenarios[0]
    print(f"  ✅ Using scenario: {scenario.name}")
    
    # Test 5: Process scenario (with minimal turns for speed)
    print("\n[5] Processing scenario (2 turns for quick test)...")
    
    async def run_test():
        result = await orchestrator.process_scenario(
            scenario,
            engine_a_turns=1,  # Minimal
            engine_b_turns=2,  # Minimal
        )
        return result
    
    result = asyncio.run(run_test())
    
    print(f"  ✅ Scenario ID: {result.scenario_id}")
    print(f"  ✅ Engine A turns: {result.engine_a_turns}")
    print(f"  ✅ Engine B turns: {result.engine_b_turns}")
    print(f"  ✅ Arbitration: {result.arbitration_result}")
    print(f"  ✅ Similarity: {result.similarity_score:.2f}")
    print(f"  ✅ Confidence: {result.confidence:.2f}")
    print(f"  ✅ Total time: {result.total_time_ms/1000:.1f}s")
    print(f"  ✅ Verified claims: {result.verified_claims}")
    print(f"  ✅ Data sources: {result.data_sources}")
    
    # Test 6: Timing breakdown
    print("\n[6] Timing breakdown...")
    timing_report = result.timing_report
    if "breakdown" in timing_report:
        for stage, ms in timing_report["breakdown"].items():
            if ms > 0:
                print(f"     {stage}: {ms:.1f}ms")
    
    # Test 7: Final content preview
    print("\n[7] Final content preview...")
    if result.final_content:
        print(f"  {result.final_content[:300]}...")
    else:
        print("  (No final content)")
    
    # Test 8: Orchestrator stats
    print("\n[8] Orchestrator stats...")
    stats = orchestrator.get_stats()
    print(f"  Scenarios processed: {stats['scenarios_processed']}")
    print(f"  Engine A calls: {stats['engine_a_calls']}")
    print(f"  Engine B calls: {stats['engine_b_calls']}")
    print(f"  Arbitrations: {stats['arbitrations']}")
    
    print("\n" + "=" * 60)
    print("✅ ORCHESTRATOR TEST COMPLETE - DUAL-ENGINE WORKING")
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

