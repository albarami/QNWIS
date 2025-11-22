"""
Synthesis Node.

Produces the final ministerial-grade synthesis with an explicit confidence score.
"""

from __future__ import annotations

from typing import List

from ..state import IntelligenceState


def _gather_sections(state: IntelligenceState) -> List[str]:
    """Collect non-empty agent narratives."""

    sections: List[str] = []
    for label, field in [
        ("Financial", "financial_analysis"),
        ("Market", "market_analysis"),
        ("Operations", "operations_analysis"),
        ("Research", "research_analysis"),
        ("Debate", "debate_synthesis"),
        ("Critique", "critique_report"),
    ]:
        content = state.get(field)
        if content:
            sections.append(f"### {label}\n{content}")
    return sections


def _compute_confidence(state: IntelligenceState) -> float:
    """Derive a confidence score based on data quality and verification results."""

    data_quality = state.get("data_quality_score") or 0.0
    fact_check = state.get("fact_check_results") or {}
    verification_pass = fact_check.get("status") == "PASS"

    confidence = data_quality
    confidence += 0.1 if verification_pass else -0.1
    confidence -= 0.05 * len(fact_check.get("issues", []) or [])
    confidence = max(0.0, min(1.0, confidence))
    return round(confidence, 2)


def synthesis_node(state: IntelligenceState) -> IntelligenceState:
    """
    Node 10: Final synthesis.

    Combines all upstream analyses into a coherent executive summary.
    """

    reasoning_chain = state.setdefault("reasoning_chain", [])
    nodes_executed = state.setdefault("nodes_executed", [])

    sections = _gather_sections(state)
    if sections:
        final_synthesis = "\n\n".join(
            ["## Ministerial Intelligence Brief", *sections]
        )
    else:
        final_synthesis = (
            "No agent narratives were available. Please rerun the workflow."
        )

    state["final_synthesis"] = final_synthesis
    state["confidence_score"] = _compute_confidence(state)

    reasoning_chain.append(
        f"Synthesis generated with confidence {state['confidence_score']:.2f}."
    )
    nodes_executed.append("synthesis")

    return state

