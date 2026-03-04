"""Perplexity AI integration for real-time intelligence gathering."""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import aiohttp

from .common import PERPLEXITY_PROMPT_TEMPLATES, generate_smart_queries

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Shared helper
# ---------------------------------------------------------------------------

async def _perplexity_chat(
    api_key: str, messages: list, max_tokens: int = 500,
) -> Optional[Tuple[str, list]]:
    """Send a chat request to Perplexity AI. Returns (answer, citations) or None."""
    url = "https://api.perplexity.ai/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": "sonar-pro", "messages": messages, "max_tokens": max_tokens}
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=payload) as response:
            if response.status == 200:
                data = await response.json()
                answer = data["choices"][0]["message"]["content"]
                citations = data.get("citations", [])
                return answer, citations
            error_text = await response.text()
            logger.warning("Perplexity error: %d - %s", response.status, error_text[:200])
    return None


def _citation_facts(citations: list, prefix: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Convert citation list to fact dicts."""
    return [
        {
            "metric": f"{prefix}_citation_{i + 1}",
            "value": citation,
            "source": "Perplexity AI (verified citation)",
            "source_priority": 80,
            "confidence": 0.80,
            "raw_text": f"Citation: {citation}",
            "timestamp": datetime.now().isoformat(),
        }
        for i, citation in enumerate(citations[:limit])
    ]


# ---------------------------------------------------------------------------
# Public fetch functions
# ---------------------------------------------------------------------------

async def fetch_perplexity_gcc(api_key: str, query: str) -> List[Dict[str, Any]]:
    """Fetch GCC competitive intelligence from Perplexity."""
    if not api_key:
        return []
    try:
        logger.info("Perplexity: Analyzing GCC competition...")
        result = await _perplexity_chat(api_key, [{
            "role": "user",
            "content": (
                "What are the latest GCC labor market trends and regional "
                f"competition related to: {query[:200]}"
            ),
        }])
        if result:
            answer, _ = result
            logger.debug("Perplexity GCC response: %s...", answer[:100])
            return [{
                "metric": "gcc_intelligence",
                "value": answer[:300],
                "source": "Perplexity AI (real-time analysis)",
                "source_priority": 70,
                "confidence": 0.75,
                "raw_text": answer,
                "timestamp": datetime.now().isoformat(),
            }]
        return []
    except Exception as e:
        logger.warning("Perplexity GCC error: %s", e)
        return []


async def fetch_perplexity_policy(api_key: str, query: str) -> List[Dict[str, Any]]:
    """Fetch policy analysis from Perplexity."""
    if not api_key:
        return []
    try:
        logger.info("Perplexity: Analyzing policy implications...")
        result = await _perplexity_chat(api_key, [{
            "role": "user",
            "content": (
                "What are successful examples and risks of workforce nationalization "
                f"policies similar to: {query[:200]}"
            ),
        }])
        if result:
            answer, _ = result
            return [{
                "metric": "policy_analysis",
                "value": answer[:300],
                "source": "Perplexity AI (policy analysis)",
                "source_priority": 70,
                "confidence": 0.75,
                "raw_text": answer,
                "timestamp": datetime.now().isoformat(),
            }]
        return []
    except Exception as e:
        logger.warning("Perplexity policy error: %s", e)
        return []


async def fetch_perplexity_energy(api_key: str, query: str) -> List[Dict[str, Any]]:
    """Fetch energy sector analysis with citations."""
    if not api_key:
        return []
    try:
        logger.info("Perplexity: Analyzing energy sector with real-time data...")
        result = await _perplexity_chat(api_key, [{
            "role": "user",
            "content": (
                f"Provide detailed, sourced data on Qatar's energy sector related to: {query[:200]}\n\n"
                "Include SPECIFIC DATA with citations:\n"
                "1. Current renewable energy capacity (MW) and percentage of total energy mix\n"
                "2. Oil and gas production volumes and export revenues (recent year)\n"
                "3. Energy transition investment commitments and timelines\n"
                "4. Carbon emissions data and reduction targets\n"
                "5. Comparison with GCC peers (Saudi, UAE)\n"
                "6. Recent energy sector projects and their costs\n\n"
                "Cite all sources and provide exact figures where available."
            ),
        }], max_tokens=800)
        if result:
            answer, citations = result
            logger.debug("Perplexity energy response: %s...", answer[:100])
            facts: List[Dict[str, Any]] = [{
                "metric": "energy_sector_analysis",
                "value": answer[:500],
                "source": "Perplexity AI (energy analysis with citations)",
                "source_priority": 85,
                "confidence": 0.85,
                "raw_text": answer,
                "citations": citations,
                "timestamp": datetime.now().isoformat(),
            }]
            facts.extend(_citation_facts(citations, "energy"))
            return facts
        return []
    except Exception as e:
        logger.warning("Perplexity energy error: %s", e)
        return []


async def fetch_perplexity_food_security(api_key: str, query: str) -> List[Dict[str, Any]]:
    """Fetch food security analysis with citations."""
    if not api_key:
        return []
    try:
        logger.info("Perplexity: Analyzing food security with real-time data...")
        result = await _perplexity_chat(api_key, [{
            "role": "user",
            "content": (
                f"Provide detailed, sourced data on Qatar's food security related to: {query[:200]}\n\n"
                "Include SPECIFIC DATA with citations:\n"
                "1. Current food import dependency percentage by category\n"
                "2. Recent food import costs (annual, in billions)\n"
                "3. Local agricultural production capacity and percentage of consumption met\n"
                "4. Food security investments and strategic reserves\n"
                "5. Comparison with GCC peers on food self-sufficiency\n"
                "6. Recent government initiatives and their budgets\n\n"
                "Cite all sources and provide exact figures where available."
            ),
        }], max_tokens=800)
        if result:
            answer, citations = result
            facts: List[Dict[str, Any]] = [{
                "metric": "food_security_analysis",
                "value": answer[:500],
                "source": "Perplexity AI (food security analysis with citations)",
                "source_priority": 85,
                "confidence": 0.85,
                "raw_text": answer,
                "citations": citations,
                "timestamp": datetime.now().isoformat(),
            }]
            facts.extend(_citation_facts(citations, "food_security"))
            return facts
        return []
    except Exception as e:
        logger.warning("Perplexity food security error: %s", e)
        return []


async def fetch_perplexity_smart(api_key: str, query: str) -> List[Dict[str, Any]]:
    """Fetch real-time intelligence using LLM-generated smart queries."""
    if not api_key:
        return []
    try:
        logger.info("Perplexity: Generating smart real-time queries...")
        smart_queries = await generate_smart_queries(query)
        realtime_queries = smart_queries.get("realtime_queries", [query[:100]])
        data_needs = smart_queries.get("data_needs", query)
        combined_query = " ".join(realtime_queries[:2])
        logger.debug("Smart queries: %s", realtime_queries)

        result = await _perplexity_chat(api_key, [{
            "role": "user",
            "content": (
                f"Find the most recent, specific data and statistics to answer:\n\n"
                f"QUESTION: {query}\n\n"
                f"SEARCH FOCUS: {combined_query}\n\n"
                f"DATA NEEDED: {data_needs}\n\n"
                "Provide:\n"
                "1. Specific numbers and statistics with exact figures\n"
                "2. Most recent data available (2024-2025 preferred)\n"
                "3. Source citations for verification\n"
                "4. Comparisons if relevant (regional, historical)\n"
                "Be concise but data-rich."
            ),
        }], max_tokens=700)
        if result:
            answer, citations = result
            logger.debug("Perplexity response: %s...", answer[:100])
            all_facts: List[Dict[str, Any]] = [{
                "metric": "realtime_intelligence",
                "value": answer[:500],
                "source": "Perplexity AI (smart context-aware search)",
                "source_priority": 85,
                "confidence": 0.85,
                "raw_text": answer,
                "citations": citations,
                "timestamp": datetime.now().isoformat(),
                "query_used": combined_query,
                "data_needs": data_needs,
            }]
            all_facts.extend(_citation_facts(citations, "verified_source", limit=3))
            return all_facts
        return []
    except Exception as e:
        logger.warning("Perplexity smart search error: %s", e)
        return []


async def fetch_perplexity_targeted(
    api_key: str, query: str, search_type: str,
) -> List[Dict[str, Any]]:
    """Targeted Perplexity search with specific prompts."""
    if not api_key:
        return []
    prompt_template = PERPLEXITY_PROMPT_TEMPLATES.get(
        search_type, PERPLEXITY_PROMPT_TEMPLATES["statistics"],
    )
    prompt = prompt_template.replace("{query}", query)
    try:
        result = await _perplexity_chat(api_key, [{"role": "user", "content": prompt}])
        if result:
            content, _ = result
            return [{
                "metric": "targeted_research",
                "value": content[:200],
                "raw_text": content,
                "source": "Perplexity (Targeted)",
                "confidence": 0.85,
                "timestamp": datetime.now().isoformat(),
            }]
    except Exception as e:
        logger.warning("Perplexity targeted error: %s", e)
    return []
