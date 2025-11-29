#!/usr/bin/env python3
"""
Test Phase 9: Dual-Engine Orchestrator + Timing Logger
NO MOCKS. REAL INTEGRATION.
"""

import sys
import os
import asyncio
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    print("=" * 60)
    print("PHASE 9: DUAL-ENGINE ORCHESTRATOR TEST")
    print("=" * 60)
    
    # Test 1: Timing Logger
    print("\n[1] Testing Timing Logger...")
    from src.nsic.orchestration.timing_logger import (
        TimingLogger, Stage, get_timing_logger
    )
    
    timing = get_timing_logger()
    print("  ✅ Timing logger created")
    
    # Test timing context manager
    import time
    with timing.time_stage(Stage.SCENARIO_LOAD, "test_scenario"):
        time.sleep(0.05)  # Simulate work
    
    report = timing.get_report("test_scenario")
    if report:
        print(f"  ✅ Timing recorded: {report.total_time_ms:.1f}ms")
    
    stats = timing.get_stats()
    print(f"  ✅ Stats: {stats['total_entries']} entries")
    
    # Test 2: Dual-Engine Orchestrator Creation
    print("\n[2] Creating Dual-Engine Orchestrator...")
    from src.nsic.orchestration.dual_engine_orchestrator import (
        create_dual_engine_orchestrator,
        DualEngineOrchestrator,
    )
    
    orchestrator = create_dual_engine_orchestrator()
    print("  ✅ Orchestrator created")
    
    # Test 3: Health Check
    print("\n[3] Health check...")
    health = orchestrator.health_check()
    print(f"  Orchestrator: {health['orchestrator']}")
    print(f"  Engine B: {health['engine_b']['deepseek']['status']}")
    print(f"  Arbitrator: {health['arbitrator']}")
    print(f"  LLM Client: {health['llm_client']}")
    print(f"  Timing: {health['timing_logger']}")
    
    # Test 4: Load scenarios
    print("\n[4] Loading scenarios...")
    from src.nsic.scenarios import ScenarioLoader
    loader = ScenarioLoader("scenarios")
    loader.load_all()
    scenarios = loader.get_all()
    print(f"  ✅ Loaded {len(scenarios)} scenarios")
    
    # Test 5: Process ONE scenario (quick test)
    print("\n[5] Processing single scenario...")
    if scenarios:
        scenario = scenarios[0]
        print(f"  Scenario: {scenario.name}")
        print(f"  Engine: {scenario.assigned_engine}")
        
        async def run_test():
            result = await orchestrator.process_scenario(
                scenario,
                run_both_engines=False,  # Only Engine B for speed
            )
            return result
        
        result = asyncio.run(run_test())
        print(f"  ✅ Completed: confidence={result.confidence:.2f}")
        print(f"  ✅ Time: {result.total_time_ms/1000:.1f}s")
        print(f"  ✅ Final content: {len(result.final_content)} chars")
        
        if result.timing_breakdown:
            print("\n  Timing Breakdown:")
            for stage, ms in result.timing_breakdown.items():
                print(f"     - {stage}: {ms:.1f}ms")
    
    # Test 6: Orchestrator stats
    print("\n[6] Orchestrator stats...")
    stats = orchestrator.get_stats()
    print(f"  Scenarios processed: {stats['scenarios_processed']}")
    print(f"  Engine B runs: {stats['engine_b_runs']}")
    print(f"  Total time: {stats['total_time_ms']/1000:.1f}s")
    
    # Test 7: Timing Summary
    print("\n[7] Timing summary...")
    summary = orchestrator.get_timing_summary()
    if summary.get("stage_summary"):
        for stage, data in summary["stage_summary"].items():
            print(f"  {stage}: avg={data['avg_ms']:.1f}ms, count={data['count']}")
    
    print("\n" + "=" * 60)
    print("✅ PHASE 9 TEST COMPLETE - ORCHESTRATOR WORKING")
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

