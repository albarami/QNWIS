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


class UICard(BaseModel):
    """Single KPI card used by UI demos."""

    title: str
    subtitle: str
    kpi: int | float
    unit: str
    meta: dict[str, Any] = Field(default_factory=dict)


class UICardsResponse(BaseModel):
    """Envelope for KPI cards responses."""

    cards: list[UICard] = Field(default_factory=list)


class ChartPoint(BaseModel):
    """Generic chart data point."""

    x: int | float
    y: int | float | None


class SalaryYoYChartResponse(BaseModel):
    """Time-series chart showing salary year-over-year growth."""

    title: str
    series: list[ChartPoint] = Field(default_factory=list)


class SectorEmploymentChartResponse(BaseModel):
    """Bar chart of sector employment distribution."""

    title: str
    categories: list[str] = Field(default_factory=list)
    values: list[int] = Field(default_factory=list)
    year: int


class EmploymentShareGaugeResponse(BaseModel):
    """Gauge output for employment share by gender."""

    year: int
    male: float | None
    female: float | None
    total: float | None


class ExportCSVMeta(BaseModel):
    """
    Metadata description for CSV exports (OpenAPI documentation helper).
    """

    filename: str = Field(
        default="sector-employment.csv",
        description="Suggested filename for the CSV download.",
    )
    content_type: str = Field(
        default="text/csv",
        description="MIME type served by the export endpoint.",
    )
    cache_control: str = Field(
        default="public, max-age=60",
        description="Cache-Control header applied to the export response.",
    )
    etag: str = Field(
        default='"<sha256>"',
        description="Strong validator representing the file contents.",
    )


class ExportSVGMeta(BaseModel):
    """
    Metadata description for SVG exports (OpenAPI documentation helper).
    """

    filename: str = Field(
        default="sector-employment.svg",
        description="Suggested filename for the SVG download.",
    )
    content_type: str = Field(
        default="image/svg+xml",
        description="MIME type served by the export endpoint.",
    )
    cache_control: str = Field(
        default="public, max-age=60",
        description="Cache-Control header applied to the export response.",
    )
    etag: str = Field(
        default='"<sha256>"',
        description="Strong validator representing the SVG markup.",
    )
