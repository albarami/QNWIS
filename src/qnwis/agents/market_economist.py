"""
Market Economist agent with Dr. Layla Al-Said persona.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, Any, List

from qnwis.agents.base import (
    coerce_llm_response_text,
    extract_assumptions,
    extract_citations_from_narrative,
    extract_data_gaps,
    extract_usage_tokens,
    resolve_response_model,
)
from qnwis.agents.prompts.base import ANTI_FABRICATION_RULES, format_extracted_facts

# Import AgentReport from typing to avoid circular dependency
from typing import Any
AgentReport = dict[str, Any]

MARKET_ECONOMIST_PERSONA = """
═══════════════════════════════════════════════════
👤 AGENT IDENTITY: Regional Market Economist
═══════════════════════════════════════════════════

CREDENTIALS:
• PhD in International Economics, London School of Economics (2013)
• Regional Director, Middle East Competitiveness Institute (2016-2021)
• Strategy Advisor to 6 GCC governments on talent attraction
• Author: "The New Gulf: Competing for Knowledge Economy Supremacy" (2022)

EXPERTISE:
• Regional competitive dynamics and game theory applications
• Talent hub strategies (Dubai, NEOM, Bahrain fintech)
• Policy arbitrage in labor markets
• FDI location determinants in knowledge sectors
• Comparative institutional analysis across GCC

ANALYTICAL FRAMEWORK:
1. Competitive Baseline: Assess Qatar's current regional position
2. Policy Divergence: Model how nationalization affects competitiveness
3. Competitor Response: Game-theoretic scenarios (UAE, Saudi reactions)
4. Talent Arbitrage: Predict cross-border mobility shifts
5. Strategic Positioning: Recommend positioning relative to regional players

═══════════════════════════════════════════════════
"""


STRUCTURED_OUTPUT_TEMPLATE = """
PROVIDE YOUR ANALYSIS IN THIS EXACT FORMAT:

## 🌍 MARKET ECONOMIST ANALYSIS
**Analyst:** Regional Market Economist

### 1. COMPETITIVE BASELINE
- Current ranking vs. UAE, Saudi, Bahrain: [cite extraction]
- Strength indicators (infrastructure, talent pipeline, incentives)
- Vulnerability indicators (regulation, speed, perception)

### 2. POLICY DIVERGENCE IMPACT
- How proposed nationalization targets alter Qatar's attractiveness
- Comparative advantage / disadvantage vs. top competitors
- Quantified effect on talent inflows or cost base (cite facts or mark NOT IN DATA)

### 3. COMPETITOR RESPONSE SCENARIOS
- UAE likely moves: [game-theoretic reasoning + citations]
- Saudi / NEOM adjustments: [reasoning + citations]
- Other GCC players (Bahrain, Oman): [summary]

### 4. TALENT ARBITRAGE SIGNALS
- Mobility vectors (which skills might leave/enter): [cite]
- Incentives competitors can deploy quickly
- Early-warning indicators to monitor

### 5. STRATEGIC POSITIONING RECOMMENDATIONS
- Positioning statement relative to UAE/Saudi
- Differentiated policy levers Qatar should emphasize
- Risk mitigation checklist

### 6. CONFIDENCE ASSESSMENT
**Overall Confidence: [X]%**
- Data coverage: [X]% (gaps listed)
- Competitive modeling robustness: [X]% (assumptions)
- Policy precedent relevance: [X]% (cite analogues)

**What Would Increase Confidence:**
[Specific missing data or monitoring inputs]

═══════════════════════════════════════════════════
"""


async def analyze(
    query: str, extracted_facts: List[Dict[str, Any]], llm_client: Any
) -> AgentReport:
    """Market Economist analysis with mandatory citation enforcement."""
    facts_formatted = format_extracted_facts(extracted_facts)
    
    prompt = f"""
{MARKET_ECONOMIST_PERSONA}

{ANTI_FABRICATION_RULES}

{facts_formatted}

MINISTERIAL QUERY:
{query}

{STRUCTURED_OUTPUT_TEMPLATE}

NOW PROVIDE YOUR ANALYSIS:
"""
    
    try:
        response = await llm_client.ainvoke(prompt)
        narrative = coerce_llm_response_text(response)

        if "Per extraction:" not in narrative and "NOT IN DATA" not in narrative:
            narrative = (
                "⚠️ ANALYSIS REJECTED - No citations found. "
                "Agent violated citation requirements.\n\n" + narrative
            )

        citations = extract_citations_from_narrative(narrative, extracted_facts)
        data_gaps = extract_data_gaps(narrative)
        assumptions = extract_assumptions(narrative)
        facts_used = sorted({citation["metric"] for citation in citations})
        confidence = extract_confidence_from_response(narrative)
        tokens_in, tokens_out = extract_usage_tokens(response)
        model_name = resolve_response_model(response, llm_client)

        return AgentReport(
            agent_name="market_economist",
            narrative=narrative,
            confidence=confidence,
            citations=citations,
            facts_used=facts_used,
            assumptions=assumptions,
            data_gaps=data_gaps,
            timestamp=datetime.utcnow().isoformat(),
            model=model_name,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
        )
    except Exception as exc:  # pragma: no cover - defensive
        error_text = f"ERROR: {exc}"
        return AgentReport(
            agent_name="market_economist",
            narrative=error_text,
            confidence=0.0,
            citations=[],
            facts_used=[],
            assumptions=[],
            data_gaps=["Agent execution failed"],
            timestamp=datetime.utcnow().isoformat(),
            model=getattr(llm_client, "model", "unknown"),
            tokens_in=0,
            tokens_out=0,
        )


def extract_confidence_from_response(response: str) -> float:
    """Extract confidence percentage from structured output."""
    import re

    patterns = [
        r"Overall Confidence:\s*(\d+)%",
        r"Confidence:\s*(\d+)%",
        r"confidence[""\s:]+(\d+)%",
        r"Feasibility Probability:\s*(\d+)%",
    ]

    for pattern in patterns:
        match = re.search(pattern, response, re.IGNORECASE)
        if match:
            confidence_pct = float(match.group(1))
            return min(confidence_pct / 100.0, 1.0)

    if "⚠️ ANALYSIS REJECTED" in response or "NOT FOUND" in response:
        return 0.0

    if len(response) < 100:
        return 0.2

    has_citations = "Per extraction:" in response or "[Per extraction:" in response
    has_calculations = any(word in response for word in ["calculated as", "equals", "totals"])
    has_scenarios = "SCENARIO" in response.upper()

    if has_citations and has_calculations and has_scenarios:
        return 0.7
    if has_citations:
        return 0.6
    return 0.4


class MarketEconomistAgent:  # pragma: no cover - compatibility shim
    """Legacy shim to retain prior import paths."""
    
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        raise RuntimeError(
            "MarketEconomistAgent class has been replaced. "
            "Use qnwis.agents.market_economist.analyze(...) instead."
        )
