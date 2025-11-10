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


# ============================================================================
# Agent API Models (Step 27)
# ============================================================================


class AgentRequestOptions(BaseModel):
    """
    Optional execution options for agent requests.

    Attributes:
        enforce_citations: Enable L19 citation enforcement (default: True)
        verify_numbers: Enable L20 numeric verification (default: True)
        audit_pack: Generate L21 audit pack (default: True)
        max_rows: Maximum result rows (default: None)
    """

    enforce_citations: bool = Field(default=True, description="Enable citation enforcement")
    verify_numbers: bool = Field(default=True, description="Enable numeric verification")
    audit_pack: bool = Field(default=True, description="Generate audit pack")
    max_rows: int | None = Field(default=None, description="Maximum result rows")


class AgentRequest(BaseModel):
    """
    Standard request envelope for agent execution.

    Attributes:
        intent: Agent intent (e.g., 'time.baseline', 'pattern.stable_relations')
        params: Agent-specific parameters
        options: Execution options (citations, verification, audit)
    """

    intent: str = Field(..., description="Agent intent (e.g., 'time.baseline')")
    params: dict[str, Any] = Field(default_factory=dict, description="Agent parameters")
    options: AgentRequestOptions = Field(
        default_factory=AgentRequestOptions,
        description="Execution options",
    )


class ConfidenceScore(BaseModel):
    """
    L22 confidence scoring result.

    Attributes:
        score: Confidence score (0-100)
        band: Confidence band (low, med, high, very_high)
        components: Component scores (data_quality, coverage, timeliness)
    """

    score: int = Field(..., ge=0, le=100, description="Confidence score (0-100)")
    band: str = Field(..., description="Confidence band (low|med|high|very_high)")
    components: dict[str, float] = Field(
        default_factory=dict,
        description="Component scores",
    )


class FreshnessInfo(BaseModel):
    """
    Data freshness information.

    Attributes:
        asof_min: Oldest data timestamp
        asof_max: Newest data timestamp
        updated_max: Latest update timestamp
        sources: Per-source freshness
    """

    asof_min: str = Field(..., description="Oldest data timestamp (YYYY-MM-DD)")
    asof_max: str = Field(..., description="Newest data timestamp (YYYY-MM-DD)")
    updated_max: str | None = Field(None, description="Latest update timestamp")
    sources: dict[str, str] = Field(default_factory=dict, description="Per-source freshness")


class Citation(BaseModel):
    """
    L19 citation reference.

    Attributes:
        qid: Query ID (e.g., 'LMIS_RETENTION_TS')
        note: Citation note (e.g., 'Per LMIS retention data')
        source: Data source identifier
    """

    qid: str = Field(..., description="Query ID")
    note: str = Field(..., description="Citation note")
    source: str | None = Field(None, description="Data source")


class TimingsMs(BaseModel):
    """
    Execution timing breakdown in milliseconds.

    Attributes:
        total: Total execution time
        agent: Agent execution time
        verification: Verification time
        cache: Cache access time
    """

    total: int = Field(..., description="Total execution time (ms)")
    agent: int = Field(..., description="Agent execution time (ms)")
    verification: int = Field(default=0, description="Verification time (ms)")
    cache: int = Field(default=0, description="Cache access time (ms)")


class AgentResponse(BaseModel):
    """
    Standard response envelope for agent execution.

    Includes verification layers (L19-L22) when enabled.

    Attributes:
        request_id: Unique request identifier
        audit_id: Audit trail identifier (if audit_pack enabled)
        confidence: L22 confidence scoring
        freshness: Data freshness information
        result: Agent-specific result payload
        citations: L19 citation references
        timings_ms: Execution timing breakdown
        warnings: Optional warning messages
    """

    request_id: str = Field(..., description="Unique request identifier")
    audit_id: str | None = Field(None, description="Audit trail identifier")
    confidence: ConfidenceScore | None = Field(None, description="Confidence scoring")
    freshness: FreshnessInfo | None = Field(None, description="Data freshness")
    result: dict[str, Any] = Field(default_factory=dict, description="Agent result payload")
    citations: list[Citation] = Field(default_factory=list, description="Citation references")
    timings_ms: TimingsMs = Field(..., description="Execution timings")
    warnings: list[str] = Field(default_factory=list, description="Warning messages")
