"""
Data Extraction Node.

Uses the existing prefetch layer to load facts from the PostgreSQL cache
and fallback APIs with a cache-first strategy.
"""

from __future__ import annotations

from typing import List

from ..state import IntelligenceState
from ..prefetch_apis import get_complete_prefetch


async def data_extraction_node(state: IntelligenceState) -> IntelligenceState:
    """
    Node 2: Extract data from PostgreSQL cache + external APIs.

    Uses cache-first strategy:
    - World Bank / ILO cached results (<100 ms)
    - Falls back to live APIs only when cache misses occur
    """

    query = state["query"]
    reasoning_chain = state.setdefault("reasoning_chain", [])
    nodes_executed = state.setdefault("nodes_executed", [])
    warnings = state.setdefault("warnings", [])
    errors = state.setdefault("errors", [])

    reasoning_chain.append("Extracting data from cache and authoritative APIs...")

    prefetch = get_complete_prefetch()

    try:
        facts = await prefetch.fetch_all_sources(query)
    except Exception as exc:  # pragma: no cover - defensive logging
        errors.append(f"Data extraction failed: {exc}")
        state["extracted_facts"] = []
        state["data_sources"] = []
        state["data_quality_score"] = 0.0
    else:
        state["extracted_facts"] = facts
        data_sources = sorted({fact.get("source", "unknown") for fact in facts})
        state["data_sources"] = data_sources

        total_count = len(facts)
        cached_count = sum(1 for fact in facts if fact.get("cached", False))

        if total_count == 0:
            state["data_quality_score"] = 0.0
            warnings.append("No data extracted from cache or APIs.")
        else:
            cache_ratio = cached_count / total_count
            state["data_quality_score"] = 0.7 + (cache_ratio * 0.3)
            reasoning_chain.append(
                f"Extracted {total_count} facts from {len(data_sources)} sources "
                f"({cached_count} cached, {total_count - cached_count} live API)."
            )

    nodes_executed.append("extraction")
    return state

