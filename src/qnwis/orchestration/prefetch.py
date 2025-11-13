"""
Declarative data prefetcher using DataClient.

Executes prefetch specifications and builds a cache of QueryResult objects
for agent use. Enforces deterministic access via DataClient only.

Enhanced with intelligent classification-based prefetching for H1:
- PrefetchStrategy: Maps question intents to relevant queries
- async prefetch_queries: Concurrent query execution with semaphore
- Backward compatible with existing PrefetchSpec system
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List

from ..agents.base import DataClient
from ..data.deterministic.models import QueryResult
from ..data.deterministic.registry import REGISTRY_VERSION
from .types import PrefetchSpec

logger = logging.getLogger(__name__)


class PrefetchError(Exception):
    """Raised when prefetch execution fails."""


class Prefetcher:
    """
    Executes declarative prefetch specs via DataClient.

    Returns a cache dictionary mapping cache_key to QueryResult.
    No HTTP or SQL access outside DataClient.
    """

    def __init__(
        self,
        client: DataClient,
        timeout_ms: int = 25000,
        cache: Any | None = None,
        cache_version: str | None = None,
    ) -> None:
        """
        Initialize the prefetcher.

        Args:
            client: DataClient instance for deterministic queries
            timeout_ms: Timeout for entire prefetch operation in milliseconds
            cache: Optional DeterministicRedisCache for write-through caching
            cache_version: Override cache version string (defaults to registry checksum)
        """
        self.client = client
        self.timeout_ms = timeout_ms
        self.cache = cache
        self.cache_version = cache_version or REGISTRY_VERSION

    def run(self, specs: list[PrefetchSpec]) -> dict[str, QueryResult]:
        """
        Execute prefetch specifications and return cache.

        Args:
            specs: List of PrefetchSpec declarations

        Returns:
            Dictionary mapping cache_key to QueryResult

        Raises:
            PrefetchError: If prefetch fails or times out
        """
        start_time = time.perf_counter()
        cache: dict[str, QueryResult] = {}
        seen_keys: set[str] = set()

        logger.info("Starting prefetch with %d specs", len(specs))

        for idx, spec in enumerate(specs):
            # Check timeout
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            if elapsed_ms > self.timeout_ms:
                msg = f"Prefetch timeout after {elapsed_ms:.0f}ms (limit: {self.timeout_ms}ms)"
                logger.error(msg)
                raise PrefetchError(msg)

            cache_key = spec["cache_key"]

            # Deduplicate by cache_key
            if cache_key in seen_keys:
                logger.debug("Skipping duplicate cache_key: %s", cache_key)
                continue
            seen_keys.add(cache_key)

            fn_name = spec["fn"]
            params = spec["params"]

            logger.debug(
                "Prefetch [%d/%d]: %s with params=%s",
                idx + 1,
                len(specs),
                fn_name,
                self._sanitize_params(params),
            )

            try:
                # Execute via DataClient
                method = getattr(self.client, fn_name, None)
                if method is None:
                    msg = f"DataClient has no method: {fn_name}"
                    logger.error(msg)
                    raise PrefetchError(msg)

                if not callable(method):
                    msg = f"DataClient.{fn_name} is not callable"
                    logger.error(msg)
                    raise PrefetchError(msg)

                # Call the method
                result = method(**params)

                # Validate result type
                if not isinstance(result, QueryResult):
                    msg = (
                        f"DataClient.{fn_name} returned {type(result).__name__}, "
                        "expected QueryResult"
                    )
                    logger.error(msg)
                    raise PrefetchError(msg)

                cache[cache_key] = result
                logger.debug("Cached result for key: %s (rows=%d)", cache_key, len(result.rows))

                # Write to Redis cache if available
                if self.cache:
                    try:
                        from ..cache.keys import make_cache_key

                        qid = getattr(result, "query_id", None)
                        if not isinstance(qid, str) or not qid:
                            raise ValueError(
                                f"Prefetch result from {fn_name} missing query_id."
                            )
                        cache_k, ttl = make_cache_key(
                            fn_name, qid, params, self.cache_version
                        )
                        self.cache.set(cache_k, result, ttl)
                    except Exception as cache_exc:
                        logger.warning(
                            "Failed to write to cache: %s", cache_exc
                        )

            except Exception as exc:
                msg = f"Prefetch failed for {fn_name}({params}): {exc}"
                logger.exception(msg)
                raise PrefetchError(msg) from exc

        total_elapsed_ms = (time.perf_counter() - start_time) * 1000
        logger.info(
            "Prefetch completed: %d results in %.0fms", len(cache), total_elapsed_ms
        )

        return cache

    @staticmethod
    def _sanitize_params(params: dict[str, Any]) -> dict[str, Any]:
        """Sanitize params for logging (remove PII)."""
        safe = {}
        for key, val in params.items():
            if isinstance(val, str) and len(val) > 50:
                safe[key] = f"{val[:50]}..."
            else:
                safe[key] = val
        return safe


def generate_cache_key(fn: str, params: dict[str, Any]) -> str:
    """
    Generate deterministic cache key from function name and parameters.

    Args:
        fn: Function name
        params: Parameters dictionary

    Returns:
        Deterministic cache key string
    """
    # Sort params for determinism
    sorted_params = json.dumps(params, sort_keys=True, default=str)
    combined = f"{fn}:{sorted_params}"
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()[:16]


# ==============================================================================
# H1: INTELLIGENT CLASSIFICATION-BASED PREFETCHING
# ==============================================================================


class PrefetchStrategy:
    """
    Intelligent prefetch strategy based on question classification (H1).
    
    Maps question intents and entities to relevant queries, enabling
    smart pre-loading of likely-needed data before agent execution.
    """

    # Mapping of intents to commonly needed queries
    INTENT_QUERY_MAP: Dict[str, List[str]] = {
        "unemployment": [
            "unemployment_trends_monthly",
            "unemployment_rate_latest",
            "employment_share_by_gender"
        ],
        "gcc_comparison": [
            "gcc_unemployment_comparison",
            "gcc_labour_force_participation"
        ],
        "qatarization": [
            "qatarization_rate_by_sector",
            "vision_2030_targets_tracking"
        ],
        "gender": [
            "employment_share_by_gender",
            "gender_pay_gap_analysis"
        ],
        "skills": [
            "skills_gap_analysis",
            "employment_by_education_level"
        ],
        "retention": [
            "retention_rate_by_sector",
            "attrition_rate_monthly"
        ],
        "salary": [
            "salary_distribution_by_sector",
            "best_paid_occupations"
        ],
        "vision_2030": [
            "vision_2030_targets_tracking",
            "qatarization_rate_by_sector"
        ],
        "trends": [
            "unemployment_trends_monthly",
            "sector_growth_rate"
        ],
        "education": [
            "employment_by_education_level",
            "skills_gap_analysis"
        ],
        "sector_analysis": [
            "sector_growth_rate",
            "sector_competitiveness_scores"
        ]
    }

    # Always prefetch these high-frequency baseline queries
    ALWAYS_PREFETCH: List[str] = [
        "unemployment_rate_latest",
        "employment_share_by_gender"
    ]

    @classmethod
    def get_queries_for_intent(cls, classification: Dict[str, Any]) -> List[str]:
        """
        Determine which queries to prefetch based on question classification.

        Args:
            classification: Question classification result from classifier
                           Expected keys: intent, entities, complexity

        Returns:
            List of query IDs to prefetch (deduplicated)
        """
        queries = set(cls.ALWAYS_PREFETCH)

        # Add intent-specific queries
        intent = classification.get("intent", "").lower()
        if intent in cls.INTENT_QUERY_MAP:
            queries.update(cls.INTENT_QUERY_MAP[intent])
            logger.debug(f"Added queries for intent '{intent}': {cls.INTENT_QUERY_MAP[intent]}")

        # Add queries based on entities
        entities = classification.get("entities", {})
        
        if entities.get("mentions_gcc") or "gcc" in str(classification).lower():
            queries.update(cls.INTENT_QUERY_MAP.get("gcc_comparison", []))
            logger.debug("Added GCC comparison queries")
        
        if entities.get("mentions_gender") or "gender" in str(classification).lower():
            queries.update(cls.INTENT_QUERY_MAP.get("gender", []))
            logger.debug("Added gender-related queries")
        
        if entities.get("mentions_vision_2030") or "vision" in str(classification).lower():
            queries.update(cls.INTENT_QUERY_MAP.get("vision_2030", []))
            logger.debug("Added Vision 2030 queries")
        
        if entities.get("mentions_qatarization") or "qatari" in str(classification).lower():
            queries.update(cls.INTENT_QUERY_MAP.get("qatarization", []))
            logger.debug("Added Qatarization queries")

        # Add queries based on complexity (complex questions need more data)
        complexity = classification.get("complexity", "medium")
        if complexity == "high":
            # For complex questions, add trend and sector analysis
            queries.update(cls.INTENT_QUERY_MAP.get("trends", []))
            queries.update(cls.INTENT_QUERY_MAP.get("sector_analysis", []))
            logger.debug("Added queries for high complexity")

        query_list = list(queries)
        logger.info(f"Selected {len(query_list)} queries for prefetch based on classification")
        return query_list


async def prefetch_queries(
    classification: Dict[str, Any],
    data_client: DataClient,
    max_concurrent: int = 5,
    timeout_seconds: float = 20.0
) -> Dict[str, QueryResult]:
    """
    Intelligent async prefetch of queries based on question classification (H1).

    Executes queries concurrently with semaphore limiting to prevent
    overwhelming the database. Returns successfully fetched results,
    logs failures but continues operation.

    Args:
        classification: Question classification result
        data_client: DataClient for deterministic query execution
        max_concurrent: Maximum concurrent queries (default: 5)
        timeout_seconds: Total timeout for all prefetch operations (default: 20s)

    Returns:
        Dictionary of {query_id: QueryResult} for successfully prefetched queries

    Raises:
        asyncio.TimeoutError: If prefetch exceeds timeout_seconds
    """
    start_time = datetime.now(timezone.utc)

    # Determine which queries to prefetch using intelligent strategy
    query_ids = PrefetchStrategy.get_queries_for_intent(classification)

    if not query_ids:
        logger.info("No queries to prefetch based on classification")
        return {}

    logger.info(f"Prefetching {len(query_ids)} queries: {query_ids}")

    # Semaphore to limit concurrent database connections
    semaphore = asyncio.Semaphore(max_concurrent)

    async def fetch_one(query_id: str) -> tuple[str, QueryResult | None]:
        """Fetch single query with semaphore limiting."""
        async with semaphore:
            try:
                # Run synchronous DataClient in thread pool to avoid blocking event loop
                logger.debug(f"Fetching query: {query_id}")
                result = await asyncio.to_thread(data_client.run, query_id)
                
                # Validate result
                if not isinstance(result, QueryResult):
                    logger.error(f"Query {query_id} returned invalid type: {type(result)}")
                    return query_id, None
                
                logger.debug(f"Prefetched {query_id}: {len(result.rows)} rows")
                return query_id, result
                
            except asyncio.CancelledError:
                logger.warning(f"Prefetch cancelled for {query_id}")
                raise
            except Exception as e:
                logger.warning(f"Failed to prefetch {query_id}: {e}")
                return query_id, None

    try:
        # Fetch all queries concurrently with timeout
        tasks = [fetch_one(qid) for qid in query_ids]
        results = await asyncio.wait_for(
            asyncio.gather(*tasks, return_exceptions=False),
            timeout=timeout_seconds
        )

    except asyncio.TimeoutError:
        logger.error(f"Prefetch timed out after {timeout_seconds}s")
        # Return empty dict on timeout - don't block workflow
        return {}

    # Filter out failures and build result dictionary
    prefetched = {qid: result for qid, result in results if result is not None}

    # Calculate and log performance metrics
    latency_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
    success_rate = (len(prefetched) / len(query_ids) * 100) if query_ids else 0
    
    logger.info(
        f"Prefetch complete: {len(prefetched)}/{len(query_ids)} succeeded "
        f"({success_rate:.1f}%) in {latency_ms:.0f}ms"
    )

    # Log performance warning if slow
    if latency_ms > 5000:  # 5 seconds
        logger.warning(
            f"Prefetch took {latency_ms:.0f}ms - consider optimizing "
            f"query selection or increasing max_concurrent"
        )

    return prefetched
