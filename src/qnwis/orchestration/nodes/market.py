"""
Market Intelligence Node.

Executes the Market Economist agent for GCC benchmarking and market signals.
"""

from __future__ import annotations

from qnwis.agents import market_economist

from ..state import IntelligenceState
from ._helpers import execute_agent_analysis


async def market_agent_node(state: IntelligenceState) -> IntelligenceState:
    """Run the Market Economist agent and capture its findings."""

    await execute_agent_analysis(
        state,
        agent_key="market_economist",
        target_field="market_analysis",
        analyzer=market_economist.analyze,
        success_message="Market economist completed GCC benchmarking analysis.",
    )

    state.setdefault("nodes_executed", []).append("market")
    return state

