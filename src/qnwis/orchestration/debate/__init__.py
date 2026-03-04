"""
Debate package for the QNWIS council legendary debate system.

Re-exports the main orchestrator and all utilities from the former
``legendary_debate_orchestrator`` module **and** the convergence helpers
that previously lived in ``orchestration/debate.py``.
"""

from ._convergence import (
    build_quantitative_context_for_debate,
    count_new_contradictions,
    detect_debate_convergence,
    multi_agent_debate,
)
from .json_parser import robust_json_parse
from .orchestrator import LegendaryDebateOrchestrator, create_debate_context

__all__ = [
    # Legendary debate orchestrator
    "LegendaryDebateOrchestrator",
    "create_debate_context",
    "robust_json_parse",
    # Convergence helpers (previously in orchestration/debate.py)
    "detect_debate_convergence",
    "multi_agent_debate",
    "build_quantitative_context_for_debate",
    "count_new_contradictions",
]
