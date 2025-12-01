"""
COMPREHENSIVE Data Extraction Node.

MINISTER-GRADE: Extracts data from ALL 18+ available data sources.
Uses intelligent routing to maximize data coverage.
"""

from __future__ import annotations

import logging
import os
import json
from typing import List, Dict, Any, Optional

from ..state import IntelligenceState
from ..prefetch_apis import get_complete_prefetch
from ..DATA_SOURCE_REGISTRY import DATA_SOURCES, QUERY_ROUTING, get_sources_for_query
from .scenario_baseline_requirements import enhance_facts_with_scenario_baselines

logger = logging.getLogger(__name__)


# =============================================================================
# LLM-BASED SEMANTIC QUERY UNDERSTANDING
# =============================================================================

SEMANTIC_ROUTING_PROMPT = """You are a data routing expert. Analyze this query and determine which data sources are most relevant.

QUERY: {query}

AVAILABLE DATA SOURCES AND THEIR DOMAINS:
1. MOL_LMIS - Qatar Ministry of Labour: employment, wages, Qatarization, skills, workforce, labor mobility
2. GCC_STAT - Regional: GCC comparisons, unemployment rates, labor participation across 6 countries
3. WORLD_BANK - Global: GDP, education, health, demographics, trade, infrastructure (1400+ indicators)
4. IMF_DATA - Economic forecasts: GDP growth, inflation, fiscal balance, debt (forecasts to 2029)
5. ILO_STAT - International labor: global employment benchmarks, working conditions, wages
6. FAO_STAT - Food/Agriculture: food security, agricultural production, food imports
7. UNWTO - Tourism: visitor arrivals, tourism revenue, hospitality sector
8. IEA_ENERGY - Energy: oil/gas production, renewable energy, emissions
9. UNCTAD - Investment: FDI flows, investment climate, trade facilitation
10. ESCWA_TRADE - Arab trade: exports, imports, bilateral trade, product-level data
11. QATAR_OPEN_DATA - Qatar government: public datasets, national statistics
12. SEMANTIC_SCHOLAR - Research: 214M academic papers, labor economics research
13. PERPLEXITY - Real-time: current events, recent statistics, market developments
14. BRAVE_SEARCH - Web: news, company info, government announcements
15. KNOWLEDGE_GRAPH - Relationships: sector-skill-occupation mappings, policy impacts
16. RAG_SYSTEM - R&D Reports: 56 research documents on Qatar labor market, AI, skills

Analyze the MEANING and CONTEXT of the query, not just keywords.

RESPOND WITH VALID JSON:
{{
    "intent": "brief description of what the user wants to know",
    "domains": ["primary_domain", "secondary_domain"],
    "required_sources": ["SOURCE1", "SOURCE2", "SOURCE3"],
    "optional_sources": ["SOURCE4", "SOURCE5"],
    "reasoning": "why these sources are relevant"
}}

IMPORTANT: Choose sources based on SEMANTIC UNDERSTANDING, not keyword matching.
For example:
- "How competitive is Qatar's workforce?" → needs GCC_STAT, WORLD_BANK, ILO (for benchmarking), not just LMIS
- "Can Qatar feed itself?" → needs FAO, UN Comtrade, World Bank (food imports), not energy data
- "Should Qatar invest in solar?" → needs IEA, UNCTAD, World Bank, Perplexity (recent developments)
"""


async def analyze_query_semantically(query: str) -> Dict[str, Any]:
    """
    Use LLM to semantically understand the query and determine relevant data sources.
    
    This replaces simple keyword matching with contextual understanding.
    """
    import aiohttp
    
    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
    api_key = os.environ.get("AZURE_OPENAI_API_KEY")
    
    if not endpoint or not api_key:
        logger.warning("⚠️ Azure OpenAI not configured, falling back to keyword routing")
        return None
    
    try:
        url = f"{endpoint}/openai/deployments/gpt-5-chat/chat/completions?api-version=2024-08-01-preview"
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                headers={"api-key": api_key, "Content-Type": "application/json"},
                json={
                    "messages": [
                        {"role": "system", "content": "You are a data routing expert. Always respond with valid JSON."},
                        {"role": "user", "content": SEMANTIC_ROUTING_PROMPT.format(query=query)}
                    ],
                    "max_tokens": 500,
                    "temperature": 0.1
                },
                timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    content = data["choices"][0]["message"]["content"]
                    
                    # Parse JSON from response
                    # Handle markdown code blocks if present
                    if "```json" in content:
                        content = content.split("```json")[1].split("```")[0]
                    elif "```" in content:
                        content = content.split("```")[1].split("```")[0]
                    
                    routing = json.loads(content.strip())
                    logger.info(f"🧠 Semantic analysis: {routing.get('intent', 'unknown')}")
                    logger.info(f"📊 Required sources: {routing.get('required_sources', [])}")
                    return routing
                else:
                    logger.warning(f"⚠️ Semantic analysis failed: {resp.status}")
                    return None
                    
    except Exception as e:
        logger.warning(f"⚠️ Semantic analysis error: {e}")
        return None


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

    # ==========================================================================
    # PHASE 0: LLM-BASED SEMANTIC QUERY UNDERSTANDING
    # Uses GPT to understand context, not just keyword matching
    # ==========================================================================
    semantic_routing = None
    try:
        logger.info("🧠 Phase 0: Semantic query analysis (LLM-based understanding)...")
        semantic_routing = await analyze_query_semantically(query)
        
        if semantic_routing:
            intent = semantic_routing.get("intent", "unknown")
            domains = semantic_routing.get("domains", [])
            required_sources = semantic_routing.get("required_sources", [])
            reasoning = semantic_routing.get("reasoning", "")
            
            logger.info(f"🧠 Intent understood: {intent}")
            logger.info(f"🧠 Domains identified: {domains}")
            logger.info(f"🧠 Required sources: {required_sources}")
            
            reasoning_chain.append(f"🧠 Semantic Analysis: {intent}")
            reasoning_chain.append(f"📊 Domains: {', '.join(domains)}")
            reasoning_chain.append(f"📊 LLM-selected sources: {', '.join(required_sources)}")
            
            # Store semantic routing in state for agents to use
            state["semantic_routing"] = semantic_routing
        else:
            logger.info("⚠️ Semantic analysis unavailable, using keyword-based routing")
            
    except Exception as e:
        logger.warning(f"⚠️ Semantic analysis failed: {e}, falling back to keywords")

    # Determine which sources to query based on query (keyword fallback)
    relevant_sources = get_sources_for_query(query)
    
    # Merge LLM-selected sources with keyword-selected sources
    if semantic_routing:
        llm_sources = semantic_routing.get("required_sources", []) + semantic_routing.get("optional_sources", [])
        for src in llm_sources:
            if src not in relevant_sources:
                relevant_sources.append(src)
    
    logger.info(f"📊 Final sources to query: {relevant_sources}")
    reasoning_chain.append(f"Identified {len(relevant_sources)} relevant data sources for query")

    all_facts = []
    sources_queried = []
    sources_failed = []

    # 1. Use the existing prefetch layer (which already has comprehensive extraction)
    prefetch = get_complete_prefetch()
    
    try:
        logger.info("📊 Phase 1: Prefetch layer extraction...")
        prefetch_facts = await prefetch.fetch_all_sources(query)
        # Guard against None return
        if prefetch_facts is None:
            logger.warning("⚠️ Prefetch returned None, using empty list")
            prefetch_facts = []
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
        # Guard against None return
        if additional_facts is None:
            additional_facts = []
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
    
    # Enhance facts with scenario baselines for stake-prompting
    # This ensures scenario generator has real numbers to modify
    scenario_baselines = {}
    try:
        logger.info("📊 Phase 3: Enhancing facts with scenario baselines...")
        enhanced_data = enhance_facts_with_scenario_baselines(query, all_facts)
        scenario_baselines = enhanced_data.get("_scenario_baselines", {})
        logger.info(f"   Added {len(scenario_baselines)} baseline metrics")
    except Exception as exc:
        logger.warning(f"⚠️ Scenario baseline enhancement failed: {exc}")
    
    # Update state - CRITICAL: extracted_facts must be a LIST for frontend!
    state["extracted_facts"] = all_facts  # List of facts (frontend expects this)
    state["scenario_baselines"] = scenario_baselines  # Dict for scenario generator
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
    
    # LMIS - Ministry of Labour Qatar (OFFICIAL DATA)
    if "LMIS" in missing_sources or "lmis" not in str(already_queried).lower():
        logger.info(f"   🏛️ Adding: LMIS (Ministry of Labour) official data extraction")
        tasks.append(_extract_lmis_data(query))
    
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
    """
    Extract MEANINGFUL entities from Knowledge Graph.
    
    Filters out:
    - Generic/placeholder nodes
    - Nodes without substantive content
    - Duplicate entities
    """
    facts = []
    seen_entities = set()  # Deduplication
    
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
        key_terms = ["labor", "employment", "skills", "qatar", "economy", "sector", "gdp", 
                     "workforce", "nationalization", "qatarization", "tourism", "energy"]
        
        matched_terms = [t for t in key_terms if t in query_lower]
        
        for term in matched_terms:
            for node in list(kg.graph.nodes())[:100]:
                node_str = str(node).lower()
                
                # Skip if term not in node
                if term not in node_str:
                    continue
                    
                node_data = kg.graph.nodes[node]
                entity_name = str(node)
                
                # =================================================
                # QUALITY FILTERS - Skip useless entities
                # =================================================
                
                # Skip generic/placeholder entities
                if entity_name.lower() in ["knowledge_entity", "entity", "unknown", "none", ""]:
                    continue
                
                # Skip very short names (likely not meaningful)
                if len(entity_name) < 3:
                    continue
                
                # Skip if already seen (deduplication)
                entity_key = entity_name.lower().strip()
                if entity_key in seen_entities:
                    continue
                seen_entities.add(entity_key)
                
                # Skip nodes without useful properties
                if not node_data or len(node_data) == 0:
                    continue
                
                # Get entity type - must be meaningful
                entity_type = node_data.get("type", "unknown")
                if entity_type.lower() in ["unknown", "none", ""]:
                    # Try to infer type from properties
                    if "value" in node_data:
                        entity_type = "metric"
                    elif "description" in node_data:
                        entity_type = "concept"
                    else:
                        continue  # Skip if we can't determine type
                
                # Build meaningful metric name from entity type
                metric_name = f"kg_{entity_type.lower().replace(' ', '_')}"
                
                facts.append({
                    "metric": metric_name,
                    "entity": entity_name,
                    "type": entity_type,
                    "properties": dict(node_data),
                    "source": "Knowledge Graph",
                    "confidence": 0.80,
                    "source_priority": 75  # Lower priority than API data
                })
        
        logger.info(f"   Knowledge Graph: {len(facts)} quality entities (filtered)")
        
    except Exception as e:
        logger.error(f"Knowledge Graph extraction error: {e}")
    
    return facts[:25]  # Cap at 25 to avoid flooding with KG data


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


async def _extract_lmis_data(query: str) -> List[Dict[str, Any]]:
    """
    COMPREHENSIVE LMIS extraction from Ministry of Labour API.
    
    Extracts from 17+ endpoints:
    - Main labor market indicators
    - SDG progress
    - Sector growth (NDS3, ISIC)
    - Skills gaps and emerging skills
    - Qatarization data
    - Expat workforce dynamics
    - SME growth metrics
    """
    facts = []
    query_lower = query.lower()
    
    try:
        from src.data.apis.lmis_mol_api import LMISAPIClient
        
        client = LMISAPIClient()
        
        # Determine which LMIS endpoints are relevant based on query
        endpoints_to_fetch = []
        
        # Always fetch main indicators for Qatar queries
        if "qatar" in query_lower or "labor" in query_lower or "employment" in query_lower:
            endpoints_to_fetch.append(("main_indicators", client.get_qatar_main_indicators))
        
        # SDG indicators
        if "sdg" in query_lower or "sustainable" in query_lower or "development goal" in query_lower:
            endpoints_to_fetch.append(("sdg_indicators", client.get_sdg_indicators))
        
        # Sector growth
        if "sector" in query_lower or "diversification" in query_lower or "growth" in query_lower:
            endpoints_to_fetch.append(("sector_growth_nds3", lambda: client.get_sector_growth("NDS3")))
            endpoints_to_fetch.append(("sector_growth_isic", lambda: client.get_sector_growth("ISIC")))
        
        # Skills-related queries
        if "skill" in query_lower or "training" in query_lower or "education" in query_lower:
            endpoints_to_fetch.append(("top_skills", lambda: client.get_top_skills_by_sector("NDS3")))
            endpoints_to_fetch.append(("emerging_skills", client.get_emerging_decaying_skills))
            endpoints_to_fetch.append(("skills_gap", client.get_education_system_skills_gap))
        
        # Qatarization queries
        if "qatarization" in query_lower or "nationalization" in query_lower or "qatari" in query_lower:
            endpoints_to_fetch.append(("qatari_skills_gap", client.get_qatari_jobseekers_skills_gap))
        
        # Expat workforce
        if "expat" in query_lower or "foreign" in query_lower or "immigrant" in query_lower:
            endpoints_to_fetch.append(("expat_dominated", client.get_expat_dominated_occupations))
            endpoints_to_fetch.append(("expat_skills", client.get_attracted_expat_skills))
            endpoints_to_fetch.append(("top_expat_skills", client.get_top_expat_skills))
        
        # SME and business
        if "sme" in query_lower or "business" in query_lower or "company" in query_lower:
            endpoints_to_fetch.append(("sme_growth", client.get_sme_growth))
            endpoints_to_fetch.append(("occupations_by_size", client.get_occupations_by_company_size))
        
        # Salary and compensation
        if "salary" in query_lower or "wage" in query_lower or "compensation" in query_lower:
            endpoints_to_fetch.append(("best_paid", client.get_best_paid_occupations))
        
        # Career mobility
        if "mobility" in query_lower or "transition" in query_lower or "career" in query_lower:
            endpoints_to_fetch.append(("occupation_transitions", client.get_occupation_transitions))
            endpoints_to_fetch.append(("sector_mobility", client.get_sector_mobility))
        
        # If no specific triggers, fetch core indicators
        if not endpoints_to_fetch:
            endpoints_to_fetch = [
                ("main_indicators", client.get_qatar_main_indicators),
                ("sector_growth", lambda: client.get_sector_growth("NDS3")),
            ]
        
        # Fetch data from selected endpoints
        for endpoint_name, fetch_func in endpoints_to_fetch:
            try:
                df = fetch_func()
                if df is not None and not df.empty:
                    # Convert DataFrame rows to facts
                    for _, row in df.iterrows():
                        fact = {
                            "metric": endpoint_name,
                            "data": row.to_dict(),
                            "source": "LMIS (Ministry of Labour Qatar)",
                            "source_type": "official_government",
                            "confidence": 0.95,  # High confidence for official data
                            "source_priority": 98,  # High priority
                            "endpoint": endpoint_name,
                            "cached": False
                        }
                        facts.append(fact)
                        
                logger.debug(f"   LMIS {endpoint_name}: {len(df) if df is not None else 0} records")
            except Exception as e:
                logger.warning(f"   LMIS {endpoint_name} error: {e}")
                continue
        
        logger.info(f"   LMIS COMPREHENSIVE: {len(facts)} official labor market facts")
        
    except ImportError:
        logger.warning("LMIS API client not available")
    except Exception as e:
        logger.error(f"LMIS comprehensive extraction error: {e}")
    
    return facts

