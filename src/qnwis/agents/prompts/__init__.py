"""
Agent prompt templates for QNWIS.

Each module contains specialized prompts for one agent type.

To avoid circular imports, import prompt builders directly from their modules:
    from qnwis.agents.prompts.labour_economist import build_labour_economist_prompt
    from qnwis.agents.prompts.nationalization import build_nationalization_prompt
    etc.

Engine B awareness prompts (shared across all agents):
    from qnwis.agents.prompts.base import ENGINE_B_VALIDATION_AWARENESS
    from qnwis.agents.prompts.base import format_engine_b_results
    from qnwis.agents.prompts.base import build_engine_a_prime_prompt
"""

from .base import (
    ANTI_FABRICATION_RULES,
    ENGINE_B_VALIDATION_AWARENESS,
    ENGINE_B_OUTPUT_GUIDE,
    ENGINE_A_PRIME_PROMPT_TEMPLATE,
    format_extracted_facts,
    format_engine_b_results,
    format_conflicts,
    build_engine_a_prime_prompt,
)

__all__ = [
    # Agent prompt builders
    "build_labour_economist_prompt",
    "build_nationalization_prompt",
    "build_skills_prompt",
    "build_pattern_detective_prompt",
    "build_national_strategy_prompt",
    # Engine B awareness (shared)
    "ANTI_FABRICATION_RULES",
    "ENGINE_B_VALIDATION_AWARENESS",
    "ENGINE_B_OUTPUT_GUIDE",
    "ENGINE_A_PRIME_PROMPT_TEMPLATE",
    "format_extracted_facts",
    "format_engine_b_results",
    "format_conflicts",
    "build_engine_a_prime_prompt",
]
