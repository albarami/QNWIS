"""
COMPREHENSIVE Data Extraction Node.

MINISTER-GRADE: Extracts data from ALL 18+ available data sources.
Uses intelligent routing to maximize data coverage.
"""

from __future__ import annotations

import logging
from typing import List, Dict, Any

from ..state import IntelligenceState
from ..prefetch_apis import get_complete_prefetch
from ..DATA_SOURCE_REGISTRY import DATA_SOURCES, QUERY_ROUTING, get_sources_for_query

logger = logging.getLogger(__name__)


async def data_extraction_node(state: IntelligenceState) -> IntelligenceState:
    """
    Node 2: COMPREHENSIVE data extraction from ALL sources.

    MINISTER-GRADE extraction:
    - PostgreSQL cache for fast retrieval
    - ALL 18+ API sources
    - RAG system for research insights
    - Knowledge Graph for relationships
    
    NO LIMITS. NO SHORTCUTS. FULL DATA UTILIZATION.
    """

    query = state["query"]
    
    logger.info(f"📊 COMPREHENSIVE DATA EXTRACTION for: {query[:100]}...")
    
    reasoning_chain = state.setdefault("reasoning_chain", [])
    nodes_executed = state.setdefault("nodes_executed", [])
    warnings = state.setdefault("warnings", [])
    errors = state.setdefault("errors", [])

    # Determine which sources to query based on query
    relevant_sources = get_sources_for_query(query)
    logger.info(f"📊 Sources identified: {relevant_sources}")
    reasoning_chain.append(f"Identified {len(relevant_sources)} relevant data sources for query")

    all_facts = []
    sources_queried = []
    sources_failed = []

    # 1. Use the existing prefetch layer (which already has comprehensive extraction)
    prefetch = get_complete_prefetch()
    
    try:
        logger.info("📊 Phase 1: Prefetch layer extraction...")
        prefetch_facts = await prefetch.fetch_all_sources(query)
        all_facts.extend(prefetch_facts)
        
        # Track sources
        for fact in prefetch_facts:
            source = fact.get("source", "unknown")
            if source not in sources_queried:
                sources_queried.append(source)
        
        logger.info(f"   Prefetch returned {len(prefetch_facts)} facts from {len(sources_queried)} sources")
        
    except Exception as exc:
        logger.error(f"❌ Prefetch layer failed: {exc}")
        errors.append(f"Prefetch extraction failed: {exc}")
        sources_failed.append(("prefetch_layer", str(exc)))

    # 2. Additional targeted extraction from priority sources not covered
    try:
        logger.info("📊 Phase 2: Targeted extraction for missing sources...")
        additional_facts = await _extract_missing_sources(query, sources_queried, relevant_sources)
        all_facts.extend(additional_facts)
        
        for fact in additional_facts:
            source = fact.get("source", "unknown")
            if source not in sources_queried:
                sources_queried.append(source)
        
        logger.info(f"   Additional extraction added {len(additional_facts)} facts")
        
    except Exception as exc:
        logger.error(f"❌ Additional extraction failed: {exc}")
        warnings.append(f"Additional extraction partial failure: {exc}")

    # 3. Calculate quality metrics
    total_facts = len(all_facts)
    unique_sources = len(sources_queried)
    cached_count = sum(1 for fact in all_facts if fact.get("cached", False))
    
    if total_facts == 0:
        data_quality_score = 0.0
        warnings.append("⚠️ No data extracted - check API connections and database")
    else:
        # Quality based on: quantity, source diversity, cache ratio
        quantity_score = min(total_facts / 100, 1.0)  # 100+ facts = full score
        diversity_score = min(unique_sources / 10, 1.0)  # 10+ sources = full score
        cache_ratio = cached_count / total_facts if total_facts > 0 else 0
        
        data_quality_score = (quantity_score * 0.4 + diversity_score * 0.4 + cache_ratio * 0.2)
    
    # Update state
    state["extracted_facts"] = all_facts
    state["data_sources"] = sources_queried
    state["data_quality_score"] = data_quality_score
    state["extraction_report"] = {
        "total_facts": total_facts,
        "unique_sources": unique_sources,
        "cached_count": cached_count,
        "live_count": total_facts - cached_count,
        "sources_queried": sources_queried,
        "sources_failed": sources_failed,
        "quality_score": data_quality_score
    }
    
    reasoning_chain.append(
        f"✅ Extracted {total_facts} facts from {unique_sources} sources "
        f"(Quality: {data_quality_score:.0%})"
    )
    
    logger.info(f"✅ EXTRACTION COMPLETE: {total_facts} facts, {unique_sources} sources, {data_quality_score:.0%} quality")

    nodes_executed.append("extraction")
    return state


async def _extract_missing_sources(
    query: str,
    already_queried: List[str],
    target_sources: List[str]
) -> List[Dict[str, Any]]:
    """
    Extract from sources that weren't covered by prefetch.
    Uses COMPREHENSIVE extractors for each source.
    """
    import asyncio
    
    additional_facts = []
    
    # Check which high-priority sources might be missing
    missing_sources = []
    for source_id in target_sources:
        source_name = DATA_SOURCES.get(source_id, {}).get("name", source_id)
        if not any(source_name.lower() in s.lower() for s in already_queried):
            missing_sources.append(source_id)
    
    logger.info(f"   🔍 Checking for missing sources to extract comprehensively...")
    
    # ALWAYS try comprehensive extraction from key sources
    # These extractors are designed to get MAXIMUM data
    tasks = []
    
    # Semantic Scholar - 214 MILLION papers
    if "SEMANTIC_SCHOLAR" in missing_sources or "semantic" not in str(already_queried).lower():
        logger.info(f"   📚 Adding: Semantic Scholar comprehensive extraction")
        tasks.append(_extract_semantic_scholar_additional(query))
    
    # Perplexity AI - Real-time web intelligence
    if "PERPLEXITY" in missing_sources or "perplexity" not in str(already_queried).lower():
        logger.info(f"   🤖 Adding: Perplexity AI comprehensive extraction")
        tasks.append(_extract_perplexity_additional(query))
    
    # Brave Search - Real-time web search
    if "BRAVE" in missing_sources or "brave" not in str(already_queried).lower():
        logger.info(f"   🦁 Adding: Brave Search comprehensive extraction")
        tasks.append(_extract_brave_additional(query))
    
    # RAG System - 56 R&D reports
    if "RAG_SYSTEM" in missing_sources or "rag" not in str(already_queried).lower():
        logger.info(f"   📄 Adding: RAG system additional extraction")
        tasks.append(_extract_rag_additional(query))
    
    # Knowledge Graph - Entity relationships
    if "KNOWLEDGE_GRAPH" in missing_sources or "knowledge" not in str(already_queried).lower():
        logger.info(f"   🕸️ Adding: Knowledge Graph additional extraction")
        tasks.append(_extract_knowledge_graph_additional(query))
    
    if tasks:
        logger.info(f"   ⚡ Running {len(tasks)} comprehensive extractors in parallel...")
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, list):
                additional_facts.extend(result)
            elif isinstance(result, Exception):
                logger.warning(f"   ⚠️ Extractor error: {result}")
    
    return additional_facts


async def _extract_perplexity_additional(query: str) -> List[Dict[str, Any]]:
    """
    COMPREHENSIVE Perplexity extraction.
    Uses multiple queries for broad coverage.
    """
    try:
        from ..perplexity_comprehensive import extract_perplexity_comprehensive
        
        facts = await extract_perplexity_comprehensive(query)
        logger.info(f"   Perplexity COMPREHENSIVE: {len(facts)} real-time facts")
        return facts
        
    except Exception as e:
        logger.error(f"Perplexity comprehensive extraction error: {e}")
        return []


async def _extract_brave_additional(query: str) -> List[Dict[str, Any]]:
    """
    COMPREHENSIVE Brave Search extraction.
    Uses multiple queries across web and news.
    """
    try:
        from ..brave_comprehensive import extract_brave_comprehensive
        
        facts = await extract_brave_comprehensive(query)
        logger.info(f"   Brave COMPREHENSIVE: {len(facts)} web results")
        return facts
        
    except Exception as e:
        logger.error(f"Brave comprehensive extraction error: {e}")
        return []


async def _extract_rag_additional(query: str) -> List[Dict[str, Any]]:
    """Additional RAG extraction with multiple search strategies."""
    facts = []
    try:
        from ...rag.retriever import DocumentStore
        
        store = DocumentStore()
        
        # Multiple search queries
        queries = [
            query,
            f"Qatar {query}",
            f"labor market {query}",
            f"skills {query}",
            f"Vision 2030 {query}"
        ]
        
        seen_chunks = set()
        
        for q in queries[:3]:
            try:
                results = store.search(q, top_k=20)
                for result in results:
                    text = result.get("text", "")[:600]
                    text_hash = hash(text[:100])
                    
                    if text_hash in seen_chunks:
                        continue
                    seen_chunks.add(text_hash)
                    
                    facts.append({
                        "metric": "research_insight",
                        "text": text,
                        "document": result.get("document", "R&D Report"),
                        "source": "RAG (R&D Reports)",
                        "confidence": result.get("score", 0.7),
                        "source_priority": 90
                    })
            except:
                continue
        
        logger.info(f"   RAG additional: {len(facts)} insights")
        
    except Exception as e:
        logger.error(f"RAG additional extraction error: {e}")
    
    return facts


async def _extract_knowledge_graph_additional(query: str) -> List[Dict[str, Any]]:
    """Additional Knowledge Graph extraction."""
    facts = []
    try:
        from pathlib import Path
        from ...knowledge.graph_builder import QNWISKnowledgeGraph
        
        kg_path = Path("data/knowledge_graph.json")
        if not kg_path.exists():
            return facts
        
        kg = QNWISKnowledgeGraph()
        kg.load(str(kg_path))
        
        # Extract key terms from query
        query_lower = query.lower()
        key_terms = ["labor", "employment", "skills", "qatar", "economy", "sector", "gdp"]
        
        for term in key_terms:
            if term in query_lower:
                for node in list(kg.graph.nodes())[:50]:
                    if term in str(node).lower():
                        node_data = kg.graph.nodes[node]
                        facts.append({
                            "metric": "knowledge_entity",
                            "entity": str(node),
                            "type": node_data.get("type", "unknown"),
                            "properties": dict(node_data),
                            "source": "Knowledge Graph",
                            "confidence": 0.85,
                            "source_priority": 88
                        })
        
        logger.info(f"   Knowledge Graph additional: {len(facts)} entities")
        
    except Exception as e:
        logger.error(f"Knowledge Graph additional extraction error: {e}")
    
    return facts


async def _extract_semantic_scholar_additional(query: str) -> List[Dict[str, Any]]:
    """
    COMPREHENSIVE Semantic Scholar extraction.
    
    Semantic Scholar has 214 MILLION papers.
    We should get 50-100+ relevant papers, not 1-3.
    """
    try:
        from ..semantic_scholar_comprehensive import extract_semantic_scholar_comprehensive
        
        facts = await extract_semantic_scholar_comprehensive(query)
        logger.info(f"   Semantic Scholar COMPREHENSIVE: {len(facts)} papers from 214M database")
        return facts
        
    except Exception as e:
        logger.error(f"Semantic Scholar comprehensive extraction error: {e}")
        return []

