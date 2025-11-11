"""
CSRF protection with signed HMAC tokens and TTL.

Provides form helpers and validation for POST actions in the ops console.
All tokens include timestamp, TTL, and HMAC signature to prevent tampering.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import cast

from fastapi import HTTPException, Request, status

logger = logging.getLogger(__name__)

# Token lifetime in seconds (15 minutes default)
DEFAULT_TOKEN_TTL = 900

# Default secret key for CSRF protection (override in production)
DEFAULT_SECRET_KEY = "qnwis-ops-console-csrf-default-key-change-in-production"


@dataclass(frozen=True)
class CSRFToken:
    """
    Signed CSRF token with embedded timestamp.

    Attributes:
        token: Base64-encoded token value
        timestamp: ISO 8601 timestamp when token was issued
        ttl: Token lifetime in seconds
    """

    token: str
    timestamp: str
    ttl: int


class CSRFProtection:
    """
    CSRF protection manager using HMAC-signed tokens.

    Generates tokens with embedded timestamp and TTL, validates them against
    tampering and expiration. Uses application secret key for signing.
    """

    def __init__(self, secret_key: str | None = None, ttl: int = DEFAULT_TOKEN_TTL) -> None:
        """
        Initialize CSRF protection.

        Args:
            secret_key: Secret key for HMAC signing (uses default if None)
            ttl: Token time-to-live in seconds
        """
        self._secret = secret_key or DEFAULT_SECRET_KEY
        self._ttl = ttl

    def generate_token(self, timestamp: str) -> CSRFToken:
        """
        Generate a new CSRF token.

        Args:
            timestamp: ISO 8601 timestamp for token issuance (from clock)

        Returns:
            CSRFToken with signed value
        """
        # Create payload: timestamp|ttl
        payload = f"{timestamp}|{self._ttl}"

        # Sign with HMAC-SHA256
        signature = hmac.new(
            self._secret.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        # Combine payload and signature
        token_value = f"{payload}|{signature}"

        return CSRFToken(token=token_value, timestamp=timestamp, ttl=self._ttl)

    def verify_token(self, token: str, current_timestamp: str) -> bool:
        """
        Verify CSRF token signature and expiration.

        Args:
            token: Token value to verify
            current_timestamp: Current ISO 8601 timestamp (from clock)

        Returns:
            True if token is valid and not expired
        """
        try:
            # Parse token: timestamp|ttl|signature
            parts = token.split("|")
            if len(parts) != 3:
                logger.warning("CSRF token format invalid (expected 3 parts)")
                return False

            token_timestamp, token_ttl_str, provided_signature = parts

            # Reconstruct payload and verify signature
            payload = f"{token_timestamp}|{token_ttl_str}"
            expected_signature = hmac.new(
                self._secret.encode("utf-8"),
                payload.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()

            # Constant-time comparison
            if not hmac.compare_digest(expected_signature, provided_signature):
                logger.warning("CSRF token signature mismatch")
                return False

            # Check expiration using ISO timestamp comparison
            # Simple string comparison works for ISO 8601 in UTC
            token_dt = datetime.fromisoformat(token_timestamp.replace("Z", "+00:00"))
            current_dt = datetime.fromisoformat(current_timestamp.replace("Z", "+00:00"))
            token_ttl = int(token_ttl_str)

            if (current_dt - token_dt).total_seconds() > token_ttl:
                logger.warning("CSRF token expired")
                return False

            return True

        except (ValueError, AttributeError) as exc:
            logger.warning("CSRF token verification failed: %s", exc)
            return False

    def form_field(self, token: CSRFToken) -> str:
        """
        Generate HTML hidden input field for CSRF token.

        Args:
            token: CSRF token to embed

        Returns:
            HTML string for hidden input
        """
        return f'<input type="hidden" name="csrf_token" value="{token.token}">'


def get_csrf_protection(request: Request) -> CSRFProtection:
    """
    Get CSRF protection instance from app state.

    Args:
        request: FastAPI request

    Returns:
        CSRFProtection instance
    """
    if not hasattr(request.app.state, "csrf_protection"):
        request.app.state.csrf_protection = CSRFProtection()
    return cast(CSRFProtection, request.app.state.csrf_protection)


async def verify_csrf_token(request: Request) -> None:
    """
    FastAPI dependency to verify CSRF token from form data.

    Args:
        request: FastAPI request with form data

    Raises:
        HTTPException: If CSRF token is missing or invalid
    """
    csrf = get_csrf_protection(request)

    # Get clock for current timestamp
    clock = getattr(request.app.state, "clock", None)
    if clock is None:
        from ..utils.clock import Clock
        clock = Clock()

    current_timestamp = clock.utcnow()

    # Extract token from form data
    form = await request.form()
    token = form.get("csrf_token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token missing",
        )

    if not csrf.verify_token(str(token), current_timestamp):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token invalid or expired",
        )


__all__ = ["CSRFToken", "CSRFProtection", "get_csrf_protection", "verify_csrf_token"]
