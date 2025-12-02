"""Check raw state for key values."""
import json
import sys

with open('data/diagnostics/raw_state_20251202_091613.json', 'r', encoding='utf-8') as f:
    state = json.load(f)

print('=== KEY CHECKS ===')
print(f"cross_scenario_table: {len(state.get('cross_scenario_table', '')) if state.get('cross_scenario_table') else 'EMPTY/MISSING'}")

engine_b_results = state.get('engine_b_results', {})
if engine_b_results:
    print(f"engine_b_results: {len(engine_b_results)} scenarios")
    for k in list(engine_b_results.keys())[:3]:
        print(f"  - {k}")
else:
    print("engine_b_results: EMPTY")

print(f"engine_b_aggregate: {state.get('engine_b_aggregate', {})}")
print(f"engine_b_scenarios_computed: {state.get('engine_b_scenarios_computed', 'MISSING')}")
print(f"engine_a_had_quantitative_context: {state.get('engine_a_had_quantitative_context', 'MISSING')}")

# Check scenario_results structure
scenario_results = state.get('scenario_results', [])
if scenario_results:
    print(f"\nscenario_results: {len(scenario_results)} scenarios")
    for i, s in enumerate(scenario_results[:2]):
        if isinstance(s, dict):
            has_eb = 'engine_b_results' in s
            eb = s.get('engine_b_results', {})
            has_mc = 'monte_carlo' in eb if eb else False
            print(f"  Scenario {i}: has_engine_b_results={has_eb}, has_monte_carlo={has_mc}")


