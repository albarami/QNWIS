#!/usr/bin/env python3
"""
Test Engine B with REAL DeepSeek server.
NO MOCKS.
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    print("=" * 60)
    print("ENGINE B (DeepSeek) - REAL TEST")
    print("=" * 60)
    
    # Test 1: Import and create
    print("\n[1] Creating Engine B...")
    from src.nsic.orchestration.engine_b_deepseek import create_engine_b
    from src.nsic.orchestration.deepseek_client import InferenceMode
    
    engine = create_engine_b(mock=False)  # REAL, NO MOCK
    print("  ✅ Engine B created")
    
    # Test 2: Health check
    print("\n[2] Health check...")
    health = engine.health_check()
    deepseek_status = health["deepseek"]["status"]
    print(f"  DeepSeek status: {deepseek_status}")
    print(f"  Components: {health['components']}")
    
    if deepseek_status == "unhealthy":
        print("  ❌ DeepSeek not healthy! Is the server running?")
        return 1
    elif deepseek_status == "degraded":
        print("  ⚠️  DeepSeek degraded (one instance running - OK for testing)")
    
    # Test 3: Load scenarios
    print("\n[3] Loading scenarios...")
    from src.nsic.scenarios import ScenarioLoader
    loader = ScenarioLoader("scenarios")
    loader.load_all()
    engine_b_scenarios = [
        s for s in loader.get_all() 
        if s.assigned_engine in ["engine_b", "auto"]
    ]
    print(f"  ✅ Found {len(engine_b_scenarios)} scenarios for Engine B")
    for s in engine_b_scenarios:
        print(f"     - {s.id} ({s.domain})")
    
    # Test 4: Run ONE scenario with 2 turns (quick test)
    print("\n[4] Running single scenario (2 turns)...")
    if engine_b_scenarios:
        scenario = engine_b_scenarios[0]
        print(f"  Scenario: {scenario.name}")
        
        async def run_test():
            result = await engine.analyze_scenario(scenario, turns=2)
            return result
        
        result = asyncio.run(run_test())
        print(f"  ✅ Completed {len(result.turns)} turns")
        print(f"  Time: {result.total_time_ms/1000:.1f}s")
        
        if result.turns:
            print(f"\n  --- Turn 1 Response Preview ---")
            print(f"  {result.turns[0].response[:300]}...")
            
            if result.turns[0].thinking:
                print(f"\n  --- Thinking Block ---")
                print(f"  {result.turns[0].thinking[:200]}...")
        
        print(f"\n  --- Synthesis Preview ---")
        print(f"  {result.final_synthesis[:300]}...")
    
    # Test 5: Stats
    print("\n[5] Engine stats...")
    stats = engine.get_stats()
    print(f"  Scenarios processed: {stats['scenarios_processed']}")
    print(f"  Total turns: {stats['total_turns']}")
    print(f"  Total tokens: {stats['total_tokens']}")
    print(f"  Total time: {stats['total_time_ms']/1000:.1f}s")
    
    print("\n" + "=" * 60)
    print("✅ ENGINE B TEST COMPLETE - REAL DEEPSEEK INTEGRATION")
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

