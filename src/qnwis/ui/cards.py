"""
Card builders for QNWIS UI components.

Provides functions that build KPI card data structures from DataAPI queries.
All outputs are deterministic and based on synthetic CSV data.
"""

from __future__ import annotations

from typing import Any

from ..data.api.client import DataAPI


def _clamp_topn(n: int, lo: int = 1, hi: int = 20) -> int:
    """
    Clamp top-N parameter to safe range.

    Args:
        n: Requested top-N value
        lo: Minimum allowed value (default 1)
        hi: Maximum allowed value (default 20)

    Returns:
        Clamped integer in range [lo, hi]
    """
    return max(lo, min(hi, int(n)))


def build_top_sectors_cards(
    api: DataAPI, year: int | None = None, top_n: int = 5
) -> list[dict[str, Any]]:
    """
    Build KPI cards for top sectors by employment.

    Args:
        api: DataAPI instance for querying synthetic data
        year: Target year (defaults to latest available)
        top_n: Number of top sectors to return (clamped to 1-20)

    Returns:
        List of card dictionaries with keys:
            - title: Sector name
            - subtitle: Description including year
            - kpi: Employment count
            - unit: Unit label ("persons")
            - meta: Additional metadata (year)

    Example:
        >>> api = DataAPI("src/qnwis/data/queries")
        >>> cards = build_top_sectors_cards(api, year=2024, top_n=3)
        >>> cards[0]["title"]
        "Energy"
    """
    n = _clamp_topn(top_n)
    y = year if year is not None else (api.latest_year("sector_employment") or 2024)
    rows = api.top_sectors_by_employment(y, n)
    return [
        {
            "title": str(r["sector"]),
            "subtitle": f"Employment {int(y)}",
            "kpi": int(r["employees"]),
            "unit": "persons",
            "meta": {"year": int(y)},
        }
        for r in rows
    ]


def build_ewi_hotlist_cards(
    api: DataAPI,
    year: int | None = None,
    threshold: float = 3.0,
    top_n: int = 5,
) -> list[dict[str, Any]]:
    """
    Build cards for sectors breaching early-warning employment drop threshold.

    Args:
        api: DataAPI instance for querying synthetic data
        year: Target year (defaults to latest available)
        threshold: Percent drop threshold for early warning
        top_n: Number of sectors to return (clamped to 1-20)

    Returns:
        List of card dictionaries with keys:
            - title: Sector name
            - subtitle: Description including year
            - kpi: Employment drop percentage
            - unit: Unit label ("percent")
            - meta: Additional metadata (year, threshold)

    Example:
        >>> api = DataAPI("src/qnwis/data/queries")
        >>> cards = build_ewi_hotlist_cards(api, threshold=3.5)
        >>> len(cards) <= 5
        True
    """
    n = _clamp_topn(top_n)
    y = year if year is not None else (api.latest_year("ewi_employment_drop") or 2024)
    rows = api.early_warning_hotlist(y, threshold=threshold, top_n=n)
    return [
        {
            "title": str(r["sector"]),
            "subtitle": f"EWI drop {int(y)}",
            "kpi": float(r["drop_percent"]),
            "unit": "percent",
            "meta": {"year": int(y), "threshold": float(threshold)},
        }
        for r in rows
    ]


def build_employment_share_gauge(
    api: DataAPI, year: int | None = None
) -> dict[str, Any]:
    """
    Build gauge data for employment share (male/female/total).

    Args:
        api: DataAPI instance for querying synthetic data
        year: Target year (defaults to latest available)

    Returns:
        Dictionary with keys:
            - year: Data year
            - male: Male employment percentage (or None if no data)
            - female: Female employment percentage (or None if no data)
            - total: Total employment percentage (or None if no data)

    Example:
        >>> api = DataAPI("src/qnwis/data/queries")
        >>> gauge = build_employment_share_gauge(api, year=2024)
        >>> set(gauge.keys()) == {"year", "male", "female", "total"}
        True
    """
    y = year if year is not None else (api.latest_year("employment_share_all") or 2024)
    rows = api.employment_share_latest(year=y)
    # Expect a single row for the chosen year in synthetic pack
    row = rows[-1] if rows else None
    if not row:
        return {"year": int(y), "male": None, "female": None, "total": None}
    return {
        "year": int(row.year),
        "male": float(row.male_percent) if row.male_percent is not None else None,
        "female": float(row.female_percent) if row.female_percent is not None else None,
        "total": float(row.total_percent) if row.total_percent is not None else None,
    }
