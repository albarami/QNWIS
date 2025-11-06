"""
Chart data builders for QNWIS UI components.

Provides functions that build chart data structures from DataAPI queries.
All outputs are deterministic and based on synthetic CSV data.
"""

from __future__ import annotations

from typing import Any

from ..data.api.client import DataAPI


def salary_yoy_series(api: DataAPI, sector: str) -> dict[str, Any]:
    """
    Build time series data for salary year-over-year growth by sector.

    Args:
        api: DataAPI instance for querying synthetic data
        sector: Sector name to query

    Returns:
        Dictionary with keys:
            - title: Chart title including sector name
            - series: List of data points [{x: year, y: yoy_percent}, ...]

    Example:
        >>> api = DataAPI("src/qnwis/data/queries")
        >>> data = salary_yoy_series(api, "Energy")
        >>> "series" in data
        True
        >>> all("x" in pt and "y" in pt for pt in data["series"])
        True
    """
    pts = api.yoy_salary_by_sector(sector=sector)
    series: list[dict[str, Any]] = []
    for item in pts:
        yoy = item.get("yoy_percent")
        if yoy is None:
            continue
        series.append({"x": int(item["year"]), "y": float(yoy)})
    return {"title": f"Salary YoY - {sector}", "series": series}


def sector_employment_bar(api: DataAPI, year: int) -> dict[str, Any]:
    """
    Build bar chart data for sector employment in a given year.

    Args:
        api: DataAPI instance for querying synthetic data
        year: Target year for employment data

    Returns:
        Dictionary with keys:
            - title: Chart title including year
            - categories: List of sector names
            - values: List of employment counts (aligned with categories)

    Example:
        >>> api = DataAPI("src/qnwis/data/queries")
        >>> data = sector_employment_bar(api, year=2024)
        >>> len(data["categories"]) == len(data["values"])
        True
    """
    rows = api.sector_employment(year)
    categories: list[str] = []
    values: list[int] = []
    for row in rows:
        categories.append(str(row.sector))
        values.append(int(row.employees))
    resolved_year = int(year)
    return {
        "title": f"Sector Employment - {resolved_year}",
        "categories": categories,
        "values": values,
        "year": resolved_year,
    }
