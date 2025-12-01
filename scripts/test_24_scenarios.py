#!/usr/bin/env python3
"""
Test all 24 Engine B scenarios with timing measurements.

Reports:
- Total Engine B time
- Time per scenario
- Time per turn
- Instance utilization
"""

import asyncio
import time
import sys
import os

# Load .env file FIRST
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def run_24_scenario_test():
    print("=" * 70)
    print("NSIC ENGINE B: Full 24-Scenario Test")
    print("=" * 70)
    print()
    
    # Import components
    from src.nsic.orchestration import create_dual_engine_orchestrator, reset_timing_logger
    from src.nsic.scenarios import create_scenario_generator
    
    # Reset timing
    reset_timing_logger()
    
    # Create orchestrator
    print("Creating orchestrator...")
    orchestrator = create_dual_engine_orchestrator()
    
    # Health check
    health = orchestrator.health_check()
    print(f"Orchestrator status: {health['orchestrator']}")
    print(f"Engine B (DeepSeek) status: {health['engine_b']['deepseek']['status']}")
    print()
    
    # Generate scenarios
    print("Generating 24 scenarios...")
    generator = create_scenario_generator()
    scenario_set = await generator.generate("Should Qatar prioritize financial hub or logistics hub?")
    
    # Get all 24 Engine B scenarios
    scenarios = scenario_set.engine_b_scenarios
    print(f"Generated {len(scenarios)} Engine B scenarios")
    print()
    
    # Run all 24 scenarios IN PARALLEL across 8 GPUs
    print("=" * 70)
    print(f"Running {len(scenarios)} scenarios across 8 DeepSeek instances IN PARALLEL...")
    print("=" * 70)
    print()
    
    # Track progress with callback
    completed_count = [0]
    def on_complete(scenario_id, result):
        completed_count[0] += 1
        status = "✅" if result else "⚠️"
        print(f"  [{completed_count[0]}/{len(scenarios)}] {status} {scenario_id[:40]}")
    
    start_time = time.time()
    
    # Use Engine B's run_all_scenarios which does 8-way parallel!
    print("Starting 8-way parallel execution...")
    print("  Instance 1-8 (Ports 8001-8008): 3 scenarios each")
    print()
    
    results = await orchestrator.engine_b.run_all_scenarios(
        scenarios=scenarios,
        on_scenario_complete=on_complete
    )
    
    total_time = time.time() - start_time
    
    # Calculate statistics
    print()
    print("=" * 70)
    print("RESULTS SUMMARY")
    print("=" * 70)
    print()
    
    successful = len(results) if results else 0
    failed = len(scenarios) - successful
    
    # With 8-way parallel: effective time per scenario = total_time / 8
    effective_scenario_time = total_time / 8 if successful > 0 else 0
    
    # Estimate turns (25 per scenario)
    total_turns = len(scenarios) * 25
    time_per_turn = (total_time * 8) / total_turns if total_turns > 0 else 0  # Multiply by 8 for sequential equivalent
    
    print(f"Scenarios Completed: {successful}/{len(scenarios)}")
    print(f"Scenarios Failed: {failed}")
    print()
    print(f"Total Wall Time: {total_time:.1f}s ({total_time/60:.1f} minutes)")
    print(f"Effective Time per Instance: {effective_scenario_time:.1f}s (3 scenarios each)")
    print(f"Est. Sequential Time per Turn: {time_per_turn:.2f}s")
    print(f"SPEEDUP: 8x parallel = {total_time * 8 / 60:.1f} min equivalent in {total_time/60:.1f} min")
    print()
    
    # Instance utilization (from DeepSeek client stats)
    try:
        stats = orchestrator.engine_b.deepseek_client.get_stats()
        print(f"Instance Usage: {stats.get('instance_counts', 'N/A')}")
        print(f"Total Requests: {stats.get('total_requests', 'N/A')}")
    except:
        pass
    
    print()
    print("=" * 70)
    print(f"ENGINE B COMPLETE: {total_time/60:.1f} minutes for {len(scenarios)} scenarios")
    print("=" * 70)
    
    return {
        "total_scenarios": len(scenarios),
        "successful": successful,
        "failed": failed,
        "total_time_seconds": total_time,
        "total_time_minutes": total_time / 60,
        "avg_scenario_time": avg_scenario_time,
        "time_per_turn": time_per_turn,
    }


if __name__ == "__main__":
    result = asyncio.run(run_24_scenario_test())
    print()
    print("Test complete!")

