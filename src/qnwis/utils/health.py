"""Health check endpoints for QNWIS."""

from __future__ import annotations

from typing import Any


async def healthcheck() -> dict[str, Any]:
    """
    Basic health check endpoint.

    Returns:
        Status dictionary
    """
    return {"status": "healthy"}


async def readiness() -> dict[str, Any]:
    """
    Readiness check endpoint.

    Returns:
        Status dictionary
    """
    return {"status": "ready"}
