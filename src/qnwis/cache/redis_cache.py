"""
Redis-backed deterministic cache for QueryResult objects.

Provides simple JSON serialization with ISO date handling for
deterministic, reproducible caching of query results.
"""

from __future__ import annotations

import json
import os
from datetime import date, datetime
from typing import Any, Dict, Optional

import redis

from ..data.deterministic.models import QueryResult


def _json_default(value: Any) -> str:
    """Serialize datetime/date values as ISO strings."""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


class DeterministicRedisCache:
    """
    Minimal JSON cache for QueryResult. Values stored as JSON with ISO dates.

    All cached values are QueryResult aggregates - never raw rows with PII.
    Cache keys are deterministic hashes of (operation, query_id, params).
    """

    def __init__(
        self, url: Optional[str] = None, namespace: str = "qnwis"
    ) -> None:
        """
        Initialize Redis cache connection.

        Args:
            url: Redis connection URL (defaults to QNWIS_REDIS_URL env var)
            namespace: Key namespace prefix for multi-tenant isolation
        """
        self.r = redis.from_url(  # type: ignore[no-untyped-call]
            url or os.getenv("QNWIS_REDIS_URL", "redis://localhost:6379/0")
        )
        self.ns = namespace

    def _ns(self, key: str) -> str:
        """Add namespace prefix to key."""
        return f"{self.ns}:{key}"

    def get(self, key: str) -> Optional[QueryResult]:
        """
        Retrieve QueryResult from cache.

        Args:
            key: Cache key (without namespace prefix)

        Returns:
            QueryResult if found, None otherwise
        """
        raw = self.r.get(self._ns(key))
        if not raw:
            return None
        payload = json.loads(raw if isinstance(raw, str) else raw.decode("utf-8"))
        try:
            return QueryResult.model_validate(payload)
        except AttributeError:
            return QueryResult(**payload)

    def set(self, key: str, qr: QueryResult, ttl: int) -> None:
        """
        Store QueryResult in cache with TTL.

        Args:
            key: Cache key (without namespace prefix)
            qr: QueryResult to cache
            ttl: Time-to-live in seconds
        """
        payload = (
            qr.model_dump(mode="json") if hasattr(qr, "model_dump") else qr.__dict__
        )
        self.r.set(
            self._ns(key),
            json.dumps(payload, separators=(",", ":"), default=_json_default),
            ex=ttl,
        )

    def delete_prefix(self, prefix: str) -> int:
        """
        Delete all keys matching a prefix.

        Args:
            prefix: Key prefix to match (without namespace)

        Returns:
            Number of keys deleted
        """
        pattern = self._ns(prefix) + "*"
        keys = list(self.r.scan_iter(pattern))
        if not keys:
            return 0
        return int(self.r.delete(*keys))

    def info(self) -> Dict[str, Any]:
        """
        Get Redis server info.

        Returns:
            Redis INFO command output as dictionary
        """
        return self.r.info()  # type: ignore[no-any-return]
