"""
Verification Node.

Performs lightweight citation/fabrication checks across agent reports.
"""

from __future__ import annotations

from typing import Dict, List

from ..state import IntelligenceState


def _agent_has_citations(report: Dict[str, object]) -> bool:
    """Return True if the agent supplied at least one citation."""

    citations = report.get("citations")
    if isinstance(citations, list) and citations:
        return True
    narrative = report.get("narrative", "")
    return isinstance(narrative, str) and "Per extraction:" in narrative


def verification_node(state: IntelligenceState) -> IntelligenceState:
    """
    Node 9: Fact checking.

    Ensures every agent report contains citations and surfaces data coverage
    issues so the synthesis node can report a confidence score.
    """

    reasoning_chain = state.setdefault("reasoning_chain", [])
    nodes_executed = state.setdefault("nodes_executed", [])
    warnings = state.setdefault("warnings", [])

    issues: List[str] = []
    agent_reports = state.get("agent_reports", [])

    for bundle in agent_reports:
        agent_name = bundle.get("agent", "unknown")
        report = bundle.get("report", {})
        if not _agent_has_citations(report):
            issues.append(f"{agent_name} missing authoritative citations.")

        confidence = report.get("confidence")
        if isinstance(confidence, (int, float)) and confidence < 0.4:
            issues.append(f"{agent_name} reported low confidence ({confidence:.2f}).")

    fabrication_detected = bool(issues)
    state["fabrication_detected"] = fabrication_detected
    state["fact_check_results"] = {
        "status": "ATTENTION" if fabrication_detected else "PASS",
        "issues": issues,
        "agent_count": len(agent_reports),
    }

    if fabrication_detected:
        warnings.append("Fact check flagged missing citations or low confidence.")
    else:
        reasoning_chain.append("Verification node confirmed citations for all agents.")

    nodes_executed.append("verification")
    return state

