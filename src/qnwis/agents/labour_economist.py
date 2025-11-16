"""
Labour Economist agent with Dr. Fatima Al-Mansoori persona.
"""

from __future__ import annotations

from typing import Dict, Any, List

from qnwis.agents.prompts.base import (
    ANTI_FABRICATION_RULES,
    format_extracted_facts,
)

LABOUR_ECONOMIST_PERSONA = """
═══════════════════════════════════════════════════
👤 AGENT IDENTITY: Senior Labour Economist
═══════════════════════════════════════════════════

CREDENTIALS:
• PhD in Labor Economics, Oxford University (2012)
• Former Senior Economist, ILO Regional Office for Arab States (2013-2018)
• Lead Consultant, GCC Workforce Development Initiatives (2018-present)
• 23 peer-reviewed publications on Gulf labor market dynamics

EXPERTISE:
• Supply-demand modeling for constrained labor markets
• Educational pipeline capacity analysis
• Nationalization policy implementation (UAE, Saudi, Oman precedents)
• Gender participation gap analysis in STEM fields
• Regional talent mobility patterns

ANALYTICAL FRAMEWORK:
1. Supply Side: Calculate current and projected national graduate production
2. Demand Side: Calculate required workforce for target Qatarization levels
3. Gap Analysis: Quantify supply-demand mismatch with timeline constraints
4. Feasibility: Assign probability to each implementation scenario
5. Risk Assessment: Identify critical bottlenecks and failure modes

═══════════════════════════════════════════════════
"""


STRUCTURED_OUTPUT_TEMPLATE = """
PROVIDE YOUR ANALYSIS IN THIS EXACT FORMAT:

## 🧑‍💼 LABOUR ECONOMIST ANALYSIS
**Analyst:** Senior Labour Economist

### 1. SUPPLY-DEMAND CALCULATION

**Current National Production:**
[Cite extraction for annual graduate numbers]

**Required National Workforce:**
[Calculate from target % × current sector employment from extraction]

**Supply Gap:**
[Calculation showing shortfall]

### 2. SCENARIO FEASIBILITY ASSESSMENT

**SCENARIO A (Aggressive - 3 years):**
- Required annual output: [calculation]
- Current capacity: [cite extraction]
- Capacity multiplier needed: [X]x
- **Feasibility Probability: [X]%**
- **Reasoning:** [Explain using cited facts]

**SCENARIO B (Moderate - 5 years):**
- Required annual output: [calculation]
- **Feasibility Probability: [X]%**
- **Reasoning:** [Explain using cited facts]

**SCENARIO C (Conservative - 8 years):**
- Required annual output: [calculation]
- **Feasibility Probability: [X]%**
- **Reasoning:** [Explain using cited facts]

### 3. CRITICAL BOTTLENECKS
1. **[Bottleneck Name]:** [Describe with evidence]
2. **[Bottleneck Name]:** [Describe with evidence]

### 4. DATA LIMITATIONS
**Missing Data That Would Improve Analysis:**
- [Specific data point needed]
- [Specific data point needed]

### 5. CONFIDENCE ASSESSMENT
**Overall Confidence: [X]%**

**Breakdown:**
- Data coverage: [X]% (have X out of Y critical data points)
- Model robustness: [X]% (assumptions needed: [list])
- Implementation precedent: [X]% (similar policies: [examples])

**What Would Increase Confidence:**
[List specific data or analysis needed]

═══════════════════════════════════════════════════
"""


async def analyze(query: str, extracted_facts: List[Dict[str, Any]], llm_client) -> Dict[str, Any]:
    """
    Labour Economist analysis with mandatory citation enforcement.
    """
    
    facts_formatted = format_extracted_facts(extracted_facts)
    
    prompt = f"""
{LABOUR_ECONOMIST_PERSONA}

{ANTI_FABRICATION_RULES}

{facts_formatted}

MINISTERIAL QUERY:
{query}

{STRUCTURED_OUTPUT_TEMPLATE}

NOW PROVIDE YOUR ANALYSIS:
"""
    
    try:
        response = await llm_client.ainvoke(prompt)
        
        if "Per extraction:" not in response and "NOT IN DATA" not in response:
            response = (
                "⚠️ ANALYSIS REJECTED - No citations found. "
                "Agent violated citation requirements.\n\n" + response
            )
        
        return {
            "agent": "LabourEconomist",
            "persona": "Dr. Fatima Al-Mansoori",
            "analysis": response,
            "confidence": extract_confidence_from_response(response),
        }
        
    except Exception as e:
        return {
            "agent": "LabourEconomist",
            "persona": "Dr. Fatima Al-Mansoori",
            "analysis": f"ERROR: {e}",
            "confidence": 0.0,
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


class LabourEconomistAgent:  # pragma: no cover - compatibility shim
    """
    Legacy shim preserved for older imports.
    
    Usage has shifted to the module-level `analyze` coroutine.
    """
    
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        raise RuntimeError(
            "LabourEconomistAgent class has been replaced. "
            "Use qnwis.agents.labour_economist.analyze(...) instead."
        )
