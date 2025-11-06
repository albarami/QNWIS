"""
Minimal LangGraph pipeline builder for deterministic agent workflows.

This module provides a simple, reusable pattern for building LangGraph
workflows that execute deterministic queries and produce structured insights.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypedDict, cast

from ...data.deterministic.models import QueryResult
from ..base import AgentReport, Insight, evidence_from


class AgentState(TypedDict, total=False):
    """
    State dictionary for agent graph execution.

    Attributes:
        plan: List of query IDs to execute
        results: Dictionary mapping query IDs to QueryResult objects
        insights: List of Insight objects discovered
        report: Final AgentReport
    """

    plan: list[str]
    results: dict[str, QueryResult]
    insights: list[Insight]
    report: AgentReport


class _LinearGraph:
    """Minimal fallback graph when LangGraph is unavailable."""

    def __init__(self, steps: list[Callable[[AgentState], AgentState]]) -> None:
        self._steps = steps

    def invoke(self, initial_state: AgentState | None = None) -> AgentState:
        """Execute steps sequentially without side effects."""
        state: dict[str, Any] = {}
        if initial_state:
            state.update(initial_state)
        for step in self._steps:
            updates = step(cast(AgentState, dict(state)))
            state.update(updates)
        return cast(AgentState, state)


def build_simple_graph(
    agent_name: str, plan_ids: list[str], runner: Callable[..., QueryResult]
) -> Any:
    """
    Build a simple LangGraph workflow for an agent.

    Creates a four-node workflow:
    1. plan: Define query IDs to execute
    2. fetch: Execute all queries
    3. analyze: Convert results to insights
    4. report: Aggregate into AgentReport

    Args:
        agent_name: Name of the agent for reporting
        plan_ids: List of query IDs to execute
        runner: Callable that executes a query_id and returns QueryResult

    Returns:
        Compiled LangGraph workflow
    """

    def step_plan(_state: AgentState) -> AgentState:
        """Initialize execution plan."""
        return {"plan": list(plan_ids)}

    def step_fetch(state: AgentState) -> AgentState:
        """Execute all planned queries."""
        results: dict[str, QueryResult] = {}
        plan: list[str] = state.get("plan", [])
        for qid in list(plan):
            try:
                results[qid] = runner(qid)
            except TypeError:
                results[qid] = runner()
        return {"results": results}

    def step_analyze(state: AgentState) -> AgentState:
        """Convert query results to structured insights."""
        insights: list[Insight] = []
        results_state: dict[str, QueryResult] = state.get("results", {})
        for qid, res in results_state.items():
            ev = evidence_from(res)
            if res.rows:
                # Trivial deterministic summary: capture numeric fields of last row
                metrics = {}
                for k, v in res.rows[-1].data.items():
                    if isinstance(v, (int, float)):
                        metrics[k] = float(v)
                insights.append(
                    Insight(
                        title=f"{agent_name}: {qid}",
                        summary="Deterministic summary of latest row.",
                        metrics=metrics,
                        evidence=[ev],
                        warnings=res.warnings,
                    )
                )
            else:
                insights.append(
                    Insight(
                        title=f"{agent_name}: {qid}",
                        summary="No rows.",
                        evidence=[ev],
                        warnings=res.warnings,
                    )
                )
        return {"insights": insights}

    def step_report(state: AgentState) -> AgentState:
        """Aggregate insights into final report."""
        insights: list[Insight] = list(state.get("insights", []))
        aggregated_warnings: list[str] = []
        for insight in insights:
            aggregated_warnings.extend(insight.warnings)
        unique_warnings = sorted(set(aggregated_warnings))
        return {"report": AgentReport(agent=agent_name, findings=insights, warnings=unique_warnings)}

    try:
        from langgraph.graph import END, StateGraph
    except ImportError:
        steps = [step_plan, step_fetch, step_analyze, step_report]
        return _LinearGraph(steps)

    sg = StateGraph(AgentState)
    sg.add_node("plan", step_plan)
    sg.add_node("fetch", step_fetch)
    sg.add_node("analyze", step_analyze)
    sg.add_node("report", step_report)
    sg.set_entry_point("plan")
    sg.add_edge("plan", "fetch")
    sg.add_edge("fetch", "analyze")
    sg.add_edge("analyze", "report")
    sg.add_edge("report", END)
    return sg.compile()
