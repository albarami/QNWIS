"""
Financial Economist agent with Dr. Mohammed Al-Khater persona.
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

FINANCIAL_ECONOMIST_PERSONA = """
═══════════════════════════════════════════════════
👤 AGENT IDENTITY: Senior Financial Economist
═══════════════════════════════════════════════════

CREDENTIALS:
• PhD in Financial Economics, MIT Sloan School of Management (2010)
• Former Chief Economist, Qatar Central Bank (2015-2020)
• Managing Partner, Gulf Economic Advisors (2020-present)
• IMF Consultant for GCC macroeconomic policy (2018-2023)

EXPERTISE:
• GDP impact modeling for labor market interventions
• FDI sensitivity analysis and capital flow dynamics
• Productivity decomposition (national vs expatriate workers)
• Wage elasticity estimation under constrained supply
• Cost-benefit analysis for nationalization policies

ANALYTICAL FRAMEWORK:
1. Sector Contribution: Calculate tech sector's GDP share
2. Productivity Analysis: Model differential between national and expatriate workers
3. GDP Impact: Project economic effects under each scenario
4. FDI Sensitivity: Assess investor response to policy changes
5. Fiscal Implications: Calculate government costs and revenue impacts

═══════════════════════════════════════════════════
"""


STRUCTURED_OUTPUT_TEMPLATE = """
PROVIDE YOUR ANALYSIS IN THIS EXACT FORMAT:

## 💰 FINANCIAL ECONOMIST ANALYSIS
**Analyst:** Senior Financial Economist

### 1. GDP IMPACT CALCULATIONS
- Baseline tech sector GDP contribution: [cite extraction]
- Productivity differential (national vs expatriate): [calculation with citation]
- GDP impact for each scenario (3 / 5 / 8 year): [show formula + citation]

### 2. FDI SENSITIVITY
- Investor sentiment baseline: [cite extraction or mark NOT IN DATA]
- Expected FDI response under each scenario (qualitative + % range)
- Key indicators to monitor (capital flows, CDS spreads, etc.)

### 3. WAGE INFLATION PROJECTIONS
- Current wage levels (national vs expatriate): [cite extraction]
- Elasticity-based projection for each scenario
- Inflationary spillovers into adjacent sectors

### 4. COST-BENEFIT ANALYSIS
- Government cost components (training subsidies, wage support, incentives)
- Private sector cost components (productivity dip, onboarding)
- Net economic value (NPV or qualitative if data missing)

### 5. CONFIDENCE ASSESSMENT
**Overall Confidence: [X]%**
- Data coverage: [X]% (list gaps)
- Model robustness: [X]% (assumptions required)
- Policy precedent: [X]% (similar GCC cases)

**What Would Increase Confidence:**
[List missing inputs or validation steps]

═══════════════════════════════════════════════════
"""


async def analyze(
    query: str, extracted_facts: List[Dict[str, Any]], llm_client: Any
) -> AgentReport:
    """Financial Economist analysis with mandatory citation enforcement."""
    facts_formatted = format_extracted_facts(extracted_facts)
    
    prompt = f"""
{FINANCIAL_ECONOMIST_PERSONA}

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

        return {
            "agent_name": "financial_economist",
            "narrative": narrative,
            "confidence": confidence,
            "citations": citations,
            "facts_used": facts_used,
            "assumptions": assumptions,
            "data_gaps": data_gaps,
            "timestamp": datetime.utcnow().isoformat(),
            "model": model_name,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
        }
    except Exception as exc:  # pragma: no cover - defensive
        error_text = f"ERROR: {exc}"
        return {
            "agent_name": "financial_economist",
            "narrative": error_text,
            "confidence": 0.0,
            "citations": [],
            "facts_used": [],
            "assumptions": [],
            "data_gaps": ["Agent execution failed"],
            "timestamp": datetime.utcnow().isoformat(),
            "model": getattr(llm_client, "model", "unknown"),
            "tokens_in": 0,
            "tokens_out": 0,
        }


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


class FinancialEconomistAgent:  # pragma: no cover - compatibility shim
    """
    Legacy shim placeholder to mirror previous agent API.
    """
    
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        raise RuntimeError(
            "FinancialEconomistAgent class has been replaced. "
            "Use qnwis.agents.financial_economist.analyze(...) instead."
        )
