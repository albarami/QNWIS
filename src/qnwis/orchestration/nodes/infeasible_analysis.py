"""
Infeasible Analysis Node

For queries where target is mathematically impossible,
provide useful analysis instead of just rejecting.

This node runs when the feasibility check determines a target
is infeasible (ratio < 0.2) but we still want to provide
actionable intelligence to ministers.
"""

import json
import logging
from typing import Dict, Any

from ..state import IntelligenceState
from ...llm.client import LLMClient

logger = logging.getLogger(__name__)


def get_llm_client() -> LLMClient:
    """Get the default LLM client."""
    return LLMClient()


def format_data_sources(data_used: Dict) -> str:
    """Format data sources for citation in output."""
    if not data_used:
        return "- No specific data sources cited"
    
    lines = []
    for key, value in data_used.items():
        if isinstance(value, (int, float)):
            lines.append(f"- {key.replace('_', ' ').title()}: {value:,.0f}")
        else:
            lines.append(f"- {key.replace('_', ' ').title()}: {value}")
    
    return "\n".join(lines) if lines else "- See extracted facts above"


INFEASIBLE_ANALYSIS_PROMPT = """
You are a senior policy advisor providing analysis for a target that has been 
identified as MATHEMATICALLY CONSTRAINED by the feasibility check.

Your job is NOT to simply reject the query, but to provide:
1. Clear explanation of WHY the target is constrained (with numbers)
2. What IS achievable given the constraints
3. What would need to change for the original target to become feasible
4. A revised, realistic recommendation

QUERY: {query}

FEASIBILITY ANALYSIS:
- Feasibility Ratio: {feasibility_ratio}
- Constraints: {constraints}
- Data Used: {data_used}

EXTRACTED FACTS:
{extracted_facts}

Provide ministerial-grade analysis in the following format:

# POLICY FEASIBILITY ANALYSIS

## ⚠️ TARGET ASSESSMENT: MATHEMATICALLY CONSTRAINED

### Why This Target Is Constrained
[Explain with specific numbers from the data why the target cannot be met]

### What Is Achievable
[Given current constraints, what is the maximum realistic target with timeline]

### What Would Need to Change
[Policy changes that could expand the ceiling]

### Recommendation
[Revised target with implementation approach]

### Data Sources
[List the data points used in this analysis]

Be specific with numbers. Use the extracted facts. Provide actionable alternatives.
"""


async def infeasible_analysis_node(state: IntelligenceState) -> IntelligenceState:
    """
    Analyze infeasible target and provide actionable alternatives.
    
    Even for truly impossible targets, provide useful analysis to ministers
    including what IS achievable and what would need to change.
    """
    logger.info("📊 INFEASIBLE ANALYSIS: Starting analysis for constrained target...")
    
    query = state.get("query", "")
    extracted_facts = state.get("extracted_facts", [])
    feasibility = state.get("feasibility_analysis", {})
    feasibility_check = state.get("feasibility_check", {})
    
    # Handle None case
    reasoning_chain = state.get("reasoning_chain") or []
    state["reasoning_chain"] = reasoning_chain
    
    # Emit SSE event
    emit_fn = state.get("emit_event_fn")
    if emit_fn:
        await emit_fn("infeasible_analysis", "running", {"query": query[:100]})
    
    try:
        llm = get_llm_client()
        
        # Format extracted facts (limit to 30 most relevant)
        facts_str = ""
        if extracted_facts:
            facts_lines = []
            for fact in extracted_facts[:30]:
                if isinstance(fact, dict):
                    indicator = fact.get('indicator', fact.get('metric', 'Data'))
                    value = fact.get('value', fact.get('data', ''))
                    source = fact.get('source', '')
                    facts_lines.append(f"- {indicator}: {value}" + (f" (Source: {source})" if source else ""))
            facts_str = "\n".join(facts_lines)
        else:
            facts_str = "No facts extracted."
        
        # Get constraint details
        constraints = feasibility.get("constraints", [])
        constraints_str = json.dumps(constraints, indent=2) if constraints else "No specific constraints identified"
        
        data_used = feasibility.get("data_used", {})
        data_used_str = json.dumps(data_used, indent=2) if data_used else "No specific data cited"
        
        feasibility_ratio = feasibility.get("feasibility_ratio", 0.1)
        
        prompt = INFEASIBLE_ANALYSIS_PROMPT.format(
            query=query,
            feasibility_ratio=f"{feasibility_ratio:.2f}" if isinstance(feasibility_ratio, float) else str(feasibility_ratio),
            constraints=constraints_str,
            data_used=data_used_str,
            extracted_facts=facts_str
        )
        
        response = await llm.generate(
            prompt=prompt,
            temperature=0.3,  # Some creativity for alternatives
            max_tokens=3000
        )
        
        # Build final synthesis with warning banner
        infeasibility_reason = state.get("infeasibility_reason", "Target exceeds available capacity")
        feasible_alt = state.get("feasible_alternative", "")
        
        synthesis = f"""
# POLICY FEASIBILITY ANALYSIS

## ⚠️ TARGET ASSESSMENT: MATHEMATICALLY CONSTRAINED

> **Note:** The original target has been identified as exceeding available capacity.
> This analysis provides what IS achievable and recommended alternatives.

### Original Query
{query}

### Feasibility Finding
- **Feasibility Ratio:** {feasibility_ratio:.2f} (below 0.2 threshold)
- **Core Constraint:** {infeasibility_reason}
{f"- **Suggested Alternative:** {feasible_alt}" if feasible_alt else ""}

---

{response}

---

## DATA SOURCES USED
{format_data_sources(data_used)}

## METHODOLOGY
This analysis was generated using the QNWIS First-Principles Reasoning Protocol,
which validates targets against extracted LMIS data before proceeding with analysis.
"""
        
        state["final_synthesis"] = synthesis
        state["meta_synthesis"] = synthesis
        state["target_constrained"] = True
        state["infeasible_analysis_complete"] = True
        
        reasoning_chain.append(
            f"📊 INFEASIBLE ANALYSIS: Provided alternative recommendations for constrained target"
        )
        
        logger.info("✅ Infeasible analysis complete - provided actionable alternatives")
        
        if emit_fn:
            await emit_fn("infeasible_analysis", "complete", {
                "synthesis_length": len(synthesis),
                "feasibility_ratio": feasibility_ratio
            })
        
    except Exception as e:
        logger.error(f"Infeasible analysis error: {e}", exc_info=True)
        
        # Fallback synthesis
        fallback = f"""
# POLICY FEASIBILITY ANALYSIS

## ⚠️ TARGET ASSESSMENT: MATHEMATICALLY CONSTRAINED

The requested target has been identified as exceeding available capacity based on 
extracted LMIS data.

**Original Query:** {query}

**Finding:** {state.get("infeasibility_reason", "Target exceeds available capacity")}

**Recommendation:** Please consult with domain experts to identify achievable 
alternatives that work within existing constraints.

*Analysis generation encountered an error: {e}*
"""
        state["final_synthesis"] = fallback
        state["meta_synthesis"] = fallback
        state["target_constrained"] = True
        
        reasoning_chain.append(f"⚠️ Infeasible analysis error: {e}")
    
    return state


__all__ = ["infeasible_analysis_node"]

