"""
Research Analysis Node.

Executes the Research Scientist agent to gather academic evidence.
"""

from __future__ import annotations

from qnwis.agents import research_scientist

from ..state import IntelligenceState
from ._helpers import execute_agent_analysis


async def research_agent_node(state: IntelligenceState) -> IntelligenceState:
    """Run the Research Scientist agent and store the literature synthesis."""

    await execute_agent_analysis(
        state,
        agent_key="research_scientist",
        target_field="research_analysis",
        analyzer=research_scientist.analyze,
        success_message="Research scientist grounded findings in peer-reviewed evidence.",
    )

    state.setdefault("nodes_executed", []).append("research")
    return state

