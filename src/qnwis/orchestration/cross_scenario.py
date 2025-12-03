"""
Cross-Scenario Analysis Module

Generates comparison tables and robustness analysis across all 6 scenarios.
This data is passed to Engine A agents to ensure they reference actual
computed numbers in their debate.
"""

import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


def generate_cross_scenario_table(engine_b_results: Dict[str, Any]) -> str:
    """
    Generate markdown table comparing all 6 scenarios.
    
    Args:
        engine_b_results: Dict with scenario names as keys, each containing:
            - monte_carlo: {success_rate, mean, std, ...}
            - sensitivity: {top_drivers, ...}
            - forecasting: {trend, forecasts, ...}
            - thresholds: {risk_level, warnings, ...}
    
    Returns:
        Formatted markdown table string
    """
    rows = []
    
    for scenario_name, results in engine_b_results.items():
        if scenario_name.startswith("_"):  # Skip internal keys like _global
            continue
        
        if not isinstance(results, dict):
            continue
        
        # Extract Monte Carlo results
        mc = results.get("monte_carlo", {}) or {}
        success_rate = mc.get("success_rate", mc.get("success_probability", None))
        
        # Extract threshold results
        thresh = results.get("thresholds", {}) or {}
        risk_level = thresh.get("risk_level", "unknown")
        
        # Extract sensitivity results
        # FIXED: sensitivity can be a list (new format) or dict (old format)
        sens = results.get("sensitivity", [])
        if isinstance(sens, list):
            # New format: list of {driver, label, contribution, direction}
            top_drivers = sens
        elif isinstance(sens, dict):
            # Old format: dict with top_drivers or parameter_impacts
            top_drivers = sens.get("top_drivers", sens.get("parameter_impacts", []))
        else:
            top_drivers = []
        
        if isinstance(top_drivers, list) and top_drivers:
            if isinstance(top_drivers[0], dict):
                top_driver = top_drivers[0].get("driver", top_drivers[0].get("variable", top_drivers[0].get("name", "unknown")))
            else:
                top_driver = str(top_drivers[0])
        else:
            top_driver = "unknown"
        
        # Extract forecasting results
        forecast = results.get("forecasting", {}) or {}
        trend = forecast.get("trend", "unknown")
        
        rows.append({
            "scenario": scenario_name.replace("_", " ").title(),
            "success_rate": success_rate,
            "risk_level": risk_level,
            "trend": trend,
            "top_driver": top_driver
        })
    
    # Sort by success rate (highest first), handling None values
    rows.sort(key=lambda x: x["success_rate"] if x["success_rate"] is not None else 0, reverse=True)
    
    # Build markdown table
    table = """
| Scenario | Success Rate | Risk Level | Trend | Top Driver |
|----------|--------------|------------|-------|------------|
"""
    
    for row in rows:
        sr = f"{row['success_rate']:.1%}" if row['success_rate'] is not None else "N/A"
        table += f"| {row['scenario']} | {sr} | {row['risk_level']} | {row['trend']} | {row['top_driver']} |\n"
    
    # Add summary statistics
    valid_rates = [r["success_rate"] for r in rows if r["success_rate"] is not None]
    passing = sum(1 for r in valid_rates if r >= 0.5)
    total = len(rows)
    
    table += f"\n**ROBUSTNESS: Policy succeeds in {passing}/{total} scenarios**\n"
    
    if valid_rates:
        worst = min(rows, key=lambda x: x["success_rate"] if x["success_rate"] is not None else float('inf'))
        best = max(rows, key=lambda x: x["success_rate"] if x["success_rate"] is not None else float('-inf'))
        
        best_sr = f"{best['success_rate']:.1%}" if best["success_rate"] is not None else "N/A"
        worst_sr = f"{worst['success_rate']:.1%}" if worst["success_rate"] is not None else "N/A"
        
        table += f"**BEST CASE:** {best['scenario']} ({best_sr})\n"
        table += f"**WORST CASE:** {worst['scenario']} ({worst_sr})\n"
    
    return table


def extract_robustness_summary(engine_b_results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract key robustness metrics from cross-scenario analysis.
    
    Returns:
        Dict with:
            - passing_scenarios: int (scenarios with success rate >= 50%)
            - total_scenarios: int
            - robustness_ratio: str (e.g., "4/6")
            - best_scenario: dict
            - worst_scenario: dict
            - top_drivers: list of top 3 drivers across all scenarios
    """
    scenarios = []
    all_drivers = []
    
    for scenario_name, results in engine_b_results.items():
        if scenario_name.startswith("_"):
            continue
        
        if not isinstance(results, dict):
            continue
        
        mc = results.get("monte_carlo", {}) or {}
        success_rate = mc.get("success_rate", mc.get("success_probability"))
        
        scenarios.append({
            "name": scenario_name,
            "success_rate": success_rate
        })
        
        # Collect drivers
        # FIXED: sensitivity can be a list (new format) or dict (old format)
        sens = results.get("sensitivity", [])
        if isinstance(sens, list):
            drivers = sens
        elif isinstance(sens, dict):
            drivers = sens.get("top_drivers", sens.get("parameter_impacts", []))
        else:
            drivers = []
        
        if isinstance(drivers, list):
            for d in drivers[:2]:  # Top 2 from each scenario
                if isinstance(d, dict):
                    all_drivers.append(d.get("driver", d.get("variable", d.get("name", ""))))
                elif isinstance(d, str):
                    all_drivers.append(d)
    
    valid_scenarios = [s for s in scenarios if s["success_rate"] is not None]
    passing = sum(1 for s in valid_scenarios if s["success_rate"] >= 0.5)
    
    # Find best/worst
    best = max(valid_scenarios, key=lambda x: x["success_rate"], default={"name": "N/A", "success_rate": None})
    worst = min(valid_scenarios, key=lambda x: x["success_rate"], default={"name": "N/A", "success_rate": None})
    
    # Get unique top drivers
    from collections import Counter
    driver_counts = Counter(all_drivers)
    top_drivers = [d for d, _ in driver_counts.most_common(3)]
    
    return {
        "passing_scenarios": passing,
        "total_scenarios": len(scenarios),
        "robustness_ratio": f"{passing}/{len(scenarios)}",
        "best_scenario": best,
        "worst_scenario": worst,
        "top_drivers": top_drivers,
    }


def build_quantitative_context_for_agents(
    engine_b_results: Dict[str, Any],
    extracted_facts: List[Dict] = None
) -> str:
    """
    Build comprehensive quantitative context for agents BEFORE debate.
    
    This ensures agents have access to:
    1. Cross-scenario comparison table
    2. Key robustness metrics
    3. Top policy levers from sensitivity analysis
    
    Args:
        engine_b_results: Results from Engine B for all scenarios
        extracted_facts: Optional list of extracted facts
    
    Returns:
        Formatted string to inject into agent prompts
    """
    cross_table = generate_cross_scenario_table(engine_b_results)
    robustness = extract_robustness_summary(engine_b_results)
    
    # Format top drivers
    drivers_formatted = "\n".join(f"- {d}" for d in robustness.get("top_drivers", [])) or "- Not computed"
    
    # Build context
    context = f"""
## QUANTITATIVE CONTEXT (Engine B Results)

Review computed analysis across {robustness.get('total_scenarios', 6)} scenarios:

{cross_table}

### Key Findings:
- **Robustness:** {robustness.get('robustness_ratio', 'N/A')} scenarios pass (success rate >= 50%)
- **Best Case:** {robustness.get('best_scenario', {}).get('name', 'N/A')} ({robustness.get('best_scenario', {}).get('success_rate', 0):.1%} success rate)
- **Worst Case:** {robustness.get('worst_scenario', {}).get('name', 'N/A')} ({robustness.get('worst_scenario', {}).get('success_rate', 0):.1%} success rate)

### Top Policy Levers (from sensitivity analysis):
{drivers_formatted}

---

**Your arguments MUST reference these numbers.**
Do not make up success rates or probabilities - use the computed values above.
"""
    
    return context


def aggregate_engine_b_from_scenarios(scenario_results: List[Dict]) -> Dict[str, Any]:
    """
    Aggregate Engine B results from parallel scenario executions.
    
    Args:
        scenario_results: List of completed scenario states, each containing
                         'engine_b_results' and 'scenario_name'
    
    Returns:
        Dict with scenario names as keys, Engine B results as values,
        plus '_global' key for run-once services
    """
    aggregated = {
        "_global": {
            "benchmarking": None,
            "correlation": None,
        }
    }
    
    for result in scenario_results:
        if not isinstance(result, dict):
            continue
        
        scenario_name = result.get("scenario_name", result.get("scenario_id", "unknown"))
        engine_b = result.get("engine_b_results", {})
        
        if engine_b:
            aggregated[scenario_name] = engine_b
            
            # Extract global services if present
            if "benchmarking" in engine_b and aggregated["_global"]["benchmarking"] is None:
                aggregated["_global"]["benchmarking"] = engine_b["benchmarking"]
            if "correlation" in engine_b and aggregated["_global"]["correlation"] is None:
                aggregated["_global"]["correlation"] = engine_b["correlation"]
    
    return aggregated


__all__ = [
    "generate_cross_scenario_table",
    "extract_robustness_summary",
    "build_quantitative_context_for_agents",
    "aggregate_engine_b_from_scenarios",
]

