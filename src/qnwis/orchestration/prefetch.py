"""
Declarative data prefetcher using DataClient.

Executes prefetch specifications and builds a cache of QueryResult objects
for agent use. Enforces deterministic access via DataClient only.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import Any, Dict, List, Optional

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
        cache: Optional[Any] = None,
        cache_version: Optional[str] = None,
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

    def run(self, specs: List[PrefetchSpec]) -> Dict[str, QueryResult]:
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
        cache: Dict[str, QueryResult] = {}
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
    def _sanitize_params(params: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize params for logging (remove PII)."""
        safe = {}
        for key, val in params.items():
            if isinstance(val, str) and len(val) > 50:
                safe[key] = f"{val[:50]}..."
            else:
                safe[key] = val
        return safe


def generate_cache_key(fn: str, params: Dict[str, Any]) -> str:
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
