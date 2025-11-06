"""
FastAPI router for UI export endpoints.

Provides CSV, SVG, and optional PNG exports that work entirely on synthetic CSV data.
No network, SQL, or LLM dependencies. Deterministic and Windows-friendly.
"""

from __future__ import annotations

import os
from hashlib import md5
from io import StringIO
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request, Response

from ...api.models import ExportCSVMeta, ExportSVGMeta
from ...data.api.client import DataAPI
from ...ui.cards import (
    build_employment_share_gauge,
    build_ewi_hotlist_cards,
    build_top_sectors_cards,
)
from ...ui.charts import salary_yoy_series, sector_employment_bar
from ...ui.svg import bar_chart_svg, line_chart_svg

router = APIRouter(tags=["ui-export"])

_TTL_MIN = 60
_TTL_MAX = 86_400
_YEAR_MIN = 2000
_YEAR_MAX = 2100

_CSV_RESPONSE_DOC = {
    "content": {
        "text/csv": {
            "example": "title,subtitle,kpi,unit\nEnergy,Employment 2024,24000,persons"
        }
    },
    "headers": {
        "ETag": {
            "description": ExportCSVMeta.model_fields["etag"].description,
            "schema": {"type": "string"},
        },
        "Cache-Control": {
            "description": ExportCSVMeta.model_fields["cache_control"].description,
            "schema": {"type": "string"},
        },
    },
    "description": "Deterministic CSV export. See ExportCSVMeta for caching headers.",
}

_SVG_RESPONSE_DOC = {
    "content": {
        "image/svg+xml": {
            "example": '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="100"><title>Example</title></svg>'
        }
    },
    "headers": {
        "ETag": {
            "description": ExportSVGMeta.model_fields["etag"].description,
            "schema": {"type": "string"},
        },
        "Cache-Control": {
            "description": ExportSVGMeta.model_fields["cache_control"].description,
            "schema": {"type": "string"},
        },
    },
    "description": "Deterministic SVG export. See ExportSVGMeta for caching headers.",
}


def _api(queries_dir: str | None, ttl_s: int) -> DataAPI:
    """
    Create DataAPI instance with clamped TTL.

    Args:
        queries_dir: Path to queries directory (uses default if None)
        ttl_s: Cache TTL in seconds (clamped to 60-86400)

    Returns:
        Configured DataAPI instance
    """
    ttl = max(_TTL_MIN, min(_TTL_MAX, int(ttl_s)))
    return DataAPI(queries_dir=queries_dir or "src/qnwis/data/queries", ttl_s=ttl)


def _etag(payload: bytes) -> str:
    """
    Generate ETag from payload bytes.

    Args:
        payload: Binary content to hash

    Returns:
        MD5 hexdigest for use as ETag
    """
    return md5(payload).hexdigest()


def _match_etag(request: Request | None, etag_value: str) -> bool:
    """
    Return True when the If-None-Match header matches the supplied ETag.
    """
    if request is None:
        return False
    if_none_match = request.headers.get("if-none-match")
    if not if_none_match:
        return False
    candidates = [token.strip() for token in if_none_match.split(",") if token.strip()]
    return etag_value in candidates or "*" in candidates


def _etag_headers(etag_value: str) -> dict[str, str]:
    """
    Common caching headers for export responses.
    """
    return {
        "ETag": etag_value,
        "Cache-Control": "public, max-age=60",
    }


def _sector_param(sector: str | None) -> str:
    """
    Sanitize sector parameter to ensure minimum length and trimming.
    """
    if sector is None:
        return "Energy"
    cleaned = sector.strip()
    if len(cleaned) < 2:
        raise HTTPException(
            status_code=422,
            detail="sector must contain at least two characters",
        )
    return cleaned


@router.get(
    "/v1/ui/export/csv",
    responses={
        200: _CSV_RESPONSE_DOC,
        304: {"description": "Not modified when If-None-Match matches resource ETag."},
    },
)
def export_csv(
    request: Request,
    resource: str = Query(
        ...,
        pattern="^(top-sectors|ewi|sector-employment|salary-yoy|employment-share)$",
    ),
    queries_dir: str | None = None,
    ttl_s: int = Query(default=300, ge=_TTL_MIN, le=_TTL_MAX),
    year: int | None = Query(default=None, ge=_YEAR_MIN, le=_YEAR_MAX),
    n: int = Query(default=5, ge=1, le=20),
    sector: str | None = Query(default=None, min_length=2, max_length=80),
    threshold: float = Query(default=3.0, ge=0.0, le=100.0),
) -> Response:
    """
    Export UI data as CSV.

    Supported resources:
    - top-sectors: Top sectors by employment (params: year, n)
    - ewi: Early warning indicators (params: year, threshold, n)
    - sector-employment: Sector employment breakdown (params: year)
    - salary-yoy: Salary year-over-year by sector (params: sector)
    - employment-share: Employment share gauge (params: year)

    Args:
        resource: Resource type to export
        queries_dir: Optional queries directory path
        ttl_s: Cache TTL in seconds (60-86400)
        year: Target year (defaults to latest)
        n: Top N results (for top-sectors, ewi)
        sector: Sector name (for salary-yoy)
        threshold: Threshold value (for ewi)

    Returns:
        CSV file as text/csv with cache headers
    """
    api = _api(queries_dir, ttl_s)
    # gather table rows deterministically
    rows: list[dict[str, Any]]
    if resource == "top-sectors":
        rows = build_top_sectors_cards(api, year=year, top_n=n)
    elif resource == "ewi":
        rows = build_ewi_hotlist_cards(api, year=year, threshold=threshold, top_n=n)
    elif resource == "sector-employment":
        data = sector_employment_bar(
            api, year=year or (api.latest_year("sector_employment") or 2024)
        )
        rows = [
            {"sector": c, "employees": v}
            for c, v in zip(data["categories"], data["values"])
        ]
    elif resource == "salary-yoy":
        sec = _sector_param(sector)
        data = salary_yoy_series(api, sector=sec)
        rows = [{"year": p["x"], "yoy_percent": p["y"]} for p in data["series"]]
    else:  # employment-share
        g = build_employment_share_gauge(api, year=year)
        rows = [
            {
                "year": g["year"],
                "male_percent": g["male"],
                "female_percent": g["female"],
                "total_percent": g["total"],
            }
        ]
    # render CSV
    if not rows:
        rows = [{}]
    headers = list(rows[0].keys())
    buf = StringIO()
    buf.write(",".join(headers) + "\n")
    for r in rows:
        buf.write(",".join(str(r.get(h, "")) for h in headers) + "\n")
    payload = buf.getvalue().encode("utf-8")
    etag_value = f"\"{_etag(payload)}\""
    if _match_etag(request, etag_value):
        return Response(status_code=304, headers=_etag_headers(etag_value))

    return Response(
        content=payload,
        media_type="text/csv",
        headers=_etag_headers(etag_value),
    )


@router.get(
    "/v1/ui/export/svg",
    responses={
        200: _SVG_RESPONSE_DOC,
        304: {"description": "Not modified when If-None-Match matches resource ETag."},
    },
)
def export_svg(
    request: Request,
    chart: str = Query(..., pattern="^(sector-employment|salary-yoy)$"),
    queries_dir: str | None = None,
    ttl_s: int = Query(default=300, ge=_TTL_MIN, le=_TTL_MAX),
    year: int | None = Query(default=None, ge=_YEAR_MIN, le=_YEAR_MAX),
    sector: str | None = Query(default=None, min_length=2, max_length=80),
) -> Response:
    """
    Export chart as SVG.

    Supported charts:
    - sector-employment: Bar chart of sector employment (params: year)
    - salary-yoy: Line chart of salary YoY by sector (params: sector)

    Args:
        chart: Chart type to export
        queries_dir: Optional queries directory path
        ttl_s: Cache TTL in seconds (60-86400)
        year: Target year (defaults to latest)
        sector: Sector name (for salary-yoy)

    Returns:
        SVG file as image/svg+xml with cache headers
    """
    api = _api(queries_dir, ttl_s)
    if chart == "sector-employment":
        y = year or (api.latest_year("sector_employment") or 2024)
        data = sector_employment_bar(api, year=y)
        svg = bar_chart_svg(
            title=data["title"], categories=data["categories"], values=data["values"]
        )
    else:
        sec = _sector_param(sector)
        data = salary_yoy_series(api, sector=sec)
        svg = line_chart_svg(title=data["title"], points=data["series"])
    payload = svg.encode("utf-8")
    etag_value = f"\"{_etag(payload)}\""
    if _match_etag(request, etag_value):
        return Response(status_code=304, headers=_etag_headers(etag_value))

    return Response(
        content=payload,
        media_type="image/svg+xml",
        headers=_etag_headers(etag_value),
    )


@router.get(
    "/v1/ui/export/png",
    responses={
        200: {
            "content": {"image/png": {}},
            "headers": _SVG_RESPONSE_DOC["headers"],  # Cache headers identical
            "description": "PNG snapshot when enabled (requires Pillow).",
        },
        304: {"description": "Not modified when If-None-Match matches resource ETag."},
        406: {
            "description": "PNG export disabled when QNWIS_ENABLE_PNG_EXPORT != 1 or Pillow missing."
        },
    },
)
def export_png(
    request: Request,
    chart: str = Query(..., pattern="^(sector-employment|salary-yoy)$"),
    queries_dir: str | None = None,
    ttl_s: int = Query(default=300, ge=_TTL_MIN, le=_TTL_MAX),
    year: int | None = Query(default=None, ge=_YEAR_MIN, le=_YEAR_MAX),
    sector: str | None = Query(default=None, min_length=2, max_length=80),
) -> Response:
    """
    Optional PNG export. If Pillow is missing or QNWIS_ENABLE_PNG_EXPORT != '1',
    respond 406 with JSON and suggest using /v1/ui/export/svg instead.

    Args:
        chart: Chart type to export
        queries_dir: Optional queries directory path
        ttl_s: Cache TTL in seconds (60-86400)
        year: Target year (defaults to latest)
        sector: Sector name (for salary-yoy)

    Returns:
        PNG file as image/png with cache headers

    Raises:
        HTTPException: 406 if PNG export is disabled or Pillow not installed
    """
    if os.environ.get("QNWIS_ENABLE_PNG_EXPORT") != "1":
        raise HTTPException(
            status_code=406,
            detail="PNG export disabled. Use /v1/ui/export/svg or set QNWIS_ENABLE_PNG_EXPORT=1 with Pillow installed.",
        )
    try:
        from PIL import Image, ImageDraw
    except Exception as exc:
        raise HTTPException(
            status_code=406,
            detail="PNG export requires Pillow. Install it or use /v1/ui/export/svg.",
        ) from exc

    api = _api(queries_dir, ttl_s)
    # minimal placeholder PNG (text header); deterministic output
    img = Image.new("RGB", (640, 360), "white")
    draw = ImageDraw.Draw(img)
    label = f"Chart: {chart}"
    if chart == "salary-yoy":
        sec = _sector_param(sector)
        label = f"{label} - {sec}"
    else:
        resolved_year = year or (api.latest_year("sector_employment") or 2024)
        label = f"{label} ({resolved_year})"
    draw.text((10, 10), label, fill="black")
    import io

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    payload = buf.getvalue()
    etag_value = f"\"{_etag(payload)}\""
    if _match_etag(request, etag_value):
        return Response(status_code=304, headers=_etag_headers(etag_value))

    return Response(
        content=payload,
        media_type="image/png",
        headers=_etag_headers(etag_value),
    )
