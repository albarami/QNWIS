"""Cache backend implementations for deterministic query results."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass


@dataclass
class CacheEntry:
    """Cache entry with optional expiration."""

    value: str
    expires_at: float | None  # epoch seconds


class CacheBackend:
    """Abstract cache backend interface."""

    def get(self, key: str) -> str | None:
        """Retrieve cached value by key."""
        raise NotImplementedError

    def set(self, key: str, value: str, ttl_s: int | None = None) -> None:
        """Store value with optional TTL in seconds."""
        raise NotImplementedError

    def delete(self, key: str) -> None:
        """Remove cached value by key."""
        raise NotImplementedError


class MemoryCacheBackend(CacheBackend):
    """In-memory cache backend with TTL support."""

    def __init__(self) -> None:
        """Initialize empty in-memory store."""
        self._store: dict[str, CacheEntry] = {}

    def get(self, key: str) -> str | None:
        """Retrieve value, checking expiration."""
        entry = self._store.get(key)
        if not entry:
            return None
        if entry.expires_at and time.time() > entry.expires_at:
            del self._store[key]
            return None
        return entry.value

    def set(self, key: str, value: str, ttl_s: int | None = None) -> None:
        """Store value with optional TTL."""
        exp = (time.time() + ttl_s) if ttl_s and ttl_s > 0 else None
        self._store[key] = CacheEntry(value=value, expires_at=exp)

    def delete(self, key: str) -> None:
        """Remove entry from store."""
        self._store.pop(key, None)


class RedisCacheBackend(CacheBackend):
    """Redis cache backend for distributed caching."""

    def __init__(self, host: str, port: int) -> None:
        """Initialize Redis client connection."""
        from redis import Redis

        self._r = Redis(host=host, port=port, decode_responses=True)

    def get(self, key: str) -> str | None:
        """Retrieve value from Redis."""
        return self._r.get(key)

    def set(self, key: str, value: str, ttl_s: int | None = None) -> None:
        """Store value in Redis with optional TTL."""
        if ttl_s and ttl_s > 0:
            self._r.setex(key, ttl_s, value)
        else:
            self._r.set(key, value)

    def delete(self, key: str) -> None:
        """Remove key from Redis."""
        self._r.delete(key)


def get_cache_backend() -> CacheBackend:
    """Factory using env: QNWIS_CACHE_BACKEND=redis|memory (default memory)."""
    mode = os.getenv("QNWIS_CACHE_BACKEND", "memory").lower()
    if mode == "redis":
        host = os.getenv("REDIS_HOST", "localhost")
        port = int(os.getenv("REDIS_PORT", "6379"))
        return RedisCacheBackend(host, port)
    return MemoryCacheBackend()
