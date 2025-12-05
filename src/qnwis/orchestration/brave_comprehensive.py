"""
COMPREHENSIVE Brave Search Extraction

Brave Search provides real-time web search results with news, academic sources,
and current statistics. We should extract 30-50+ relevant results, not just 5-10.

Strategy:
1. Multiple search queries for different aspects
2. Different search types (web, news)
3. Extract structured data from snippets
4. Domain-agnostic query generation
"""

import logging
import asyncio
import os
import re
from typing import List, Dict, Any

import aiohttp

logger = logging.getLogger(__name__)


async def extract_brave_comprehensive(query: str) -> List[Dict[str, Any]]:
    """
    Extract comprehensive real-time web data from Brave Search.
    
    Uses multiple strategies:
    1. Multiple targeted search queries
    2. Web and news search types
    3. Snippet extraction and parsing
    """
    all_results = []
    seen_urls = set()
    
    api_key = os.getenv("BRAVE_API_KEY")
    if not api_key:
        logger.warning("  Brave API key not configured")
        return all_results
    
    try:
        # Generate multiple search queries
        search_queries = _generate_search_queries(query)
        logger.info(f"  Searching Brave with {len(search_queries)} queries")
        
        async with aiohttp.ClientSession() as session:
            for i, sq in enumerate(search_queries):
                try:
                    logger.debug(f"  Query {i+1}/{len(search_queries)}: {sq[:50]}...")
                    
                    # Web search
                    web_results = await _brave_search(session, api_key, sq, search_type="web")
                    for result in web_results:
                        url = result.get("url", "")
                        if url and url not in seen_urls:
                            seen_urls.add(url)
                            all_results.append(_format_brave_result(result, sq))
                    
                    # Small delay between queries
                    await asyncio.sleep(0.3)
                    
                except Exception as e:
                    logger.warning(f"  Brave query failed: {e}")
                    continue
            
            # Also search news for recent developments
            try:
                news_query = f"{query[:50]} 2024 Qatar"
                news_results = await _brave_search(session, api_key, news_query, search_type="news")
                for result in news_results:
                    url = result.get("url", "")
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        all_results.append(_format_brave_result(result, news_query, is_news=True))
            except Exception as e:
                logger.warning(f"  Brave news search failed: {e}")
        
        logger.info(f"  Brave TOTAL: {len(all_results)} unique results")
        
    except Exception as e:
        logger.error(f"Brave comprehensive extraction error: {e}")
    
    return all_results


async def _brave_search(
    session: aiohttp.ClientSession,
    api_key: str,
    query: str,
    search_type: str = "web",
    count: int = 20
) -> List[Dict[str, Any]]:
    """
    Execute a single Brave search.
    """
    url = "https://api.search.brave.com/res/v1/web/search"
    
    headers = {
        "Accept": "application/json",
        "X-Subscription-Token": api_key
    }
    
    params = {
        "q": query,
        "count": count,
        "search_lang": "en",
        "text_decorations": "false",  # Must be string, not bool
        "safesearch": "off"
    }
    
    if search_type == "news":
        params["freshness"] = "pw"  # Past week
    
    async with session.get(url, headers=headers, params=params) as response:
        if response.status == 200:
            data = await response.json()
            results = data.get("web", {}).get("results", [])
            
            # Also get news results if available
            news = data.get("news", {}).get("results", [])
            if news:
                results.extend(news)
            
            return results
        else:
            logger.warning(f"Brave API error {response.status}")
            return []


def _generate_search_queries(main_query: str) -> List[str]:
    """
    Generate multiple search queries for comprehensive coverage.
    """
    queries = [main_query]  # Original query
    
    query_lower = main_query.lower()
    
    # Add domain-specific search queries
    if any(term in query_lower for term in ["labor", "employment", "job", "work", "unemployment"]):
        queries.extend([
            f"Qatar labor market statistics 2024",
            f"Qatarization employment policy progress",
            f"Qatar workforce skills demand",
        ])
    
    if any(term in query_lower for term in ["gdp", "economy", "economic", "growth"]):
        queries.extend([
            f"Qatar GDP economic growth 2024",
            f"Qatar economic diversification progress",
            f"Qatar non-oil economy statistics",
        ])
    
    if any(term in query_lower for term in ["oil", "gas", "lng", "energy"]):
        queries.extend([
            f"Qatar LNG production export 2024",
            f"North Field expansion QatarEnergy",
            f"Qatar energy sector investment",
        ])
    
    if any(term in query_lower for term in ["tourism", "visitor", "hotel"]):
        queries.extend([
            f"Qatar tourism statistics 2024",
            f"Qatar World Cup tourism legacy",
            f"Qatar hotel occupancy visitors",
        ])
    
    if any(term in query_lower for term in ["education", "university", "stem"]):
        queries.extend([
            f"Qatar education system statistics",
            f"Qatar university enrollment graduation",
            f"Education City Qatar STEM",
        ])
    
    if any(term in query_lower for term in ["trade", "export", "import"]):
        queries.extend([
            f"Qatar trade balance exports imports 2024",
            f"Qatar trading partners statistics",
            f"Qatar non-oil exports diversification",
        ])
    
    if any(term in query_lower for term in ["health", "hospital", "medical"]):
        queries.extend([
            f"Qatar healthcare system statistics",
            f"Qatar hospitals medical facilities",
            f"Qatar health expenditure per capita",
        ])
    
    if any(term in query_lower for term in ["skill", "training", "workforce"]):
        queries.extend([
            f"Qatar skills gap analysis training",
            f"Qatar workforce development programs",
            f"Qatar technical training institutes",
        ])
    
    # Always add Qatar-specific query
    queries.append(f"Qatar {main_query[:40]} statistics data")
    
    # Deduplicate
    seen = set()
    unique = []
    for q in queries:
        q_lower = q.lower().strip()
        if q_lower not in seen:
            seen.add(q_lower)
            unique.append(q)
    
    return unique[:10]  # Max 10 queries


def _format_brave_result(result: Dict[str, Any], query: str, is_news: bool = False) -> Dict[str, Any]:
    """
    Format a Brave search result as a fact.
    """
    # Extract numerical data from snippet
    snippet = result.get("description", "") or result.get("snippet", "")
    
    return {
        "metric": "brave_search_result",
        "title": result.get("title", ""),
        "text": snippet[:500],
        "url": result.get("url", ""),
        "query": query[:100],
        "source": f"Brave Search ({'News' if is_news else 'Web'})",
        "source_priority": 75 if is_news else 70,
        "confidence": 0.70,
        "is_news": is_news,
        "age": result.get("age", ""),
        "cached": False
    }


async def search_brave_direct(query: str, count: int = 10) -> List[Dict[str, Any]]:
    """
    Direct Brave search for a single query.
    """
    api_key = os.getenv("BRAVE_API_KEY")
    if not api_key:
        return []
    
    async with aiohttp.ClientSession() as session:
        return await _brave_search(session, api_key, query, count=count)
