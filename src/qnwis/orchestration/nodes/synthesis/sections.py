"""
Section builders for the Legendary Synthesis pipeline.

Builds scenario summaries, cross-scenario comparison tables,
robustness calculations, edge case extraction, and risk extraction.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from ...state import IntelligenceState

logger = logging.getLogger(__name__)


def extract_scenario_summaries(state: IntelligenceState) -> List[Dict[str, Any]]:
    """Extract scenario analysis summaries with Engine B quantitative results.

    Handles three cases:
    1. Both scenarios and scenario_results exist – match them
    2. Only scenarios exist – use scenario definitions
    3. Only scenario_results exist – build from results directly
    """
    scenarios = state.get("scenarios") or []
    scenario_results = state.get("scenario_results") or []

    summaries: List[Dict[str, Any]] = []

    if scenarios:
        for i, scenario in enumerate(scenarios):
            if not isinstance(scenario, dict):
                continue

            result = None
            scenario_id = scenario.get("id", scenario.get("scenario_id"))
            for r in scenario_results:
                if isinstance(r, dict):
                    r_id = r.get("scenario_id", r.get("id"))
                    if r_id and scenario_id and r_id == scenario_id:
                        result = r
                        break

            if not result and i < len(scenario_results):
                result = scenario_results[i] if isinstance(scenario_results[i], dict) else {}

            summaries.append(_build_scenario_summary(scenario, result, i))

    elif scenario_results:
        logger.info(f"📊 No scenario definitions, building summaries from {len(scenario_results)} results")
        for i, result in enumerate(scenario_results):
            if not isinstance(result, dict):
                continue
            pseudo_scenario = {
                "name": result.get("scenario_name", result.get("name", f"Scenario {i+1}")),
                "description": result.get("description", ""),
                "probability": result.get("probability", 0.5),
                "id": result.get("scenario_id", result.get("id", f"scenario_{i}")),
            }
            summaries.append(_build_scenario_summary(pseudo_scenario, result, i))
    else:
        logger.warning("⚠️ No scenario definitions or results found!")
        return []

    return summaries[:6]


def _build_scenario_summary(
    scenario: Dict[str, Any],
    result: Optional[Dict[str, Any]],
    index: int
) -> Dict[str, Any]:
    """Build a single scenario summary from scenario definition and result."""
    confidence = 0.75
    if result:
        confidence = result.get("confidence_score", result.get("confidence", 0.75))

    engine_b = result.get("engine_b_results", {}) if result else {}
    monte_carlo = engine_b.get("monte_carlo", {}) or {}
    sensitivity = engine_b.get("sensitivity", [])
    forecasting = engine_b.get("forecasting", {}) or {}

    key_drivers: List[str] = []
    if isinstance(sensitivity, list):
        key_drivers = [
            d.get("driver", d.get("variable", d.get("label", "")))
            for d in sensitivity[:3] if isinstance(d, dict)
        ]
    elif isinstance(sensitivity, dict):
        sens_list = sensitivity.get("sensitivities", sensitivity.get("parameter_impacts", []))
        key_drivers = [d.get("variable", "") for d in sens_list[:3] if isinstance(d, dict)]

    success_prob = 0
    if monte_carlo:
        success_prob = monte_carlo.get(
            "success_probability",
            monte_carlo.get("success_rate", monte_carlo.get("probability", 0))
        )

    engine_status = "not_run"
    if engine_b:
        if success_prob > 0 or monte_carlo.get("mean", 0) > 0:
            engine_status = "complete"
        elif engine_b.get("status"):
            engine_status = engine_b.get("status")
        else:
            engine_status = "failed"

    return {
        "name": scenario.get("name", f"Scenario {index+1}"),
        "description": scenario.get("description", ""),
        "probability": scenario.get("probability", 0.5),
        "confidence": confidence,
        "key_finding": (
            result.get("final_synthesis", result.get("synthesis", ""))[:300]
            if result else ""
        ),
        "success_probability": success_prob,
        "monte_carlo_mean": (
            monte_carlo.get("mean", monte_carlo.get("mean_result", 0))
            if monte_carlo else 0
        ),
        "monte_carlo_std": (
            monte_carlo.get("std", monte_carlo.get("std_result", 0))
            if monte_carlo else 0
        ),
        "key_drivers": key_drivers,
        "forecast_trend": (
            forecasting.get("trend", "stable") if forecasting else "unknown"
        ),
        "engine_b_status": engine_status,
    }


def build_cross_scenario_comparison(scenario_summaries: List[Dict[str, Any]]) -> str:
    """Build a cross-scenario comparison table with Engine B results.

    CRITICAL for McKinsey-grade output – showing how options
    perform across different future scenarios.
    """
    if not scenario_summaries:
        return "No scenarios available for comparison."

    lines = [
        "┌─────────────────────────────┬────────────┬────────────┬────────────────┬─────────────────┐",
        "│ Scenario                    │ Probability│ Success %  │ Monte Carlo    │ Key Drivers     │",
        "├─────────────────────────────┼────────────┼────────────┼────────────────┼─────────────────┤",
    ]

    for s in scenario_summaries:
        name = s.get("name", "Scenario")[:27]

        raw_prob = s.get('probability', 0.5)
        prob_pct = raw_prob * 100 if raw_prob <= 1 else raw_prob
        prob = f"{prob_pct:.0f}%"

        raw_success = s.get('success_probability', 0)
        success_pct = raw_success * 100 if raw_success <= 1 else raw_success
        success = f"{success_pct:.1f}%" if raw_success > 0 else "N/A"

        mc_mean = s.get("monte_carlo_mean", 0)
        mc_str = f"{mc_mean:,.0f}" if mc_mean else "N/A"

        drivers = ", ".join(s.get("key_drivers", [])[:2]) or "N/A"

        engine_status = s.get("engine_b_status", "unknown")
        if engine_status == "failed" and success == "N/A":
            success = "Failed"

        lines.append(
            f"│ {name:<27} │ {prob:>10} │ {success:>10} │ {mc_str:>14} │ {drivers[:15]:<15} │"
        )

    lines.append(
        "└─────────────────────────────┴────────────┴────────────┴────────────────┴─────────────────┘"
    )
    return "\n".join(lines)


def calculate_robustness_ratio(
    scenario_summaries: List[Dict[str, Any]],
    threshold: float = 0.4
) -> Dict[str, Any]:
    """Calculate robustness ratio – how many scenarios pass the success threshold.

    FIX RUN 23: Changed threshold from 0.5 to 0.4 to match frontend calculation.
    NOTE: threshold is in decimal form (0.4 = 40%)
    """
    total = len(scenario_summaries)
    if total == 0:
        return {
            "passed": 0, "total": 0, "ratio_str": "0/0",
            "ratio_pct": 0, "robust": False,
            "passing_scenarios": [], "failing_scenarios": [],
            "threshold_used": threshold,
        }

    passed = 0
    passing_scenarios: List[str] = []
    failing_scenarios: List[str] = []

    for s in scenario_summaries:
        raw_success = s.get("success_probability", 0)
        success_prob = raw_success / 100 if raw_success > 1 else raw_success

        if success_prob >= threshold:
            passed += 1
            passing_scenarios.append(s.get("name", "Unknown"))
        else:
            failing_scenarios.append(s.get("name", "Unknown"))

    return {
        "passed": passed,
        "total": total,
        "ratio_str": f"{passed}/{total}",
        "ratio_pct": (passed / total) * 100 if total > 0 else 0,
        "robust": passed >= (total * 0.67),
        "passing_scenarios": passing_scenarios,
        "failing_scenarios": failing_scenarios,
        "threshold_used": threshold,
    }


def extract_edge_cases(state: IntelligenceState) -> List[Dict[str, Any]]:
    """Extract edge case analyses from debate conversation."""
    edge_cases: List[Dict[str, Any]] = []

    explicit_cases = state.get("edge_case_results", [])
    if explicit_cases:
        for case in explicit_cases:
            if isinstance(case, dict):
                edge_cases.append({
                    "name": case.get("name", case.get("description", "Edge Case")[:50]),
                    "description": case.get("description", ""),
                    "severity": case.get("severity", "medium"),
                    "probability": case.get("probability_pct", 15),
                    "impact": case.get("impact_on_recommendations", ""),
                    "source": case.get("source", "Edge Case Analysis"),
                })

    debate_results = state.get("debate_results", {}) or {}
    conversation = (
        state.get("conversation_history", [])
        or debate_results.get("conversation_history", [])
    )

    edge_case_keywords = [
        "oil price", "oil shock", "recession", "pandemic", "automation",
        "geopolitical", "regional conflict", "talent exodus", "wage competition",
        "technology disruption", "black swan", "tail risk", "catastrophic"
    ]

    for turn in conversation:
        if not isinstance(turn, dict):
            continue

        turn_type = turn.get("type", "")
        message = turn.get("message", "").lower()

        if turn_type == "edge_case_analysis" or any(kw in message for kw in edge_case_keywords):
            case_name = "Edge Case"
            for kw in edge_case_keywords:
                if kw in message:
                    case_name = kw.title()
                    break

            edge_cases.append({
                "name": case_name,
                "turn": turn.get("turn", 0),
                "agent": turn.get("agent", "Unknown"),
                "description": turn.get("message", "")[:500],
                "severity": (
                    "high" if any(w in message for w in ["catastrophic", "collapse", "crisis"])
                    else "medium"
                ),
            })

    seen: set[str] = set()
    unique_cases: List[Dict[str, Any]] = []
    for case in edge_cases:
        name = case.get("name", "")
        if name not in seen:
            seen.add(name)
            unique_cases.append(case)

    logger.info(f"Extracted {len(unique_cases)} unique edge cases for synthesis")
    return unique_cases[:8]


def extract_risks(state: IntelligenceState) -> List[Dict[str, Any]]:
    """Extract risk intelligence from edge cases and critique."""
    critique = state.get("critique_results", {}) or {}
    red_flags = critique.get("red_flags", [])
    critiques = critique.get("critiques", [])

    risks: List[Dict[str, Any]] = []

    for i, flag in enumerate(red_flags):
        if isinstance(flag, str):
            flag_text = flag
        elif isinstance(flag, dict):
            flag_text = flag.get("description", flag.get("flag", str(flag)))
        else:
            flag_text = str(flag)

        risks.append({
            "type": "red_flag",
            "id": i + 1,
            "title": (
                f"Red Flag #{i+1}: {flag_text[:50]}..."
                if len(flag_text) > 50
                else f"Red Flag #{i+1}: {flag_text}"
            ),
            "description": flag_text,
            "severity": "HIGH",
            "source": "Devil's Advocate Critique",
            "requires_response": True,
        })

    for c in critiques:
        if isinstance(c, dict):
            risks.append({
                "type": "critique",
                "title": c.get("weakness_found", "Issue identified")[:50],
                "description": c.get("counter_argument", c.get("critique", "")),
                "severity": c.get("severity", "medium").upper(),
                "source": f"Expert {c.get('agent_name', 'Analysis')}",
                "agent": c.get("agent_name", ""),
                "turn": c.get("turn", 0),
            })

    return risks[:10]
