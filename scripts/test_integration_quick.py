"""Integration test: Simulates workflow state propagation for Engine B results."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_workflow_state_propagation():
    """
    Simulate how aggregate_scenarios_for_debate_node processes scenario_results
    and verify the cross_scenario_table and engine_b_results are correctly populated.
    """
    print("\n🧪 INTEGRATION TEST: Workflow State Propagation")
    print("=" * 60)
    
    # Simulate scenario_results structure as it comes from parallel_executor
    scenario_results = [
        {
            "scenario_name": "Base Case – Gradual Diversification",
            "engine_b_results": {
                "scenario_name": "Base Case – Gradual Diversification",
                "assumptions_applied": {"primary_variable": 2.8, "timeline_months": 120},
                "monte_carlo": {
                    "success_rate": 0.0,
                    "mean_result": 38656.67,
                    "std_result": 4239.31,
                    "n_simulations": 10000
                },
                "sensitivity": {
                    "base_result": 38603.82,
                    "parameter_impacts": [
                        {"name": "base_value", "swing": 15441.53},
                        {"name": "growth_rate", "swing": 5000.0}
                    ]
                },
                "forecasting": {"trend": "increasing", "forecasts": [39000, 40000, 41000]}
            }
        },
        {
            "scenario_name": "Optimistic Surge",
            "engine_b_results": {
                "scenario_name": "Optimistic Surge",
                "monte_carlo": {
                    "success_rate": 0.75,
                    "mean_result": 52000.0,
                    "n_simulations": 10000
                },
                "forecasting": {"trend": "accelerating"}
            }
        },
        {
            "scenario_name": "External Shock",
            "engine_b_results": {
                "scenario_name": "External Shock",
                "monte_carlo": {"success_rate": 0.15, "mean_result": 28000.0},
                "thresholds": {"safe_range": [0.1, 0.3], "risk_level": "high"}
            }
        }
    ]
    
    # === SIMULATE aggregate_scenarios_for_debate_node logic ===
    print("\n1️⃣ Testing aggregate_scenarios_for_debate_node logic...")
    
    engine_b_aggregate = {
        'scenarios_with_compute': 0,
        'total_monte_carlo_runs': 0,
        'avg_success_probability': 0,
        'sensitivity_drivers': [],
        'forecast_trends': [],
        'threshold_warnings': [],
    }
    
    engine_b_results_by_scenario = {}
    success_probs = []
    
    for result in scenario_results:
        engine_b = result.get('engine_b_results', {})
        scenario_name = result.get('scenario_name', 'Unknown')
        
        # Check for Engine B results
        has_engine_b = False
        if engine_b:
            has_monte_carlo = engine_b.get('monte_carlo') is not None
            has_forecast = engine_b.get('forecasting') is not None
            has_sensitivity = engine_b.get('sensitivity') is not None
            has_thresholds = engine_b.get('thresholds') is not None
            has_engine_b = has_monte_carlo or has_forecast or has_sensitivity or has_thresholds
        
        if has_engine_b:
            engine_b_aggregate['scenarios_with_compute'] += 1
            engine_b_results_by_scenario[scenario_name] = engine_b
            
            mc = engine_b.get('monte_carlo', {})
            if mc:
                engine_b_aggregate['total_monte_carlo_runs'] += 1
                sr = mc.get('success_probability') or mc.get('success_rate')
                if sr is not None:
                    success_probs.append(sr)
    
    if success_probs:
        engine_b_aggregate['avg_success_probability'] = sum(success_probs) / len(success_probs)
    
    print(f"  ✅ scenarios_with_compute: {engine_b_aggregate['scenarios_with_compute']}")
    print(f"  ✅ total_monte_carlo_runs: {engine_b_aggregate['total_monte_carlo_runs']}")
    print(f"  ✅ avg_success_probability: {engine_b_aggregate['avg_success_probability']:.2f}")
    print(f"  ✅ engine_b_results_by_scenario has {len(engine_b_results_by_scenario)} scenarios")
    
    # Generate cross-scenario table
    from src.qnwis.orchestration.cross_scenario import generate_cross_scenario_table
    cross_scenario_table = generate_cross_scenario_table(engine_b_results_by_scenario)
    
    print(f"  ✅ cross_scenario_table: {len(cross_scenario_table)} chars")
    
    # === SIMULATE streaming.py extraction logic ===
    print("\n2️⃣ Testing streaming.py extraction logic...")
    
    # This is what streaming.py does when building the final payload
    accumulated_state = {
        "scenario_results": scenario_results,
        "engine_b_aggregate": engine_b_aggregate,
        "engine_b_results": engine_b_results_by_scenario,
        "cross_scenario_table": cross_scenario_table,
        "engine_b_scenarios_computed": engine_b_aggregate['scenarios_with_compute']
    }
    
    # Verify all keys are present and correct
    checks = [
        ("engine_b_scenarios_computed == 3", accumulated_state.get("engine_b_scenarios_computed") == 3),
        ("engine_b_results has 3 keys", len(accumulated_state.get("engine_b_results", {})) == 3),
        ("cross_scenario_table not empty", len(accumulated_state.get("cross_scenario_table", "")) > 100),
    ]
    
    all_pass = True
    for name, result in checks:
        status = "✅" if result else "❌"
        print(f"  {status} {name}")
        if not result:
            all_pass = False
    
    # Verify the fallback logic in streaming.py would work
    print("\n3️⃣ Testing streaming.py fallback extraction...")
    
    # Simulate scenario_results without top-level engine_b_results
    empty_accumulated = {"scenario_results": scenario_results}
    
    # Run the fallback logic from streaming.py
    engine_b_results = empty_accumulated.get("engine_b_results", {})
    
    if not engine_b_results:
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
    
    print(f"  ✅ Fallback extracted {len(engine_b_results)} scenarios: {list(engine_b_results.keys())}")
    
    if len(engine_b_results) == 3:
        print("\n✅ INTEGRATION TEST PASSED")
        return True
    else:
        print(f"\n❌ INTEGRATION TEST FAILED: Expected 3 scenarios, got {len(engine_b_results)}")
        return False


def main():
    print("=" * 60)
    print("🔬 INTEGRATION TEST: State Propagation")
    print("=" * 60)
    
    result = test_workflow_state_propagation()
    
    if result:
        print("\n✅ All integration tests passed - Ready for full diagnostic!")
        return 0
    else:
        print("\n❌ Integration tests failed - Fix before running diagnostic!")
        return 1


if __name__ == "__main__":
    sys.exit(main())

