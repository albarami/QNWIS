"""
Parallel Research Node - Starts Case Studies & Research Early

This node runs in parallel with data extraction to save time.
Case studies and academic research don't depend on extracted facts,
only on the query - so they can start immediately after classification.

Time savings: ~60-90 seconds per analysis.
"""

import asyncio
import logging

from ..case_studies import extract_case_studies
from ..state import IntelligenceState

logger = logging.getLogger(__name__)


async def parallel_research_node(state: IntelligenceState) -> IntelligenceState:
    """
    Fetch case studies and research in parallel with data extraction.
    
    This node starts as soon as the query is classified, running
    concurrently with fact extraction. Results are cached in state
    for the debate node to use.
    
    Runs:
    1. Case study extraction (Perplexity, Brave, Semantic Scholar)
    2. Stores results in state['case_studies_cache']
    
    Time savings: 60-90 seconds (case studies fetch during extraction)
    """
    query = state.get("query", "")
    
    if not query:
        logger.warning("⚠️ PARALLEL_RESEARCH: No query provided, skipping")
        state["case_studies_cache"] = []
        state["research_cache"] = {}
        return state
    
    logger.info("🚀 PARALLEL_RESEARCH: Starting early case study fetch...")
    logger.info(f"   Query: {query[:80]}...")
    
    try:
        # Fetch case studies in parallel
        # This runs while data_extraction_node is gathering facts
        case_studies = await extract_case_studies(query, max_cases=4)
        
        logger.info(f"✅ PARALLEL_RESEARCH: Fetched {len(case_studies)} case studies")
        
        # Cache results for debate node
        state["case_studies_cache"] = case_studies
        state["case_studies_fetched_early"] = True
        
        # Add to reasoning chain
        reasoning = state.get("reasoning_chain", [])
        reasoning.append(f"📚 Pre-fetched {len(case_studies)} case studies (parallel optimization)")
        state["reasoning_chain"] = reasoning
        
    except Exception as e:
        logger.error(f"❌ PARALLEL_RESEARCH: Error fetching case studies: {e}")
        state["case_studies_cache"] = []
        state["case_studies_fetched_early"] = False
    
    return state


def parallel_research_node_sync(state: IntelligenceState) -> IntelligenceState:
    """Synchronous wrapper for parallel_research_node."""
    import nest_asyncio
    nest_asyncio.apply()
    
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(parallel_research_node(state))

