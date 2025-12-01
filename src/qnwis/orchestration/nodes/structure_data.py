"""
Data Structuring Node.

Uses LLM to structure extracted facts into calculation inputs.
THE LLM DOES NOT GENERATE NUMBERS - it identifies and organizes existing numbers.

This node bridges data extraction and calculation:
- Input: Raw extracted facts with values and sources
- Output: Structured JSON matching FinancialModelInput schema
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

from ..state import IntelligenceState

logger = logging.getLogger(__name__)


STRUCTURE_PROMPT = """You are a Data Structurer. Your job is to organize extracted facts into 
structured inputs for financial modeling.

CRITICAL RULES:
1. You DO NOT generate any numbers
2. You ONLY use numbers from the extracted facts below
3. Every number MUST have a citation: [Source: X]
4. If a number is not in the facts, write "NOT_AVAILABLE"
5. If you must estimate, clearly label it: [ESTIMATE: rationale]

QUERY:
{query}

EXTRACTED FACTS:
{extracted_facts}

OPTIONS TO ANALYZE:
{options}

TASK: Structure the financial inputs for each option.

For each option, extract or note as NOT_AVAILABLE:

1. INITIAL INVESTMENT
   - Total capital required (Year 0-2)
   - Source of this figure
   
2. ANNUAL REVENUE PROJECTIONS (Years 1-10)
   - Base revenue estimate
   - Growth rate (if mentioned)
   - Source
   
3. ANNUAL OPERATING COSTS (Years 1-10)
   - Fixed costs
   - Variable costs
   - Source
   
4. DISCOUNT RATE
   - Appropriate rate for this context (government: 6-8%, corporate: 10-15%)
   - Justification

5. TIME HORIZON
   - Standard: 10 years
   - Or specific if mentioned in query

OUTPUT FORMAT - Respond with ONLY this JSON, no other text:
{{
  "options": [
    {{
      "name": "Option A name",
      "description": "Brief description",
      "initial_investment": {{
        "amount": 50000000000,
        "currency": "QAR",
        "source": "Ministry of Finance budget allocation",
        "confidence": 0.9
      }},
      "revenue_projections": [
        {{"year": 1, "amount": 1000000000, "source": "...", "confidence": 0.7}},
        {{"year": 2, "amount": 2000000000, "source": "...", "confidence": 0.7}}
      ],
      "cost_projections": [
        {{"year": 1, "amount": 500000000, "source": "...", "confidence": 0.8}}
      ],
      "growth_rate": {{"value": 0.15, "source": "Industry benchmark", "confidence": 0.6}},
      "data_gaps": ["No data on Year 5-10 costs", "Growth rate is estimated"],
      "assumptions": ["Assumed 15% annual growth based on DIFC precedent"]
    }}
  ],
  "discount_rate": {{
    "value": 0.08,
    "justification": "Qatar sovereign cost of capital",
    "source": "Central Bank of Qatar"
  }},
  "time_horizon_years": 10,
  "overall_data_quality": "MEDIUM",
  "critical_data_gaps": ["..."]
}}

REMEMBER: 
- If data is not in the extracted facts, say NOT_AVAILABLE
- Do not invent numbers
- Cite sources for every number
"""


async def structure_data_node(state: IntelligenceState) -> IntelligenceState:
    """
    Structure extracted data into calculation inputs.

    This node uses an LLM to identify and organize numbers from extracted facts.
    It does NOT generate new numbers.

    Args:
        state: Current intelligence state with extracted_facts

    Returns:
        Updated state with structured_inputs
    """
    from src.qnwis.llm.client import LLMClient

    logger.info("📊 Structuring extracted data for calculations...")

    query = state.get("query", "")
    extracted_facts = state.get("extracted_facts", [])

    # Identify options from query
    options = _identify_options(query)

    # Format facts for prompt
    facts_text = _format_facts(extracted_facts)

    # Build prompt
    prompt = STRUCTURE_PROMPT.format(
        query=query,
        extracted_facts=facts_text,
        options=json.dumps(options),
    )

    # Call LLM
    try:
        llm = LLMClient()
        response = await llm.generate_with_routing(
            prompt=prompt,
            task_type="extraction",
            temperature=0.1,  # Low temperature for structured output
            max_tokens=4000,
        )

        # Parse response
        structured_data = _parse_structured_response(response)
        state["structured_inputs"] = structured_data
        state["data_quality"] = structured_data.get("overall_data_quality", "UNKNOWN")
        state["data_gaps"] = structured_data.get("critical_data_gaps", [])

        # Count how many values we have vs NOT_AVAILABLE
        available_count, missing_count = _count_data_availability(structured_data)
        data_coverage = (
            available_count / (available_count + missing_count)
            if (available_count + missing_count) > 0
            else 0
        )

        logger.info(
            f"✅ Data structured successfully. Quality: {state['data_quality']}, "
            f"Coverage: {data_coverage:.0%}"
        )

    except Exception as e:
        logger.error(f"❌ Failed to structure data: {e}")
        state["structured_inputs"] = None
        state["data_quality"] = "FAILED"
        state["data_gaps"] = ["Failed to structure data"]

    state.setdefault("nodes_executed", []).append("structure_data")
    return state


def _identify_options(query: str) -> List[Dict[str, str]]:
    """Extract options being compared from the query."""
    options: List[Dict[str, str]] = []
    query_lower = query.lower()

    # Look for explicit "Option A / Option B" patterns
    if "option a" in query_lower or "option 1" in query_lower:
        options.append({"id": "A", "name": "Option A"})
    if "option b" in query_lower or "option 2" in query_lower:
        options.append({"id": "B", "name": "Option B"})

    # Look for "X vs Y" or "X or Y" patterns
    vs_pattern = r"(\w+(?:\s+\w+){0,3})\s+(?:vs\.?|versus|or)\s+(\w+(?:\s+\w+){0,3})"
    matches = re.findall(vs_pattern, query, re.IGNORECASE)

    for match in matches:
        option_a_name = match[0].strip()
        option_b_name = match[1].strip()
        # Avoid duplicates and short matches
        if len(option_a_name) > 2 and len(option_b_name) > 2:
            if not options:
                options.append({"id": "A", "name": option_a_name})
                options.append({"id": "B", "name": option_b_name})

    # Look for hub-type patterns common in Qatar context
    hub_patterns = [
        r"(financial\s+hub)",
        r"(logistics\s+hub)",
        r"(tech\s+hub)",
        r"(innovation\s+hub)",
        r"(knowledge\s+hub)",
    ]
    hub_matches = []
    for pattern in hub_patterns:
        if re.search(pattern, query, re.IGNORECASE):
            hub_matches.append(re.search(pattern, query, re.IGNORECASE).group(1))

    if len(hub_matches) >= 2 and not options:
        options.append({"id": "A", "name": hub_matches[0].title()})
        options.append({"id": "B", "name": hub_matches[1].title()})

    # Default if no options found
    if not options:
        options = [
            {"id": "A", "name": "Option A"},
            {"id": "B", "name": "Option B"},
        ]

    return options


def _format_facts(facts: List[Any]) -> str:
    """Format extracted facts for the prompt."""
    if not facts:
        return "No facts extracted."

    formatted = []
    for i, fact in enumerate(facts[:100], 1):  # Limit to first 100 facts
        if isinstance(fact, dict):
            source = fact.get("source", "Unknown")
            content = fact.get("content", fact.get("fact", fact.get("description", str(fact))))
            value = fact.get("value", "")
            metric = fact.get("metric", "")

            if value and metric:
                formatted.append(f"{i}. [{source}] {metric}: {value}")
            elif content:
                formatted.append(f"{i}. [{source}] {content}")
            else:
                formatted.append(f"{i}. [{source}] {str(fact)[:200]}")
        else:
            formatted.append(f"{i}. {str(fact)[:200]}")

    return "\n".join(formatted)


def _parse_structured_response(response: str) -> Dict[str, Any]:
    """Parse the LLM's structured response."""
    # Try to extract JSON from response
    # Look for JSON block (may be wrapped in markdown)
    cleaned = response.strip()

    # Remove markdown code blocks if present
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    # Try to find JSON object
    json_match = re.search(r"\{[\s\S]*\}", cleaned)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

    # Try parsing the whole cleaned response
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.warning(f"Could not parse structured response as JSON: {e}")

        # Return a minimal structure with error
        return {
            "options": [],
            "discount_rate": {"value": 0.08, "justification": "Default", "source": "Default"},
            "time_horizon_years": 10,
            "overall_data_quality": "FAILED",
            "critical_data_gaps": ["Failed to parse LLM response"],
            "parse_error": str(e),
            "raw_response": response[:500],
        }


def _count_data_availability(structured_data: Dict[str, Any]) -> tuple[int, int]:
    """Count available vs missing data points."""
    available = 0
    missing = 0

    def check_value(val: Any) -> None:
        nonlocal available, missing
        if val is None or val == "NOT_AVAILABLE" or val == "":
            missing += 1
        elif isinstance(val, (int, float)) and val != 0:
            available += 1
        elif isinstance(val, str) and val.strip():
            available += 1

    for option in structured_data.get("options", []):
        # Check investment
        inv = option.get("initial_investment", {})
        check_value(inv.get("amount"))

        # Check revenues
        for rev in option.get("revenue_projections", []):
            check_value(rev.get("amount"))

        # Check costs
        for cost in option.get("cost_projections", []):
            check_value(cost.get("amount"))

        # Check growth rate
        gr = option.get("growth_rate", {})
        check_value(gr.get("value"))

        # Count data gaps as missing
        missing += len(option.get("data_gaps", []))

    return available, missing


def convert_structured_to_model_input(
    structured_data: Dict[str, Any], option_index: int = 0
) -> Optional[Dict[str, Any]]:
    """
    Convert structured data to FinancialModelInput format.

    This is a helper function that can be called by the calculation node.

    Args:
        structured_data: Output from structure_data_node
        option_index: Which option to convert (0 or 1)

    Returns:
        Dictionary compatible with FinancialModelInput
    """
    options = structured_data.get("options", [])
    if not options or option_index >= len(options):
        return None

    option = options[option_index]
    discount_info = structured_data.get("discount_rate", {})
    time_horizon = structured_data.get("time_horizon_years", 10)

    # Build cash flows
    cash_flows = []

    # Year 0: Initial investment
    inv = option.get("initial_investment", {})
    if inv.get("amount") and inv.get("amount") != "NOT_AVAILABLE":
        cash_flows.append(
            {
                "year": 0,
                "investment": float(inv["amount"]),
                "revenue": 0,
                "operating_costs": 0,
                "source": inv.get("source", "Structured from facts"),
                "confidence": inv.get("confidence", 0.5),
            }
        )

    # Years 1-N: Revenue and costs
    revenue_by_year = {r["year"]: r for r in option.get("revenue_projections", [])}
    cost_by_year = {c["year"]: c for c in option.get("cost_projections", [])}

    # Get base values for projection
    growth_rate = 0.10  # Default
    gr_info = option.get("growth_rate", {})
    if gr_info.get("value") and gr_info.get("value") != "NOT_AVAILABLE":
        growth_rate = float(gr_info["value"])

    base_revenue = None
    base_cost = None

    if revenue_by_year:
        first_year = min(revenue_by_year.keys())
        base_revenue = float(revenue_by_year[first_year].get("amount", 0))

    if cost_by_year:
        first_year = min(cost_by_year.keys())
        base_cost = float(cost_by_year[first_year].get("amount", 0))

    for year in range(1, time_horizon + 1):
        # Get actual data or project
        if year in revenue_by_year and revenue_by_year[year].get("amount") not in [
            None,
            "NOT_AVAILABLE",
        ]:
            revenue = float(revenue_by_year[year]["amount"])
            rev_source = revenue_by_year[year].get("source", "")
            rev_confidence = revenue_by_year[year].get("confidence", 0.8)
        elif base_revenue is not None:
            # Project using growth rate
            revenue = base_revenue * ((1 + growth_rate) ** (year - 1))
            rev_source = f"Projected at {growth_rate*100:.0f}% growth"
            rev_confidence = max(0.3, 0.8 - (year * 0.05))
        else:
            revenue = 0
            rev_source = "NOT_AVAILABLE"
            rev_confidence = 0.1

        if year in cost_by_year and cost_by_year[year].get("amount") not in [
            None,
            "NOT_AVAILABLE",
        ]:
            cost = float(cost_by_year[year]["amount"])
            cost_source = cost_by_year[year].get("source", "")
            cost_confidence = cost_by_year[year].get("confidence", 0.8)
        elif base_cost is not None:
            # Project costs (assume 5% annual increase)
            cost = base_cost * ((1 + 0.05) ** (year - 1))
            cost_source = "Projected at 5% annual increase"
            cost_confidence = max(0.3, 0.8 - (year * 0.05))
        else:
            cost = 0
            cost_source = "NOT_AVAILABLE"
            cost_confidence = 0.1

        avg_confidence = (rev_confidence + cost_confidence) / 2

        cash_flows.append(
            {
                "year": year,
                "investment": 0,
                "revenue": revenue,
                "operating_costs": cost,
                "source": f"Revenue: {rev_source}; Costs: {cost_source}",
                "confidence": avg_confidence,
            }
        )

    return {
        "option_name": option.get("name", f"Option {option_index + 1}"),
        "option_description": option.get("description", ""),
        "cash_flows": cash_flows,
        "discount_rate": float(discount_info.get("value", 0.08)),
        "discount_rate_source": discount_info.get(
            "justification", discount_info.get("source", "Default")
        ),
        "currency": option.get("initial_investment", {}).get("currency", "USD"),
        "time_horizon_years": time_horizon,
    }

