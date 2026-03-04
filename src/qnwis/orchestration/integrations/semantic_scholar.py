"""Semantic Scholar integration for academic research retrieval."""
import asyncio
import logging
import math
import os
from datetime import datetime
from typing import Any, Dict, List

import requests

from .common import generate_smart_queries

logger = logging.getLogger(__name__)

SEED_PAPER_ID = "649def34f8be52c8b66281af98ae884c09aef38b"

LABOR_KEYWORDS = [
    "labor", "labour", "employment", "workforce", "worker", "nationalization",
    "localization", "qatarization", "gcc", "qatar", "expat", "migration",
    "talent", "skill", "job", "hiring", "recruitment", "training", "education",
]

POLICY_KEYWORDS = [
    "policy", "regulation", "government", "legislation", "reform", "strategy",
    "initiative", "program", "framework", "implementation", "compliance",
    "mandate", "requirement",
]


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _get_headers() -> dict:
    api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY", "").strip()
    return {"x-api-key": api_key} if api_key else {}


async def _recommendations_search(
    seed_paper_id: str, keywords: List[str], headers: dict,
    top_n: int = 10, metric_name: str = "research_finding",
) -> List[Dict[str, Any]]:
    """Search via recommendations API and filter by keywords."""
    try:
        url = f"https://api.semanticscholar.org/recommendations/v1/papers/forpaper/{seed_paper_id}"
        params = {
            "fields": "title,year,abstract,url,citationCount",
            "limit": "20",
            "from": "recent",
        }
        logger.debug("Strategy 1: Recommendations API...")
        response = await asyncio.to_thread(
            lambda: requests.get(url, params=params, headers=headers, timeout=10)
        )
        if response.status_code != 200:
            logger.debug("Recommendations API: HTTP %d", response.status_code)
            return []

        papers = response.json().get("recommendedPapers", [])
        logger.debug("Recommendations returned %d papers", len(papers))

        filtered = [
            p for p in papers
            if any(
                kw in p.get("title", "").lower() or kw in str(p.get("abstract", "")).lower()
                for kw in keywords
            )
        ]
        logger.debug("Filtered to %d relevant papers", len(filtered))

        facts: List[Dict[str, Any]] = []
        for paper in filtered[:top_n]:
            facts.append({
                "metric": metric_name,
                "value": paper.get("title", ""),
                "source": f"Semantic Scholar ({paper.get('year', 'N/A')})",
                "source_priority": 75,
                "confidence": 0.75,
                "raw_text": (
                    f"Research: {paper.get('title')} | "
                    f"Citations: {paper.get('citationCount', 0)} | "
                    f"{str(paper.get('abstract', ''))[:150]}"
                ),
                "timestamp": datetime.now().isoformat(),
                "url": paper.get("url", ""),
            })
        await asyncio.sleep(1)
        return facts
    except Exception as e:
        logger.debug("Recommendations error: %s", e)
        return []


async def _broad_search_fallback(
    search_queries: List[str], headers: dict,
    metric_name: str = "research_finding",
) -> List[Dict[str, Any]]:
    """Fallback to broad search queries."""
    logger.debug("Strategy 2: Broad search fallback...")
    for search_query in search_queries:
        try:
            url = "https://api.semanticscholar.org/graph/v1/paper/search/bulk"
            response = await asyncio.to_thread(
                lambda q=search_query: requests.get(
                    url,
                    params={"query": q, "fields": "title,year,abstract,url", "year": "2015-", "limit": "10"},
                    headers=headers,
                    timeout=10,
                )
            )
            if response.status_code == 200:
                papers = response.json().get("data", [])
                if papers:
                    facts = [{
                        "metric": metric_name,
                        "value": p.get("title", ""),
                        "source": f"Semantic Scholar ({p.get('year', 'N/A')})",
                        "source_priority": 75,
                        "confidence": 0.70,
                        "raw_text": f"Research: {p.get('title')}",
                        "timestamp": datetime.now().isoformat(),
                        "url": p.get("url", ""),
                    } for p in papers[:3]]
                    await asyncio.sleep(1)
                    return facts
        except Exception as e:
            logger.debug("Search '%s' error: %s", search_query, e)
    return []


# ---------------------------------------------------------------------------
# Public fetch functions
# ---------------------------------------------------------------------------

async def fetch_semantic_scholar_labor(query: str) -> List[Dict[str, Any]]:
    """Fetch labor market research using recommendations + broad search."""
    try:
        logger.info("Semantic Scholar: Fetching labor market research...")
        headers = _get_headers()
        facts = await _recommendations_search(SEED_PAPER_ID, LABOR_KEYWORDS, headers)
        if facts:
            return facts
        return await _broad_search_fallback(
            ["workforce development", "employment policy", "labor economics",
             "talent management", "human capital"],
            headers, "research_finding",
        )
    except Exception as e:
        logger.warning("Semantic Scholar labor error: %s", e)
        return []


async def fetch_semantic_scholar_policy(query: str) -> List[Dict[str, Any]]:
    """Fetch policy research using recommendations + broad search."""
    try:
        logger.info("Semantic Scholar: Fetching policy research...")
        headers = _get_headers()
        facts = await _recommendations_search(
            SEED_PAPER_ID, POLICY_KEYWORDS, headers, metric_name="policy_research",
        )
        if facts:
            return facts
        return await _broad_search_fallback(
            ["public policy", "policy analysis", "government policy", "economic policy"],
            headers, "policy_research",
        )
    except Exception as e:
        logger.warning("Semantic Scholar policy error: %s", e)
        return []


async def fetch_semantic_scholar_smart(query: str) -> List[Dict[str, Any]]:
    """Fetch academic research using LLM-generated smart queries (aggressive strategy)."""
    try:
        logger.info("Semantic Scholar: Comprehensive academic research extraction...")
        smart_queries = await generate_smart_queries(query)
        academic_queries = smart_queries.get("academic_queries", [query[:100]])
        key_concepts = smart_queries.get("key_concepts", [])

        broader_queries = [
            query[:80],
            " ".join(key_concepts[:3]) if key_concepts else query[:50],
        ]
        all_queries = list(set(academic_queries + broader_queries))
        logger.debug("Searching with %d queries, concepts: %s", len(all_queries), key_concepts)

        headers = _get_headers()
        all_papers: List[Dict[str, Any]] = []
        seen_ids: set = set()

        for search_query in all_queries[:4]:
            try:
                url = "https://api.semanticscholar.org/graph/v1/paper/search"
                response = await asyncio.to_thread(
                    lambda q=search_query: requests.get(
                        url,
                        params={
                            "query": q,
                            "fields": "title,year,abstract,url,citationCount,paperId",
                            "limit": "50",
                        },
                        headers=headers,
                        timeout=15,
                    )
                )
                if response.status_code == 200:
                    for paper in response.json().get("data", []):
                        pid = paper.get("paperId")
                        if pid and pid not in seen_ids:
                            seen_ids.add(pid)
                            paper["_query"] = search_query
                            all_papers.append(paper)
                await asyncio.sleep(0.3)
            except Exception as e:
                logger.debug("Query error: %s", e)

        if len(all_papers) < 30:
            try:
                bulk_query = " OR ".join(key_concepts[:3]) if key_concepts else query[:60]
                response = await asyncio.to_thread(
                    lambda: requests.get(
                        "https://api.semanticscholar.org/graph/v1/paper/search/bulk",
                        params={
                            "query": bulk_query,
                            "fields": "title,year,abstract,url,citationCount,paperId",
                            "limit": "100",
                        },
                        headers=headers,
                        timeout=15,
                    )
                )
                if response.status_code == 200:
                    for paper in response.json().get("data", []):
                        pid = paper.get("paperId")
                        if pid and pid not in seen_ids:
                            seen_ids.add(pid)
                            all_papers.append(paper)
            except Exception as e:
                logger.debug("Bulk search error: %s", e)

        logger.debug("Total unique papers collected: %d", len(all_papers))

        scored_papers = []
        for paper in all_papers:
            text = paper.get("title", "").lower() + " " + str(paper.get("abstract", "")).lower()
            citations = paper.get("citationCount", 0) or 0
            year = paper.get("year", 2020) or 2020
            score = (
                sum(1 for c in key_concepts if c.lower() in text) * 20
                + sum(1 for w in query.lower().split() if len(w) > 3 and w in text) * 5
                + math.log10(citations + 1) * 3
                + max(0, (year - 2015)) * 2
            )
            paper["_score"] = score
            scored_papers.append(paper)

        scored_papers.sort(key=lambda p: p.get("_score", 0), reverse=True)
        top_papers = scored_papers[:20]

        return [{
            "metric": "academic_research",
            "value": p.get("title", ""),
            "source": f"Semantic Scholar ({p.get('year', 'N/A')}) - {p.get('citationCount', 0) or 0} citations",
            "source_priority": 75 + min(p.get("_score", 0) / 10, 15),
            "confidence": min(0.70 + (p.get("_score", 0) / 100), 0.95),
            "raw_text": (
                f"Research: {p.get('title')} | "
                f"Citations: {p.get('citationCount', 0) or 0} | "
                f"{str(p.get('abstract', ''))[:300]}"
            ),
            "timestamp": datetime.now().isoformat(),
            "url": p.get("url", ""),
            "paper_id": p.get("paperId", ""),
            "relevance_score": p.get("_score", 0),
        } for p in top_papers]

    except Exception as e:
        logger.warning("Semantic Scholar smart search error: %s", e)
        return []
