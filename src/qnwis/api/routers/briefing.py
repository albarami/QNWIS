"""
Briefing API endpoints.

Uses LLM-powered multi-agent workflow to generate ministerial briefings.
"""
from __future__ import annotations

import warnings
from typing import Any

from fastapi import APIRouter

router = APIRouter(tags=["briefing"])


@router.post("/briefing/minister")
def minister_briefing(
    queries_dir: str | None = None,
    ttl_s: int = 300
) -> dict[str, Any]:
    """
    [DEPRECATED] Generate Minister Briefing - Legacy endpoint.

    **Use `/api/v1/council/run-llm` or `/api/v1/council/stream` instead**
    for LLM-powered ministerial analysis with real-time reasoning.

    This legacy endpoint used deterministic council orchestration.
    It is maintained for backward compatibility only.

    Args:
        queries_dir: Optional queries directory path (unused)
        ttl_s: Cache TTL in seconds (unused)

    Returns:
        Deprecation notice with redirect instructions
    """
    warnings.warn(
        "DEPRECATED: /v1/briefing/minister → use /v1/council/run-llm or /v1/council/stream",
        DeprecationWarning,
        stacklevel=2,
    )

    return {
        "status": "deprecated",
        "message": (
            "This endpoint is deprecated. "
            "Use /api/v1/council/run-llm for complete LLM analysis "
            "or /api/v1/council/stream for real-time streaming."
        ),
        "redirect": {
            "complete_json": "/api/v1/council/run-llm",
            "streaming_sse": "/api/v1/council/stream",
        },
        "example": {
            "method": "POST",
            "url": "/api/v1/council/run-llm",
            "body": {
                "question": "Generate a comprehensive briefing on Qatar's labour market status",
                "provider": "anthropic",
            },
        },
    }
