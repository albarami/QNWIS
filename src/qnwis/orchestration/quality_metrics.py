"""
Quality and confidence scoring helpers for the orchestration layer.

The scoring model intentionally keeps the implementation lightweight so it can
run inside synchronous verification nodes without additional dependencies.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List

DATA_WEIGHT = 0.40
AGREEMENT_WEIGHT = 0.30
CITATION_WEIGHT = 0.30


def calculate_analysis_confidence(
    facts: List[Dict[str, Any]],
    required_data: Iterable[str],
    agent_outputs: Dict[str, Any],
    citation_violations: int,
) -> Dict[str, Any]:
    """
    Compute a composite confidence score using three components.

    Component weights:
        - Data quality (coverage + volume): 40%
        - Agent agreement (consensus on findings): 30%
        - Citation compliance: 30%
    """
    required_list = list(required_data)
    data_quality_score = _score_data_quality(facts, required_list)
    agent_agreement = calculate_agent_consensus(agent_outputs)
    citation_score = _score_citation_compliance(
        citation_violations,
        len(agent_outputs) if agent_outputs else 1,
    )

    overall = (
        data_quality_score * DATA_WEIGHT
        + agent_agreement * AGREEMENT_WEIGHT
        + citation_score * CITATION_WEIGHT
    )

    recommendation = get_confidence_recommendation(overall)

    return {
        "overall_confidence": round(overall, 2),
        "components": {
            "data_quality": round(data_quality_score, 2),
            "agent_agreement": round(agent_agreement, 2),
            "citation_compliance": round(citation_score, 2),
        },
        "facts_extracted": len(facts),
        "citation_violations": citation_violations,
        "recommendation": recommendation,
    }


def _score_data_quality(facts: List[Dict[str, Any]], required_data: List[str]) -> float:
    """Combine required coverage and raw fact volume into a single value."""
    if required_data:
        covered = {
            req
            for req in required_data
            if any(req in str(fact) for fact in facts)
        }
        coverage = len(covered) / len(required_data)
    else:
        coverage = 0.8  # Neutral default when no requirements provided

    volume = min(len(facts) / 50.0, 1.0)  # 50 facts == ideal coverage
    return (coverage * 0.7) + (volume * 0.3)


def _score_citation_compliance(violations: int, agent_count: int) -> float:
    """Map citation violations into a 0-1 score."""
    max_acceptable = max(agent_count * 2, 1)  # two violations per agent
    ratio = min(max(violations, 0) / max_acceptable, 1.0)
    return max(0.0, 1.0 - ratio)


def calculate_agent_consensus(agent_outputs: Dict[str, Any]) -> float:
    """
    Heuristic consensus score among agent narratives.

    In the absence of semantic similarity (which would require an embedding
    model), use a simple step function based on the number of agreeing agents.
    """
    count = len(agent_outputs)
    if count == 0:
        return 0.5
    if count == 1:
        return 0.7
    if count <= 3:
        return 0.75
    if count <= 5:
        return 0.85
    return 0.9


def get_confidence_recommendation(score: float) -> str:
    """Return a human-readable recommendation based on the score."""
    if score >= 0.85:
        return "HIGH confidence – evidence rich, strong agreement, and full citations."
    if score >= 0.70:
        return "MEDIUM-HIGH confidence – minor data gaps remain."
    if score >= 0.55:
        return "MEDIUM confidence – gather additional data before briefing."
    return "LOW confidence – major gaps or citation issues detected."


def calculate_data_completeness(
    facts: List[Dict[str, Any]],
    required_categories: Iterable[str],
) -> Dict[str, Any]:
    """
    Track which required categories are covered by the extracted facts.
    """
    required_list = [cat.lower() for cat in required_categories]
    if not required_list:
        return {"completeness_score": 0.8, "missing_categories": [], "covered_categories": []}

    covered: list[str] = []
    for category in required_list:
        if any(category in str(fact).lower() for fact in facts):
            covered.append(category)

    missing = [cat for cat in required_list if cat not in covered]
    score = len(covered) / len(required_list)

    return {
        "completeness_score": round(score, 2),
        "missing_categories": missing,
        "covered_categories": covered,
    }


def format_confidence_report(confidence_data: Dict[str, Any]) -> str:
    """
    Render the analysis confidence breakdown as Markdown.
    """
    components = confidence_data["components"]
    return (
        "## Analysis Confidence Report\n\n"
        f"**Overall Confidence:** {confidence_data['overall_confidence']:.0%}\n\n"
        "### Component Scores\n"
        f"- Data Quality: {components['data_quality']:.0%}\n"
        f"- Agent Agreement: {components['agent_agreement']:.0%}\n"
        f"- Citation Compliance: {components['citation_compliance']:.0%}\n\n"
        f"Facts Reviewed: {confidence_data['facts_extracted']}\n"
        f"Citation Violations: {confidence_data['citation_violations']}\n\n"
        f"**Recommendation:** {confidence_data['recommendation']}"
    )

