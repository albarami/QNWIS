"""
Shared orchestration utilities.

Currently exposes helpers for sanitising parameter payloads before they are
logged or embedded in metadata to avoid leaking secrets.
"""

from __future__ import annotations

from typing import Any, Mapping

SENSITIVE_KEYS = {"token", "secret", "password", "apikey", "api_key", "key"}


def filter_sensitive_params(params: Mapping[str, Any]) -> dict[str, Any]:
    """
    Return a copy of ``params`` with sensitive values redacted.

    Keys containing any substring from :data:`SENSITIVE_KEYS` are replaced by
    ``"[REDACTED]"`` to prevent leaking secrets into logs, telemetry, or result
    metadata. Non-sensitive keys are copied verbatim.
    """
    sanitized: dict[str, Any] = {}
    for key, value in params.items():
        lowered = key.lower()
        if any(marker in lowered for marker in SENSITIVE_KEYS):
            sanitized[key] = "[REDACTED]"
        else:
            sanitized[key] = value
    return sanitized
