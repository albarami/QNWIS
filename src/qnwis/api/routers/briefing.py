"""Briefing API endpoints."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from ...briefing.minister import build_briefing

router = APIRouter(tags=["briefing"])


def _clamp_ttl(ttl_s: int) -> int:
    """Bound ttl_s to supported limits."""
    clamped = max(60, min(86400, int(ttl_s)))
    return clamped


@router.post("/v1/briefing/minister")
def minister_briefing(
    queries_dir: str | None = None,
    ttl_s: int = 300
) -> dict[str, Any]:
    """
    Generate Minister Briefing combining council findings and verification.

    This endpoint:
    1. Runs the agent council on synthetic data
    2. Performs cross-source triangulation checks
    3. Returns a structured briefing with embedded Markdown

    Args:
        queries_dir: Optional queries directory path
        ttl_s: Cache TTL in seconds

    Returns:
        JSON with briefing structure including:
        - title: Briefing title
        - headline: List of key bullet points
        - key_metrics: Dictionary of numeric metrics
        - red_flags: List of verification issues
        - provenance: List of data source locators
        - markdown: Full briefing in Markdown format
    """
    effective_ttl = _clamp_ttl(ttl_s)
    b = build_briefing(queries_dir=queries_dir, ttl_s=effective_ttl)
    return {
        "title": b.title,
        "headline": b.headline,
        "key_metrics": b.key_metrics,
        "red_flags": b.red_flags,
        "provenance": b.provenance,
        "min_confidence": b.min_confidence,
        "licenses": b.licenses,
        "markdown": b.markdown,
    }
