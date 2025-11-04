"""Semantic Scholar API Client for QNWIS.

PRODUCTION-READY: Uses environment variables, no hardcoded secrets.
Provides academic research data for labor market intelligence.
"""

from __future__ import annotations

import os
import time
from collections.abc import Iterable
from typing import Any

import httpx

from ._http import send_with_retry

DEFAULT_TIMEOUT = 15.0
BASE_URL = "https://api.semanticscholar.org/graph/v1"
RECOMMENDATIONS_URL = "https://api.semanticscholar.org/recommendations/v1/papers"
USER_AGENT = "QNWIS-SemanticScholarClient/1.0"


class ResponseList(list):
    """List subclass that carries API request metadata."""

    def __init__(self, items: Iterable[dict[str, Any]], metadata: dict[str, Any]) -> None:
        super().__init__(items)
        self.metadata = metadata


_LAST_REQUEST_METADATA: dict[str, Any] = {}


def get_last_request_metadata() -> dict[str, Any]:
    """Return metadata describing the most recent Semantic Scholar calls."""

    return _LAST_REQUEST_METADATA


def _get_api_key() -> str:
    """Get Semantic Scholar API key from environment.

    Returns:
        API key string

    Raises:
        RuntimeError: If SEMANTIC_SCHOLAR_API_KEY is not set
    """
    key = os.getenv("SEMANTIC_SCHOLAR_API_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "SEMANTIC_SCHOLAR_API_KEY environment variable not set. "
            "Obtain a key from https://www.semanticscholar.org/product/api"
        )
    return key


def _client(timeout: float = DEFAULT_TIMEOUT) -> httpx.Client:
    """Create HTTP client with standard configuration.

    Args:
        timeout: Request timeout in seconds

    Returns:
        Configured httpx.Client
    """
    return httpx.Client(
        timeout=timeout,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        },
    )


def search_papers(
    query: str,
    fields: str = "title,year,abstract,citationCount,authors,url,paperId",
    year_filter: str | None = None,
    limit: int = 10,
) -> ResponseList:
    """Search for papers using Semantic Scholar API.

    Args:
        query: Search query string
        fields: Comma-separated fields to return
        year_filter: Year range filter (e.g., "2020-" for 2020 onwards)
        limit: Maximum number of results

    Returns:
        ResponseList containing paper dictionaries with metadata attached.

    Raises:
        ValueError: If input parameters are invalid.
        RuntimeError: If API key not configured
        httpx.HTTPStatusError: If API request fails
    """
    if not query or not query.strip():
        raise ValueError("query must be a non-empty string")
    if not fields or not fields.strip():
        raise ValueError("fields must be a non-empty string")
    if limit <= 0:
        raise ValueError("limit must be a positive integer")

    api_key = _get_api_key()

    params: dict[str, Any] = {
        "query": query.strip(),
        "fields": fields.strip(),
        "limit": limit,
    }

    if year_filter:
        params["year"] = year_filter.strip()

    with _client() as client:
        response, metadata = send_with_retry(
            client,
            "GET",
            f"{BASE_URL}/paper/search",
            params=params,
            headers={"x-api-key": api_key},
        )
        data = response.json()
        result_metadata: dict[str, Any] = {
            "endpoint": "paper/search",
            "rate_limited": metadata.rate_limited,
            "retries": metadata.retries,
            "query": params["query"],
        }
        if metadata.rate_limited:
            result_metadata["warning"] = "Semantic Scholar API returned HTTP 429."
        _LAST_REQUEST_METADATA["search_papers"] = result_metadata
        return ResponseList(data.get("data", []), result_metadata)


def get_paper_recommendations(
    positive_paper_ids: list[str],
    limit: int = 10,
    fields: str = "title,year,citationCount,authors,url,paperId",
) -> ResponseList:
    """Get paper recommendations based on seed papers.

    Args:
        positive_paper_ids: List of paper IDs to base recommendations on
        limit: Number of recommendations to return
        fields: Comma-separated fields to return

    Returns:
        ResponseList containing recommended paper dictionaries.

    Raises:
        ValueError: If input parameters are invalid.
        RuntimeError: If API key not configured
        httpx.HTTPStatusError: If API request fails
    """
    if not positive_paper_ids:
        raise ValueError("positive_paper_ids must contain at least one paper id")
    if any(not paper_id or not paper_id.strip() for paper_id in positive_paper_ids):
        raise ValueError("positive_paper_ids cannot contain empty values")
    if limit <= 0:
        raise ValueError("limit must be a positive integer")
    if not fields or not fields.strip():
        raise ValueError("fields must be a non-empty string")

    api_key = _get_api_key()

    params = {"fields": fields.strip(), "limit": limit}
    payload = {"positivePaperIds": [pid.strip() for pid in positive_paper_ids]}

    with _client() as client:
        response, metadata = send_with_retry(
            client,
            "POST",
            RECOMMENDATIONS_URL,
            params=params,
            json=payload,
            headers={"x-api-key": api_key},
        )
        result = response.json()
        result_metadata: dict[str, Any] = {
            "endpoint": "recommendations",
            "rate_limited": metadata.rate_limited,
            "retries": metadata.retries,
            "seed_count": len(payload["positivePaperIds"]),
        }
        if metadata.rate_limited:
            result_metadata["warning"] = "Semantic Scholar API returned HTTP 429."
        _LAST_REQUEST_METADATA["recommendations"] = result_metadata
        return ResponseList(result.get("recommendedPapers", []), result_metadata)


def get_paper_by_id(
    paper_id: str,
    fields: str = "title,year,abstract,citationCount,authors,url",
) -> dict[str, Any] | None:
    """Get a specific paper by its Semantic Scholar ID.

    Args:
        paper_id: Semantic Scholar paper ID
        fields: Comma-separated fields to return

    Returns:
        Paper dictionary enriched with metadata or None if not found

    Raises:
        ValueError: If input parameters are invalid.
        RuntimeError: If API key not configured
        httpx.HTTPStatusError: If API request fails
    """
    if not paper_id or not paper_id.strip():
        raise ValueError("paper_id must be a non-empty string")
    if not fields or not fields.strip():
        raise ValueError("fields must be a non-empty string")

    api_key = _get_api_key()
    normalized_id = paper_id.strip()
    params = {"fields": fields.strip()}

    with _client() as client:
        response, metadata = send_with_retry(
            client,
            "GET",
            f"{BASE_URL}/paper/{normalized_id}",
            params=params,
            headers={"x-api-key": api_key},
            expected_statuses={404},
        )
        if response.status_code == 404:
            not_found_metadata: dict[str, Any] = {
                "endpoint": "paper/detail",
                "status": 404,
                "rate_limited": metadata.rate_limited,
                "retries": metadata.retries,
                "paper_id": normalized_id,
            }
            _LAST_REQUEST_METADATA["paper_by_id"] = not_found_metadata
            return None

        data = response.json()
        result_metadata: dict[str, Any] = {
            "endpoint": "paper/detail",
            "rate_limited": metadata.rate_limited,
            "retries": metadata.retries,
            "paper_id": normalized_id,
        }
        if metadata.rate_limited:
            result_metadata["warning"] = "Semantic Scholar API returned HTTP 429."
        data["_metadata"] = result_metadata
        _LAST_REQUEST_METADATA["paper_by_id"] = result_metadata
        return data


def main() -> None:
    """Test Semantic Scholar API functionality."""
    print("=" * 70)
    print("SEMANTIC SCHOLAR API TEST - QNWIS")
    print("=" * 70)
    print("Testing API with environment-based authentication")
    print("=" * 70)

    try:
        # Test 1: Qatar labor market research
        print("\n" + "=" * 70)
        print("TEST 1: Qatar Labor Market Research")
        print("=" * 70)
        papers_labor = search_papers(
            query='"qatar labor" OR "qatar employment"',
            year_filter="2020-",
            limit=5,
        )
        print(f"✅ Found {len(papers_labor)} labor market papers")
        for i, paper in enumerate(papers_labor[:3], 1):
            print(f"  {i}. {paper.get('title', 'N/A')} ({paper.get('year', 'N/A')})")

        time.sleep(1.5)  # Rate limit: 1 request/second

        # Test 2: Get recommendations if we have seed papers
        if papers_labor and len(papers_labor) >= 2:
            print("\n" + "=" * 70)
            print("TEST 2: Paper Recommendations")
            print("=" * 70)
            seed_ids = [p["paperId"] for p in papers_labor[:2] if "paperId" in p]
            if seed_ids:
                recommendations = get_paper_recommendations(seed_ids, limit=5)
                print(f"✅ Got {len(recommendations)} recommendations")
                for i, paper in enumerate(recommendations[:3], 1):
                    print(f"  {i}. {paper.get('title', 'N/A')}")

    except RuntimeError as e:
        print(f"\n❌ Configuration Error: {e}")
        print("Please set SEMANTIC_SCHOLAR_API_KEY in your environment")
        return
    except Exception as e:
        print(f"\n❌ API Error: {e}")
        return

    print("\n" + "=" * 70)
    print("✅ SEMANTIC SCHOLAR API TEST COMPLETE")
    print("=" * 70)
    print("API client working correctly with environment-based authentication")
    print("Ready for use in QNWIS deterministic data layer")


if __name__ == "__main__":
    main()
