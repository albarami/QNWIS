"""
NSIC Agents - Specialized analytical personas for dual-engine analysis.

Engine A Agents (in qnwis/agents/):
- Dr. Ahmed (MicroEconomist)
- Dr. Sarah (MacroEconomist)
- Dr. Fatima (Labour Economist)
- Dr. Mohammed (Nationalization)
- Dr. Layla (Competitive/Skills)

Engine B Agents (in nsic/agents/engine_b/):
- Dr. Rashid (Lead Economist) - defined in engine_b_deepseek.py
- Dr. Noor (Risk Analyst)
- Dr. Hassan (Competitive Analyst)
"""

from .engine_b import (
    DR_NOOR_SYSTEM_PROMPT,
    DR_HASSAN_SYSTEM_PROMPT,
    ENGINE_B_AGENTS,
    get_engine_b_agent_prompt,
)

__all__ = [
    "DR_NOOR_SYSTEM_PROMPT",
    "DR_HASSAN_SYSTEM_PROMPT",
    "ENGINE_B_AGENTS",
    "get_engine_b_agent_prompt",
]
