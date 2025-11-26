"""
Query Classifier Node.

Analyzes query complexity to determine the routing strategy.
"""

from __future__ import annotations

import re
from typing import Dict, List

from ..state import IntelligenceState


def _matches_any(patterns: List[str], text: str) -> bool:
    """Return True if any pattern matches the provided text."""
    return any(re.search(pattern, text) for pattern in patterns)


def classify_query_node(state: IntelligenceState) -> IntelligenceState:
    """
    Node 1: Classify query complexity.

    Routes to:
    - "simple": Quick fact lookup (skip most agents)
    - "medium": Single domain analysis
    - "complex": Full multi-agent analysis
    - "critical": Emergency analysis (parallel execution)
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # CRITICAL DEBUG - What is the state we receive?
    logger.warning(f"🔍 classify_query_node received state keys: {list(state.keys())}")
    logger.warning(f"🔍 classify_query_node state['query'] = {repr(state.get('query', 'NOT_FOUND'))}")
    logger.warning(f"🔍 classify_query_node state type = {type(state)}")

    query = state.get("query", "")
    if not query:
        logger.error("❌ CRITICAL: Query is empty in classifier node!")
    query = query.lower()

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
    nodes_executed.append("classifier")
    state["complexity"] = complexity

    return state

