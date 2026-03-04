"""
Ground truth extraction, confidence calibration, question classification,
and probability aggregation for the Legendary Synthesis pipeline.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Literal, Optional

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIDENCE CALIBRATION (Domain-Agnostic)
# ═══════════════════════════════════════════════════════════════════════════════

def calculate_calibrated_confidence(
    gap: float,
    consensus_count: int,
    total_agents: int = 5,
    tied_threshold: float = 5.0
) -> int:
    """
    Calculate confidence from scenario gap and agent consensus.

    Domain-agnostic: Uses only numerical inputs, no domain knowledge.

    Args:
        gap: Absolute difference between best and worst scenario rates (pp)
        consensus_count: Number of agents agreeing on recommendation
        total_agents: Total number of agents in debate
        tied_threshold: Gap below which scenarios are considered tied (default 5pp)

    Returns:
        Calibrated confidence (0-100)

    Calibration Rules:
        - Tied (<5pp): 50-60% max (acknowledges uncertainty)
        - Clear winner (≥5pp): 65-80% (based on gap + consensus)
        - Never exceed 80% (irreducible strategic uncertainty)
    """
    if gap < tied_threshold:
        base = 50
        consensus_bonus = 5 if consensus_count == total_agents else 0
        return min(base + consensus_bonus + int(gap), 60)

    base = 65

    consensus_ratio = consensus_count / total_agents if total_agents > 0 else 0
    if consensus_ratio >= 1.0:
        consensus_bonus = 5
    elif consensus_ratio >= 0.8:
        consensus_bonus = 3
    elif consensus_ratio >= 0.6:
        consensus_bonus = 0
    else:
        consensus_bonus = -5

    if gap >= 20:
        gap_bonus = 7
    elif gap >= 15:
        gap_bonus = 5
    elif gap >= 10:
        gap_bonus = 3
    else:
        gap_bonus = 0

    confidence = base + consensus_bonus + gap_bonus
    return min(max(confidence, 40), 80)


# ═══════════════════════════════════════════════════════════════════════════════
# QUESTION TYPE DETECTION (FIX RUN 36)
# ═══════════════════════════════════════════════════════════════════════════════

def classify_question_type(query: str) -> Literal["COMPARATIVE", "DIAGNOSTIC", "FORECAST", "HYBRID"]:
    """
    Classify question type to determine appropriate analysis framework.

    COMPARATIVE: "A vs B, which is better?" – Use A/B framework
    DIAGNOSTIC: "Why is X happening?" – Root cause analysis
    FORECAST: "What is probability of Y?" – Probability estimation
    HYBRID: Combination or unclear
    """
    query_lower = query.lower()

    diagnostic_patterns = [
        r"what are the (?:root )?causes",
        r"why (?:is|has|did|are|does|do)",
        r"what (?:is|are) the (?:reason|driver|factor)",
        r"explain (?:the|why)",
        r"what (?:is|are) (?:driving|causing|behind)",
        r"analyze the (?:cause|driver|factor|reason)",
        r"root cause",
        r"underlying factor",
        r"what led to",
        r"stagnation",
    ]

    forecast_patterns = [
        r"what is the probability",
        r"probability that",
        r"will .* succeed",
        r"can .* achieve",
        r"likelihood of",
        r"chances of",
        r"by \d{4}",
        r"reverse this trend",
    ]

    comparative_patterns = [
        r"(?:should|would) .* (?:invest|allocate|choose|prioritize)",
        r"which (?:path|option|strategy|approach)",
        r"(?:better|prefer|recommend) .* or",
        r"(?:option a|option b)",
        r"(?:between|versus|vs\.?)",
        r"(?:tourism|ai|technology|hub).* (?:or|vs)",
        r"prioritize .* over",
        r"invest .* in",
        r"qr \d+ (?:billion|million)",
    ]

    diagnostic_score = sum(1 for p in diagnostic_patterns if re.search(p, query_lower))
    forecast_score = sum(1 for p in forecast_patterns if re.search(p, query_lower))
    comparative_score = sum(1 for p in comparative_patterns if re.search(p, query_lower))

    logger.info(f"📊 Question type scores: DIAGNOSTIC={diagnostic_score}, FORECAST={forecast_score}, COMPARATIVE={comparative_score}")

    if diagnostic_score >= 2 and diagnostic_score > comparative_score:
        return "DIAGNOSTIC"
    elif comparative_score >= 2 and comparative_score > diagnostic_score:
        return "COMPARATIVE"
    elif forecast_score >= 2 and forecast_score > max(diagnostic_score, comparative_score):
        return "FORECAST"
    elif diagnostic_score > 0 and forecast_score > 0:
        return "HYBRID"
    elif comparative_score > 0:
        return "COMPARATIVE"
    else:
        return "HYBRID"


def cap_unrealistic_rates(rate: float, max_realistic: float = 85.0) -> float:
    """
    Cap unrealistic success rates (>85% is unrealistic for strategic forecasting).

    FIX RUN 36: 98% success rates are inappropriate for complex strategic decisions.
    """
    if rate > max_realistic:
        logger.warning(f"⚠️ UNREALISTIC RATE DETECTED: {rate:.1f}% capped to {max_realistic}%")
        return max_realistic
    return rate


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT PROBABILITY EXTRACTION
# ═══════════════════════════════════════════════════════════════════════════════

def extract_probability_estimate(agent_output: str) -> Optional[Dict[str, Any]]:
    """
    Extract structured probability estimate from agent output.

    Looks for the structured format:
    ### PROBABILITY ESTIMATE
    **Central Estimate:** [X]%
    **Range:** [Lower]% - [Upper]%
    **Confidence:** [High/Medium/Low]

    Returns:
        Dict with 'central', 'range', 'confidence' or None if not found
    """
    if not agent_output:
        return None

    central_match = re.search(
        r'\*\*Central Estimate:\*\*\s*(\d+(?:\.\d+)?)\s*%',
        agent_output, re.IGNORECASE
    )
    range_match = re.search(
        r'\*\*Range:\*\*\s*(\d+(?:\.\d+)?)\s*%\s*[-–]\s*(\d+(?:\.\d+)?)\s*%',
        agent_output, re.IGNORECASE
    )
    confidence_match = re.search(
        r'\*\*Confidence:\*\*\s*(High|Medium|Low)',
        agent_output, re.IGNORECASE
    )

    if central_match:
        central = float(central_match.group(1)) / 100

        result: Dict[str, Any] = {'central': central}

        if range_match:
            lower = float(range_match.group(1)) / 100
            upper = float(range_match.group(2)) / 100
            result['range'] = (lower, upper)
        else:
            result['range'] = (max(0, central - 0.10), min(1, central + 0.10))

        if confidence_match:
            result['confidence'] = confidence_match.group(1).lower()
        else:
            result['confidence'] = 'medium'

        logger.info(
            f"📊 Extracted probability estimate: {central*100:.1f}% "
            f"(range: {result['range'][0]*100:.0f}%-{result['range'][1]*100:.0f}%)"
        )
        return result

    fallback_match = re.search(
        r'(?:probability|estimate|likelihood|chance)[^\d]*(\d{1,2}(?:\.\d+)?)\s*%',
        agent_output, re.IGNORECASE
    )
    if fallback_match:
        central = float(fallback_match.group(1)) / 100
        logger.info(f"📊 Extracted fallback probability: {central*100:.1f}%")
        return {
            'central': central,
            'range': (max(0, central - 0.15), min(1, central + 0.15)),
            'confidence': 'low'
        }

    return None


def aggregate_agent_estimates(agent_positions: List[Any]) -> Dict[str, Any]:
    """
    Aggregate probability estimates from multiple agents.

    Returns:
        Dict with 'consensus_probability', 'consensus_confidence', 'spread',
        'n_estimates', 'estimates'
    """
    estimates = []

    for pos in agent_positions:
        if isinstance(pos, dict):
            position_text = pos.get('position', pos.get('content', str(pos)))
        else:
            position_text = str(pos)

        estimate = extract_probability_estimate(position_text)
        if estimate:
            estimates.append(estimate)

    if not estimates:
        logger.warning("⚠️ No probability estimates extracted from agents, using default")
        return {
            'consensus_probability': 0.45,
            'consensus_confidence': 0.50,
            'spread': 0,
            'n_estimates': 0,
            'estimates': []
        }

    centrals = [e['central'] for e in estimates]
    consensus_prob = sum(centrals) / len(centrals)
    spread = max(centrals) - min(centrals) if len(centrals) > 1 else 0

    if spread < 0.10:
        consensus_conf = 0.75
    elif spread < 0.20:
        consensus_conf = 0.60
    else:
        consensus_conf = 0.45

    conf_levels = [e.get('confidence', 'medium') for e in estimates]
    high_conf_count = sum(1 for c in conf_levels if c == 'high')
    low_conf_count = sum(1 for c in conf_levels if c == 'low')

    if high_conf_count > len(estimates) / 2:
        consensus_conf = min(consensus_conf + 0.05, 0.80)
    elif low_conf_count > len(estimates) / 2:
        consensus_conf = max(consensus_conf - 0.10, 0.40)

    logger.info(
        f"📊 AGENT CONSENSUS: {consensus_prob*100:.1f}% probability "
        f"(spread: {spread*100:.1f}pp, confidence: {consensus_conf*100:.0f}%)"
    )
    estimate_strs = [f"{e['central']*100:.0f}%" for e in estimates]
    logger.info(f"   Based on {len(estimates)} agent estimates: {estimate_strs}")

    return {
        'consensus_probability': consensus_prob,
        'consensus_confidence': consensus_conf,
        'spread': spread,
        'n_estimates': len(estimates),
        'estimates': estimates
    }


def validate_output_consistency(state: Dict[str, Any], question_type: str) -> Dict[str, Any]:
    """
    PHASE 7: Validate that Summary Card and Brief show consistent probabilities.

    For DIAGNOSTIC/FORECAST questions, all probabilities must be within 15pp.
    """
    if question_type not in ("DIAGNOSTIC", "FORECAST", "HYBRID"):
        return state

    debate_verdict = state.get('debate_verdict', {})
    summary_prob = debate_verdict.get('probability', 0) / 100 if debate_verdict.get('probability') else None
    consensus_prob = state.get('consensus_probability')

    brief_prob = None
    final_synthesis = state.get('final_synthesis', '')
    if final_synthesis:
        prob_match = re.search(r'(\d{1,2}(?:\.\d+)?)\s*%', final_synthesis[:3000])
        if prob_match:
            brief_prob = float(prob_match.group(1)) / 100

    all_probs = [p for p in [summary_prob, brief_prob, consensus_prob] if p is not None]

    if len(all_probs) >= 2:
        spread = max(all_probs) - min(all_probs)

        if spread > 0.15:
            logger.error("❌ CONSISTENCY VALIDATION FAILED:")
            logger.error(f"   Summary Card: {summary_prob*100:.0f}% " if summary_prob else "   Summary Card: N/A")
            logger.error(f"   Brief: {brief_prob*100:.0f}%" if brief_prob else "   Brief: N/A")
            logger.error(f"   Consensus: {consensus_prob*100:.0f}%" if consensus_prob else "   Consensus: N/A")
            logger.error(f"   Spread: {spread*100:.1f}pp (threshold: 15pp)")

            if consensus_prob is not None and 'debate_verdict' in state:
                state['debate_verdict']['probability'] = consensus_prob * 100
                state['debate_verdict']['confidence'] = state.get('consensus_confidence', 0.55) * 100
                state['validation_override'] = True
                state['validation_error'] = f"Forced alignment: spread was {spread*100:.1f}pp"
                logger.warning(f"⚠️ FORCED ALIGNMENT: debate_verdict.probability set to {consensus_prob*100:.0f}%")

    return state
