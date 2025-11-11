"""Security headers middleware for QNWIS."""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from .csp import ensure_csp_nonce
from .security_settings import get_security_settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses."""

    def __init__(self, app: ASGIApp):
        """
        Initialize security headers middleware.

        Args:
            app: ASGI application
        """
        super().__init__(app)
        self.cfg = get_security_settings()

    async def dispatch(self, request: Request, call_next):
        """
        Process request and add security headers to response.

        Args:
            request: Incoming request
            call_next: Next middleware in chain

        Returns:
            Response with security headers
        """
        nonce: str | None = None
        if self.cfg.csp_enable_nonce:
            nonce = ensure_csp_nonce(request)

        rsp: Response = await call_next(request)

        # Strict security headers
        if self.cfg.hsts_enabled:
            hsts = f"max-age={self.cfg.hsts_max_age}"
            if self.cfg.hsts_include_subdomains:
                hsts += "; includeSubDomains"
            if self.cfg.hsts_preload:
                hsts += "; preload"
            rsp.headers.setdefault("Strict-Transport-Security", hsts)

        script_src = self.cfg.csp_script_src
        if nonce:
            script_src = f"{script_src} 'nonce-{nonce}'"

        csp = (
            "default-src "
            + self.cfg.csp_default_src
            + "; "
            + "script-src "
            + script_src
            + "; "
            + "style-src "
            + self.cfg.csp_style_src
            + "; "
            + "img-src "
            + self.cfg.csp_img_src
            + "; "
            + "font-src "
            + self.cfg.csp_font_src
            + "; "
            + "connect-src "
            + self.cfg.csp_connect_src
            + "; "
            + "frame-ancestors "
            + self.cfg.csp_frame_ancestors
        )
        rsp.headers.setdefault("Content-Security-Policy", csp)
        rsp.headers.setdefault("X-Content-Type-Options", "nosniff")
        rsp.headers.setdefault("X-Frame-Options", "DENY")
        rsp.headers.setdefault("Referrer-Policy", "no-referrer")
        rsp.headers.setdefault(
            "Permissions-Policy", "geolocation=(), microphone=(), camera=()"
        )
        rsp.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        rsp.headers.setdefault("Cross-Origin-Resource-Policy", "same-site")
        return rsp
