"""
Operations Analysis Node.

Executes the Operations Expert agent to evaluate implementation feasibility.
"""

from __future__ import annotations

from qnwis.agents import operations_expert

from ..state import IntelligenceState
from ._helpers import execute_agent_analysis


async def operations_agent_node(state: IntelligenceState) -> IntelligenceState:
    """Run the Operations Expert agent and store the execution narrative."""

    await execute_agent_analysis(
        state,
        agent_key="operations_expert",
        target_field="operations_analysis",
        analyzer=operations_expert.analyze,
        success_message="Operations expert mapped timelines and implementation phases.",
    )

    state.setdefault("nodes_executed", []).append("operations")
    return state

