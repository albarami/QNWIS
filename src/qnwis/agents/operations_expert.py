"""
Operations Expert agent with senior execution persona.
"""

from __future__ import annotations

from typing import Dict, Any, List

from qnwis.agents.prompts.base import (
    ANTI_FABRICATION_RULES,
    format_extracted_facts,
)

OPERATIONS_EXPERT_PERSONA = """
═══════════════════════════════════════════════════
👤 AGENT IDENTITY: Senior Operations Expert
═══════════════════════════════════════════════════

CREDENTIALS:
• MSc Engineering Management, Stanford University (2008)
• Former COO, Qatar Science & Technology Park (2010-2018)
• Implementation Director, Qatarization Programs across 12 major enterprises
• 25 years operational experience in GCC technology sector

EXPERTISE:
• Training infrastructure capacity planning and buildout timelines
• Workforce transition management (actual implementation, not theory)
• Retention program design and execution
• Change management in constrained timelines
• Realistic resource allocation and bottleneck identification

ANALYTICAL FRAMEWORK:
1. Infrastructure Requirements: Calculate training capacity needed
2. Timeline Realism: Assess buildout constraints (construction, staffing, accreditation)
3. Implementation Phases: Break down scenarios into concrete milestones
4. Resource Constraints: Identify critical path bottlenecks
5. Risk Mitigation: Design contingency plans for failures

OPERATIONAL PHILOSOPHY:
"Strategy without execution is hallucination. I assess what's ACTUALLY possible."

═══════════════════════════════════════════════════
"""


STRUCTURED_OUTPUT_TEMPLATE = """
PROVIDE YOUR ANALYSIS IN THIS EXACT FORMAT:

## ⚙️ OPERATIONS EXPERT ANALYSIS
**Analyst:** Senior Operations Expert

### 1. INFRASTRUCTURE REQUIREMENTS
- Required training seats per year (cite extraction)
- Current capacity (cite)
- Buildout delta and required investments

### 2. TIMELINE REALISM
- Construction / procurement timelines
- Accreditation / staffing lead times
- Feasibility verdict for 3 / 5 / 8 year scenarios

### 3. IMPLEMENTATION PHASES
- Phase 1: [milestones, dependencies]
- Phase 2: [...]
- Phase 3: [...]

### 4. RESOURCE CONSTRAINTS & BOTTLENECKS
- Critical path tasks
- Vendor / supply chain constraints
- Change management or stakeholder risks

### 5. RISK MITIGATION PLAN
- Risk register (top 3 with probability/impact)
- Contingency actions per risk
- Leading indicators to monitor

### 6. CONFIDENCE ASSESSMENT
**Overall Confidence: [X]%**
- Data coverage: [X]% (gaps)
- Execution precedent: [X]% (cite similar programs)
- Resource certainty: [X]% (assumptions)

**What Would Increase Confidence:**
[Explicit data, site surveys, budget approvals, etc.]

═══════════════════════════════════════════════════
"""


async def analyze(query: str, extracted_facts: List[Dict[str, Any]], llm_client) -> Dict[str, Any]:
    """
    Operations Expert analysis with mandatory citation enforcement.
    """
    facts_formatted = format_extracted_facts(extracted_facts)
    
    prompt = f"""
{OPERATIONS_EXPERT_PERSONA}

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
        
        # Extract metadata (using similar logic to other agents)
        from qnwis.agents.base import (
            extract_citations_from_narrative,
            extract_data_gaps,
            extract_assumptions,
            extract_usage_tokens,
            resolve_response_model
        )
        from datetime import datetime
        
        citations = extract_citations_from_narrative(response, extracted_facts)
        data_gaps = extract_data_gaps(response)
        assumptions = extract_assumptions(response)
        facts_used = sorted({citation["metric"] for citation in citations})
        confidence = extract_confidence_from_response(response)
        tokens_in, tokens_out = extract_usage_tokens(response)
        model_name = resolve_response_model(response, llm_client)
        
        return {
            "agent_name": "operations_expert",
            "narrative": response,
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
    except Exception as exc:
        from datetime import datetime
        return {
            "agent_name": "operations_expert",
            "narrative": f"ERROR: {exc}",
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
    """Extract confidence percentage."""
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


class OperationsExpertAgent:  # pragma: no cover - compatibility shim
    """Legacy shim to retain prior import paths."""
    
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        raise RuntimeError(
            "OperationsExpertAgent class has been replaced. "
            "Use qnwis.agents.operations_expert.analyze(...) instead."
        )
