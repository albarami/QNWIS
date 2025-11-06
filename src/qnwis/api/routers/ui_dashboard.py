"""
FastAPI router for HTML dashboard and PNG/CSV exports.

Provides endpoints for:
- HTML dashboard with embedded PNG charts
- PNG chart exports (matplotlib-based)
- CSV table exports

All endpoints return deterministic output with ETag and Cache-Control headers.
"""

from __future__ import annotations

import hashlib

from fastapi import APIRouter, Query, Request, Response

from ...ui.export import (
    csv_sector_employment,
    csv_top_sectors,
    png_salary_yoy,
    png_sector_employment_bar,
)
from ...ui.html import render_dashboard_html
from ..routers.ui import _api  # reuse clamp + DataAPI init

router = APIRouter(tags=["dashboard"])

_CACHE = "public, max-age=60"


def _etag_header(etag: str) -> str:
    """
    Format ETag value for HTTP header usage (quoted-string).
    """
    return f"\"{etag}\""


def _matches_etag(request: Request | None, etag_header: str) -> bool:
    """
    Return True when the incoming request supplies an If-None-Match header
    that matches the provided ETag value.
    """
    if request is None:
        return False
    if_none_match = request.headers.get("if-none-match")
    if not if_none_match:
        return False
    candidates = [token.strip() for token in if_none_match.split(",") if token.strip()]
    return etag_header in candidates or "*" in candidates


def _resp(request: Request, payload: bytes, media_type: str, etag: str) -> Response:
    """
    Build Response with payload, media type, ETag, and cache headers.

    Args:
        request: The incoming HTTP request (for ETag short-circuiting)
        payload: Response body as bytes
        media_type: MIME type for Content-Type header
        etag: ETag value for caching

    Returns:
        FastAPI Response object
    """
    etag_header = _etag_header(etag)
    if _matches_etag(request, etag_header):
        return Response(
            status_code=304,
            headers={"ETag": etag_header, "Cache-Control": _CACHE},
        )
    r = Response(content=payload, media_type=media_type)
    r.headers["ETag"] = etag_header
    r.headers["Cache-Control"] = _CACHE
    return r


@router.get("/v1/ui/dashboard/summary", response_class=Response)
def dashboard_summary_html(
    request: Request,
    queries_dir: str | None = None,
    ttl_s: int = Query(default=300, ge=60, le=86_400),
    year: int | None = None,
    sector: str = Query(default="Energy", min_length=2),
) -> Response:
    """
    Get HTML dashboard with embedded PNG charts and KPI cards.

    Args:
        queries_dir: Optional queries directory path
        ttl_s: Cache TTL in seconds (60-86400)
        year: Target year (defaults to latest available)
        sector: Sector name for salary YoY chart

    Returns:
        HTML document with embedded base64 PNG images

    Example:
        GET /v1/ui/dashboard/summary?year=2024&sector=Energy
    """
    api = _api(queries_dir, ttl_s)
    html = render_dashboard_html(api, year=year, sector=sector)
    payload = html.encode("utf-8")
    etag = hashlib.sha256(payload).hexdigest()
    return _resp(request, payload, "text/html; charset=utf-8", etag)


@router.get("/v1/ui/export/sector-employment.csv")
def export_sector_employment_csv(
    request: Request,
    queries_dir: str | None = None,
    ttl_s: int = Query(default=300, ge=60, le=86_400),
    year: int = Query(..., ge=2000, le=2100),
) -> Response:
    """
    Export sector employment data as CSV.

    Args:
        queries_dir: Optional queries directory path
        ttl_s: Cache TTL in seconds (60-86400)
        year: Target year (required)

    Returns:
        CSV file with columns: year, sector, employees

    Example:
        GET /v1/ui/export/sector-employment.csv?year=2024
    """
    api = _api(queries_dir, ttl_s)
    data, etag = csv_sector_employment(api, year)
    return _resp(request, data, "text/csv; charset=utf-8", etag)


@router.get("/v1/ui/export/top-sectors.csv")
def export_top_sectors_csv(
    request: Request,
    queries_dir: str | None = None,
    ttl_s: int = Query(default=300, ge=60, le=86_400),
    year: int | None = None,
    n: int = Query(default=5, ge=1, le=20),
) -> Response:
    """
    Export top N sectors by employment as CSV.

    Args:
        queries_dir: Optional queries directory path
        ttl_s: Cache TTL in seconds (60-86400)
        year: Target year (defaults to latest available)
        n: Number of top sectors to return

    Returns:
        CSV file with columns: year, sector, employees

    Example:
        GET /v1/ui/export/top-sectors.csv?year=2024&n=5
    """
    api = _api(queries_dir, ttl_s)
    y = year if year is not None else (api.latest_year("sector_employment") or 2024)
    data, etag = csv_top_sectors(api, y, top_n=n)
    return _resp(request, data, "text/csv; charset=utf-8", etag)


@router.get("/v1/ui/export/salary-yoy.png")
def export_salary_yoy_png(
    request: Request,
    queries_dir: str | None = None,
    ttl_s: int = Query(default=300, ge=60, le=86_400),
    sector: str = Query(..., min_length=2),
) -> Response:
    """
    Export salary year-over-year line chart as PNG.

    Args:
        queries_dir: Optional queries directory path
        ttl_s: Cache TTL in seconds (60-86400)
        sector: Sector name (required)

    Returns:
        PNG image (matplotlib-generated)

    Example:
        GET /v1/ui/export/salary-yoy.png?sector=Energy
    """
    api = _api(queries_dir, ttl_s)
    data, etag = png_salary_yoy(api, sector=sector)
    return _resp(request, data, "image/png", etag)


@router.get("/v1/ui/export/sector-employment.png")
def export_sector_employment_png(
    request: Request,
    queries_dir: str | None = None,
    ttl_s: int = Query(default=300, ge=60, le=86_400),
    year: int = Query(..., ge=2000, le=2100),
) -> Response:
    """
    Export sector employment bar chart as PNG.

    Args:
        queries_dir: Optional queries directory path
        ttl_s: Cache TTL in seconds (60-86400)
        year: Target year (required)

    Returns:
        PNG image (matplotlib-generated)

    Example:
        GET /v1/ui/export/sector-employment.png?year=2024
    """
    api = _api(queries_dir, ttl_s)
    data, etag = png_sector_employment_bar(api, year=year)
    return _resp(request, data, "image/png", etag)
