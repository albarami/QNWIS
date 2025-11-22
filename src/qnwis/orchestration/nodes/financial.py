"""
Financial Analysis Node.

Executes the Financial Economist agent to analyze macro/ROI impacts.
"""

from __future__ import annotations

from qnwis.agents import financial_economist

from ..state import IntelligenceState
from ._helpers import execute_agent_analysis


async def financial_agent_node(state: IntelligenceState) -> IntelligenceState:
    """Run the Financial Economist agent and store the narrative."""

    await execute_agent_analysis(
        state,
        agent_key="financial_economist",
        target_field="financial_analysis",
        analyzer=financial_economist.analyze,
        success_message="Financial economist completed capital impact review.",
    )

    state.setdefault("nodes_executed", []).append("financial")
    return state

