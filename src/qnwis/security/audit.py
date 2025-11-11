"""Audit logging utilities and middleware with privacy-aware redaction."""

from __future__ import annotations

import hashlib
from typing import Any, Dict, Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from src.qnwis.utils.logger import setup_logger

logger = setup_logger(__name__)


def _hash_identifier(identifier: Optional[str]) -> Optional[str]:
    """
    Hash identifiers so logs avoid storing PII while remaining correlatable.

    Args:
        identifier: Raw identifier

    Returns:
        Short hash or None
    """
    if not identifier:
        return None
    digest = hashlib.sha256(identifier.encode("utf-8")).hexdigest()
    return digest[:12]


def audit_log(
    action: str,
    user_id: Optional[str],
    resource: str,
    success: bool,
    extra: Optional[Dict[str, Any]] = None,
):
    """
    Log an audit event (identifiers are hashed to avoid storing PII).

    Args:
        action: Action being performed
        user_id: User identifier (if available)
        resource: Resource being accessed
        success: Whether action succeeded
        extra: Additional context data
    """
    logger.info(
        "AUDIT",
        extra={
            "action": action,
            "user_hash": _hash_identifier(user_id),
            "resource": resource,
            "success": success,
            "extra": (extra or {}),
        },
    )


class RequestAuditMiddleware(BaseHTTPMiddleware):
    """Middleware to audit all HTTP requests."""

    async def dispatch(self, request: Request, call_next):
        """
        Process request and log audit trail.

        Args:
            request: Incoming request
            call_next: Next middleware in chain

        Returns:
            Response with audit logging
        """
        principal = getattr(request.state, "principal", None)
        user_obj = getattr(request.state, "user", None)
        user_id = None
        if principal and getattr(principal, "subject", None):
            user_id = principal.subject
        elif user_obj and getattr(user_obj, "id", None):
            user_id = user_obj.id

        resp = await call_next(request)
        client_host = request.client.host if request.client else None
        audit_log(
            "http_request",
            user_id,
            f"{request.method} {request.url.path}",
            True,
            {
                "status": resp.status_code,
                "client_hash": _hash_identifier(client_host),
            },
        )
        # Propagate any rate-limit headers added by deps
        headers = getattr(request.state, "rate_limit_headers", None)
        if headers:
            for k, v in headers.items():
                resp.headers.setdefault(k, v)
        return resp
