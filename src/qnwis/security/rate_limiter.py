"""Rate limiting with Redis backend and in-memory fallback."""

from __future__ import annotations

import threading
import time
from typing import Tuple

from fastapi import HTTPException, Request

from .security_settings import get_security_settings

try:
    import redis  # type: ignore
except ImportError:
    redis = None  # optional


class _InMemoryStore:
    """In-memory rate limit store for development/testing."""

    def __init__(self):
        """Initialize in-memory store."""
        self._lock = threading.Lock()
        self._buckets = {}  # key -> (count, reset_ts)

    def incr(self, key: str, window: int) -> Tuple[int, int]:
        """
        Increment counter for key.

        Args:
            key: Rate limit key
            window: Time window in seconds

        Returns:
            Tuple of (count, ttl)
        """
        now = int(time.time())
        with self._lock:
            count, reset = self._buckets.get(key, (0, now + window))
            if now >= reset:
                count, reset = 0, now + window
            count += 1
            self._buckets[key] = (count, reset)
            return count, max(0, reset - now)


class _RedisStore:
    """Redis-backed rate limit store for production."""

    def __init__(self, url: str):
        """
        Initialize Redis store.

        Args:
            url: Redis connection URL
        """
        self._r = redis.Redis.from_url(url, decode_responses=True)

    def incr(self, key: str, window: int) -> Tuple[int, int]:
        """
        Increment counter for key.

        Args:
            key: Rate limit key
            window: Time window in seconds

        Returns:
            Tuple of (count, ttl)
        """
        p = self._r.pipeline()
        p.incr(key, 1)
        p.expire(key, window, nx=True)
        count, _ = p.execute()
        ttl = self._r.ttl(key)
        return int(count), max(0, ttl)


class RateLimiter:
    """Rate limiter with sliding window algorithm."""

    def __init__(self):
        """Initialize rate limiter with configured backend."""
        cfg = get_security_settings()
        self.window = cfg.rate_limit_window_sec
        self.max_req = cfg.rate_limit_max_requests
        if cfg.redis_url and redis is not None:
            self.store = _RedisStore(cfg.redis_url)
        else:
            self.store = _InMemoryStore()

    def check(self, key: str) -> Tuple[bool, int, int]:
        """
        Check if request is within rate limit.

        Args:
            key: Rate limit key (typically client IP + path)

        Returns:
            Tuple of (allowed, count, ttl)
        """
        count, ttl = self.store.incr(key, self.window)
        return (count <= self.max_req, count, ttl)


limiter = RateLimiter()


async def rate_limit(request: Request):
    """
    FastAPI dependency for rate limiting.

    Args:
        request: Incoming request

    Raises:
        HTTPException: 429 if rate limit exceeded
    """
    # Determine client ID (behind proxy use X-Forwarded-For if present)
    fwd = request.headers.get("X-Forwarded-For")
    client = (
        (fwd.split(",")[0].strip() if fwd else request.client.host)
        if request.client
        else "unknown"
    )
    ok, count, ttl = limiter.check(f"rl:{client}:{request.url.path}")
    limit = get_security_settings().rate_limit_max_requests
    remaining = max(0, limit - count)
    reset_epoch = str(int(time.time()) + ttl)
    request.state.rate_limit_headers = {
        "X-RateLimit-Limit": str(limit),
        "X-RateLimit-Remaining": str(remaining),
        "X-RateLimit-Reset": reset_epoch,
        "Retry-After": str(ttl if remaining == 0 else 0),
    }
    if not ok:
        raise HTTPException(status_code=429, detail="Too Many Requests")
