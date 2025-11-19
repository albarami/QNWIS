"""
Agent prompt templates for QNWIS.

Each module contains specialized prompts for one agent type.

To avoid circular imports, import prompt builders directly from their modules:
    from qnwis.agents.prompts.labour_economist import build_labour_economist_prompt
    from qnwis.agents.prompts.nationalization import build_nationalization_prompt
    etc.
"""

__all__ = [
    "build_labour_economist_prompt",
    "build_nationalization_prompt",
    "build_skills_prompt",
    "build_pattern_detective_prompt",
    "build_national_strategy_prompt",
]
