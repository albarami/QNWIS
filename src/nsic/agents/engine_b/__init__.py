"""
Engine B Agents - DeepSeek-powered analytical personas.

Three agents rotate through 24 broad scenarios:
1. Dr. Rashid (Lead Economist) - Economic scenario assessment
2. Dr. Noor (Risk Analyst) - Risk identification and mitigation
3. Dr. Hassan (Competitive Analyst) - Competitive dynamics and positioning

All agents use <think> tags for chain-of-thought reasoning as required by DeepSeek-R1.
"""

from .risk_analyst import DR_NOOR_SYSTEM_PROMPT
from .competitive_analyst import DR_HASSAN_SYSTEM_PROMPT

# Dr. Rashid's prompt is defined inline in engine_b_deepseek.py
# This is kept for historical compatibility
DR_RASHID_SYSTEM_PROMPT = """You are **Dr. Rashid**, a senior strategic analyst for Qatar's NSIC with 14 years advising Gulf sovereign wealth funds.

YOUR CREDENTIALS:
- PhD Strategic Studies, Georgetown University (2011)
- Published 22 papers on economic diversification strategies
- Expert in scenario planning and second-order effects analysis
- Known for identifying cross-domain impacts others miss

YOUR ANALYTICAL APPROACH:
- Explore scenarios BROADLY, considering multiple perspectives
- Quantify impacts with ranges, not point estimates (e.g., "2-4% GDP impact")
- Explicitly acknowledge uncertainties and data gaps
- If data missing, state: "NOT IN DATA - cannot verify [claim]"

OUTPUT FORMAT RULES:
- Provide DIRECT analysis - no meta-commentary
- Do NOT output headers like "## Step 1:", "## Turn 2:", "## Analysis:"
- Do NOT describe what you're about to do - just DO it
- Write in flowing paragraphs, not numbered steps
- Stay focused on the specific scenario question

CITATION RULES:
- Every fact MUST be cited: [Per extraction: 'value' from source]
- If data missing: "NOT IN DATA - cannot verify"
- Never fabricate Qatar-specific numbers
"""

# All Engine B agents with their rotation order
ENGINE_B_AGENTS = {
    "dr_rashid": {
        "name": "Dr. Rashid",
        "role": "Lead Economist",
        "system_prompt": DR_RASHID_SYSTEM_PROMPT,
        "focus": ["economic assessment", "scenario analysis", "second-order effects"],
    },
    "dr_noor": {
        "name": "Dr. Noor",
        "role": "Risk Analyst",
        "system_prompt": DR_NOOR_SYSTEM_PROMPT,
        "focus": ["risk identification", "probability assessment", "mitigation strategies"],
    },
    "dr_hassan": {
        "name": "Dr. Hassan",
        "role": "Competitive Analyst",
        "system_prompt": DR_HASSAN_SYSTEM_PROMPT,
        "focus": ["competitive dynamics", "game theory", "regional positioning"],
    },
}


def get_engine_b_agent_prompt(agent_id: str, scenario_domain: str = "") -> str:
    """
    Get the system prompt for an Engine B agent.

    Args:
        agent_id: One of "dr_rashid", "dr_noor", "dr_hassan"
        scenario_domain: Optional domain for domain-specific additions

    Returns:
        Complete system prompt with domain-specific additions
    """
    if agent_id not in ENGINE_B_AGENTS:
        raise ValueError(f"Unknown agent: {agent_id}. Available: {list(ENGINE_B_AGENTS.keys())}")

    base_prompt = ENGINE_B_AGENTS[agent_id]["system_prompt"]

    # Add domain-specific focus areas
    domain_additions = {
        "economic": "\n\nFocus areas for this scenario: GDP impact, trade flows, oil/gas revenues, investment, employment.",
        "policy": "\n\nFocus areas for this scenario: Policy implications, regulatory changes, international relations, governance.",
        "competitive": "\n\nFocus areas for this scenario: Regional competition, market positioning, strategic advantages.",
        "timing": "\n\nFocus areas for this scenario: Timing considerations, phasing, dependencies, sequencing.",
    }

    return base_prompt + domain_additions.get(scenario_domain, "")


def get_agent_rotation(scenario_index: int) -> str:
    """
    Get the agent ID for a given scenario index.

    Rotates through all 3 agents evenly across 24 scenarios.

    Args:
        scenario_index: 0-based index of the scenario

    Returns:
        Agent ID (dr_rashid, dr_noor, or dr_hassan)
    """
    agents = list(ENGINE_B_AGENTS.keys())
    return agents[scenario_index % len(agents)]


__all__ = [
    "DR_RASHID_SYSTEM_PROMPT",
    "DR_NOOR_SYSTEM_PROMPT",
    "DR_HASSAN_SYSTEM_PROMPT",
    "ENGINE_B_AGENTS",
    "get_engine_b_agent_prompt",
    "get_agent_rotation",
]
