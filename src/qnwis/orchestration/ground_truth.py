"""
Ground Truth Module - Single Source of Truth for All Outputs.

This module provides a centralized way to extract authoritative numbers
that BOTH Summary Card AND Brief must use. This prevents the inconsistency
where Summary Card shows 85% and Brief shows 45%.

CRITICAL: All output components (Summary Card, Brief, API response) 
MUST use extract_ground_truth() to get their numbers.
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class QuestionType(Enum):
    """Question type classification."""
    COMPARATIVE = "comparative"   # "Should we do A or B?"
    DIAGNOSTIC = "diagnostic"     # "What is probability of X?"
    FORECAST = "forecast"         # "What will happen by 2030?"
    HYBRID = "hybrid"             # Combined


class ScenarioType(Enum):
    """Scenario outcome classification."""
    TIED = "tied"                    # gap < 5pp
    MODERATE_ADVANTAGE = "moderate"  # 5pp <= gap < 15pp
    CLEAR_WINNER = "clear"           # gap >= 15pp


@dataclass
class GroundTruth:
    """
    Single Source of Truth - ALL outputs use this.
    
    This dataclass contains the authoritative numbers that must be
    used consistently across Summary Card, Brief, and API response.
    """
    
    # Core metrics (always present)
    probability: float           # 0.0 to 1.0
    confidence: float            # 0.0 to 1.0
    question_type: QuestionType
    source: str                  # "agent_consensus" or "scenario_analysis"
    
    # For comparative questions only
    best_option: Optional[str] = None
    best_rate: Optional[float] = None      # Percentage (0-100)
    worst_option: Optional[str] = None
    worst_rate: Optional[float] = None     # Percentage (0-100)
    gap_pp: Optional[float] = None         # Gap in percentage points
    scenario_type: Optional[ScenarioType] = None
    
    # For diagnostic questions - agent estimates
    agent_estimates: List[float] = field(default_factory=list)  # List of probabilities (0-1)
    agent_spread: float = 0.0              # max - min estimate
    
    # Metadata
    recommendation: Optional[str] = None
    decision: Optional[str] = None
    is_close_call: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        # Get consistent verdict
        verdict = determine_verdict(self.probability, self.question_type.value)
        
        return {
            'probability': self.probability,
            'probability_percent': round(self.probability * 100, 1),
            'confidence': self.confidence,
            'confidence_percent': round(self.confidence * 100, 0),
            'question_type': self.question_type.value,
            'source': self.source,
            'best_option': self.best_option,
            'best_rate': self.best_rate,
            'worst_option': self.worst_option,
            'worst_rate': self.worst_rate,
            'gap_pp': self.gap_pp,
            'scenario_type': self.scenario_type.value if self.scenario_type else None,
            'agent_estimates': self.agent_estimates,
            'agent_spread': self.agent_spread,
            'recommendation': self.recommendation,
            'decision': self.decision,
            'is_close_call': self.is_close_call,
            # FIX RUN 57: Consistent verdict from centralized function
            'verdict': verdict['verdict'],
            'verdict_color': verdict['color'],
            'verdict_recommendation': verdict['recommendation'],
        }


@dataclass
class VerdictResult:
    """Consistent verdict determination result."""
    verdict: str           # e.g., "LIKELY ACHIEVABLE", "UNCERTAIN - EXECUTION DEPENDENT"
    color: str             # green, yellow, orange, red
    recommendation: str    # Action recommendation
    short_verdict: str     # GO, CONDITIONAL GO, RECONSIDER, NO GO


def determine_verdict(probability: float, question_type: str) -> Dict[str, str]:
    """
    CENTRALIZED verdict determination - SINGLE SOURCE OF TRUTH.
    
    FIX RUN 57: This function ensures consistent verdicts across all outputs.
    Both Summary Card and Brief MUST use this function.
    
    Args:
        probability: Success probability (0.0 to 1.0)
        question_type: COMPARATIVE, DIAGNOSTIC, FORECAST, or HYBRID
        
    Returns:
        Dict with verdict, color, recommendation, and short_verdict
    """
    question_type_upper = question_type.upper() if isinstance(question_type, str) else "COMPARATIVE"
    
    if question_type_upper in ('FORECAST', 'DIAGNOSTIC', 'HYBRID'):
        # FORECAST/DIAGNOSTIC: Use probability-based verdicts
        # These are SINGLE OUTCOME questions (not A vs B)
        if probability >= 0.60:
            return {
                'verdict': 'LIKELY ACHIEVABLE',
                'color': 'green',
                'recommendation': 'Proceed with current approach and standard monitoring',
                'short_verdict': 'GO'
            }
        elif probability >= 0.45:
            return {
                'verdict': 'UNCERTAIN - EXECUTION DEPENDENT',
                'color': 'yellow',
                'recommendation': 'Proceed with enhanced monitoring and contingency plans',
                'short_verdict': 'CONDITIONAL GO'
            }
        elif probability >= 0.30:
            return {
                'verdict': 'CHALLENGING - REFORMS NEEDED',
                'color': 'orange',
                'recommendation': 'Consider timeline adjustments or accelerated reform measures',
                'short_verdict': 'RECONSIDER'
            }
        else:
            return {
                'verdict': 'UNLIKELY WITHOUT MAJOR CHANGES',
                'color': 'red',
                'recommendation': 'Fundamental reassessment of approach required',
                'short_verdict': 'NO GO'
            }
    else:
        # COMPARATIVE: Use gap-based verdicts (A vs B questions)
        if probability >= 0.65:
            return {
                'verdict': 'CLEAR ADVANTAGE',
                'color': 'green',
                'recommendation': 'Proceed with recommended option',
                'short_verdict': 'GO'
            }
        elif probability >= 0.50:
            return {
                'verdict': 'MODERATE ADVANTAGE',
                'color': 'yellow',
                'recommendation': 'Proceed with monitoring of key risk factors',
                'short_verdict': 'CONDITIONAL GO'
            }
        elif probability >= 0.40:
            return {
                'verdict': 'MARGINAL DIFFERENCE',
                'color': 'orange',
                'recommendation': 'Consider secondary factors before deciding',
                'short_verdict': 'RECONSIDER'
            }
        else:
            return {
                'verdict': 'INSUFFICIENT EVIDENCE',
                'color': 'red',
                'recommendation': 'Gather more data before proceeding',
                'short_verdict': 'NO GO'
            }


def extract_ground_truth(state: Dict[str, Any]) -> GroundTruth:
    """
    Extract ground truth from workflow state.
    
    CRITICAL: This is the ONLY function that determines authoritative numbers.
    Both Summary Card AND Brief MUST use this function.
    
    Args:
        state: Workflow state dictionary
        
    Returns:
        GroundTruth object with authoritative values
    """
    question_type_str = state.get('question_type', 'COMPARATIVE')
    
    # Normalize question type
    if isinstance(question_type_str, str):
        question_type_str = question_type_str.upper()
    
    logger.info(f"📊 GROUND TRUTH: Extracting for question_type={question_type_str}")
    
    if question_type_str in ('DIAGNOSTIC', 'FORECAST', 'HYBRID'):
        return _extract_diagnostic_ground_truth(state, question_type_str)
    else:
        return _extract_comparative_ground_truth(state)


def _extract_diagnostic_ground_truth(state: Dict, question_type_str: str) -> GroundTruth:
    """
    Extract ground truth for DIAGNOSTIC/FORECAST questions.
    
    PRIORITY ORDER (Debate > Consensus > Feasibility):
    1. debate_verdict.probability - from debate synthesis (BEST)
    2. consensus_probability - aggregated agent estimates
    3. feasibility_check.probability - fallback only
    
    Uses agent consensus/debate, NOT Monte Carlo.
    """
    debate_verdict = state.get('debate_verdict', {})
    feasibility_check = state.get('feasibility_check', {})
    
    # PRIORITY 1: Get probability from debate verdict (most reliable)
    debate_prob = debate_verdict.get('probability')
    if debate_prob is not None and debate_prob > 0:
        consensus_prob = debate_prob if debate_prob <= 1 else debate_prob / 100
        logger.info(f"📊 Using debate_verdict.probability: {consensus_prob*100:.1f}%")
    else:
        # PRIORITY 2: Try consensus probability from state
        consensus_prob = state.get('consensus_probability')
        if consensus_prob is not None and consensus_prob > 0:
            consensus_prob = consensus_prob if consensus_prob <= 1 else consensus_prob / 100
            logger.info(f"📊 Using consensus_probability: {consensus_prob*100:.1f}%")
        else:
            # PRIORITY 3: Extract from debate synthesis text
            synthesis = state.get('final_synthesis', '') or state.get('debate_synthesis', '')
            extracted_prob = _extract_probability_from_text(synthesis)
            if extracted_prob:
                consensus_prob = extracted_prob
                logger.info(f"📊 Extracted probability from synthesis text: {consensus_prob*100:.1f}%")
            else:
                # FALLBACK: Use feasibility ratio (but this is less reliable)
                feas_ratio = feasibility_check.get('ratio', 0.45)
                consensus_prob = feas_ratio if feas_ratio <= 1 else feas_ratio / 100
                logger.warning(f"⚠️ Falling back to feasibility ratio: {consensus_prob*100:.1f}%")
    
    # Get confidence from debate verdict or calculate
    consensus_conf = debate_verdict.get('confidence', state.get('consensus_confidence', 0.55))
    if consensus_conf and consensus_conf > 1:
        consensus_conf = consensus_conf / 100
    
    agent_estimates = state.get('agent_estimates', [])
    
    # Calculate spread if we have estimates
    if agent_estimates:
        spread = max(agent_estimates) - min(agent_estimates)
    else:
        spread = state.get('consensus_spread', 0)
    
    # Map string to enum
    qt_map = {
        'DIAGNOSTIC': QuestionType.DIAGNOSTIC,
        'FORECAST': QuestionType.FORECAST,
        'HYBRID': QuestionType.HYBRID,
    }
    question_type = qt_map.get(question_type_str, QuestionType.DIAGNOSTIC)
    
    # Determine if close call based on spread
    is_close_call = spread > 0.15  # High disagreement among agents
    
    recommendation = debate_verdict.get('recommendation', None)
    decision = debate_verdict.get('decision', None)
    
    # Generate feasibility warning if applicable (but don't override probability)
    feasibility_warning = None
    feas_ratio = feasibility_check.get('ratio', 1.0) if isinstance(feasibility_check, dict) else 1.0
    if feas_ratio < 0.5:
        feasibility_warning = f"Note: Feasibility ratio ({feas_ratio:.0%}) indicates structural challenges"
    
    logger.info(f"📊 DIAGNOSTIC GROUND TRUTH:")
    logger.info(f"   Source: debate_consensus (OVERRIDES feasibility)")
    logger.info(f"   Probability: {consensus_prob*100:.1f}%")
    logger.info(f"   Confidence: {consensus_conf*100:.0f}%")
    logger.info(f"   Agent estimates: {[f'{e*100:.0f}%' for e in agent_estimates]}")
    logger.info(f"   Spread: {spread*100:.1f}pp")
    logger.info(f"   Feasibility warning: {feasibility_warning}")
    
    return GroundTruth(
        probability=consensus_prob,
        confidence=consensus_conf,
        question_type=question_type,
        source='debate_consensus',
        agent_estimates=agent_estimates,
        agent_spread=spread,
        is_close_call=is_close_call,
        recommendation=recommendation,
        decision=decision,
    )


def _extract_probability_from_text(text: str) -> Optional[float]:
    """
    Extract probability from debate synthesis text.
    Looks for patterns like "63% probability" or "~63% chance".
    """
    if not text:
        return None
    
    # Look for probability patterns
    patterns = [
        r'~?\s*(\d{1,2}(?:\.\d+)?)\s*%\s*(?:probability|chance|likelihood|success)',
        r'(?:probability|chance|likelihood)\s*(?:of|at)\s*~?\s*(\d{1,2}(?:\.\d+)?)\s*%',
        r'(\d{1,2}(?:\.\d+)?)\s*-\s*(\d{1,2}(?:\.\d+)?)\s*%\s*(?:probability|chance|likelihood|success)',
        r'estimate[sd]?\s*(?:at|of)?\s*~?\s*(\d{1,2}(?:\.\d+)?)\s*%',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            if len(match.groups()) == 2:
                # Range - take midpoint
                low, high = float(match.group(1)), float(match.group(2))
                return (low + high) / 2 / 100
            else:
                return float(match.group(1)) / 100
    
    return None


def _extract_comparative_ground_truth(state: Dict) -> GroundTruth:
    """
    Extract ground truth for COMPARATIVE questions.
    Uses scenario analysis results.
    """
    # Try to get from debate_verdict first (most reliable)
    debate_verdict = state.get('debate_verdict', {})
    
    # Get scenario ground truth
    best_option = debate_verdict.get('ground_truth_winner') or debate_verdict.get('recommendation')
    best_rate = debate_verdict.get('ground_truth_rate') or debate_verdict.get('probability', 50)
    worst_option = debate_verdict.get('ground_truth_loser', 'Alternative')
    worst_rate = debate_verdict.get('ground_truth_loser_rate', 50)
    gap = debate_verdict.get('ground_truth_gap') or debate_verdict.get('scenario_gap', 0)
    
    # If not in debate_verdict, try scenario_ground_truth
    if not best_option:
        scenario_gt = state.get('scenario_ground_truth', {})
        best_option = scenario_gt.get('best_option', 'Option A')
        best_rate = scenario_gt.get('best_rate', 50)
        worst_option = scenario_gt.get('worst_option', 'Option B')
        worst_rate = scenario_gt.get('worst_rate', 50)
        gap = scenario_gt.get('gap', 0)
    
    # Determine scenario type based on gap
    if gap < 5:
        scenario_type = ScenarioType.TIED
        confidence = min(0.60, state.get('calibrated_confidence', 55) / 100)
    elif gap < 15:
        scenario_type = ScenarioType.MODERATE_ADVANTAGE
        confidence = min(0.70, state.get('calibrated_confidence', 65) / 100)
    else:
        scenario_type = ScenarioType.CLEAR_WINNER
        confidence = min(0.80, state.get('calibrated_confidence', 75) / 100)
    
    is_close_call = debate_verdict.get('is_close_call', gap < 10)
    
    logger.info(f"📊 COMPARATIVE GROUND TRUTH:")
    logger.info(f"   Source: scenario_analysis")
    logger.info(f"   Best: {best_option} at {best_rate:.1f}%")
    logger.info(f"   Worst: {worst_option} at {worst_rate:.1f}%")
    logger.info(f"   Gap: {gap:.1f}pp")
    logger.info(f"   Scenario type: {scenario_type.value}")
    logger.info(f"   Confidence: {confidence*100:.0f}%")
    
    return GroundTruth(
        probability=best_rate / 100 if best_rate > 1 else best_rate,
        confidence=confidence,
        question_type=QuestionType.COMPARATIVE,
        source='scenario_analysis',
        best_option=best_option,
        best_rate=best_rate,
        worst_option=worst_option,
        worst_rate=worst_rate,
        gap_pp=gap,
        scenario_type=scenario_type,
        is_close_call=is_close_call,
        recommendation=best_option,
        decision=debate_verdict.get('decision', 'GO' if confidence >= 0.6 else 'CONDITIONAL GO'),
    )


def validate_no_fabrication(text: str, gt: GroundTruth) -> List[str]:
    """
    Validate that text contains no fabricated numbers.
    
    Args:
        text: Text to validate (e.g., Brief content)
        gt: Ground truth to compare against
        
    Returns:
        List of fabrication warnings (empty if valid)
    """
    warnings = []
    
    # Extract all percentages from text
    found_percentages = re.findall(r'(\d{1,2}(?:\.\d)?)\s*%', text)
    found = [float(p) for p in found_percentages]
    
    # Build allowed set from ground truth
    allowed = {
        round(gt.probability * 100, 1),
        round(gt.confidence * 100, 0),
    }
    if gt.best_rate:
        allowed.add(round(gt.best_rate, 1))
    if gt.worst_rate:
        allowed.add(round(gt.worst_rate, 1))
    if gt.agent_estimates:
        for e in gt.agent_estimates:
            allowed.add(round(e * 100, 0))
    
    # Add benign constants (commonly used non-fabricated values)
    allowed.update({50, 60, 65, 70, 75, 80, 85, 90, 95, 100})
    
    # Check each found percentage
    for pct in found:
        if pct > 10:  # Ignore small numbers (likely dates, counts)
            closest = min(allowed, key=lambda x: abs(x - pct))
            if abs(pct - closest) > 5:  # Allow 5pp tolerance
                warnings.append(
                    f"Potential fabrication: {pct}% not in ground truth "
                    f"(closest allowed: {closest}%)"
                )
    
    if warnings:
        logger.warning(f"⚠️ FABRICATION CHECK: {len(warnings)} potential issues")
        for w in warnings:
            logger.warning(f"   {w}")
    else:
        logger.info(f"✅ FABRICATION CHECK: All percentages validated")
    
    return warnings


def format_ground_truth_for_prompt(gt: GroundTruth) -> str:
    """
    Format ground truth for injection into Brief prompt.
    This ensures Brief LLM knows the exact numbers to use.
    """
    if gt.question_type == QuestionType.COMPARATIVE:
        return f"""
═══════════════════════════════════════════════════════════════════════════════
BINDING GROUND TRUTH (YOU MUST USE THESE EXACT VALUES)
═══════════════════════════════════════════════════════════════════════════════

QUESTION TYPE: COMPARATIVE

AUTHORITATIVE RATES:
• Best Option: {gt.best_option} at {gt.best_rate:.1f}%
• Alternative: {gt.worst_option} at {gt.worst_rate:.1f}%
• Gap: {gt.gap_pp:.1f} percentage points
• Scenario Type: {gt.scenario_type.value.title() if gt.scenario_type else 'Unknown'}

CONFIDENCE: {gt.confidence*100:.0f}%

CRITICAL: Use ONLY these numbers in your brief. Any other percentages will be flagged as fabrication.
═══════════════════════════════════════════════════════════════════════════════
"""
    else:
        agent_range = ""
        if gt.agent_estimates:
            agent_range = f"\n• Expert Range: {min(gt.agent_estimates)*100:.0f}% - {max(gt.agent_estimates)*100:.0f}%"
        
        return f"""
═══════════════════════════════════════════════════════════════════════════════
BINDING GROUND TRUTH (YOU MUST USE THESE EXACT VALUES)
═══════════════════════════════════════════════════════════════════════════════

QUESTION TYPE: {gt.question_type.value.upper()}

AUTHORITATIVE ESTIMATE:
• Success Probability: {gt.probability*100:.0f}%
• Confidence: {gt.confidence*100:.0f}%{agent_range}
• Source: Expert Consensus (NOT Monte Carlo)

CRITICAL: 
1. Use ONLY these numbers in your brief
2. Do NOT cite Monte Carlo scenario rates
3. Any fabricated percentages will be flagged

═══════════════════════════════════════════════════════════════════════════════
"""

