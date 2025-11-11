"""Content-Security-Policy helpers (nonce generation and retrieval)."""

from __future__ import annotations

import secrets
from typing import Optional

from starlette.requests import Request

from .security_settings import get_security_settings

_STATE_ATTR = "csp_nonce"


def ensure_csp_nonce(request: Request) -> str:
    """
    Ensure the request has a CSP nonce associated with it.

    Args:
        request: Incoming request

    Returns:
        The nonce value (newly generated if missing)
    """
    nonce = getattr(request.state, _STATE_ATTR, None)
    if nonce:
        return nonce
    cfg = get_security_settings()
    nonce = secrets.token_urlsafe(max(8, cfg.csp_nonce_length))
    setattr(request.state, _STATE_ATTR, nonce)
    return nonce


def get_csp_nonce(request: Request) -> Optional[str]:
    """
    Retrieve previously generated CSP nonce, if any.

    Args:
        request: Incoming request

    Returns:
        Nonce string or None when not yet generated
    """
    return getattr(request.state, _STATE_ATTR, None)
