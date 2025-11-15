"""CSRF protection middleware using double-submit cookie pattern."""

from __future__ import annotations

import secrets
from datetime import timedelta

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import PlainTextResponse

from .security_settings import get_security_settings

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
CSRF_EXEMPT_PATHS = {"/api/v1/council/stream"}  # SSE streaming endpoint


class CSRFMiddleware(BaseHTTPMiddleware):
    """CSRF protection using double-submit cookie pattern."""

    def __init__(self, app):
        """
        Initialize CSRF middleware.

        Args:
            app: ASGI application
        """
        super().__init__(app)
        self.cfg = get_security_settings()

    async def dispatch(self, request: Request, call_next):
        """
        Process request and enforce CSRF protection.

        Args:
            request: Incoming request
            call_next: Next middleware in chain

        Returns:
            Response with CSRF cookie or 403 if validation fails
        """
        # Skip CSRF for auth bypass or exempt paths
        if getattr(request.app.state, "auth_bypass", False):
            return await call_next(request)
        
        if request.url.path in CSRF_EXEMPT_PATHS:
            return await call_next(request)

        # Ensure token cookie exists on all safe requests
        token = request.cookies.get(self.cfg.csrf_cookie_name)
        if request.method in SAFE_METHODS:
            if not token:
                token = secrets.token_urlsafe(32)
            resp = await call_next(request)
            resp.set_cookie(
                self.cfg.csrf_cookie_name,
                token,
                secure=self.cfg.csrf_secure,
                httponly=False,  # must be JS-readable for double submit
                samesite=self.cfg.csrf_samesite.capitalize(),
                max_age=int(timedelta(days=7).total_seconds()),
            )
            return resp

        # For state-changing requests: header must match cookie
        header_val = request.headers.get(self.cfg.csrf_header_name)
        if not token or not header_val or header_val != token:
            return PlainTextResponse("CSRF validation failed", status_code=403)

        return await call_next(request)
