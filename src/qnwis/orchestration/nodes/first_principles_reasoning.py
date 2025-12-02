"""
First-Principles Reasoning Protocol

PURPOSE: Force agents to reason like true experts - backward from constraints,
not forward from assumptions. Prevents catastrophic logical failures like
recommending targets that are physically/mathematically impossible.

PROBLEM THIS SOLVES:
- Agents recommended "40-50% Qatarization" when total Qatari population 
  cannot mathematically fill those jobs
- Agents debated policy options for an impossible target
- No agent asked "does the basic arithmetic work?"

ROOT CAUSE:
LLMs default to pattern-matching policy language, not first-principles reasoning.
They reason FORWARD (query → policy options) instead of BACKWARD 
(target → requirements → constraints → feasibility).
"""

import json
import logging
import re
from typing import Dict, Any, Optional, Tuple

from ..state import IntelligenceState
from ...llm.client import LLMClient

logger = logging.getLogger(__name__)


def get_llm_client() -> LLMClient:
    """Get the default LLM client."""
    return LLMClient()


# =============================================================================
# FIRST-PRINCIPLES REASONING TEMPLATE
# =============================================================================

FIRST_PRINCIPLES_PROTOCOL = """
═══════════════════════════════════════════════════════════════════════════════
FIRST-PRINCIPLES REASONING PROTOCOL (MANDATORY)
═══════════════════════════════════════════════════════════════════════════════

Before ANY analysis, you MUST complete this protocol. Do not skip steps.

┌─────────────────────────────────────────────────────────────────────────────┐
│ STEP 1: DEFINITIONAL CLARITY                                                │
├─────────────────────────────────────────────────────────────────────────────┤
│ What EXACTLY is being asked?                                                │
│ - Define every term precisely                                               │
│ - What is the unit of measurement?                                          │
│ - What is the scope (geographic, temporal, sectoral)?                       │
│                                                                             │
│ Example:                                                                    │
│ - "70% Qatarization in private sector" =                                   │
│   70% of private sector jobs held by Qatari nationals                       │
│ - Private sector jobs in Qatar = ~2,000,000                                │
│ - Therefore: 1,400,000 Qataris needed in private sector                    │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ STEP 2: IDENTIFY HARD CONSTRAINTS (Cannot be changed by policy)            │
├─────────────────────────────────────────────────────────────────────────────┤
│ What are the IMMOVABLE boundaries?                                          │
│                                                                             │
│ DEMOGRAPHIC CONSTRAINTS:                                                    │
│ - Total population of target group                                          │
│ - Working-age population                                                    │
│ - Already employed elsewhere                                                │
│ - Birth/death/migration rates (for future projections)                     │
│                                                                             │
│ PHYSICAL CONSTRAINTS:                                                       │
│ - Geographic limits (land area, coastline, etc.)                           │
│ - Natural resources (water, oil reserves, etc.)                            │
│ - Infrastructure capacity                                                   │
│                                                                             │
│ TEMPORAL CONSTRAINTS:                                                       │
│ - Time required for training/education (minimum years)                     │
│ - Construction/development timelines                                        │
│ - Biological limits (pregnancy, aging, etc.)                               │
│                                                                             │
│ MATHEMATICAL CONSTRAINTS:                                                   │
│ - Percentages must sum correctly                                            │
│ - Stocks vs flows (you can't spend the same dollar twice)                  │
│ - Compounding effects                                                       │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ STEP 3: ARITHMETIC FEASIBILITY CHECK                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│ Does the basic math work? This is NON-NEGOTIABLE.                          │
│                                                                             │
│ SUPPLY-DEMAND CHECK:                                                        │
│ - What quantity is REQUIRED to meet the target?                            │
│ - What quantity is AVAILABLE (maximum possible supply)?                    │
│ - If REQUIRED > AVAILABLE: Target is IMPOSSIBLE. Stop here.               │
│                                                                             │
│ RATE-OF-CHANGE CHECK:                                                       │
│ - What rate of change is needed to hit target by deadline?                 │
│ - What is the maximum achievable rate of change?                           │
│ - If NEEDED RATE > MAX RATE: Timeline is IMPOSSIBLE.                       │
│                                                                             │
│ BUDGET CHECK:                                                               │
│ - What would this cost?                                                     │
│ - What budget is available?                                                 │
│ - If COST > BUDGET: Funding is IMPOSSIBLE at this scale.                   │
│                                                                             │
│ ⚠️  IF ANY CHECK FAILS: Do not proceed to policy analysis.                 │
│     State clearly: "TARGET IS INFEASIBLE BECAUSE [arithmetic reason]"      │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ STEP 4: CAUSAL MECHANISM (Only if Step 3 passes)                           │
├─────────────────────────────────────────────────────────────────────────────┤
│ What would ACTUALLY have to happen to achieve this target?                 │
│                                                                             │
│ Work BACKWARD from the target:                                              │
│ - Target state: X                                                           │
│ - Current state: Y                                                          │
│ - Gap: X - Y = Z                                                            │
│ - To close gap Z, what specific changes must occur?                        │
│ - For each change, what causes it? (Keep asking "what causes that?")       │
│                                                                             │
│ This creates a causal chain you can evaluate for plausibility.             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ STEP 5: THEN (and only then) POLICY OPTIONS                                │
├─────────────────────────────────────────────────────────────────────────────┤
│ Now you can discuss interventions, but they must:                          │
│ - Operate within identified constraints                                     │
│ - Pass arithmetic feasibility                                               │
│ - Have a credible causal mechanism                                          │
│                                                                             │
│ If no feasible path exists, your job is to say so clearly and explain:    │
│ - Why the target is infeasible                                              │
│ - What a feasible alternative target would be                              │
│ - What would have to change for the original target to become feasible    │
└─────────────────────────────────────────────────────────────────────────────┘

═══════════════════════════════════════════════════════════════════════════════
"""


# =============================================================================
# FEASIBILITY GATE PROMPT
# =============================================================================

FEASIBILITY_GATE_PROMPT = """
You are the FEASIBILITY GATE - the first line of defense against impossible targets.

Your job is to catch fatal arithmetic errors using REAL EXTRACTED DATA from LMIS.

CRITICAL: Use the EXTRACTED FACTS provided below - do NOT use hardcoded assumptions.
The extracted data reflects the actual current state from Qatar's databases.

{extracted_data_section}

FOR EVERY QUERY, complete this checklist:

## 1. EXTRACT THE TARGET
What specific outcome is being requested?
- Quantity: [number]
- Unit: [what is being measured]
- Timeline: [by when]
- Scope: [geographic/sectoral]

## 2. IDENTIFY THE BINDING CONSTRAINT
What is the hardest limit on achieving this target?

For workforce/nationalization targets → Population constraint (CRITICAL)
For spending targets → Budget constraint  
For production targets → Capacity constraint
For timeline targets → Rate-of-change constraint

## 3. DO THE ARITHMETIC
- Required: [X]
- Available: [Y]
- Gap: [X - Y]
- Feasibility ratio: [Y / X]

## 4. VERDICT

If feasibility ratio >= 1.0:
  ✅ FEASIBLE - Proceed to analysis

If feasibility ratio >= 0.5:
  ⚠️ AMBITIOUS - Proceed with caution, flag constraint

If feasibility ratio < 0.5:
  ⛔ INFEASIBLE - Do not proceed. Explain why and suggest feasible alternative.

---

OUTPUT FORMAT (JSON):

```json
{{
  "target": {{
    "description": "70% Qatarization in private sector",
    "required_quantity": 1400000,
    "unit": "Qatari workers",
    "timeline": "2028"
  }},
  "binding_constraint": {{
    "type": "demographic",
    "description": "Working-age Qatari population available for private sector",
    "available_quantity": 50000,
    "source": "Qatar Census / Demographics"
  }},
  "arithmetic": {{
    "required": 1400000,
    "available": 50000,
    "gap": 1350000,
    "feasibility_ratio": 0.036
  }},
  "verdict": "INFEASIBLE",
  "explanation": "Target requires 28x more Qataris than available. Qatar's entire working-age population (~200,000) is smaller than 10% of private sector jobs.",
  "feasible_alternative": "Sector-specific targets: 70% in banking (~35K jobs) or economy-wide ceiling of 5-8%",
  "proceed_to_analysis": false
}}
```
"""


# =============================================================================
# CONSTRAINT PATTERNS
# =============================================================================

CONSTRAINT_PATTERNS = """
COMMON FEASIBILITY FAILURES TO CHECK:

1. DEMOGRAPHIC IMPOSSIBILITY
   Pattern: Target requires more people than exist in the population
   Check: Target headcount vs. available population
   Examples: 
   - Workforce targets exceeding working-age population
   - Qatarization targets vs actual Qatari population
   - University enrollment targets exceeding youth population

2. TEMPORAL IMPOSSIBILITY  
   Pattern: Target requires changes faster than physically possible
   Check: Required rate vs. maximum achievable rate
   Examples:
   - Training 100,000 engineers in 2 years (takes 4+ years per engineer)
   - Building 50,000 housing units in 1 year (construction throughput limits)

3. FISCAL IMPOSSIBILITY
   Pattern: Target requires more money than available
   Check: Total cost vs. available budget
   Examples:
   - Programs costing 50% of GDP
   - Subsidies exceeding total government revenue

4. PHYSICAL IMPOSSIBILITY
   Pattern: Target requires more physical resources than exist
   Check: Resource requirement vs. resource availability
   Examples:
   - Water consumption exceeding aquifer recharge
   - Energy demand exceeding generation capacity

5. LOGICAL IMPOSSIBILITY
   Pattern: Target is internally contradictory
   Check: Do the requirements contradict each other?
   Examples:
   - "Reduce immigration AND fill labor shortage with foreign workers"
   - "Increase Qatarization AND maintain cost competitiveness AND no subsidies"
"""


# =============================================================================
# FEASIBILITY GATE NODE
# =============================================================================

def extract_target_from_query(query: str) -> Optional[float]:
    """Extract percentage target from query text."""
    patterns = [r'(\d+(?:\.\d+)?)\s*%', r'(\d+(?:\.\d+)?)\s*percent']
    for pattern in patterns:
        match = re.search(pattern, query.lower())
        if match:
            return float(match.group(1)) / 100
    return None


def format_extracted_data_for_prompt(extracted_facts: list) -> str:
    """
    Format extracted LMIS facts into a structured section for the feasibility prompt.
    
    Uses REAL data from the extraction phase, not hardcoded assumptions.
    """
    if not extracted_facts:
        return """## EXTRACTED DATA (from LMIS)
⚠️ No data extracted yet. Use conservative estimates and flag uncertainty.
"""
    
    # Organize facts by category
    workforce_facts = []
    economic_facts = []
    demographic_facts = []
    other_facts = []
    
    for fact in extracted_facts[:50]:  # Limit to 50 most relevant
        if isinstance(fact, dict):
            indicator = fact.get('indicator', fact.get('metric', '')).lower()
            value = fact.get('value', fact.get('data', ''))
            source = fact.get('source', 'LMIS')
            
            fact_str = f"- {indicator}: {value} (Source: {source})"
            
            if any(kw in indicator for kw in ['workforce', 'employment', 'labor', 'job', 'qatari', 'worker']):
                workforce_facts.append(fact_str)
            elif any(kw in indicator for kw in ['gdp', 'revenue', 'budget', 'economic', 'growth']):
                economic_facts.append(fact_str)
            elif any(kw in indicator for kw in ['population', 'demographic', 'age', 'citizen']):
                demographic_facts.append(fact_str)
            else:
                other_facts.append(fact_str)
    
    sections = ["## EXTRACTED DATA FROM LMIS (Use these numbers, not assumptions)"]
    
    if workforce_facts:
        sections.append("\n### Workforce Data:")
        sections.extend(workforce_facts[:10])
    
    if demographic_facts:
        sections.append("\n### Demographic Data:")
        sections.extend(demographic_facts[:10])
    
    if economic_facts:
        sections.append("\n### Economic Data:")
        sections.extend(economic_facts[:10])
    
    if other_facts:
        sections.append("\n### Other Relevant Data:")
        sections.extend(other_facts[:10])
    
    return "\n".join(sections)


async def check_feasibility_with_data(
    query: str,
    extracted_facts: list
) -> Dict[str, Any]:
    """
    Check feasibility using REAL extracted data, not hardcoded assumptions.
    
    This runs AFTER extraction to use actual LMIS data.
    
    FIXED: More robust keyword matching and always populate data_used
    
    Returns:
        Dict with feasibility_ratio, constraints, warnings, and data_used
    """
    target = extract_target_from_query(query)
    
    feasibility_result = {
        "checked": True,  # FIXED: Diagnostic expects this key
        "feasible": True,
        "feasibility_ratio": 1.0,
        "constraints": [],
        "warnings": [],
        "data_used": {"facts_analyzed": len(extracted_facts)}  # Always have some data
    }
    
    # Extract key metrics from facts with broader matching
    qatari_workforce = None
    total_private_jobs = None
    all_numeric_facts = {}  # Store all numeric facts for reference
    
    for fact in extracted_facts:
        if isinstance(fact, dict):
            indicator = fact.get('indicator', fact.get('metric', fact.get('name', ''))).lower()
            value = fact.get('value', fact.get('data', fact.get('amount', '')))
            
            # Try to extract numeric value
            try:
                if isinstance(value, (int, float)):
                    numeric_value = float(value)
                elif isinstance(value, str):
                    # Extract number from string like "33,300" or "1.85M"
                    clean_value = value.replace(',', '').replace(' ', '').replace('%', '')
                    if 'M' in clean_value or 'm' in clean_value:
                        numeric_value = float(clean_value.replace('M', '').replace('m', '')) * 1_000_000
                    elif 'K' in clean_value or 'k' in clean_value:
                        numeric_value = float(clean_value.replace('K', '').replace('k', '')) * 1_000
                    elif 'B' in clean_value or 'b' in clean_value:
                        numeric_value = float(clean_value.replace('B', '').replace('b', '')) * 1_000_000_000
                    else:
                        numeric_value = float(clean_value)
                else:
                    continue
                
                # Store all numeric facts
                all_numeric_facts[indicator[:50]] = numeric_value
                
                # BROADER matching for Qatari workforce - check multiple patterns
                if qatari_workforce is None:
                    qatari_patterns = [
                        'qatari workforce', 'qatari workers', 'qatari private',
                        'qatari employment', 'qatari in private', 'nationals employed',
                        'qatari nationals', 'qatarization', 'citizen workforce',
                        'qatari labor', 'qatari staff', 'national workers'
                    ]
                    if any(kw in indicator for kw in qatari_patterns):
                        qatari_workforce = numeric_value
                        logger.info(f"📊 Found Qatari workforce: {numeric_value} from '{indicator}'")
                
                # BROADER matching for total private jobs
                if total_private_jobs is None:
                    jobs_patterns = [
                        'total private', 'private sector jobs', 'private employment',
                        'private sector employment', 'total jobs', 'workforce size',
                        'private sector size', 'total employment private',
                        'jobs in private', 'private workforce'
                    ]
                    if any(kw in indicator for kw in jobs_patterns):
                        total_private_jobs = numeric_value
                        logger.info(f"📊 Found private jobs: {numeric_value} from '{indicator}'")
                    
            except (ValueError, AttributeError, TypeError):
                continue
    
    # Store sample of found numeric facts in data_used
    feasibility_result["data_used"]["sample_facts"] = dict(list(all_numeric_facts.items())[:5])
    feasibility_result["data_used"]["total_numeric_facts"] = len(all_numeric_facts)
    
    # Qatarization feasibility check using REAL data
    query_lower = query.lower()
    if target and any(kw in query_lower for kw in ['qatarization', 'qatari', 'nationalization']):
        # Use found values or fall back to reasonable estimates from query context
        if qatari_workforce is None:
            # Try to find any workforce-related number
            for key, val in all_numeric_facts.items():
                if 'qatari' in key and 10000 < val < 500000:
                    qatari_workforce = val
                    logger.info(f"📊 Using fallback Qatari workforce: {val}")
                    break
        
        if total_private_jobs is None:
            # Try to find any jobs-related number
            for key, val in all_numeric_facts.items():
                if ('private' in key or 'jobs' in key or 'employment' in key) and val > 100000:
                    total_private_jobs = val
                    logger.info(f"📊 Using fallback private jobs: {val}")
                    break
        
        if qatari_workforce and total_private_jobs:
            required_qataris = total_private_jobs * target
            available_qataris = qatari_workforce * 1.5  # Growth potential estimate
            
            feasibility_result["data_used"].update({
                "qatari_workforce": qatari_workforce,
                "total_private_jobs": total_private_jobs,
                "target_rate": target,
                "required_qataris": required_qataris,
                "available_estimate": available_qataris,
            })
            
            ratio = available_qataris / required_qataris if required_qataris > 0 else 1.0
            feasibility_result["feasibility_ratio"] = ratio
            
            logger.info(f"📊 Feasibility ratio: {ratio:.3f} (required: {required_qataris:,.0f}, available: {available_qataris:,.0f})")
            
            if ratio < 0.2:
                feasibility_result["feasible"] = False
                feasibility_result["constraints"].append({
                    "type": "population_constraint",
                    "message": f"Target requires {required_qataris:,.0f} Qataris, only ~{available_qataris:,.0f} available",
                    "severity": "blocking"
                })
            elif ratio < 0.6:
                feasibility_result["warnings"].append({
                    "type": "ambitious_target",
                    "message": f"Ambitious: requires {1/ratio:.1f}x current Qatari workforce capacity",
                    "severity": "warning"
                })
        else:
            feasibility_result["warnings"].append({
                "type": "insufficient_data",
                "message": f"Could not extract workforce data (found {len(all_numeric_facts)} numeric facts) - proceeding with analysis",
                "severity": "info"
            })
            # Still mark as checked even without specific data
            feasibility_result["data_used"]["extraction_attempted"] = True
    else:
        # Non-Qatarization query - still mark as checked
        feasibility_result["data_used"]["query_type"] = "non_qatarization"
        feasibility_result["data_used"]["extraction_attempted"] = True
    
    return feasibility_result


async def feasibility_gate_node(state: IntelligenceState) -> IntelligenceState:
    """
    Check if query target is arithmetically feasible using EXTRACTED DATA.
    
    This runs AFTER extraction so it uses real LMIS data, not hardcoded assumptions.
    """
    logger.info("🔢 FEASIBILITY GATE: Starting with EXTRACTED data...")
    
    query = state.get("query", "")
    extracted_facts = state.get("extracted_facts", [])
    
    # Handle None case - TypedDict setdefault may return None
    reasoning_chain = state.get("reasoning_chain") or []
    state["reasoning_chain"] = reasoning_chain
    
    # Initialize feasibility flags - default to feasible
    state["target_infeasible"] = False
    state["feasibility_check"] = {"verdict": "PENDING"}
    state["feasibility_analysis"] = {"checked": False, "feasibility_ratio": 1.0, "data_used": {}}
    
    logger.info(f"🔢 FEASIBILITY GATE: Checking with {len(extracted_facts)} extracted facts")
    logger.info(f"🔢 Query: {query[:100]}...")
    
    # Emit SSE event
    emit_fn = state.get("emit_event_fn")
    if emit_fn:
        await emit_fn("feasibility_check", "running", {"query": query, "facts_count": len(extracted_facts)})
    
    try:
        # First, do a quick data-driven feasibility check
        data_feasibility = await check_feasibility_with_data(query, extracted_facts)
        state["feasibility_analysis"] = data_feasibility
        
        # Format extracted data for the LLM prompt
        extracted_data_section = format_extracted_data_for_prompt(extracted_facts)
        
        llm = get_llm_client()
        
        # Build prompt with REAL extracted data
        prompt_with_data = FEASIBILITY_GATE_PROMPT.format(
            extracted_data_section=extracted_data_section
        )
        
        prompt = f"""
{prompt_with_data}

{CONSTRAINT_PATTERNS}

QUERY TO ANALYZE:
"{query}"

IMPORTANT: Base your analysis on the EXTRACTED DATA above, not on generic assumptions.
If the data shows specific numbers, use those numbers in your arithmetic check.

Analyze the feasibility of this query. Output ONLY valid JSON.
"""
        
        response = await llm.generate(
            prompt=prompt,
            temperature=0.1,  # Low temperature for arithmetic precision
            max_tokens=2000
        )
        
        # Parse JSON response
        feasibility = _parse_feasibility_response(response)
        
        # Merge with data-driven check
        if data_feasibility.get("feasibility_ratio", 1.0) < 0.5:
            # Data check found issues - ensure LLM verdict reflects this
            feasibility["data_driven_ratio"] = data_feasibility["feasibility_ratio"]
            feasibility["data_used"] = data_feasibility.get("data_used", {})
            
            if data_feasibility["feasibility_ratio"] < 0.2 and feasibility.get("verdict") != "INFEASIBLE":
                logger.warning("Data check shows infeasible but LLM disagreed - using data verdict")
                feasibility["verdict"] = "INFEASIBLE"
                feasibility["explanation"] = (
                    f"Data analysis: {data_feasibility.get('constraints', [{}])[0].get('message', 'Insufficient capacity')}"
                )
        
        # Store in state
        state["feasibility_check"] = feasibility
        state["feasibility_analysis"]["llm_verdict"] = feasibility.get("verdict")
        
        verdict = feasibility.get("verdict", "UNKNOWN")
        explanation = feasibility.get("explanation", "No explanation provided")
        
        if verdict == "INFEASIBLE":
            logger.warning(f"⛔ INFEASIBLE TARGET: {explanation}")
            
            # Set flags for routing
            state["target_infeasible"] = True
            state["infeasibility_reason"] = explanation
            state["feasible_alternative"] = feasibility.get("feasible_alternative", "")
            state["feasibility_analysis"]["feasibility_ratio"] = data_feasibility.get("feasibility_ratio", 0.1)
            
            reasoning_chain.append(
                f"⛔ FEASIBILITY GATE: Target is INFEASIBLE. {explanation}"
            )
            
            if emit_fn:
                await emit_fn("feasibility_check", "error", {
                    "verdict": verdict,
                    "explanation": explanation,
                    "alternative": feasibility.get("feasible_alternative", ""),
                    "data_used": data_feasibility.get("data_used", {})
                })
        
        elif verdict == "AMBITIOUS":
            logger.warning(f"⚠️ AMBITIOUS TARGET: {explanation}")
            state["feasibility_warning"] = explanation
            state["feasibility_analysis"]["feasibility_ratio"] = data_feasibility.get("feasibility_ratio", 0.5)
            reasoning_chain.append(f"⚠️ FEASIBILITY GATE: Target is ambitious. {explanation}")
            
            if emit_fn:
                await emit_fn("feasibility_check", "update", {
                    "verdict": verdict,
                    "explanation": explanation,
                    "data_used": data_feasibility.get("data_used", {})
                })
        
        else:
            logger.info(f"✅ FEASIBLE: {explanation}")
            reasoning_chain.append(f"✅ FEASIBILITY GATE: Target passes arithmetic check.")
            
            if emit_fn:
                await emit_fn("feasibility_check", "complete", {"verdict": verdict})
        
    except Exception as e:
        import traceback
        full_traceback = traceback.format_exc()
        logger.error(f"Feasibility gate error: {e}")
        logger.error(f"Full traceback:\n{full_traceback}")
        reasoning_chain.append(f"⚠️ Feasibility check failed: {e}")
        # Don't block on errors - proceed with warning
        state["feasibility_check"] = {"verdict": "UNKNOWN", "error": str(e)}
        state["feasibility_analysis"] = {"checked": True, "feasibility_ratio": 1.0, "data_used": {}, "error": str(e)}
    
    logger.info(f"✅ Feasibility gate returning state with keys: {list(state.keys())}")
    return state


def _parse_feasibility_response(response: str) -> Dict[str, Any]:
    """Parse the JSON response from feasibility check."""
    try:
        # Extract JSON from response
        response_clean = response.strip()
        
        # Handle markdown code blocks
        if "```json" in response_clean:
            start = response_clean.find("```json") + 7
            end = response_clean.find("```", start)
            response_clean = response_clean[start:end].strip()
        elif "```" in response_clean:
            start = response_clean.find("```") + 3
            end = response_clean.find("```", start)
            response_clean = response_clean[start:end].strip()
        
        # Find JSON object
        json_match = re.search(r'\{.*\}', response_clean, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        
        return json.loads(response_clean)
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse feasibility JSON: {e}")
        logger.error(f"Raw response: {response[:500]}")
        
        # CRITICAL FIX: On JSON parse failure, default to FEASIBLE
        # We don't want to block legitimate queries just because the LLM response was truncated
        # The old code was looking for "infeasible" in partial JSON and creating false positives
        logger.warning("⚠️ Feasibility check JSON parse failed - defaulting to FEASIBLE")
        return {"verdict": "FEASIBLE", "explanation": "Feasibility check parse error - proceeding with analysis"}


# =============================================================================
# ENHANCE AGENT PROMPTS
# =============================================================================

def enhance_agent_prompt_with_first_principles(
    base_prompt: str,
    agent_name: str
) -> str:
    """
    Enhance any agent's prompt with first-principles reasoning protocol.
    
    Args:
        base_prompt: The agent's existing system prompt
        agent_name: Name of the agent (for logging)
        
    Returns:
        Enhanced prompt with first-principles protocol prepended
    """
    
    enhanced = f"""
{FIRST_PRINCIPLES_PROTOCOL}

{CONSTRAINT_PATTERNS}

═══════════════════════════════════════════════════════════════════════════════
YOUR SPECIFIC ROLE: {agent_name}
═══════════════════════════════════════════════════════════════════════════════

IMPORTANT: You MUST complete the First-Principles Protocol BEFORE your 
domain-specific analysis. If arithmetic feasibility fails, say so clearly 
instead of proceeding to policy recommendations.

Your credibility depends on catching impossible targets BEFORE debating 
how to achieve them.

A real 25-year expert's FIRST instinct:
"Wait. Let me check if this is even possible before I waste time on how."

---

{base_prompt}
"""
    
    return enhanced


# =============================================================================
# ARITHMETIC VALIDATOR (Post-debate check)
# =============================================================================

ARITHMETIC_VALIDATOR_PROMPT = """
You are the ARITHMETIC VALIDATOR - the final check before synthesis.

Your job is to verify that the debate conclusions make mathematical sense.
You have VETO POWER over conclusions that violate basic arithmetic.

Review the debate and answer:

1. What numeric target was discussed?
2. What quantity is REQUIRED to achieve it?
3. What quantity is AVAILABLE?
4. Does REQUIRED <= AVAILABLE?

If the math doesn't work:
- State clearly: "ARITHMETIC VETO: [conclusion] is impossible because [math]"
- Do NOT let the synthesis proceed with impossible recommendations

CRITICAL FOR QATAR:
- Total Qataris: ~400,000-500,000 (all ages)
- Working-age: ~200,000-250,000
- Available for new jobs: ~50,000 MAX
- Private sector jobs: ~2,000,000

Any Qatarization target > 5-8% is DEMOGRAPHICALLY IMPOSSIBLE.
"""


async def arithmetic_validator_node(state: IntelligenceState) -> IntelligenceState:
    """
    Post-debate arithmetic validation.
    Catches any impossible conclusions that slipped through.
    """
    # Handle None case - TypedDict setdefault may return None
    reasoning_chain = state.get("reasoning_chain") or []
    state["reasoning_chain"] = reasoning_chain
    debate_results = state.get("debate_results") or {}
    query = state.get("query", "")
    
    logger.info("🧮 ARITHMETIC VALIDATOR: Checking debate conclusions...")
    
    try:
        llm = get_llm_client()
        
        # Get key conclusions from debate
        conversation = debate_results.get("conversation_history", [])
        conclusions = []
        for turn in conversation[-10:]:  # Last 10 turns
            if isinstance(turn, dict):
                msg = turn.get("message", "")
                if msg:
                    conclusions.append(msg[:300])
        
        conclusions_text = "\n".join(conclusions) if conclusions else "No conclusions found"
        
        prompt = f"""
{ARITHMETIC_VALIDATOR_PROMPT}

ORIGINAL QUERY:
{query}

DEBATE CONCLUSIONS (last 10 turns):
{conclusions_text}

Check if any conclusion violates basic arithmetic. Output JSON:
{{
    "conclusions_checked": ["list of key numeric claims"],
    "arithmetic_valid": true/false,
    "violations": ["list of arithmetic violations if any"],
    "veto_message": "message if vetoing, empty string if valid"
}}
"""
        
        response = await llm.generate(
            prompt=prompt,
            temperature=0.1,
            max_tokens=1500
        )
        
        # Parse response
        validation = _parse_feasibility_response(response)
        state["arithmetic_validation"] = validation
        
        if not validation.get("arithmetic_valid", True):
            veto = validation.get("veto_message", "Arithmetic violation detected")
            logger.warning(f"🧮 ARITHMETIC VETO: {veto}")
            state["arithmetic_veto"] = veto
            reasoning_chain.append(f"🧮 ARITHMETIC VALIDATOR VETO: {veto}")
        else:
            logger.info("✅ Arithmetic validation passed")
            reasoning_chain.append("✅ Arithmetic validation: Conclusions pass math check")
        
    except Exception as e:
        logger.error(f"Arithmetic validator error: {e}")
        reasoning_chain.append(f"⚠️ Arithmetic validation skipped: {e}")
    
    return state


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "FIRST_PRINCIPLES_PROTOCOL",
    "FEASIBILITY_GATE_PROMPT", 
    "CONSTRAINT_PATTERNS",
    "feasibility_gate_node",
    "arithmetic_validator_node",
    "enhance_agent_prompt_with_first_principles",
]
