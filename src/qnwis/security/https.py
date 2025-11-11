"""Strict transport security middleware enforcing HTTPS-only traffic."""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response
from starlette.types import ASGIApp

from .security_settings import get_security_settings


class StrictTransportMiddleware(BaseHTTPMiddleware):
    """Reject inbound HTTP when HTTPS is required."""

    def __init__(self, app: ASGIApp):
        """
        Initialize middleware.

        Args:
            app: Wrapped ASGI application
        """
        super().__init__(app)
        self.cfg = get_security_settings()
        self._localhosts = {host.lower() for host in self.cfg.https_localhost_allowlist}

    async def dispatch(self, request: Request, call_next):
        """
        Enforce HTTPS by rejecting plain HTTP except on localhost hosts.

        Args:
            request: Incoming request
            call_next: Next middleware callable

        Returns:
            Response or 400 response if HTTPS is required
        """
        if not self.cfg.require_https:
            return await call_next(request)

        forwarded_proto = request.headers.get("x-forwarded-proto", "")
        if forwarded_proto:
            forwarded_proto = forwarded_proto.split(",")[0].strip()
        scheme = (forwarded_proto or request.url.scheme or "http").lower()
        host = (request.headers.get("host") or request.url.hostname or "").split(":")[0].lower()

        if scheme != "https" and host not in self._localhosts:
            return PlainTextResponse("HTTPS required", status_code=400)

        response: Response = await call_next(request)
        return response
