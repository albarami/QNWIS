"""
Multi-agent council orchestration with sequential execution.

Provides deterministic council execution with optional LangGraph orchestration.
Falls back to sequential execution when LangGraph is unavailable.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol, TypedDict

from ..agents.base import AgentReport, DataClient


class Agent(Protocol):
    """Protocol for agent implementations."""

    def run(self) -> AgentReport:
        """Execute agent and return report."""
        ...


from ..agents.labour_economist import LabourEconomistAgent
from ..agents.national_strategy import NationalStrategyAgent
from ..agents.nationalization import NationalizationAgent
from ..agents.pattern_detective import PatternDetectiveAgent
from ..agents.skills import SkillsAgent
from .synthesis import CouncilReport, synthesize
from .verification import VerificationIssue, verify_report


@dataclass
class CouncilConfig:
    """
    Configuration for council execution.

    Attributes:
        queries_dir: Path to deterministic query definitions (None for default)
        ttl_s: Cache TTL in seconds for data client
    """

    queries_dir: str | None = None
    ttl_s: int = 300


def default_agents(client: DataClient) -> list[Agent]:
    """
    Create default set of 5 agents for council execution.

    Args:
        client: DataClient instance for agent initialization

    Returns:
        List of initialized agent instances
    """
    return [
        LabourEconomistAgent(client),
        NationalizationAgent(client),
        SkillsAgent(client),
        PatternDetectiveAgent(client),
        NationalStrategyAgent(client),
    ]


def _apply_rate_limit(ttl_s: int) -> tuple[int, bool]:
    """
    Clip TTL to accommodate rate limiting when requested via environment variable.

    Args:
        ttl_s: Requested TTL value from configuration

    Returns:
        Tuple of (effective_ttl, rate_limit_applied)
    """
    rate_limit_env = os.getenv("QNWIS_RATE_LIMIT_RPS")
    if rate_limit_env is not None:
        return max(ttl_s, 60), True
    return ttl_s, False


def _run_agents(agents: list[Agent]) -> list[AgentReport]:
    """Execute agents deterministically and collect their reports."""
    reports: list[AgentReport] = []
    for agent in agents:
        reports.append(agent.run())
    return reports


def _verify_reports(reports: list[AgentReport]) -> dict[str, list[VerificationIssue]]:
    """Run verification on each agent report."""
    verification: dict[str, list[VerificationIssue]] = {}
    for rep in reports:
        verification[rep.agent] = verify_report(rep).issues
    return verification


def _compute_min_confidence(findings: list[Any]) -> float:
    """Return the minimum confidence score across findings (defaulting to 1.0)."""
    if not findings:
        return 1.0
    return min(float(getattr(f, "confidence_score", 1.0)) for f in findings)


def _serialize_issue(issue: VerificationIssue) -> dict[str, Any]:
    """Convert a VerificationIssue into a JSON-safe dictionary."""
    return {"level": issue.level, "code": issue.code, "detail": issue.detail}


def _assemble_response(
    council: CouncilReport,
    verification: dict[str, list[VerificationIssue]],
    *,
    rate_limit_applied: bool,
) -> dict[str, Any]:
    """Serialize council output and verification results into JSON-safe structure."""
    findings_payload = [
        {
            "title": finding.title,
            "summary": finding.summary,
            "metrics": finding.metrics,
            "evidence": [vars(evi) for evi in finding.evidence],
            "warnings": finding.warnings,
            "confidence_score": getattr(finding, "confidence_score", 1.0),
        }
        for finding in council.findings
    ]
    min_confidence = _compute_min_confidence(council.findings)
    return {
        "council": {
            "agents": council.agents,
            "findings": findings_payload,
            "consensus": council.consensus,
            "warnings": council.warnings,
            "min_confidence": min_confidence,
        },
        "verification": {agent: [_serialize_issue(i) for i in issues] for agent, issues in verification.items()},
        "rate_limit_applied": rate_limit_applied,
    }


class _CouncilState(TypedDict, total=False):
    """State carried through LangGraph execution."""

    config: CouncilConfig
    ttl_s: int
    agents: list[Agent]
    reports: list[AgentReport]
    verification: dict[str, list[VerificationIssue]]
    council: CouncilReport
    result: dict[str, Any]
    rate_limit_applied: bool


def build_council_graph(make_agents: Callable[[DataClient], list[Agent]]) -> Any:
    """
    Build a LangGraph pipeline for council execution if LangGraph is available.

    The graph mirrors sequential execution steps: plan → run → verify → synthesize → report.

    Args:
        make_agents: Factory function used to build the agent list.

    Returns:
        Compiled LangGraph application ready for invocation.

    Raises:
        ImportError: If LangGraph is not installed.
    """

    from langgraph.graph import END, START, StateGraph

    graph: StateGraph[_CouncilState] = StateGraph(_CouncilState)

    def plan_step(state: _CouncilState) -> _CouncilState:
        cfg = state["config"]
        client = DataClient(queries_dir=cfg.queries_dir, ttl_s=state["ttl_s"])
        state["agents"] = make_agents(client)
        return state

    def run_step(state: _CouncilState) -> _CouncilState:
        state["reports"] = _run_agents(state["agents"])
        return state

    def verify_step(state: _CouncilState) -> _CouncilState:
        state["verification"] = _verify_reports(state["reports"])
        return state

    def synthesize_step(state: _CouncilState) -> _CouncilState:
        state["council"] = synthesize(state["reports"])
        return state

    def report_step(state: _CouncilState) -> _CouncilState:
        state["result"] = _assemble_response(
            state["council"],
            state["verification"],
            rate_limit_applied=state.get("rate_limit_applied", False),
        )
        return state

    graph.add_node("plan", plan_step)
    graph.add_node("run", run_step)
    graph.add_node("verify", verify_step)
    graph.add_node("synthesize", synthesize_step)
    graph.add_node("report", report_step)

    graph.add_edge(START, "plan")
    graph.add_edge("plan", "run")
    graph.add_edge("run", "verify")
    graph.add_edge("verify", "synthesize")
    graph.add_edge("synthesize", "report")
    graph.add_edge("report", END)

    return graph.compile()


def _run_sequential(
    config: CouncilConfig,
    make_agents: Callable[[DataClient], list[Agent]],
    ttl_s: int,
    *,
    rate_limit_applied: bool,
) -> dict[str, Any]:
    """Sequential fallback execution when LangGraph is unavailable."""
    client = DataClient(queries_dir=config.queries_dir, ttl_s=ttl_s)
    agents = make_agents(client)
    reports = _run_agents(agents)
    verification = _verify_reports(reports)
    council = synthesize(reports)
    return _assemble_response(
        council,
        verification,
        rate_limit_applied=rate_limit_applied,
    )


def run_council(
    config: CouncilConfig, make_agents: Callable[[DataClient], list[Agent]] = default_agents
) -> dict[str, Any]:
    """
    Execute deterministic council run with sequential agent execution.

    This is the primary entry point for council orchestration. It creates
    a data client, initializes agents, runs them sequentially, verifies
    outputs, and synthesizes a unified council report.

    Args:
        config: CouncilConfig with queries_dir and ttl_s
        make_agents: Factory function to create agent list (default: default_agents)

    Returns:
        JSON-serializable dict with:
            - council: CouncilReport with findings, consensus, warnings
            - verification: Dict mapping agent names to verification issues
    """
    ttl_s, rate_limit_applied = _apply_rate_limit(config.ttl_s)

    try:
        graph_app = build_council_graph(make_agents)
    except ImportError:
        return _run_sequential(
            config,
            make_agents,
            ttl_s,
            rate_limit_applied=rate_limit_applied,
        )

    state: _CouncilState = {
        "config": config,
        "ttl_s": ttl_s,
        "rate_limit_applied": rate_limit_applied,
    }
    final_state = graph_app.invoke(state)
    result: dict[str, Any] | None = final_state.get("result")
    if result is None:
        # Safety net: fall back if graph execution failed to materialize a result.
        return _run_sequential(
            config,
            make_agents,
            ttl_s,
            rate_limit_applied=rate_limit_applied,
        )
    return result
