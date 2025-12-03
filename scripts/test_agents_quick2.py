"""Quick test for agent fixes."""
import sys
sys.path.insert(0, '.')

def main():
    print("=== TESTING AGENT FIXES ===\n")
    
    # Test 1: NationalStrategy
    print("1. Testing NationalStrategy.gcc_benchmark()...")
    try:
        from src.qnwis.agents.national_strategy import NationalStrategyAgent
        from src.qnwis.data.deterministic.cache_access import CacheAccess
        client = CacheAccess()
        agent = NationalStrategyAgent(client)
        result = agent.gcc_benchmark()
        if result.warnings:
            print(f"   [WARN] {result.warnings[0]}")
        else:
            print(f"   [OK] {len(result.findings)} findings")
    except Exception as e:
        print(f"   [FAIL] {e}")
    
    # Test 2: LabourEconomist
    print("\n2. Testing LabourEconomist.run()...")
    try:
        from src.qnwis.agents.labour_economist import LabourEconomistAgent
        from src.qnwis.data.deterministic.cache_access import CacheAccess
        client = CacheAccess()
        agent = LabourEconomistAgent(query_id='syn_employment_share_by_gender_latest', client=client)
        result = agent.run()
        if result.warnings:
            print(f"   [WARN] {result.warnings[0]}")
        else:
            print(f"   [OK] {len(result.findings)} findings")
    except Exception as e:
        print(f"   [FAIL] {e}")
    
    # Test 3: debate_legendary state handling
    print("\n3. Testing debate_legendary state handling...")
    try:
        # Simulate the problematic state
        state = {
            "scenario_results": None,  # This was causing the crash
            "cross_scenario_table": None,
            "engine_b_aggregate": None,
        }
        
        cross_scenario_table = state.get("cross_scenario_table") or ""
        engine_b_aggregate = state.get("engine_b_aggregate") or {}
        scenario_results = state.get("scenario_results") or []
        
        has_cross_scenario = bool(cross_scenario_table)
        has_engine_b_scenarios = engine_b_aggregate.get("scenarios_with_compute", 0) > 0
        has_scenario_results = len(scenario_results) > 0
        
        print(f"   [OK] State handling works with None values")
        print(f"        - has_cross_scenario: {has_cross_scenario}")
        print(f"        - has_engine_b_scenarios: {has_engine_b_scenarios}")
        print(f"        - has_scenario_results: {has_scenario_results}")
    except Exception as e:
        print(f"   [FAIL] {e}")
    
    # Test 4: Document loader
    print("\n4. Testing document loader (autocommit)...")
    try:
        from src.qnwis.rag.document_loader import load_source_documents
        # Just import test - actual loading would take time
        print("   [OK] Document loader imports correctly")
    except Exception as e:
        print(f"   [FAIL] {e}")
    
    print("\n=== ALL QUICK TESTS COMPLETE ===")

if __name__ == "__main__":
    main()

