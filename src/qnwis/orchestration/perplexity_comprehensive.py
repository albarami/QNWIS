"""
COMPREHENSIVE Perplexity AI Extraction - Using PRO SEARCH API

Perplexity Pro Search provides:
- Multi-step reasoning with automated tools
- web_search: Intelligent web searches
- fetch_url_content: Fetch detailed content from URLs  
- execute_python: Run Python code for calculations
- Real-time thought streaming
- reasoning_steps in responses
- Context management with threading

This extractor uses PRO SEARCH for ministerial-grade data extraction.
"""

import logging
import asyncio
import os
import re
import json
from typing import List, Dict, Any, Optional, AsyncIterator

import aiohttp

logger = logging.getLogger(__name__)

# Perplexity API endpoints
PERPLEXITY_SEARCH_URL = "https://api.perplexity.ai/search"
PERPLEXITY_CHAT_URL = "https://api.perplexity.ai/chat/completions"

# Pro Search model
SONAR_PRO_MODEL = "sonar-pro"


async def extract_perplexity_comprehensive(query: str) -> List[Dict[str, Any]]:
    """
    Extract comprehensive real-time intelligence from Perplexity AI.
    
    Uses PRO SEARCH with:
    1. Multi-step reasoning with automated tools
    2. web_search, fetch_url_content, execute_python tools
    3. Threading for context management
    4. Automatic classification (pro/fast based on complexity)
    5. Real-time thought streaming and reasoning_steps
    """
    all_facts = []
    api_key = os.getenv("PERPLEXITY_API_KEY")
    
    if not api_key:
        logger.warning("  Perplexity API key not configured")
        return all_facts
    
    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        async with aiohttp.ClientSession() as session:
            # 1. Use PRO SEARCH for complex multi-step reasoning
            logger.info("  Using Perplexity PRO SEARCH for multi-step reasoning...")
            pro_search_facts = await _perplexity_pro_search(
                session, headers, query
            )
            all_facts.extend(pro_search_facts)
            
            # 2. Use threaded conversation for follow-up questions
            if pro_search_facts:
                thread_id = pro_search_facts[0].get("thread_id") if pro_search_facts else None
                
                if thread_id:
                    # Ask follow-up questions in same thread context
                    follow_up_questions = _generate_follow_up_questions(query)
                    
                    for fq in follow_up_questions[:2]:  # 2 follow-ups
                        try:
                            follow_up_facts = await _perplexity_threaded_followup(
                                session, headers, fq, thread_id
                            )
                            all_facts.extend(follow_up_facts)
                            await asyncio.sleep(0.3)
                        except Exception as e:
                            logger.warning(f"  Follow-up failed: {e}")
            
            # 3. Also use Search API for additional coverage
            search_queries = _generate_search_queries(query)
            for sq in search_queries[:3]:  # 3 searches
                try:
                    search_facts = await _perplexity_search(
                        session, headers, [sq],
                        max_results=10,
                        search_recency_filter="year"
                    )
                    all_facts.extend(search_facts)
                    await asyncio.sleep(0.3)
                except Exception as e:
                    logger.warning(f"  Search query failed: {e}")
        
        logger.info(f"  Perplexity PRO SEARCH TOTAL: {len(all_facts)} facts with reasoning")
        
    except Exception as e:
        logger.error(f"Perplexity comprehensive extraction error: {e}")
    
    return all_facts


async def _perplexity_pro_search(
    session: aiohttp.ClientSession,
    headers: dict,
    query: str
) -> List[Dict[str, Any]]:
    """
    Execute Perplexity PRO SEARCH with multi-step reasoning.
    
    Pro Search uses automated tools:
    - web_search: Intelligent web searches
    - fetch_url_content: Fetch detailed content from URLs
    - execute_python: Run Python code for calculations
    
    Requires streaming for full reasoning capabilities.
    """
    facts = []
    
    # Build system prompt for ministerial-grade research
    system_prompt = """You are an expert research analyst for Qatar's Ministry. 
Provide SPECIFIC statistics, numbers, and data with exact citations.
Focus on Qatar, GCC, and relevant global benchmarks.
Use multiple sources to verify facts.
Include recent data (2023-2024) when available.
Always cite your sources with URLs."""
    
    payload = {
        "model": SONAR_PRO_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"""Research the following question thoroughly. Use multiple sources, fetch detailed content, and perform any necessary calculations:

{query}

Provide:
1. Key statistics with exact numbers and citations
2. Recent developments (2023-2024)
3. Regional comparisons (GCC, global)
4. Data sources and methodology
5. Any calculations or analysis needed"""
            }
        ],
        "stream": False,  # Non-streaming for now to get full response
        "use_threads": True,  # Enable threading for follow-ups
        "web_search_options": {
            "search_type": "pro"  # Enable PRO SEARCH with tools
        },
        "temperature": 0.1,
        "max_tokens": 4000,
        "return_citations": True
    }
    
    try:
        async with session.post(PERPLEXITY_CHAT_URL, headers=headers, json=payload) as response:
            if response.status == 200:
                data = await response.json()
                
                # Extract thread_id for follow-ups
                thread_id = data.get("thread_id")
                
                # Extract content
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                
                # Extract citations
                citations = data.get("citations", [])
                
                # Extract search results if available
                search_results = data.get("search_results", [])
                
                # Extract reasoning steps if available
                reasoning_steps = data.get("reasoning_steps", [])
                
                # Process reasoning steps (contains tool outputs)
                for step in reasoning_steps:
                    step_type = step.get("type", "")
                    thought = step.get("thought", "")
                    
                    if step_type == "web_search":
                        web_search_data = step.get("web_search", {})
                        results = web_search_data.get("search_results", [])
                        for result in results:
                            facts.append({
                                "metric": "perplexity_pro_web_search",
                                "title": result.get("title", ""),
                                "text": result.get("snippet", "")[:1000],
                                "url": result.get("url", ""),
                                "date": result.get("date", ""),
                                "thought": thought,
                                "source": "Perplexity Pro Search (web_search tool)",
                                "source_priority": 90,
                                "confidence": 0.92,
                                "thread_id": thread_id
                            })
                    
                    elif step_type == "fetch_url_content":
                        fetch_data = step.get("fetch_url_content", {})
                        contents = fetch_data.get("contents", [])
                        for content_item in contents:
                            facts.append({
                                "metric": "perplexity_pro_url_content",
                                "title": content_item.get("title", ""),
                                "text": content_item.get("snippet", "")[:1500],
                                "url": content_item.get("url", ""),
                                "thought": thought,
                                "source": "Perplexity Pro Search (fetch_url_content tool)",
                                "source_priority": 92,
                                "confidence": 0.95,
                                "thread_id": thread_id
                            })
                    
                    elif step_type == "execute_python":
                        python_data = step.get("execute_python", {})
                        code = python_data.get("code", "")
                        result = python_data.get("result", "")
                        if result:
                            facts.append({
                                "metric": "perplexity_pro_calculation",
                                "text": f"Calculation result: {result}",
                                "code": code[:500],
                                "thought": thought,
                                "source": "Perplexity Pro Search (execute_python tool)",
                                "source_priority": 88,
                                "confidence": 0.90,
                                "thread_id": thread_id
                            })
                
                # Process search results
                for result in search_results:
                    facts.append({
                        "metric": "perplexity_pro_search_result",
                        "title": result.get("title", ""),
                        "text": result.get("snippet", "")[:1000],
                        "url": result.get("url", ""),
                        "date": result.get("date", ""),
                        "source": "Perplexity Pro Search",
                        "source_priority": 88,
                        "confidence": 0.90,
                        "thread_id": thread_id
                    })
                
                # Extract facts from main content
                if content:
                    content_facts = _extract_facts_from_content(content, query, citations)
                    for fact in content_facts:
                        fact["thread_id"] = thread_id
                        fact["source"] = "Perplexity Pro Search (sonar-pro)"
                        fact["source_priority"] = 90
                    facts.extend(content_facts)
                
                logger.info(f"    Pro Search: {len(facts)} facts, {len(reasoning_steps)} reasoning steps")
                
            else:
                error_text = await response.text()
                logger.warning(f"  Perplexity Pro Search error {response.status}: {error_text[:300]}")
                
    except Exception as e:
        logger.error(f"Perplexity Pro Search error: {e}")
    
    return facts


async def _perplexity_threaded_followup(
    session: aiohttp.ClientSession,
    headers: dict,
    question: str,
    thread_id: str
) -> List[Dict[str, Any]]:
    """
    Ask a follow-up question using thread context.
    
    Thread maintains conversation history for contextual follow-ups.
    """
    facts = []
    
    payload = {
        "model": SONAR_PRO_MODEL,
        "messages": [
            {
                "role": "user",
                "content": question
            }
        ],
        "stream": False,
        "use_threads": True,
        "thread_id": thread_id,  # Continue in same context
        "web_search_options": {
            "search_type": "auto"  # Auto-classify complexity
        },
        "temperature": 0.1,
        "max_tokens": 2000,
        "return_citations": True
    }
    
    try:
        async with session.post(PERPLEXITY_CHAT_URL, headers=headers, json=payload) as response:
            if response.status == 200:
                data = await response.json()
                
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                citations = data.get("citations", [])
                
                if content:
                    content_facts = _extract_facts_from_content(content, question, citations)
                    for fact in content_facts:
                        fact["thread_id"] = thread_id
                        fact["source"] = "Perplexity Threaded Follow-up"
                        fact["source_priority"] = 85
                    facts.extend(content_facts)
                
                logger.debug(f"    Threaded follow-up: {len(facts)} facts")
                
            else:
                error_text = await response.text()
                logger.warning(f"  Threaded follow-up error {response.status}: {error_text[:200]}")
                
    except Exception as e:
        logger.error(f"Perplexity threaded follow-up error: {e}")
    
    return facts


def _generate_follow_up_questions(query: str) -> List[str]:
    """Generate contextual follow-up questions based on query."""
    query_lower = query.lower()
    questions = []
    
    if any(term in query_lower for term in ["labor", "employment", "job", "workforce"]):
        questions.extend([
            "What are the specific Qatarization targets and current progress rates?",
            "What are the major skills gaps in Qatar's labor market?"
        ])
    
    if any(term in query_lower for term in ["gdp", "economy", "growth"]):
        questions.extend([
            "What is Qatar's non-oil GDP growth rate and diversification progress?",
            "How does Qatar's fiscal position compare to other GCC countries?"
        ])
    
    if any(term in query_lower for term in ["oil", "gas", "lng", "energy"]):
        questions.extend([
            "What is the current status of North Field expansion projects?",
            "What are Qatar's LNG export contracts and capacity projections?"
        ])
    
    if any(term in query_lower for term in ["skill", "training"]):
        questions.extend([
            "What technical training capacity does Qatar have currently?",
            "What are the major skills shortages by sector?"
        ])
    
    # Default follow-ups
    questions.extend([
        f"What are the latest 2024 statistics and developments for this topic?",
        f"How does Qatar compare to other GCC countries on this topic?"
    ])
    
    return questions[:4]  # Max 4 follow-ups


def _generate_search_queries(query: str) -> List[str]:
    """Generate search queries for additional coverage."""
    query_lower = query.lower()
    queries = []
    
    queries.append(f"Qatar {query[:50]} statistics 2024")
    queries.append(f"GCC {query[:40]} comparison data")
    
    if "labor" in query_lower or "employment" in query_lower:
        queries.append("Qatar labor market statistics unemployment rate 2024")
    
    if "gdp" in query_lower or "economy" in query_lower:
        queries.append("Qatar GDP economic growth forecast 2024 2025")
    
    if "energy" in query_lower or "lng" in query_lower:
        queries.append("Qatar LNG production capacity North Field 2024")
    
    return queries[:5]


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
