"""Brave Search integration for real-time economic news."""
import logging
from datetime import datetime
from typing import Any, Dict, List

import aiohttp

logger = logging.getLogger(__name__)


async def fetch_brave_economic(brave_api_key: str, query: str) -> List[Dict[str, Any]]:
    """Fetch real-time economic news from Brave Search."""
    if not brave_api_key:
        return []
    try:
        logger.info("Brave: Searching recent economic news...")
        url = "https://api.search.brave.com/res/v1/web/search"
        headers = {"Accept": "application/json", "X-Subscription-Token": brave_api_key}
        params = {
            "q": f"Qatar economic growth OR tech sector {query[:50]}",
            "count": 5,
            "freshness": "pd",
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    facts: List[Dict[str, Any]] = []
                    for result in data.get("web", {}).get("results", [])[:3]:
                        facts.append({
                            "metric": "news_finding",
                            "value": result.get("title"),
                            "source": "Brave Search (real-time)",
                            "source_priority": 65,
                            "confidence": 0.60,
                            "raw_text": f"Recent: {result.get('description', '')}",
                            "timestamp": datetime.now().isoformat(),
                            "url": result.get("url"),
                        })
                    logger.info("Found %d recent articles", len(facts))
                    return facts
        return []
    except Exception as e:
        logger.warning("Brave error: %s", e)
        return []
