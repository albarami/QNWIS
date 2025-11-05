"""
Simple per-process token bucket rate limiting middleware.

Enforces a fixed requests-per-second ceiling using an in-memory token bucket.
"""

from __future__ import annotations

import time

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send


class RateLimitMiddleware:
    """ASGI middleware implementing a naive per-process token bucket."""

    def __init__(self, app: ASGIApp, rate: float) -> None:
        """
        Initialize middleware.

        Args:
            app: ASGI application to wrap
            rate: Allowed requests per second; values <= 0 raise ValueError
        """
        if rate <= 0:
            raise ValueError("Rate must be greater than zero.")
        self.app = app
        self._rate = rate
        self._capacity = max(1.0, rate)
        self._tokens = self._capacity
        self._last_refill = time.perf_counter()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        Apply rate limiting to HTTP requests.

        Non-HTTP scopes are passed through without throttling.
        """
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        now = time.perf_counter()
        elapsed = now - self._last_refill
        self._tokens = min(self._capacity, self._tokens + elapsed * self._rate)
        self._last_refill = now

        if self._tokens >= 1.0:
            self._tokens -= 1.0
            await self.app(scope, receive, send)
            return

        retry_after = max(1, int(1 / self._rate))
        response = JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded"},
            headers={"Retry-After": str(retry_after)},
        )
        await response(scope, receive, send)
