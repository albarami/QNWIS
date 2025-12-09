"""
Diagnostic Pipeline - Bypasses Monte Carlo for Diagnostic Questions.

This pipeline is used for DIAGNOSTIC, FORECAST, and HYBRID questions where
Monte Carlo simulation would generate fabricated A/B scenarios.

Instead of Monte Carlo, agents reason INDEPENDENTLY and we calculate
consensus from their estimates.

CRITICAL: This pipeline does NOT use Monte Carlo. Agents derive their own
probability estimates based on verified data.
"""

import logging
import statistics
from dataclasses import dataclass
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


@dataclass
class AgentEstimate:
    """Individual agent's probability estimate."""
    agent_name: str
    probability: float  # 0.0 to 1.0
    confidence: str     # "low", "moderate", "high"
    reasoning: str
    key_factors: List[str]


@dataclass
class ConsensusResult:
    """Aggregated consensus from multiple agents."""
    probability: float       # 0.0 to 1.0
    confidence: float        # 0.0 to 1.0
    agent_estimates: List[AgentEstimate]
    spread: float            # max - min estimate (0-1 scale)
    disagreement_level: str  # "low", "moderate", "high"
    n_agents: int


def should_use_diagnostic_pipeline(state: Dict) -> bool:
    """
    Determine if this question should use the diagnostic pipeline.
    
    Returns True for DIAGNOSTIC, FORECAST, HYBRID questions.
    Returns False for COMPARATIVE questions.
    """
    question_type = state.get('question_type', 'COMPARATIVE')
    
    if isinstance(question_type, str):
        question_type = question_type.upper()
    
    return question_type in ('DIAGNOSTIC', 'FORECAST', 'HYBRID')


def extract_agent_probability(agent_output: str, agent_name: str) -> Optional[AgentEstimate]:
    """
    Extract structured probability estimate from agent output.
    
    Looks for patterns like:
    - **My Probability Estimate:** 45%
    - **Central Estimate:** 45%
    - Probability: 40-50%
    
    Args:
        agent_output: Raw text output from agent
        agent_name: Name of the agent
        
    Returns:
        AgentEstimate or None if not found
    """
    import re
    
    if not agent_output:
        return None
    
    # Try various probability patterns
    patterns = [
        # Explicit estimate format
        r'\*\*(?:My Probability Estimate|Central Estimate|Probability Estimate):\*\*\s*(\d+(?:\.\d+)?)\s*%',
        r'\*\*(?:My Probability Estimate|Central Estimate|Probability Estimate):\*\*\s*(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*%',
        # Confidence patterns
        r'probability[^\d]*(\d+(?:\.\d+)?)\s*%',
        r'(\d+(?:\.\d+)?)\s*%\s*(?:probability|likelihood|chance)',
        # Range patterns
        r'(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*%',
    ]
    
    probability = None
    
    for pattern in patterns:
        match = re.search(pattern, agent_output, re.IGNORECASE)
        if match:
            if len(match.groups()) == 2:
                # Range - take midpoint
                low = float(match.group(1))
                high = float(match.group(2))
                probability = (low + high) / 2 / 100
            else:
                probability = float(match.group(1)) / 100
            break
    
    if probability is None:
        return None
    
    # Clamp to valid range
    probability = max(0.0, min(1.0, probability))
    
    # Extract confidence level
    confidence = 'moderate'
    if re.search(r'\*\*Confidence:\*\*\s*(?:High|high)', agent_output):
        confidence = 'high'
    elif re.search(r'\*\*Confidence:\*\*\s*(?:Low|low)', agent_output):
        confidence = 'low'
    
    # Extract key factors (look for numbered lists)
    factors = []
    factor_matches = re.findall(r'\d+\.\s*([^\n]+)', agent_output)
    factors = factor_matches[:3]  # Take first 3
    
    # Extract reasoning (first paragraph after "Reasoning")
    reasoning = ""
    reasoning_match = re.search(r'\*\*Reasoning:\*\*\s*([^\n]+(?:\n[^\n]+)?)', agent_output, re.IGNORECASE)
    if reasoning_match:
        reasoning = reasoning_match.group(1).strip()
    
    logger.info(f"📊 Extracted from {agent_name}: {probability*100:.0f}% ({confidence} confidence)")
    
    return AgentEstimate(
        agent_name=agent_name,
        probability=probability,
        confidence=confidence,
        reasoning=reasoning,
        key_factors=factors
    )


def calculate_consensus(estimates: List[AgentEstimate]) -> ConsensusResult:
    """
    Aggregate independent agent estimates into consensus.
    
    Key insight: Disagreement reveals uncertainty.
    - Low spread (<10pp) = high confidence in consensus
    - Moderate spread (10-20pp) = moderate confidence
    - High spread (>20pp) = low confidence
    
    Args:
        estimates: List of agent probability estimates
        
    Returns:
        ConsensusResult with aggregated values
    """
    if not estimates:
        logger.warning("⚠️ No agent estimates to aggregate, using default")
        return ConsensusResult(
            probability=0.45,  # Conservative default
            confidence=0.50,
            agent_estimates=[],
            spread=0.0,
            disagreement_level="unknown",
            n_agents=0
        )
    
    probabilities = [e.probability for e in estimates]
    
    # Calculate spread
    spread = max(probabilities) - min(probabilities)
    
    # Determine disagreement level and confidence
    if spread < 0.10:
        disagreement = "low"
        confidence = 0.70
    elif spread < 0.20:
        disagreement = "moderate"
        confidence = 0.55
    else:
        disagreement = "high"
        confidence = 0.40
    
    # Use trimmed mean if enough estimates (exclude outliers)
    if len(probabilities) >= 5:
        sorted_probs = sorted(probabilities)
        trimmed = sorted_probs[1:-1]  # Remove highest and lowest
        consensus_prob = statistics.mean(trimmed)
    else:
        consensus_prob = statistics.mean(probabilities)
    
    # Adjust confidence based on individual agent confidence levels
    high_conf_count = sum(1 for e in estimates if e.confidence == 'high')
    low_conf_count = sum(1 for e in estimates if e.confidence == 'low')
    
    if high_conf_count > len(estimates) / 2:
        confidence = min(confidence + 0.05, 0.75)
    elif low_conf_count > len(estimates) / 2:
        confidence = max(confidence - 0.10, 0.35)
    
    logger.info(f"📊 CONSENSUS CALCULATION:")
    logger.info(f"   Agent probabilities: {[f'{p*100:.0f}%' for p in probabilities]}")
    logger.info(f"   Spread: {spread*100:.1f}pp")
    logger.info(f"   Disagreement: {disagreement}")
    logger.info(f"   Consensus probability: {consensus_prob*100:.1f}%")
    logger.info(f"   Consensus confidence: {confidence*100:.0f}%")
    
    return ConsensusResult(
        probability=consensus_prob,
        confidence=confidence,
        agent_estimates=estimates,
        spread=spread,
        disagreement_level=disagreement,
        n_agents=len(estimates)
    )


def apply_diagnostic_consensus(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply diagnostic pipeline consensus to state.
    
    This function:
    1. Extracts probability estimates from agent outputs
    2. Calculates consensus
    3. Stores results in state for use by Summary Card and Brief
    
    Args:
        state: Workflow state
        
    Returns:
        Updated state with consensus values
    """
    logger.info("📊 DIAGNOSTIC PIPELINE: Calculating agent consensus")
    
    # Collect agent outputs from various sources
    agent_outputs = []
    
    # From conversation history
    conversation = state.get('conversation_history', [])
    if not conversation:
        conversation = state.get('debate_results', {}).get('conversation_history', [])
    
    for turn in conversation:
        agent_name = turn.get('agent', turn.get('speaker', 'Unknown'))
        content = turn.get('message', turn.get('content', ''))
        if content and agent_name:
            agent_outputs.append((agent_name, content))
    
    # From agent reports
    agent_reports = state.get('agent_reports_map', {})
    for name, report in agent_reports.items():
        if report:
            narrative = getattr(report, 'narrative', str(report))
            if narrative:
                agent_outputs.append((name, narrative))
    
    logger.info(f"   Found {len(agent_outputs)} agent outputs to process")
    
    # Extract estimates from each agent
    estimates = []
    seen_agents = set()
    
    for agent_name, output in agent_outputs:
        # Avoid duplicates from same agent
        if agent_name in seen_agents:
            continue
        
        estimate = extract_agent_probability(output, agent_name)
        if estimate:
            estimates.append(estimate)
            seen_agents.add(agent_name)
    
    logger.info(f"   Extracted {len(estimates)} valid probability estimates")
    
    # Calculate consensus
    consensus = calculate_consensus(estimates)
    
    # Store in state
    state['consensus_probability'] = consensus.probability
    state['consensus_confidence'] = consensus.confidence
    state['consensus_spread'] = consensus.spread
    state['agent_estimates'] = [e.probability for e in consensus.agent_estimates]
    state['monte_carlo_valid'] = False  # Mark Monte Carlo as invalid
    state['probability_source'] = 'agent_consensus'
    
    # Update debate_verdict for frontend
    if 'debate_verdict' not in state:
        state['debate_verdict'] = {}
    
    state['debate_verdict'].update({
        'probability': consensus.probability * 100,
        'confidence': consensus.confidence * 100,
        'source': 'agent_consensus',
        'monte_carlo_valid': False,
        'question_type': state.get('question_type', 'DIAGNOSTIC'),
        'consensus_spread': consensus.spread * 100,
        'n_agent_estimates': consensus.n_agents,
        'disagreement_level': consensus.disagreement_level,
    })
    
    logger.info(f"✅ DIAGNOSTIC CONSENSUS APPLIED:")
    logger.info(f"   Probability: {consensus.probability*100:.1f}%")
    logger.info(f"   Confidence: {consensus.confidence*100:.0f}%")
    logger.info(f"   Based on {consensus.n_agents} agent estimates")
    
    return state


# Calibration guidance for different question types
CALIBRATION_GUIDANCE = {
    'structural_reform': {
        'typical_range': (0.25, 0.55),
        'description': 'Structural economic reforms typically have 25-55% success rate',
    },
    'policy_reversal': {
        'typical_range': (0.20, 0.50),
        'description': 'Reversing entrenched problems by deadline: 20-50% probability',
    },
    'technology_adoption': {
        'typical_range': (0.40, 0.70),
        'description': 'Technology adoption initiatives: 40-70% success rate',
    },
    'market_entry': {
        'typical_range': (0.30, 0.60),
        'description': 'New market entry success: 30-60% probability',
    },
    'diversification': {
        'typical_range': (0.35, 0.65),
        'description': 'Economic diversification efforts: 35-65% success rate',
    },
}


def get_calibration_warning(probability: float, question_context: str) -> Optional[str]:
    """
    Check if probability estimate is outside typical range for this type of question.
    
    Returns warning message if estimate seems implausible.
    """
    # Very high estimates for complex reforms are suspicious
    if probability > 0.85:
        return (
            f"⚠️ Estimate of {probability*100:.0f}% is unusually high for complex strategic questions. "
            f"Historical base rates for structural reforms are typically 25-65%."
        )
    
    # Very low estimates for reasonable initiatives are also suspicious
    if probability < 0.15:
        return (
            f"⚠️ Estimate of {probability*100:.0f}% is unusually low. "
            f"Please verify this isn't overly pessimistic."
        )
    
    return None

