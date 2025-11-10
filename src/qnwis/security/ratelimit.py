"""Deterministic token-bucket rate limiter with Redis or in-memory backends."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from ..utils.clock import Clock
from .auth import Principal

try:  # pragma: no cover - optional dependency
    import redis  # type: ignore
except Exception:  # pragma: no cover
    redis = None

logger = logging.getLogger(__name__)
PREFIX = "qnwis:ratelimit"


@dataclass
class RateLimitResult:
    """Result metadata returned after checking limits."""

    allowed: bool
    remaining: int
    reset_after: float
    reason: str | None = None
    daily_remaining: int | None = None


@dataclass
class TokenBucket:
    """Simple token bucket for in-memory fallback."""

    capacity: float
    refill_rate: float
    tokens: float
    updated_at: float

    def consume(self, cost: float, now: float) -> tuple[bool, float]:
        elapsed = max(0.0, now - self.updated_at)
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.updated_at = now
        if self.tokens >= cost:
            self.tokens -= cost
            return True, self.capacity - self.tokens
        return False, self.capacity - self.tokens

    def reset_after(self) -> float:
        if self.tokens >= self.capacity:
            return 0.0
        needed = self.capacity - self.tokens
        return needed / self.refill_rate


def _redis_client(redis_url: str | None) -> Any | None:
    if not redis_url or redis is None:
        return None
    try:  # pragma: no cover - handshake
        client = redis.from_url(redis_url, decode_responses=True, socket_connect_timeout=1)
        client.ping()
        return client
    except Exception as exc:  # pragma: no cover
        logger.warning("Redis rate-limiter backend unavailable: %s", exc)
        return None


class RateLimiter:
    """Hybrid rate limiter combining Redis (if available) and in-memory fallback."""

    def __init__(
        self,
        *,
        rps: int | None = None,
        burst: int | None = None,
        daily: int | None = None,
        redis_url: str | None = None,
        clock: Clock | None = None,
    ) -> None:
        self.rps = rps or int(os.getenv("QNWIS_RATE_LIMIT_RPS", "5"))
        self.burst = burst or self.rps * 3
        self.daily = daily or int(os.getenv("QNWIS_RATE_LIMIT_DAILY", "1000"))
        self._clock = clock or Clock()
        self._redis = _redis_client(redis_url or os.getenv("QNWIS_REDIS_URL"))
        self._buckets: dict[str, TokenBucket] = {}
        self._daily_counts: dict[str, tuple[int, int]] = {}

    def consume(self, principal: Principal, cost: int = 1) -> RateLimitResult:
        """Consume tokens for principal, returning rate-limit metadata."""
        if self._redis:
            return self._consume_redis(principal, cost)
        return self._consume_memory(principal, cost)

    # -------------------------------
    # Redis backend (fixed windows)
    # -------------------------------
    def _consume_redis(self, principal: Principal, cost: int) -> RateLimitResult:
        assert self._redis  # for mypy
        now = int(self._clock.time())
        second_window = f"{PREFIX}:rps:{principal.ratelimit_id}:{now}"
        second_count = self._redis.incrby(second_window, cost)  # type: ignore[attr-defined]
        self._redis.expire(second_window, 1)

        if second_count > self.burst:
            return RateLimitResult(
                allowed=False,
                remaining=max(0, self.burst - (second_count - cost)),
                reset_after=1.0,
                reason="rps_limit_exceeded",
                daily_remaining=None,
            )

        day = datetime.now(UTC).strftime("%Y%m%d")
        daily_key = f"{PREFIX}:daily:{principal.ratelimit_id}:{day}"
        daily_count = self._redis.incrby(daily_key, cost)  # type: ignore[attr-defined]
        self._redis.expire(daily_key, 86400)

        if daily_count > self.daily:
            return RateLimitResult(
                allowed=False,
                remaining=0,
                reset_after=86400.0,
                reason="daily_limit_exceeded",
                daily_remaining=0,
            )

        remaining = max(0, self.burst - second_count)
        return RateLimitResult(
            allowed=True,
            remaining=remaining,
            reset_after=1.0,
            reason=None,
            daily_remaining=max(0, self.daily - daily_count),
        )

    # -------------------------------
    # In-memory fallback
    # -------------------------------
    def _bucket(self, principal: Principal) -> TokenBucket:
        bucket = self._buckets.get(principal.ratelimit_id)
        if not bucket:
            bucket = TokenBucket(
                capacity=float(self.burst),
                refill_rate=float(self.rps),
                tokens=float(self.burst),
                updated_at=self._clock.time(),
            )
            self._buckets[principal.ratelimit_id] = bucket
        return bucket

    def _consume_memory(self, principal: Principal, cost: int) -> RateLimitResult:
        now = self._clock.time()
        bucket = self._bucket(principal)
        allowed, _ = bucket.consume(cost, now)
        if not allowed:
            return RateLimitResult(
                allowed=False,
                remaining=int(bucket.tokens),
                reset_after=bucket.reset_after(),
                reason="rps_limit_exceeded",
                daily_remaining=self._daily_remaining(principal, cost, increment=False),
            )

        daily_remaining = self._daily_remaining(principal, cost, increment=True)
        if daily_remaining is not None and daily_remaining < 0:
            return RateLimitResult(
                allowed=False,
                remaining=int(bucket.tokens),
                reset_after=self._seconds_until_midnight(),
                reason="daily_limit_exceeded",
                daily_remaining=0,
            )

        return RateLimitResult(
            allowed=True,
            remaining=int(bucket.tokens),
            reset_after=bucket.reset_after(),
            reason=None,
            daily_remaining=daily_remaining,
        )

    def _seconds_until_midnight(self) -> float:
        now = datetime.now(UTC)
        tomorrow = datetime(now.year, now.month, now.day, tzinfo=UTC) + timedelta(days=1)  # type: ignore[name-defined]
        return (tomorrow - now).total_seconds()

    def _daily_remaining(self, principal: Principal, cost: int, increment: bool) -> int:
        today = int(self._clock.time() // 86400)
        count, stored_day = self._daily_counts.get(principal.ratelimit_id, (0, today))
        if stored_day != today:
            count = 0
        if increment:
            count += cost
        self._daily_counts[principal.ratelimit_id] = (count, today)
        return self.daily - count


def create_rate_limiter() -> RateLimiter:
    """Factory used by FastAPI app startup."""
    return RateLimiter()


__all__ = ["RateLimitResult", "RateLimiter", "create_rate_limiter"]
