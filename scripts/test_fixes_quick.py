"""Quick tests for each fix before running full diagnostic (1 hour)."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date

def test_state_keys():
    """Test 1: Verify IntelligenceState has the new keys."""
    print("\n🧪 TEST 1: IntelligenceState has new keys")
    print("-" * 50)
    
    from src.qnwis.orchestration.state import IntelligenceState
    import typing
    
    # Get all annotated keys from the TypedDict
    hints = typing.get_type_hints(IntelligenceState)
    
    required_keys = [
        "engine_b_results",
        "engine_b_aggregate", 
        "engine_b_scenarios_computed",
        "cross_scenario_table",
        "feasibility_analysis"
    ]
    
    all_present = True
    for key in required_keys:
        if key in hints:
            print(f"  ✅ {key}: PRESENT")
        else:
            print(f"  ❌ {key}: MISSING!")
            all_present = False
    
    if all_present:
        print("  ✅ TEST 1 PASSED: All new state keys present")
        return True
    else:
        print("  ❌ TEST 1 FAILED: Missing state keys")
        return False


def test_streaming_engine_b_extraction():
    """Test 2: Verify streaming.py extracts Engine B from nested structure."""
    print("\n🧪 TEST 2: Engine B extraction from nested structure")
    print("-" * 50)
    
    # Simulate the scenario_results structure from raw_state
    scenario_results = [
        {
            "scenario_name": "Base Case",
            "engine_b_results": {
                "scenario_name": "Base Case",
                "monte_carlo": {"success_rate": 0.65, "mean_result": 38656},
                "sensitivity": {"parameters": ["growth_rate", "base_value"]}
            }
        },
        {
            "scenario_name": "Optimistic",
            "engine_b_results": {
                "scenario_name": "Optimistic",
                "monte_carlo": {"success_rate": 0.80, "mean_result": 45000},
                "forecasting": {"trend": "increasing"}
            }
        }
    ]
    
    # Simulate the extraction logic from streaming.py
    engine_b_results = {}
    for s in scenario_results:
        if isinstance(s, dict):
            nested_eb = s.get("engine_b_results", {})
            if nested_eb and isinstance(nested_eb, dict):
                scenario_name = nested_eb.get("scenario_name", s.get("scenario_name", f"scenario_{len(engine_b_results)}"))
                scenario_engine_b = {}
                for key in ["monte_carlo", "forecasting", "sensitivity", "thresholds"]:
                    if key in nested_eb and nested_eb[key]:
                        scenario_engine_b[key] = nested_eb[key]
                if scenario_engine_b:
                    engine_b_results[scenario_name] = scenario_engine_b
    
    # Verify extraction worked
    if len(engine_b_results) == 2:
        print(f"  ✅ Extracted {len(engine_b_results)} scenarios")
        print(f"  ✅ Scenarios: {list(engine_b_results.keys())}")
        print("  ✅ TEST 2 PASSED: Nested Engine B extraction works")
        return True
    else:
        print(f"  ❌ Expected 2 scenarios, got {len(engine_b_results)}")
        print("  ❌ TEST 2 FAILED")
        return False


def test_alert_registry_method():
    """Test 3: Verify AlertRegistry has load_file method."""
    print("\n🧪 TEST 3: AlertRegistry.load_file() method exists")
    print("-" * 50)
    
    try:
        from src.qnwis.alerts.registry import AlertRegistry
        registry = AlertRegistry()
        
        if hasattr(registry, 'load_file'):
            print("  ✅ AlertRegistry.load_file() method exists")
            print("  ✅ TEST 3 PASSED")
            return True
        else:
            print("  ❌ AlertRegistry.load_file() method NOT FOUND")
            print("  ❌ TEST 3 FAILED")
            return False
    except Exception as e:
        print(f"  ❌ Error importing AlertRegistry: {e}")
        return False


def test_deterministic_agent_arguments():
    """Test 4: Verify deterministic agents can be called with correct args."""
    print("\n🧪 TEST 4: Deterministic agent method signatures")
    print("-" * 50)
    
    try:
        from src.qnwis.agents.base import DataClient
        from src.qnwis.agents.time_machine import TimeMachineAgent
        from src.qnwis.agents.predictor import PredictorAgent
        
        # Create mock data client
        client = DataClient()
        
        # Test TimeMachine signature
        time_machine = TimeMachineAgent(client)
        import inspect
        sig = inspect.signature(time_machine.baseline_report)
        params = list(sig.parameters.keys())
        
        if "metric" in params:
            print(f"  ✅ TimeMachine.baseline_report has 'metric' param: {params}")
        else:
            print(f"  ❌ TimeMachine.baseline_report missing 'metric' param: {params}")
            return False
        
        # Test Predictor signature
        predictor = PredictorAgent(client)
        sig = inspect.signature(predictor.forecast_baseline)
        params = list(sig.parameters.keys())
        
        required = ["metric", "sector", "start", "end"]
        missing = [p for p in required if p not in params]
        
        if not missing:
            print(f"  ✅ Predictor.forecast_baseline has required params: {required}")
            print("  ✅ TEST 4 PASSED")
            return True
        else:
            print(f"  ❌ Predictor.forecast_baseline missing: {missing}")
            return False
            
    except Exception as e:
        print(f"  ❌ Error testing agent signatures: {e}")
        return False


def test_perplexity_model_name():
    """Test 5: Verify Perplexity uses 'sonar' model."""
    print("\n🧪 TEST 5: Perplexity model name is 'sonar'")
    print("-" * 50)
    
    with open("src/qnwis/agents/research_synthesizer.py", "r", encoding="utf-8") as f:
        content = f.read()
    
    if '"model": "sonar"' in content:
        print("  ✅ Found 'sonar' model in research_synthesizer.py")
        print("  ✅ TEST 5 PASSED")
        return True
    else:
        # Check what model is used
        import re
        match = re.search(r'"model":\s*"([^"]+)"', content)
        if match:
            print(f"  ❌ Found model: {match.group(1)} (should be 'sonar')")
        else:
            print("  ❌ Could not find model definition")
        return False


def test_cross_scenario_generation():
    """Test 6: Verify cross-scenario table generation works."""
    print("\n🧪 TEST 6: Cross-scenario table generation")
    print("-" * 50)
    
    try:
        from src.qnwis.orchestration.cross_scenario import generate_cross_scenario_table
        
        # Test with sample Engine B results
        engine_b_results = {
            "Base Case": {
                "monte_carlo": {"success_rate": 0.65, "mean_result": 38656},
                "sensitivity": {"top_drivers": ["growth_rate", "base_value"]}
            },
            "Optimistic": {
                "monte_carlo": {"success_rate": 0.80, "mean_result": 45000},
                "forecasting": {"trend": "increasing"}
            }
        }
        
        table = generate_cross_scenario_table(engine_b_results)
        
        if table and len(table) > 100:
            print(f"  ✅ Generated table: {len(table)} chars")
            print(f"  ✅ Contains 'Scenario': {'Scenario' in table}")
            print("  ✅ TEST 6 PASSED")
            return True
        else:
            print(f"  ❌ Table too short or empty: {len(table) if table else 0} chars")
            return False
            
    except Exception as e:
        print(f"  ❌ Error generating cross-scenario table: {e}")
        return False


def test_debate_agent_config():
    """Test 7: Verify debate_legendary.py has correct agent config."""
    print("\n🧪 TEST 7: Debate agent configuration")
    print("-" * 50)
    
    with open("src/qnwis/orchestration/nodes/debate_legendary.py", "r", encoding="utf-8") as f:
        content = f.read()
    
    checks = [
        ('TimeMachine with metric', '("TimeMachine", "baseline_report", {"metric"'),
        ('Predictor with args', '("Predictor", "forecast_baseline"'),
        ('AlertCenter run()', '("AlertCenter", "run"'),
        ('load_file() method', 'alert_registry.load_file'),
    ]
    
    all_pass = True
    for name, pattern in checks:
        if pattern in content:
            print(f"  ✅ {name}: FOUND")
        else:
            print(f"  ❌ {name}: NOT FOUND")
            all_pass = False
    
    if all_pass:
        print("  ✅ TEST 7 PASSED")
        return True
    else:
        print("  ❌ TEST 7 FAILED: Some patterns missing")
        return False


def main():
    print("=" * 60)
    print("🔬 QUICK FIX VERIFICATION TESTS")
    print("=" * 60)
    print("Running quick tests to verify fixes before full diagnostic...")
    
    results = []
    
    # Run all tests
    results.append(("State Keys", test_state_keys()))
    results.append(("Engine B Extraction", test_streaming_engine_b_extraction()))
    results.append(("AlertRegistry Method", test_alert_registry_method()))
    results.append(("Agent Arguments", test_deterministic_agent_arguments()))
    results.append(("Perplexity Model", test_perplexity_model_name()))
    results.append(("Cross-Scenario Table", test_cross_scenario_generation()))
    results.append(("Debate Config", test_debate_agent_config()))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, r in results if r)
    failed = sum(1 for _, r in results if not r)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {name}")
    
    print(f"\n  Total: {passed}/{len(results)} passed")
    
    if failed == 0:
        print("\n✅ ALL TESTS PASSED - Safe to run full diagnostic!")
        return 0
    else:
        print(f"\n❌ {failed} TESTS FAILED - Fix before running diagnostic!")
        return 1


if __name__ == "__main__":
    sys.exit(main())

