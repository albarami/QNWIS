"""Middleware to bound Range headers and mitigate quadratic parsing in Starlette."""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response
from starlette.types import ASGIApp


class RangeHeaderGuardMiddleware(BaseHTTPMiddleware):
    """Reject pathological Range headers to mitigate Starlette GHSA-7f5h-v6xp-fcq8."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        max_length: int = 256,
        max_ranges: int = 5,
    ):
        """
        Initialize guard middleware.

        Args:
            app: Wrapped ASGI application
            max_length: Maximum allowed Range header length
            max_ranges: Maximum allowed comma-separated ranges
        """
        super().__init__(app)
        self.max_length = max_length
        self.max_ranges = max_ranges

    async def dispatch(self, request: Request, call_next):
        """
        Reject requests with Range headers that would trigger quadratic parsing.
        """
        header = request.headers.get("range")
        if header:
            if len(header) > self.max_length:
                return PlainTextResponse("Range header too long", status_code=416)
            segments = header.split(",")
            if len(segments) > self.max_ranges:
                return PlainTextResponse("Too many ranges requested", status_code=416)
        response: Response = await call_next(request)
        return response
