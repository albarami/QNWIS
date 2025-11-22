"""
Debate Node.

Performs lightweight contradiction detection and creates a synthesis narrative
based on the agent reports generated earlier in the workflow.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from ..state import IntelligenceState


POSITIVE_TOKENS = {"increase", "growth", "opportunity", "improve", "expansion"}
NEGATIVE_TOKENS = {"risk", "decline", "decrease", "concern", "shortfall", "deficit"}


@dataclass
class AgentPerspective:
    """Normalized agent report view."""

    name: str
    narrative: str
    confidence: float
    facts_used: List[str]


def _sentiment_score(text: str) -> int:
    """Very lightweight sentiment heuristic based on domain tokens."""

    text_lower = text.lower()
    positive = sum(token in text_lower for token in POSITIVE_TOKENS)
    negative = sum(token in text_lower for token in NEGATIVE_TOKENS)
    return positive - negative


def _extract_perspectives(state: IntelligenceState) -> List[AgentPerspective]:
    """Return normalized perspectives from agent reports."""

    perspectives: List[AgentPerspective] = []
    for bundle in state.get("agent_reports", []):
        report = bundle.get("report", {})
        narrative = report.get("narrative") or ""
        confidence = float(report.get("confidence") or 0.0)
        facts_used = report.get("facts_used") or []

        perspectives.append(
            AgentPerspective(
                name=bundle.get("agent", "unknown"),
                narrative=narrative,
                confidence=confidence,
                facts_used=facts_used,
            )
        )
    return perspectives


def _detect_contradictions(perspectives: List[AgentPerspective]) -> List[Dict[str, str]]:
    """Identify contradictory perspectives using heuristics."""

    contradictions: List[Dict[str, str]] = []

    for i, left in enumerate(perspectives):
        for right in perspectives[i + 1 :]:
            shared_topics = set(left.facts_used) & set(right.facts_used)
            topic = next(iter(shared_topics), "overall assessment")

            sentiment_delta = _sentiment_score(left.narrative) - _sentiment_score(
                right.narrative
            )
            confidence_delta = left.confidence - right.confidence

            if abs(sentiment_delta) >= 1 or abs(confidence_delta) >= 0.25:
                if sentiment_delta > 0 or confidence_delta > 0.25:
                    winning_agent = left.name
                elif sentiment_delta < 0 or confidence_delta < -0.25:
                    winning_agent = right.name
                else:
                    winning_agent = "undetermined"

                contradictions.append(
                    {
                        "topic": topic,
                        "agent_a": left.name,
                        "agent_b": right.name,
                        "agent_a_confidence": f"{left.confidence:.2f}",
                        "agent_b_confidence": f"{right.confidence:.2f}",
                        "sentiment_delta": f"{sentiment_delta:+d}",
                        "winning_agent": winning_agent,
                    }
                )
    return contradictions


def _build_synthesis(contradictions: List[Dict[str, str]]) -> str:
    """Create human-readable synthesis for debate results."""

    if not contradictions:
        return (
            "No material contradictions detected across agent reports. "
            "Consensus: agents reached aligned conclusions based on shared data."
        )

    lines = [
        "Multi-agent debate summary:",
        f"- Contradictions detected: {len(contradictions)}",
    ]

    for item in contradictions:
        lines.append(
            f"  • {item['agent_a']} vs {item['agent_b']} on {item['topic']} "
            f"(sentiment delta {item['sentiment_delta']}, "
            f"winner: {item['winning_agent']})"
        )

    lines.append(
        "Dominant positions were retained when supported by higher confidence "
        "and positive sentiment reinforced by data citations."
    )
    return "\n".join(lines)


def debate_node(state: IntelligenceState) -> IntelligenceState:
    """
    Node 7: Multi-agent debate.

    Resolves contradictions between agent narratives and creates a synthesis
    that downstream critique/verification nodes can leverage.
    """

    reasoning_chain = state.setdefault("reasoning_chain", [])
    nodes_executed = state.setdefault("nodes_executed", [])

    perspectives = _extract_perspectives(state)
    contradictions = _detect_contradictions(perspectives)
    synthesis = _build_synthesis(contradictions)

    state["debate_synthesis"] = synthesis
    state["debate_results"] = {
        "contradictions_found": len(contradictions),
        "details": contradictions,
        "status": "complete" if contradictions else "skipped",
    }

    reasoning_chain.append(
        f"Debate completed with {len(contradictions)} contradictions analyzed."
    )
    nodes_executed.append("debate")
    return state

