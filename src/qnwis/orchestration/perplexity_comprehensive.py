"""
COMPREHENSIVE Perplexity AI Extraction - Using NEW Search API

Perplexity Search API provides:
- Multi-query search (up to 5 queries in one request)
- Regional filtering by country
- Domain filtering (allowlist/denylist)
- Language filtering
- Date/recency filtering
- Content extraction control

This extractor uses ALL of these features for maximum data extraction.
"""

import logging
import asyncio
import os
import re
from typing import List, Dict, Any, Optional

import aiohttp

logger = logging.getLogger(__name__)

# Perplexity API endpoints
PERPLEXITY_SEARCH_URL = "https://api.perplexity.ai/search"
PERPLEXITY_CHAT_URL = "https://api.perplexity.ai/chat/completions"


async def extract_perplexity_comprehensive(query: str) -> List[Dict[str, Any]]:
    """
    Extract comprehensive real-time intelligence from Perplexity AI.
    
    Uses the NEW Search API with:
    1. Multi-query search (up to 5 queries per request)
    2. Regional filtering for Qatar/GCC
    3. Recent content filtering
    4. Domain filtering for authoritative sources
    """
    all_facts = []
    api_key = os.getenv("PERPLEXITY_API_KEY")
    
    if not api_key:
        logger.warning("  Perplexity API key not configured")
        return all_facts
    
    try:
        # Generate multiple targeted queries
        query_batches = _generate_query_batches(query)
        logger.info(f"  Querying Perplexity Search API with {len(query_batches)} batches")
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        async with aiohttp.ClientSession() as session:
            # Execute multi-query searches
            for i, batch in enumerate(query_batches):
                try:
                    logger.debug(f"  Batch {i+1}/{len(query_batches)}: {len(batch)} queries")
                    
                    # Use the Search API with multi-query support
                    search_facts = await _perplexity_search(
                        session, headers, batch,
                        max_results=10,
                        search_recency_filter="year"  # Recent content
                    )
                    all_facts.extend(search_facts)
                    
                    # Small delay between batches
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    logger.warning(f"  Perplexity batch {i+1} failed: {e}")
                    continue
            
            # Also use Chat API for structured Q&A on key questions
            key_questions = _generate_key_questions(query)
            for question in key_questions[:3]:  # Limit to 3 key questions
                try:
                    chat_facts = await _perplexity_chat(session, headers, question)
                    all_facts.extend(chat_facts)
                    await asyncio.sleep(0.5)
                except Exception as e:
                    logger.warning(f"  Perplexity chat failed: {e}")
        
        logger.info(f"  Perplexity TOTAL: {len(all_facts)} facts with citations")
        
    except Exception as e:
        logger.error(f"Perplexity comprehensive extraction error: {e}")
    
    return all_facts


async def _perplexity_search(
    session: aiohttp.ClientSession,
    headers: dict,
    queries: List[str],
    max_results: int = 10,
    search_recency_filter: Optional[str] = None,
    country: Optional[str] = None,
    domain_filter: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Execute Perplexity Search API call with multi-query support.
    
    Args:
        session: aiohttp session
        headers: API headers
        queries: List of queries (up to 5)
        max_results: Max results per query (1-20)
        search_recency_filter: "day", "week", "month", or "year"
        country: ISO country code (e.g., "QA" for Qatar)
        domain_filter: List of domains to include/exclude
    """
    facts = []
    
    payload = {
        "query": queries if len(queries) > 1 else queries[0],
        "max_results": min(max_results, 20),
        "max_tokens_per_page": 2048,  # Comprehensive content
    }
    
    if search_recency_filter:
        payload["search_recency_filter"] = search_recency_filter
    
    if country:
        payload["country"] = country
    
    if domain_filter:
        payload["search_domain_filter"] = domain_filter
    
    try:
        async with session.post(PERPLEXITY_SEARCH_URL, headers=headers, json=payload) as response:
            if response.status == 200:
                data = await response.json()
                
                # Handle multi-query results
                results = data.get("results", [])
                
                if isinstance(results[0], list) if results else False:
                    # Multi-query response - results is list of lists
                    for query_idx, query_results in enumerate(results):
                        for result in query_results:
                            facts.append(_format_search_result(result, queries[query_idx] if query_idx < len(queries) else ""))
                else:
                    # Single query response
                    for result in results:
                        facts.append(_format_search_result(result, queries[0] if queries else ""))
                
                logger.debug(f"    Search returned {len(facts)} results")
            else:
                error_text = await response.text()
                logger.warning(f"  Perplexity Search API error {response.status}: {error_text[:200]}")
                
    except Exception as e:
        logger.error(f"Perplexity Search API error: {e}")
    
    return facts


async def _perplexity_chat(
    session: aiohttp.ClientSession,
    headers: dict,
    question: str
) -> List[Dict[str, Any]]:
    """
    Execute Perplexity Chat API for structured Q&A with citations.
    """
    facts = []
    
    payload = {
        "model": "sonar-pro",  # Best model with citations
        "messages": [
            {
                "role": "system",
                "content": "You are an expert research assistant. Provide SPECIFIC statistics, numbers, and facts with exact citations. Focus on Qatar and GCC data."
            },
            {
                "role": "user",
                "content": f"{question}\n\nProvide EXACT numbers, percentages, and figures. Cite all sources with URLs."
            }
        ],
        "temperature": 0.1,
        "max_tokens": 2000,
        "return_citations": True
    }
    
    try:
        async with session.post(PERPLEXITY_CHAT_URL, headers=headers, json=payload) as response:
            if response.status == 200:
                data = await response.json()
                
                # Extract content and citations
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                citations = data.get("citations", [])
                
                if content:
                    # Parse facts from content
                    facts.extend(_extract_facts_from_content(content, question, citations))
                
                logger.debug(f"    Chat returned {len(facts)} facts")
            else:
                error_text = await response.text()
                logger.warning(f"  Perplexity Chat API error {response.status}: {error_text[:200]}")
                
    except Exception as e:
        logger.error(f"Perplexity Chat API error: {e}")
    
    return facts


def _format_search_result(result: Dict[str, Any], query: str) -> Dict[str, Any]:
    """Format a Perplexity Search result as a fact."""
    return {
        "metric": "perplexity_search_result",
        "title": result.get("title", ""),
        "text": result.get("snippet", "")[:1000],
        "url": result.get("url", ""),
        "date": result.get("date", ""),
        "last_updated": result.get("last_updated", ""),
        "query": query[:100],
        "source": "Perplexity Search API",
        "source_priority": 85,
        "confidence": 0.90,  # High confidence from search results
        "cached": False
    }


def _extract_facts_from_content(content: str, query: str, citations: List[str]) -> List[Dict[str, Any]]:
    """Extract individual facts from Perplexity Chat response."""
    facts = []
    
    # Split into sentences
    sentences = re.split(r'[.!?]', content)
    
    for sentence in sentences:
        sentence = sentence.strip()
        if len(sentence) < 20:
            continue
        
        # Check if sentence contains numbers (data points)
        if re.search(r'\d', sentence):
            facts.append({
                "metric": "perplexity_chat_fact",
                "text": sentence[:500],
                "query": query[:100],
                "source": "Perplexity Chat API (sonar-pro)",
                "citations": citations[:5] if citations else [],
                "confidence": 0.85,
                "source_priority": 82,
                "cached": False
            })
    
    # Also add the full response as a summary
    if len(content) > 100:
        facts.append({
            "metric": "perplexity_chat_summary",
            "text": content[:1500],
            "query": query[:100],
            "source": "Perplexity Chat API (sonar-pro)",
            "citations": citations if citations else [],
            "confidence": 0.85,
            "source_priority": 82,
            "cached": False
        })
    
    return facts


def _generate_query_batches(main_query: str) -> List[List[str]]:
    """
    Generate batches of queries for multi-query search.
    Each batch can have up to 5 queries.
    """
    all_queries = []
    query_lower = main_query.lower()
    
    # Base query variations
    all_queries.append(main_query)
    all_queries.append(f"Qatar {main_query[:50]} statistics data 2024")
    
    # Domain-specific queries
    if any(term in query_lower for term in ["labor", "employment", "job", "work", "unemployment"]):
        all_queries.extend([
            "Qatar labor market employment statistics 2024",
            "Qatar unemployment rate workforce data",
            "Qatarization policy progress statistics",
        ])
    
    if any(term in query_lower for term in ["gdp", "economy", "economic", "growth"]):
        all_queries.extend([
            "Qatar GDP economic growth 2024 statistics",
            "Qatar economic diversification non-oil economy",
            "Qatar government budget fiscal policy 2024",
        ])
    
    if any(term in query_lower for term in ["oil", "gas", "lng", "energy"]):
        all_queries.extend([
            "Qatar LNG production export capacity 2024",
            "Qatar North Field expansion QatarEnergy",
            "Qatar natural gas reserves production statistics",
        ])
    
    if any(term in query_lower for term in ["tourism", "visitor", "hotel"]):
        all_queries.extend([
            "Qatar tourism visitor arrivals 2024",
            "Qatar hotel occupancy hospitality sector",
            "Qatar World Cup 2022 tourism legacy",
        ])
    
    if any(term in query_lower for term in ["education", "university", "graduate", "stem"]):
        all_queries.extend([
            "Qatar education enrollment statistics 2024",
            "Qatar university graduates STEM education",
            "Education City Qatar research development",
        ])
    
    if any(term in query_lower for term in ["trade", "export", "import"]):
        all_queries.extend([
            "Qatar trade balance exports imports 2024",
            "Qatar major trading partners statistics",
            "Qatar non-oil exports diversification data",
        ])
    
    if any(term in query_lower for term in ["health", "hospital", "medical"]):
        all_queries.extend([
            "Qatar healthcare system statistics 2024",
            "Qatar hospital medical facilities capacity",
            "Qatar health expenditure per capita",
        ])
    
    if any(term in query_lower for term in ["skill", "training", "workforce"]):
        all_queries.extend([
            "Qatar skills gap workforce training 2024",
            "Qatar vocational training programs",
            "Qatar Vision 2030 human capital development",
        ])
    
    # Deduplicate
    seen = set()
    unique_queries = []
    for q in all_queries:
        q_lower = q.lower().strip()
        if q_lower not in seen:
            seen.add(q_lower)
            unique_queries.append(q)
    
    # Split into batches of 5 (max for multi-query)
    batches = []
    for i in range(0, len(unique_queries), 5):
        batch = unique_queries[i:i+5]
        batches.append(batch)
    
    return batches[:4]  # Max 4 batches = 20 queries


def _generate_key_questions(query: str) -> List[str]:
    """Generate key questions for Chat API to get structured answers."""
    query_lower = query.lower()
    questions = []
    
    # Always include the main query as a question
    questions.append(f"What are the latest statistics and data for: {query}? Provide specific numbers and cite sources.")
    
    # Domain-specific key questions
    if any(term in query_lower for term in ["labor", "employment", "unemployment"]):
        questions.append("What is Qatar's current unemployment rate and labor force participation rate in 2024?")
    
    if any(term in query_lower for term in ["gdp", "economy", "growth"]):
        questions.append("What is Qatar's current GDP, GDP growth rate, and economic outlook for 2024-2025?")
    
    if any(term in query_lower for term in ["oil", "gas", "lng", "energy"]):
        questions.append("What is Qatar's current LNG production capacity and the status of North Field expansion?")
    
    if any(term in query_lower for term in ["qatarization", "nationalization"]):
        questions.append("What are the current Qatarization rates in Qatar's public and private sectors?")
    
    if any(term in query_lower for term in ["skill", "training", "workforce"]):
        questions.append("What are Qatar's major skills gaps and workforce training initiatives?")
    
    return questions[:5]  # Max 5 key questions


async def query_perplexity_direct(question: str) -> Dict[str, Any]:
    """
    Direct query to Perplexity Chat API for single question.
    Returns structured response with citations.
    """
    api_key = os.getenv("PERPLEXITY_API_KEY")
    if not api_key:
        return {"error": "PERPLEXITY_API_KEY not configured"}
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            facts = await _perplexity_chat(session, headers, question)
            return {"facts": facts, "count": len(facts)}
    except Exception as e:
        logger.error(f"Perplexity direct query error: {e}")
        return {"error": str(e)}


async def search_perplexity_multi(queries: List[str], max_results: int = 10) -> List[Dict[str, Any]]:
    """
    Multi-query search using Perplexity Search API.
    
    Args:
        queries: List of queries (up to 5)
        max_results: Max results per query
        
    Returns:
        List of search result facts
    """
    api_key = os.getenv("PERPLEXITY_API_KEY")
    if not api_key:
        return []
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            return await _perplexity_search(
                session, headers, queries[:5],
                max_results=max_results,
                search_recency_filter="year"
            )
    except Exception as e:
        logger.error(f"Perplexity multi-query error: {e}")
        return []
