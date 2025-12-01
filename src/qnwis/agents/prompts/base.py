"""
Shared prompt utilities for all agents.

Includes:
- Anti-fabrication rules
- Engine B quantitative validation awareness
- Formatting utilities
"""

from __future__ import annotations

from typing import Iterable, Mapping, Any, Dict, List, Optional


# =============================================================================
# ENGINE B QUANTITATIVE VALIDATION AWARENESS
# =============================================================================

ENGINE_B_VALIDATION_AWARENESS = """
═══════════════════════════════════════════════════════════════════════
QUANTITATIVE VALIDATION (Engine B)
═══════════════════════════════════════════════════════════════════════

After your debate concludes, your recommendations will be validated by 
Engine B - a quantitative compute engine that runs:

• Monte Carlo simulations (10,000 scenarios) → probability of success
• Time series forecasting → trend projections with confidence bands
• Threshold analysis → breaking points where policy fails
• Sensitivity analysis → key drivers ranked by impact
• Benchmark comparisons → Qatar vs GCC peers

WHAT THIS MEANS FOR YOU:

1. MAKE TESTABLE CLAIMS
   ❌ "This is likely to succeed"
   ✅ "We expect 15% Qatarization is achievable by 2028"

2. IDENTIFY YOUR ASSUMPTIONS
   State what variables your recommendation depends on:
   - Oil price assumptions
   - Workforce growth rate
   - Policy enforcement level

3. FLAG UNCERTAINTY
   If you're uncertain about feasibility, say so explicitly.
   Engine B will quantify it with probability distributions.

4. DON'T FABRICATE NUMBERS
   If you don't have data, write:
   "Engine B should validate [specific claim]"

YOUR OUTPUT SHOULD INCLUDE:

At the end of the debate, provide structured validation requests:

```json
{
  "recommendation": "Your main recommendation",
  "confidence": 0.75,
  "key_claims": [
    "15% Qatarization is achievable by 2028",
    "Wage subsidies are more effective than quotas"
  ],
  "assumptions": {
    "qatari_workforce_growth": "2.1% annually",
    "private_sector_growth": "4.3% annually"
  },
  "validation_requests": [
    "Run Monte Carlo on Qatarization feasibility",
    "Find threshold where labor shortage occurs"
  ]
}
```

These validation requests tell Engine B exactly what to compute.

═══════════════════════════════════════════════════════════════════════
"""


# =============================================================================
# ENGINE B OUTPUT INTERPRETATION GUIDE
# =============================================================================

ENGINE_B_OUTPUT_GUIDE = """
═══════════════════════════════════════════════════════════════════════
HOW TO READ ENGINE B RESULTS
═══════════════════════════════════════════════════════════════════════

MONTE CARLO RESULTS:
• success_rate < 0.30 = High risk, likely infeasible
• success_rate 0.30-0.60 = Moderate risk, achievable with effort  
• success_rate > 0.60 = Good probability of success
• Look at sensitivity to identify what policy should focus on

FORECAST RESULTS:
• trend = "increasing" / "decreasing" / "stable"
• lower/upper = 95% confidence bands (widen over time)
• If your claim contradicts trend, you have a conflict

THRESHOLD RESULTS:
• threshold = breaking point - DO NOT exceed this
• safe_range = where policy works
• If recommendation exceeds threshold, you have a conflict

SENSITIVITY RESULTS:
• top_driver = what policy should focus on
• impact_pct = relative importance (sums to 100%)
• direction = "positive" (increase helps) or "negative" (increase hurts)

BENCHMARK RESULTS:
• percentile = where Qatar stands (higher = better if metric is positive)
• gaps = how far behind/ahead of peers
• Use for context in recommendations

CORRELATION RESULTS:
• correlation > 0.7 = Strong driver, prioritize this
• correlation 0.4-0.7 = Moderate driver
• correlation < 0.3 = Weak driver, less important

═══════════════════════════════════════════════════════════════════════
"""


# =============================================================================
# ANTI-FABRICATION RULES
# =============================================================================

ANTI_FABRICATION_RULES = """
═══════════════════════════════════════════════════
🚨 CRITICAL CITATION REQUIREMENTS 🚨
═══════════════════════════════════════════════════

RULE 1: CITE EVERY FACT
✅ CORRECT: "Per extraction: Qatar produces 347 tech graduates annually (MoL Education Data, confidence 70%)"
❌ WRONG: "Qatar produces approximately 800-1,200 tech graduates annually"

RULE 2: NEVER INVENT NUMBERS
✅ CORRECT: "NOT IN DATA - cannot estimate training infrastructure costs without Ministry of Education budget data"
❌ WRONG: "$2.5B investment in specialized tech education"

RULE 3: FLAG ALL ASSUMPTIONS
✅ CORRECT: "ASSUMPTION (confidence: 40%): 15% productivity differential between national and expatriate workers"
❌ WRONG: "Productivity differential: 15%"

RULE 4: SHOW YOUR CALCULATIONS
✅ CORRECT: "Required workforce: 7,440 (calculated as 60% × 12,400 [Per extraction: MoL LMIS])"
❌ WRONG: "Required workforce: approximately 7,500"

RULE 5: USE EXTRACTION OR ADMIT IGNORANCE
- If the data exists in EXTRACTED FACTS, cite it
- If the data is missing, write "NOT IN DATA - [explain what's missing]"
- DO NOT fill gaps with estimates unless explicitly labeled as ASSUMPTION

═══════════════════════════════════════════════════
VIOLATIONS = SYNTHESIS REJECTION
═══════════════════════════════════════════════════
"""


def format_extracted_facts(facts: Iterable[Mapping[str, Any]]) -> str:
    """
    Format deterministic fact records for inclusion in prompts.
    """
    formatted = ["EXTRACTED FACTS DATABASE:", "═" * 60, ""]
    
    for fact in facts:
        metric = str(fact.get("metric", "UNKNOWN METRIC"))
        value = fact.get("value", "N/A")
        source = fact.get("source", "UNKNOWN SOURCE")
        confidence = fact.get("confidence")
        
        formatted.append(f"• {metric}: {value}")
        formatted.append(f"  Source: {source}")
        if isinstance(confidence, (int, float)):
            formatted.append(f"  Confidence: {confidence * 100:.0f}%")
        else:
            formatted.append("  Confidence: N/A")
        
        raw_text = fact.get("raw_text")
        if raw_text:
            formatted.append(f"  Context: {str(raw_text)[:100]}...")
        
        formatted.append("")
    
    formatted.append("═" * 60)
    formatted.append("")
    return "\n".join(formatted)


# =============================================================================
# ENGINE A PRIME - CONFLICT RESOLUTION PROMPT
# =============================================================================

ENGINE_A_PRIME_PROMPT_TEMPLATE = """
═══════════════════════════════════════════════════════════════════════
CONFLICT RESOLUTION ROUND
═══════════════════════════════════════════════════════════════════════

Your previous recommendation is being challenged by quantitative analysis.

YOUR ORIGINAL RECOMMENDATION:
{engine_a_recommendation}

YOUR ORIGINAL CONFIDENCE: {engine_a_confidence:.0%}

YOUR KEY CLAIMS:
{engine_a_key_claims}

───────────────────────────────────────────────────────────────────────
ENGINE B QUANTITATIVE FINDINGS
───────────────────────────────────────────────────────────────────────

{formatted_engine_b_results}

───────────────────────────────────────────────────────────────────────
CONFLICTS DETECTED
───────────────────────────────────────────────────────────────────────

{conflicts_list}

───────────────────────────────────────────────────────────────────────
YOUR TASK
───────────────────────────────────────────────────────────────────────

Address each conflict using one of these resolutions:

1. ACCEPT - If the math is correct, revise your recommendation
2. CHALLENGE - If you believe the model assumptions are wrong, explain why
3. CONTEXTUALIZE - If the numbers are correct but misleading, explain context

RULES:
• You CANNOT ignore the quantitative findings
• You MUST either revise OR explain why the numbers don't change your conclusion
• If you revise, clearly state what changed and why
• Your final recommendation must incorporate the quantitative evidence

OUTPUT FORMAT:

```json
{{
  "conflict_resolutions": [
    {{
      "conflict": "Engine B shows only 12% success rate for 20% target",
      "resolution": "accept",
      "action": "Revise target from 20% to 15%",
      "reasoning": "Monte Carlo confirms 20% is mathematically infeasible"
    }}
  ],
  "revised_recommendation": "Target 15% Qatarization by 2028 (revised from 20%)",
  "revised_confidence": 0.82,
  "incorporated_statistics": [
    "15% achievable in 67.4% of scenarios",
    "Labor shortage threshold at 16.4%"
  ]
}}
```

This is a focused round. Be direct and efficient. You have 30-50 turns maximum.

═══════════════════════════════════════════════════════════════════════
"""


# =============================================================================
# ENGINE B RESULT FORMATTING FUNCTIONS
# =============================================================================

def format_engine_b_results(results: Dict[str, Any]) -> str:
    """
    Format Engine B results for agent consumption.
    
    Args:
        results: Dict containing monte_carlo, forecast, thresholds, etc.
        
    Returns:
        Human-readable formatted string
    """
    sections = []
    
    if "monte_carlo" in results:
        mc = results["monte_carlo"]
        n_sims = mc.get("n_simulations", 10000)
        mean = mc.get("mean_result", mc.get("mean", 0))
        success = mc.get("success_rate", 0)
        p5 = mc.get("var_95", mc.get("p5", 0))
        p95 = mc.get("p95", mean * 1.5 if mean else 0)
        
        # Get top driver from sensitivity
        sens = mc.get("variable_contributions", mc.get("sensitivity", {}))
        top_driver = max(sens, key=sens.get) if sens else "N/A"
        top_impact = sens.get(top_driver, 0) if sens else 0
        
        sections.append(f"""
### Monte Carlo Simulation ({n_sims:,} scenarios)
- **Mean outcome**: {mean:.2f}
- **Success rate**: {success:.1%}
- **95% range**: [{p5:.2f}, {p95:.2f}]
- **Top driver**: {top_driver} ({top_impact:.0%} of variance)
        """.strip())
    
    if "forecasting" in results or "forecast" in results:
        fc = results.get("forecasting") or results.get("forecast", {})
        trend = fc.get("trend", "unknown")
        forecasts = fc.get("forecasts", [])
        
        if forecasts:
            last = forecasts[-1] if isinstance(forecasts[-1], dict) else {}
            last_val = last.get("point_forecast", last.get("forecast", 0))
            last_lower = last.get("lower_bound", last.get("lower", 0))
            last_upper = last.get("upper_bound", last.get("upper", 0))
            
            sections.append(f"""
### Time Series Forecast
- **Trend**: {trend}
- **Final projection**: {last_val:,.0f}
- **95% confidence band**: [{last_lower:,.0f}, {last_upper:,.0f}]
            """.strip())
    
    if "thresholds" in results:
        th = results["thresholds"]
        thresholds_list = th.get("thresholds", [])
        risk_level = th.get("risk_level", "unknown")
        
        for t in thresholds_list[:3]:  # Limit to 3
            constraint = t.get("constraint_description", t.get("constraint", "Policy constraint"))
            threshold_val = t.get("threshold_value", t.get("threshold", 0))
            safe = t.get("safe_range", [0, threshold_val])
            breached = t.get("breached", False)
            
            sections.append(f"""
### Threshold Analysis: {constraint}
- **Breaking point**: {threshold_val:.1%}
- **Safe range**: {safe[0]:.1%} to {safe[1]:.1%}
- **Currently breached**: {'⚠️ YES' if breached else '✅ NO'}
- **Risk level**: {risk_level.upper()}
            """.strip())
    
    if "benchmarking" in results or "benchmark" in results:
        bm = results.get("benchmarking") or results.get("benchmark", {})
        
        # Handle different formats
        if "metric_benchmarks" in bm:
            mb = bm["metric_benchmarks"][0] if bm["metric_benchmarks"] else {}
            metric = mb.get("metric_name", "Primary metric")
            qatar_val = mb.get("qatar_value", 0)
            rank = mb.get("qatar_rank", 0)
            total = mb.get("total_peers", 6) + 1
            percentile = mb.get("qatar_percentile", 0)
        else:
            metric = bm.get("metric", "Primary metric")
            qatar_val = bm.get("qatar_value", 0)
            rank = bm.get("qatar_rank", 0)
            total = bm.get("total_peers", 6)
            percentile = bm.get("percentile", 0)
        
        sections.append(f"""
### GCC Benchmark: {metric}
- **Qatar value**: {qatar_val}
- **Qatar rank**: {rank}/{total}
- **Percentile**: {percentile:.0f}%
        """.strip())
    
    if "sensitivity" in results:
        sens = results["sensitivity"]
        top_drivers = sens.get("top_drivers", [])
        impacts = sens.get("parameter_impacts", [])
        
        if top_drivers:
            drivers_text = ", ".join(top_drivers[:3])
        elif impacts:
            drivers_text = ", ".join([
                f"{d.get('name', d.get('parameter', 'N/A'))} ({d.get('elasticity', d.get('impact_pct', 0)):.0f}%)"
                for d in impacts[:3]
            ])
        else:
            drivers_text = "N/A"
        
        sections.append(f"""
### Sensitivity Analysis
- **Top drivers**: {drivers_text}
        """.strip())
    
    if "correlation" in results:
        corr = results["correlation"]
        pairs = corr.get("significant_pairs", corr.get("drivers", []))
        
        if pairs:
            top = pairs[0]
            var1 = top.get("variable_1", top.get("variable", ""))
            var2 = top.get("variable_2", "target")
            r = top.get("pearson_r", top.get("correlation", 0))
            
            sections.append(f"""
### Correlation Analysis
- **Strongest relationship**: {var1} ↔ {var2} (r={r:.2f})
            """.strip())
    
    return "\n\n".join(sections) if sections else "No Engine B results available."


def format_conflicts(conflicts: List[Dict[str, Any]]) -> str:
    """
    Format conflict list for agent consumption.
    
    Args:
        conflicts: List of conflict dictionaries
        
    Returns:
        Formatted conflict list
    """
    if not conflicts:
        return "No conflicts detected."
    
    lines = []
    for i, conflict in enumerate(conflicts, 1):
        conflict_type = conflict.get("conflict_type", conflict.get("type", "unknown"))
        severity = conflict.get("severity", "medium")
        if hasattr(severity, "value"):
            severity = severity.value
        
        engine_a_claim = conflict.get("engine_a_claim", "")
        engine_b_finding = conflict.get("engine_b_finding", conflict.get("finding", ""))
        
        lines.append(f"""
{i}. [{severity.upper()}] {conflict_type}
   Engine A claimed: {engine_a_claim}
   Engine B found: {engine_b_finding}
        """.strip())
    
    return "\n\n".join(lines)


def build_engine_a_prime_prompt(
    engine_a_recommendation: str,
    engine_a_confidence: float,
    engine_a_key_claims: List[str],
    engine_b_results: Dict[str, Any],
    conflicts: List[Dict[str, Any]],
) -> str:
    """
    Build the Engine A Prime conflict resolution prompt.
    
    Args:
        engine_a_recommendation: Original recommendation text
        engine_a_confidence: Original confidence (0-1)
        engine_a_key_claims: List of key claims made
        engine_b_results: Raw Engine B results dict
        conflicts: List of conflict dictionaries
        
    Returns:
        Complete Engine A Prime prompt
    """
    claims_formatted = "\n".join(f"• {claim}" for claim in engine_a_key_claims)
    
    return ENGINE_A_PRIME_PROMPT_TEMPLATE.format(
        engine_a_recommendation=engine_a_recommendation,
        engine_a_confidence=engine_a_confidence,
        engine_a_key_claims=claims_formatted,
        formatted_engine_b_results=format_engine_b_results(engine_b_results),
        conflicts_list=format_conflicts(conflicts),
    )
