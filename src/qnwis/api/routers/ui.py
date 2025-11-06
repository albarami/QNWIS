"""
FastAPI router for UI demo endpoints.

Provides JSON endpoints for cards and charts that work entirely on synthetic CSV data.
No network, SQL, or LLM dependencies. Deterministic and Windows-friendly.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from ...api.models import (
    ChartPoint,
    EmploymentShareGaugeResponse,
    SalaryYoYChartResponse,
    SectorEmploymentChartResponse,
    UICard,
    UICardsResponse,
)
from ...data.api.client import DataAPI
from ...ui.cards import (
    build_employment_share_gauge,
    build_ewi_hotlist_cards,
    build_top_sectors_cards,
)
from ...ui.charts import salary_yoy_series, sector_employment_bar

router = APIRouter(tags=["ui"])

_TTL_MIN = 60
_TTL_MAX = 86_400
_YEAR_MIN = 2000
_YEAR_MAX = 2100


def _api(queries_dir: str | None, ttl_s: int) -> DataAPI:
    """
    Create DataAPI instance with clamped TTL.

    Args:
        queries_dir: Path to queries directory (uses default if None)
        ttl_s: Cache TTL in seconds (clamped to 60-86400)

    Returns:
        Configured DataAPI instance
    """
    ttl = int(ttl_s)
    if ttl < _TTL_MIN:
        ttl = _TTL_MIN
    elif ttl > _TTL_MAX:
        ttl = _TTL_MAX
    return DataAPI(
        queries_dir=queries_dir or "src/qnwis/data/queries", ttl_s=ttl
    )


def _cached_response(payload: Any) -> JSONResponse:
    """
    Serialize payload, attach cache headers, and return JSONResponse.
    """
    body = (
        payload.model_dump(mode="json")
        if hasattr(payload, "model_dump")
        else payload
    )

    serialized = json.dumps(
        body,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    response = JSONResponse(content=body)
    response.headers["ETag"] = f"\"{digest}\""
    response.headers["Cache-Control"] = "public, max-age=60"
    return response


def _sanitize_sector(raw_sector: str) -> str:
    """
    Trim sector input and ensure it satisfies minimum length.
    """
    sector = raw_sector.strip()
    if len(sector) < 2:
        raise HTTPException(
            status_code=422, detail="sector must contain at least two characters"
        )
    return sector


def _resolve_year(api: DataAPI, key: str, year: int | None) -> int:
    """
    Resolve target year using DataAPI.latest_year when not provided.
    """
    if year is not None:
        return int(year)
    latest = api.latest_year(key)
    if latest is None:
        raise HTTPException(
            status_code=404, detail=f"No data available for '{key}'"
        )
    return int(latest)


@router.get(
    "/v1/ui/cards/top-sectors",
    response_model=UICardsResponse,
)
def ui_cards_top_sectors(
    queries_dir: str | None = None,
    ttl_s: int = 300,
    year: int | None = Query(default=None, ge=_YEAR_MIN, le=_YEAR_MAX),
    n: int = Query(default=5, ge=1, le=20),
) -> JSONResponse:
    """
    Get KPI cards for top sectors by employment.
    """
    api = _api(queries_dir, ttl_s)
    resolved_year = _resolve_year(api, "sector_employment", year)
    cards_raw = build_top_sectors_cards(api, year=resolved_year, top_n=n)
    cards = [UICard.model_validate(item) for item in cards_raw]
    return _cached_response(UICardsResponse(cards=cards))


@router.get(
    "/v1/ui/cards/ewi",
    response_model=UICardsResponse,
)
def ui_cards_ewi(
    queries_dir: str | None = None,
    ttl_s: int = 300,
    year: int | None = Query(default=None, ge=_YEAR_MIN, le=_YEAR_MAX),
    threshold: float = Query(default=3.0, ge=0.0, le=100.0),
    n: int = Query(default=5, ge=1, le=20),
) -> JSONResponse:
    """
    Get KPI cards for early warning indicators (employment drop hotlist).
    """
    api = _api(queries_dir, ttl_s)
    resolved_year = _resolve_year(api, "ewi_employment_drop", year)
    cards_raw = build_ewi_hotlist_cards(
        api, year=resolved_year, threshold=threshold, top_n=n
    )
    cards = [UICard.model_validate(item) for item in cards_raw]
    return _cached_response(UICardsResponse(cards=cards))


@router.get(
    "/v1/ui/charts/salary-yoy",
    response_model=SalaryYoYChartResponse,
)
def ui_chart_salary_yoy(
    queries_dir: str | None = None,
    ttl_s: int = 300,
    sector: str = Query(..., min_length=2, max_length=80),
) -> JSONResponse:
    """
    Get time series chart data for salary year-over-year growth.
    """
    api = _api(queries_dir, ttl_s)
    sector_clean = _sanitize_sector(sector)
    raw = salary_yoy_series(api, sector=sector_clean)
    series = [ChartPoint.model_validate(point) for point in raw.get("series", [])]
    chart = SalaryYoYChartResponse(title=str(raw.get("title", "")), series=series)
    return _cached_response(chart)


@router.get(
    "/v1/ui/charts/sector-employment",
    response_model=SectorEmploymentChartResponse,
)
def ui_chart_sector_employment(
    queries_dir: str | None = None,
    ttl_s: int = 300,
    year: int | None = Query(default=None, ge=_YEAR_MIN, le=_YEAR_MAX),
) -> JSONResponse:
    """
    Get bar chart data for sector employment in a given year.
    """
    api = _api(queries_dir, ttl_s)
    resolved_year = _resolve_year(api, "sector_employment", year)
    raw = sector_employment_bar(api, year=resolved_year)
    chart = SectorEmploymentChartResponse(
        title=str(raw.get("title", "")),
        categories=[str(value) for value in raw.get("categories", [])],
        values=[int(v) for v in raw.get("values", [])],
    )
    return _cached_response(chart)


@router.get(
    "/v1/ui/charts/employment-share",
    response_model=EmploymentShareGaugeResponse,
)
def ui_chart_employment_share(
    queries_dir: str | None = None,
    ttl_s: int = 300,
    year: int | None = Query(default=None, ge=_YEAR_MIN, le=_YEAR_MAX),
) -> JSONResponse:
    """
    Get gauge data for employment share (male/female/total percentages).
    """
    api = _api(queries_dir, ttl_s)
    resolved_year = _resolve_year(api, "employment_share_all", year)
    raw = build_employment_share_gauge(api, year=resolved_year)
    gauge = EmploymentShareGaugeResponse.model_validate(raw)
    return _cached_response(gauge)
