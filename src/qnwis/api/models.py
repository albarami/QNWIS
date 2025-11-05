"""
Pydantic models for the QNWIS HTTP API.

Defines request and response schemas for deterministic query endpoints,
ensuring type safety and automatic validation.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class QueryRunRequest(BaseModel):
    """Request model for executing a deterministic query."""

    ttl_s: int | None = Field(
        default=None, description="Override cache TTL (seconds)"
    )
    override_params: dict[str, Any] = Field(
        default_factory=dict,
        description="Whitelisted parameter overrides (year, timeout_s, max_rows, to_percent)",
    )


class QueryRunResponse(BaseModel):
    """Response model for query execution results."""

    query_id: str
    unit: str
    rows: list[dict[str, Any]]
    provenance: dict[str, Any]
    freshness: dict[str, Any]
    warnings: list[str] = Field(default_factory=list)
    request_id: str | None = None
