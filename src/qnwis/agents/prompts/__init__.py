"""
Agent prompt templates for QNWIS.

Each module contains specialized prompts for one agent type.
"""

from src.qnwis.agents.prompts.labour_economist import build_labour_economist_prompt
from src.qnwis.agents.prompts.nationalization import build_nationalization_prompt
from src.qnwis.agents.prompts.skills import build_skills_prompt
from src.qnwis.agents.prompts.pattern_detective import build_pattern_detective_prompt
from src.qnwis.agents.prompts.national_strategy import build_national_strategy_prompt

__all__ = [
    "build_labour_economist_prompt",
    "build_nationalization_prompt",
    "build_skills_prompt",
    "build_pattern_detective_prompt",
    "build_national_strategy_prompt",
]
