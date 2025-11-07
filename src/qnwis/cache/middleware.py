"""
Read-through cache middleware for DataClient.

Wraps DataClient methods with transparent caching - cache hits return
immediately, cache misses populate the cache after fetching.
"""

from __future__ import annotations

import logging
from functools import wraps
from typing import Any

from ..data.deterministic.models import QueryResult
from ..data.deterministic.registry import REGISTRY_VERSION
from .keys import make_cache_key
from .redis_cache import DeterministicRedisCache

# Allowlist of methods eligible for caching
# Only explicit read operations with deterministic outputs
ALLOWLIST = {
    "get_retention_by_company",
    "get_salary_statistics",
    "get_employee_transitions",
    "get_qatarization_rates",
    "get_gcc_indicator",
    "get_world_bank_indicator",
}

NEGATIVE_CACHE_TTL_DEFAULT = 5 * 60  # 5 minutes

logger = logging.getLogger(__name__)


class CachedDataClient:
    """
    Read-through cache wrapper around an existing DataClient.

    Only allows explicit allowlisted read methods and returns QueryResult.
    Transparent to callers - same interface as unwrapped DataClient.
    """

    def __init__(
        self,
        delegate: Any,
        cache: DeterministicRedisCache,
        version: str | None = None,
        negative_ttl: int | None = NEGATIVE_CACHE_TTL_DEFAULT,
    ) -> None:
        """
        Initialize cached data client wrapper.

        Args:
            delegate: Underlying DataClient to wrap
            cache: Redis cache instance
            version: Cache version for schema evolution (defaults to registry checksum)
            negative_ttl: Optional TTL (seconds) for empty QueryResult caching; set to
                ``None`` to disable negative caching.
        """
        if negative_ttl is not None and negative_ttl < 0:
            raise ValueError("negative_ttl must be >= 0 or None.")
        self._d = delegate
        self._cache = cache
        self._version = version or REGISTRY_VERSION
        self._negative_ttl = negative_ttl

    def __getattr__(self, name: str) -> Any:
        """
        Proxy attribute access with caching for allowlisted methods.

        Non-allowlisted attributes pass through unchanged.
        Allowlisted methods get wrapped with cache logic.

        Args:
            name: Attribute name

        Returns:
            Cached wrapper for allowlisted methods, raw attribute otherwise
        """
        target = getattr(self._d, name)
        if not callable(target):
            return target

        if name not in ALLOWLIST:
            logger.info("Bypassing cache for non-allowlisted method '%s'", name)
            return target

        @wraps(target)
        def _wrapped(*args: Any, **kwargs: Any) -> QueryResult:
            # Build a deterministic cache key using delegate's derived query_id
            # We attempt to probe a 'peek_query_id' helper if present
            peek_qid = getattr(self._d, "peek_query_id", None)
            query_id = None
            if callable(peek_qid):
                try:
                    query_id = peek_qid(name, kwargs)
                except Exception:
                    query_id = None
                else:
                    if not isinstance(query_id, str) or not query_id.strip():
                        query_id = None

            # If we can peek, try cache first
            if isinstance(query_id, str) and query_id:
                key, ttl = make_cache_key(name, query_id, kwargs, self._version)
                hit = self._cache.get(key)
                if hit:
                    return hit

            # Cache miss: call underlying delegate
            qr: QueryResult = target(*args, **kwargs)

            # Compute key (with real qr.query_id if peek failed)
            qid_attr = getattr(qr, "query_id", None)
            if not isinstance(qid_attr, str) or not qid_attr:
                raise ValueError(
                    f"QueryResult returned from '{name}' is missing a valid query_id."
                )

            qid = query_id if isinstance(query_id, str) and query_id else qid_attr
            key, ttl = make_cache_key(name, qid, kwargs, self._version)
            ttl_to_use = ttl
            if self._negative_ttl is not None and not qr.rows:
                ttl_to_use = min(ttl, self._negative_ttl)
                logger.debug(
                    "Applying negative cache TTL=%s for empty QueryResult (key=%s)",
                    ttl_to_use,
                    key,
                )

            try:
                self._cache.set(key, qr, ttl_to_use)
            except Exception as exc:
                logger.warning(
                    "Failed to persist cache key '%s' (ttl=%s): %s", key, ttl_to_use, exc
                )
            return qr

        return _wrapped
