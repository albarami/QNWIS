"""
Query Classifier Node.

Analyzes query complexity to determine the routing strategy.

PHASE 1 FIX: Added question_type classification to distinguish:
- COMPARATIVE: "A vs B, which is better?" (use Monte Carlo)
- DIAGNOSTIC: "What are the root causes?" (agents derive estimates)
- FORECAST: "What is the probability of X?" (agents derive estimates)
- HYBRID: Combination of above
"""

from __future__ import annotations

import logging
import re
from typing import List, Literal

from ..state import IntelligenceState

logger = logging.getLogger(__name__)


def _matches_any(patterns: List[str], text: str) -> bool:
    """Return True if any pattern matches the provided text."""
    return any(re.search(pattern, text) for pattern in patterns)


def _count_matches(patterns: List[str], text: str) -> int:
    """Count how many patterns match the text."""
    return sum(1 for p in patterns if re.search(p, text))


def classify_question_type(query: str) -> Literal["COMPARATIVE", "DIAGNOSTIC", "FORECAST", "HYBRID"]:
    """
    Classify question type BEFORE scenario generation.
    
    This determines whether to use Monte Carlo A/B scenarios (COMPARATIVE)
    or let agents derive their own probability estimates (DIAGNOSTIC/FORECAST).
    
    Args:
        query: The user's question
        
    Returns:
        Question type classification
    """
    query_lower = query.lower()
    
    # DIAGNOSTIC patterns - asking about causes/reasons/factors
    DIAGNOSTIC_PATTERNS = [
        r"what are the (?:root )?causes",
        r"why (?:is|has|did|does|are|do)",
        r"what (?:explains|drives|factors)",
        r"analyze the (?:impact|effect|consequences)",
        r"what (?:is|are) the (?:main|key|primary) (?:driver|factor|cause)",
        r"explain (?:why|how)",
        r"root cause",
        r"underlying factor",
        r"what led to",
        r"stagnation",
        r"reason(?:s)? (?:for|behind)",
    ]
    
    # FORECAST patterns - asking about probability/likelihood
    FORECAST_PATTERNS = [
        r"what is the probability",
        r"probability that",
        r"will .* (?:succeed|reverse|achieve|fail)",
        r"can .* (?:be achieved|happen|occur)",
        r"likelihood of",
        r"chances of",
        r"(?:can|will|could) .* (?:be achieved|succeed|fail)",
        r"what (?:is|are) the (?:chance|likelihood|prospect)",
        r"estimate the probability",
        r"by \d{4}",  # Timeline target like "by 2030"
        r"reverse this trend",
    ]
    
    # COMPARATIVE patterns - asking to choose between options
    COMPARATIVE_PATTERNS = [
        r"should (?:we|qatar|the ministry) (?:invest|allocate|choose|pursue|prioritize)",
        r"which (?:is better|should we|option|path|strategy)",
        r"(?:better|prefer|recommend) .* or",
        r"(?:option a|option b)",
        r"(?:between|versus|vs\.?)\s+\w+",
        r"(?:tourism|ai|technology|hub).* (?:or|vs)",
        r"prioritize .* over",
        r"invest .* in .* or",
        r"qr \d+ (?:billion|million)",  # Investment amount suggests A/B
        r"allocate .* between",
        r"compare .* (?:to|with|and|versus)",
    ]
    
    # Count matches for each type
    diagnostic_score = _count_matches(DIAGNOSTIC_PATTERNS, query_lower)
    forecast_score = _count_matches(FORECAST_PATTERNS, query_lower)
    comparative_score = _count_matches(COMPARATIVE_PATTERNS, query_lower)
    
    logger.info("📊 Question type classification scores:")
    logger.info(f"   DIAGNOSTIC: {diagnostic_score}")
    logger.info(f"   FORECAST: {forecast_score}")
    logger.info(f"   COMPARATIVE: {comparative_score}")
    
    # Classification logic
    # HYBRID: Both diagnostic AND forecast patterns present
    if diagnostic_score >= 1 and forecast_score >= 1:
        question_type = "HYBRID"
    # DIAGNOSTIC: Strong diagnostic signal, weak comparative
    elif diagnostic_score >= 2 and diagnostic_score > comparative_score:
        question_type = "DIAGNOSTIC"
    # FORECAST: Strong forecast signal, weak comparative
    elif forecast_score >= 2 and forecast_score > comparative_score:
        question_type = "FORECAST"
    # COMPARATIVE: Any comparative signal (default for investment questions)
    elif comparative_score >= 1:
        question_type = "COMPARATIVE"
    # DIAGNOSTIC: Any diagnostic signal
    elif diagnostic_score >= 1:
        question_type = "DIAGNOSTIC"
    # FORECAST: Any forecast signal
    elif forecast_score >= 1:
        question_type = "FORECAST"
    # Default: COMPARATIVE (safest - keeps existing behavior)
    else:
        question_type = "COMPARATIVE"
    
    logger.info(f"✅ Question type classified as: {question_type}")
    return question_type


def classify_query_node(state: IntelligenceState) -> IntelligenceState:
    """
    Node 1: Classify query complexity AND question type.

    Complexity routes to:
    - "simple": Quick fact lookup (skip most agents)
    - "medium": Single domain analysis
    - "complex": Full multi-agent analysis
    - "critical": Emergency analysis (parallel execution)
    
    Question type routes to:
    - "COMPARATIVE": Use Monte Carlo A/B scenarios
    - "DIAGNOSTIC": Agents derive estimates, skip fabricated rates
    - "FORECAST": Agents derive estimates, skip fabricated rates
    - "HYBRID": Combined diagnostic + forecast
    """
    # CRITICAL DEBUG - What is the state we receive?
    logger.warning(f"🔍 classify_query_node received state keys: {list(state.keys())}")
    logger.warning(f"🔍 classify_query_node state['query'] = {repr(state.get('query', 'NOT_FOUND'))}")
    logger.warning(f"🔍 classify_query_node state type = {type(state)}")

    query_original = state.get("query", "")
    if not query_original:
        logger.error("❌ CRITICAL: Query is empty in classifier node!")
    query = query_original.lower()
    
    # PHASE 1: Classify QUESTION TYPE (determines scenario generation behavior)
    question_type = classify_question_type(query_original)
    state["question_type"] = question_type
    
    # EXPLICIT PRINT FOR DEBUGGING (bypasses log level issues)
    print(f"\n{'='*70}")
    print("[CHECKPOINT 1] CLASSIFIER NODE - QUESTION TYPE")
    print(f"{'='*70}")
    print(f"[CHECKPOINT 1] Question type: {question_type}")
    print(f"[CHECKPOINT 1] Query: {query_original[:100]}...")
    print(f"[CHECKPOINT 1] state['question_type'] = {state.get('question_type')}")
    print(f"{'='*70}\n")
    
    logger.warning("[CHECKPOINT 1] ═══════════════════════════════════════════════")
    logger.warning(f"[CHECKPOINT 1] Question type classified: {question_type}")
    logger.warning(f"[CHECKPOINT 1] state['question_type'] = {state.get('question_type')}")
    logger.warning(f"[CHECKPOINT 1] Query: {query_original[:100]}...")
    logger.warning("[CHECKPOINT 1] ═══════════════════════════════════════════════")

    # Critical: Urgent/emergency queries
    critical_patterns = [
        r"urgent",
        r"emergency",
        r"crisis",
        r"dropped \d+%",
        r"stock.*dropped",
        r"immediate",
    ]

    # Complex: Strategic decisions requiring multi-agent debate
    complex_patterns = [
        r"should we",
        r"recommend.*strategy",
        r"analyze.*vs",
        r"compare.*and.*",
        r"evaluate.*decision",
        r"diversification.*progress",
        r"assess.*security",
        r"implications? of",         # "What are the implications of..."
        r"impact of",                # "What is the impact of..."
        r"effects? of",              # "What are the effects of..."
        r"consequences? of",         # "What are the consequences of..."
        r"pros and cons",            # "What are pros and cons..."
    ]

    # Medium: Single domain analysis
    medium_patterns = [
        r"how (is|was)",
        r"what are.*trends",
        r"analyze.*performance",
        r"show.*breakdown",
        r"explain.*changes",
    ]

    # Simple: Single fact lookup
    simple_patterns = [
        r"what (is|was).*\d{4}",    # "What is GDP in 2024?"
        r"show me.*latest",          # "Show me latest data"
        r"what.*current",            # "What is current GDP?" (FIXED)
        r"what.*latest",             # "What is latest unemployment?"
        r"when did",                 # "When did..."
        r"^what is ",                # "What is unemployment rate?" (simple fact)
        r"^what are ",               # "What are latest numbers?" (simple fact)
    ]

    # MINISTER-GRADE: Classify all queries as at least "complex"
    # No query is "simple" when ministers are the audience
    if _matches_any(critical_patterns, query):
        complexity = "critical"
    elif _matches_any(complex_patterns, query):
        complexity = "complex"
    else:
        # EVERYTHING ELSE IS COMPLEX - ministers expect thorough analysis
        complexity = "complex"
    
    logger.info(f"✅ Query classified as: {complexity} (minister-grade: full analysis)")

    reasoning_chain = state.setdefault("reasoning_chain", [])
    nodes_executed = state.setdefault("nodes_executed", [])

    reasoning_chain.append(f"Query classified as: {complexity}")
    reasoning_chain.append(f"Question type: {question_type}")
    nodes_executed.append("classifier")
    state["complexity"] = complexity
    
    # Log routing decision for DIAGNOSTIC/FORECAST questions
    if question_type in ("DIAGNOSTIC", "FORECAST", "HYBRID"):
        logger.warning(f"⚠️ {question_type} question detected - Monte Carlo A/B scenarios will be skipped")
        logger.warning("   Agents will derive their own probability estimates")

    return state

