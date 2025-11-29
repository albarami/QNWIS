#!/usr/bin/env python3
"""Quick verification script for hybrid model routing."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

def main():
    print("=" * 60)
    print("HYBRID MODEL ROUTING VERIFICATION")
    print("=" * 60)
    
    # Test 1: Import model router
    print("\n1. Testing model router import...")
    try:
        from src.qnwis.llm.model_router import (
            ModelRouter, TaskType, get_router, get_model_for_task
        )
        print("   ✓ model_router imports OK")
    except Exception as e:
        print(f"   ✗ Import failed: {e}")
        return 1
    
    # Test 2: Create router
    print("\n2. Testing router initialization...")
    try:
        router = ModelRouter()
        print(f"   ✓ Router created")
        print(f"   Primary model: {router.primary_config.deployment} (temp={router.primary_config.temperature})")
        print(f"   Fast model: {router.fast_config.deployment} (temp={router.fast_config.temperature})")
        print(f"   Hybrid enabled: {router.hybrid_enabled}")
    except Exception as e:
        print(f"   ✗ Router creation failed: {e}")
        return 1
    
    # Test 3: Test task routing
    print("\n3. Testing task-to-model routing...")
    
    fast_tasks = ["extraction", "verification", "classification", "fact_check"]
    primary_tasks = ["debate", "final_synthesis", "scenario_generation", "agent_analysis"]
    
    print("   Fast tasks (should use GPT-4o):")
    for task in fast_tasks:
        config = router.get_model_for_task(task)
        status = "✓" if "4o" in config.deployment.lower() or config.deployment == router.fast_config.deployment else "✗"
        print(f"     {status} {task} -> {config.deployment}")
    
    print("   Primary tasks (should use GPT-5):")
    for task in primary_tasks:
        config = router.get_model_for_task(task)
        status = "✓" if "5" in config.deployment or config.deployment == router.primary_config.deployment else "✗"
        print(f"     {status} {task} -> {config.deployment}")
    
    # Test 4: Test unknown task fallback
    print("\n4. Testing unknown task fallback...")
    config = router.get_model_for_task("unknown_xyz_task")
    expected = router.primary_config.deployment
    status = "✓" if config.deployment == expected else "✗"
    print(f"   {status} unknown_xyz_task -> {config.deployment} (expected: {expected})")
    
    # Test 5: Test usage tracking
    print("\n5. Testing usage tracking...")
    router.track_usage("primary", 100)
    router.track_usage("fast", 50)
    report = router.get_usage_report()
    print(f"   Primary calls: {report['primary_model']['calls']}, tokens: {report['primary_model']['tokens']}")
    print(f"   Fast calls: {report['fast_model']['calls']}, tokens: {report['fast_model']['tokens']}")
    
    # Test 6: Test LLMClient import with routing
    print("\n6. Testing LLMClient generate_with_routing method exists...")
    try:
        from src.qnwis.llm.client import LLMClient
        client = LLMClient.__new__(LLMClient)  # Don't initialize (would fail without API keys)
        has_method = hasattr(client, 'generate_with_routing')
        status = "✓" if has_method else "✗"
        print(f"   {status} generate_with_routing method: {'exists' if has_method else 'missing'}")
    except Exception as e:
        print(f"   ✗ LLMClient check failed: {e}")
    
    # Test 7: Test llm_wrapper import
    print("\n7. Testing llm_wrapper routing function...")
    try:
        from src.qnwis.orchestration.llm_wrapper import call_llm_with_routing
        print("   ✓ call_llm_with_routing imported successfully")
    except Exception as e:
        print(f"   ✗ Import failed: {e}")
    
    print("\n" + "=" * 60)
    print("VERIFICATION COMPLETE")
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

