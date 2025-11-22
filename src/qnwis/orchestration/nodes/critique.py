"""
Critique Node.

Acts as a devil's advocate by stress-testing the debate outcome and highlighting
key risks as well as missing evidence.
"""

from __future__ import annotations

from typing import Dict, List

from ..state import IntelligenceState


def _collect_data_gaps(agent_reports: List[Dict[str, object]]) -> List[str]:
    """Aggregate all data gaps surfaced by agents."""

    gaps: List[str] = []
    for bundle in agent_reports:
        report = bundle.get("report", {})
        for gap in report.get("data_gaps", []) or []:
            gaps.append(str(gap))
    return gaps


def _collect_high_risk_assumptions(agent_reports: List[Dict[str, object]]) -> List[str]:
    """Aggregate assumptions that might invalidate the recommendation."""

    assumptions: List[str] = []
    for bundle in agent_reports:
        report = bundle.get("report", {})
        for assumption in report.get("assumptions", []) or []:
            assumptions.append(str(assumption))
    return assumptions


def critique_node(state: IntelligenceState) -> IntelligenceState:
    """
    Node 8: Devil's advocate critique.

    Reviews debate results, agent warnings, and data gaps to provide a concise
    critique report and recommended follow-ups.
    """

    reasoning_chain = state.setdefault("reasoning_chain", [])
    nodes_executed = state.setdefault("nodes_executed", [])
    warnings = state.setdefault("warnings", [])

    agent_reports = state.get("agent_reports", [])
    data_gaps = _collect_data_gaps(agent_reports)
    assumptions = _collect_high_risk_assumptions(agent_reports)

    debate_results = state.get("debate_results") or {}
    contradiction_count = debate_results.get("contradictions_found", 0)
    data_quality = state.get("data_quality_score") or 0.0

    critique_lines = []

    if contradiction_count:
        critique_lines.append(
            f"- {contradiction_count} contradiction(s) remain unresolved; "
            "human review recommended."
        )

    if data_quality < 0.7:
        critique_lines.append(
            "- Data quality score below 0.70; refresh cache or fetch additional sources."
        )

    if data_gaps:
        critique_lines.append(
            f"- Agents reported {len(data_gaps)} data gaps (top gap: {data_gaps[0]})."
        )

    if assumptions:
        critique_lines.append(
            f"- Key assumptions requiring validation: {', '.join(assumptions[:3])}"
        )

    if not critique_lines:
        critique_lines.append(
            "- No material critiques detected; evidence base appears sufficient."
        )

    critique_report = "\n".join(["Devil's advocate review:"] + critique_lines)

    state["critique_report"] = critique_report
    reasoning_chain.append("Critique node documented devil's advocate findings.")
    nodes_executed.append("critique")

    if contradiction_count or data_quality < 0.7:
        warnings.append("Critique flagged outstanding concerns; review recommended.")

    return state

