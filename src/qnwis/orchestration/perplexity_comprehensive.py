"""
COMPREHENSIVE Perplexity AI Extraction

Perplexity AI has access to BILLIONS of web sources with real-time information.
We should extract 20-50+ high-quality facts with citations, not just 1-3.

Strategy:
1. Multiple targeted queries for different aspects
2. Extract citations from responses
3. Parse structured data from responses
4. Domain-agnostic query generation
"""

import logging
import asyncio
import re
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


async def extract_perplexity_comprehensive(query: str) -> List[Dict[str, Any]]:
    """
    Extract comprehensive real-time intelligence from Perplexity AI.
    
    Uses multiple strategies:
    1. Multiple targeted sub-queries
    2. Citation extraction
    3. Fact parsing from responses
    
    Uses direct API calls (no separate client module needed).
    """
    import os
    import aiohttp
    
    all_facts = []
    api_key = os.getenv("PERPLEXITY_API_KEY")
    
    if not api_key:
        logger.warning("  Perplexity API key not configured")
        return all_facts
    
    try:
        # Generate multiple targeted queries
        sub_queries = _generate_sub_queries(query)
        logger.info(f"  Querying Perplexity with {len(sub_queries)} targeted questions")
        
        url = "https://api.perplexity.ai/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        async with aiohttp.ClientSession() as session:
            for i, q in enumerate(sub_queries):
                try:
                    logger.debug(f"  Query {i+1}/{len(sub_queries)}: {q[:50]}...")
                    
                    # Build the payload for this query
                    payload = {
                        "model": "llama-3.1-sonar-small-128k-online",
                        "messages": [
                            {
                                "role": "system",
                                "content": "You are an expert research assistant. Provide SPECIFIC statistics, numbers, and facts with citations. Always cite sources."
                            },
                            {
                                "role": "user",
                                "content": f"Find specific statistics and data for: {q}\n\nProvide EXACT numbers, percentages, and figures. Cite all sources."
                            }
                        ],
                        "temperature": 0.1,
                        "max_tokens": 1000,
                        "return_citations": True
                    }
                    
                    async with session.post(url, headers=headers, json=payload) as response:
                        if response.status == 200:
                            data = await response.json()
                            facts = _extract_facts_from_response(data, q)
                            all_facts.extend(facts)
                            logger.debug(f"    Extracted {len(facts)} facts")
                        else:
                            error_text = await response.text()
                            logger.warning(f"  Perplexity API error {response.status}: {error_text[:100]}")
                    
                    # Small delay between queries to be respectful
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    logger.warning(f"  Perplexity query failed: {e}")
                    continue
        
        logger.info(f"  Perplexity TOTAL: {len(all_facts)} facts with citations")
        
    except Exception as e:
        logger.error(f"Perplexity comprehensive extraction error: {e}")
    
    return all_facts


def _generate_sub_queries(main_query: str) -> List[str]:
    """
    Generate multiple targeted sub-queries for comprehensive coverage.
    """
    queries = [main_query]  # Original query
    
    # Detect domains from query
    query_lower = main_query.lower()
    
    # Add domain-specific queries
    if any(term in query_lower for term in ["labor", "employment", "job", "work", "unemployment"]):
        queries.extend([
            f"Qatar current unemployment rate statistics 2024",
            f"Qatar labor market trends and employment data",
            f"Qatarization policy progress and targets",
        ])
    
    if any(term in query_lower for term in ["gdp", "economy", "economic", "growth", "fiscal"]):
        queries.extend([
            f"Qatar GDP 2024 current statistics",
            f"Qatar economic growth forecast 2025",
            f"Qatar government budget and fiscal policy",
        ])
    
    if any(term in query_lower for term in ["oil", "gas", "lng", "energy", "petroleum"]):
        queries.extend([
            f"Qatar LNG production capacity 2024",
            f"Qatar North Field expansion progress",
            f"Qatar energy sector statistics",
        ])
    
    if any(term in query_lower for term in ["tourism", "visitor", "hotel", "tourist"]):
        queries.extend([
            f"Qatar tourism statistics 2024",
            f"Qatar visitor arrivals World Cup legacy",
            f"Qatar hotel occupancy rates",
        ])
    
    if any(term in query_lower for term in ["education", "university", "school", "graduate", "stem"]):
        queries.extend([
            f"Qatar education system statistics 2024",
            f"Qatar university enrollment and graduation rates",
            f"Qatar STEM education initiatives",
        ])
    
    if any(term in query_lower for term in ["trade", "export", "import", "commerce"]):
        queries.extend([
            f"Qatar trade balance 2024",
            f"Qatar major trading partners",
            f"Qatar non-oil exports statistics",
        ])
    
    if any(term in query_lower for term in ["health", "hospital", "medical", "healthcare"]):
        queries.extend([
            f"Qatar healthcare system statistics 2024",
            f"Qatar hospital capacity and services",
            f"Qatar health expenditure per capita",
        ])
    
    if any(term in query_lower for term in ["skill", "training", "workforce"]):
        queries.extend([
            f"Qatar skills gap analysis 2024",
            f"Qatar workforce training programs",
            f"Qatar Vision 2030 human capital development",
        ])
    
    # Always add these general Qatar queries
    queries.extend([
        f"Qatar {main_query[:50]} latest statistics",
        f"Qatar Vision 2030 {main_query[:30]} targets",
    ])
    
    # Deduplicate
    seen = set()
    unique_queries = []
    for q in queries:
        q_lower = q.lower().strip()
        if q_lower not in seen:
            seen.add(q_lower)
            unique_queries.append(q)
    
    return unique_queries[:8]  # Max 8 queries


def _extract_facts_from_response(response: Dict[str, Any], query: str) -> List[Dict[str, Any]]:
    """
    Extract individual facts from Perplexity response.
    """
    facts = []
    
    # Get the main content
    content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
    if not content:
        content = response.get("text", "") or response.get("answer", "")
    
    if not content:
        return facts
    
    # Get citations
    citations = response.get("citations", [])
    
    # Extract numerical facts
    number_pattern = r'(\d+(?:,\d{3})*(?:\.\d+)?)\s*(%|percent|billion|million|trillion|thousand|USD|\$|QAR|workers|jobs|people|years|months)?'
    matches = re.findall(number_pattern, content, re.IGNORECASE)
    
    # Split content into sentences
    sentences = re.split(r'[.!?]', content)
    
    for sentence in sentences:
        sentence = sentence.strip()
        if len(sentence) < 20:
            continue
        
        # Check if sentence contains numbers (data points)
        if re.search(r'\d', sentence):
            facts.append({
                "metric": "perplexity_fact",
                "text": sentence[:500],
                "query": query[:100],
                "source": "Perplexity AI (Real-time Web)",
                "citations": citations[:3] if citations else [],
                "confidence": 0.85,
                "source_priority": 82,
                "cached": False
            })
    
    # Also add the full response as a summary fact
    if len(content) > 100:
        facts.append({
            "metric": "perplexity_summary",
            "text": content[:1000],
            "query": query[:100],
            "source": "Perplexity AI (Real-time Web)",
            "citations": citations if citations else [],
            "confidence": 0.80,
            "source_priority": 82,
            "cached": False
        })
    
    return facts


async def query_perplexity_direct(question: str) -> Dict[str, Any]:
    """
    Direct query to Perplexity for single question.
    Returns structured response with citations.
    """
    import os
    import aiohttp
    
    api_key = os.getenv("PERPLEXITY_API_KEY")
    if not api_key:
        return {"error": "PERPLEXITY_API_KEY not configured"}
    
    try:
        url = "https://api.perplexity.ai/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "llama-3.1-sonar-small-128k-online",
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert research assistant. Provide SPECIFIC statistics and data with citations."
                },
                {
                    "role": "user",
                    "content": question
                }
            ],
            "temperature": 0.1,
            "max_tokens": 1000,
            "return_citations": True
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {"error": f"API error {response.status}"}
                    
    except Exception as e:
        logger.error(f"Perplexity direct query error: {e}")
        return {"error": str(e)}
