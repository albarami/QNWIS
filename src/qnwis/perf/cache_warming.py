"""
Cache warming utilities for deterministic queries.

Allows the API layer to pre-populate cache entries for the most frequent
queries during startup so the first user does not pay the full cost.
"""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, wait
from typing import Callable, Iterable

from qnwis.agents.base import DataClient

logger = logging.getLogger(__name__)


def warm_queries(
    factory: Callable[[], DataClient],
    query_ids: Iterable[str],
    *,
    max_workers: int = 4,
) -> None:
    """
    Warm cache entries for the supplied query identifiers.

    Args:
        factory: Callable returning a DataClient instance
        query_ids: Iterable of query identifiers to pre-load
        max_workers: Maximum number of worker threads for warming
    """
    start = time.perf_counter()
    ids = [qid for qid in set(query_ids) if qid]
    if not ids:
        logger.info("No cache warming targets configured.")
        return

    logger.info("Warming %d deterministic queries", len(ids))

    def _run(query_id: str) -> None:
        client = factory()
        try:
            client.run(query_id)
        except Exception as exc:  # pragma: no cover - best-effort
            logger.warning("Cache warm failed for %s: %s", query_id, exc)

    if max_workers <= 1 or len(ids) == 1:
        client = factory()
        for query_id in ids:
            try:
                client.run(query_id)
            except Exception as exc:  # pragma: no cover - best-effort
                logger.warning("Cache warm failed for %s: %s", query_id, exc)
    else:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(_run, query_id) for query_id in ids]
            wait(futures)

    elapsed_ms = (time.perf_counter() - start) * 1000
    logger.info("Cache warming completed in %.0fms", elapsed_ms)


__all__ = ["warm_queries"]
