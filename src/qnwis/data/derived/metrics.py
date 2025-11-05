"""
Deterministic derived metric transformations.

This module provides functions for computing share-of-total, year-over-year
growth rates, and compound annual growth rates (CAGR) from structured data.
All computations are deterministic and handle edge cases gracefully.
"""

from __future__ import annotations

from collections.abc import Mapping
from math import isnan
from typing import Any

from ..deterministic.models import Row


def _val(x: Any) -> float | None:
    """
    Safely extract numeric value from any type.

    Args:
        x: Value to convert

    Returns:
        Float value or None if conversion fails or value is NaN
    """
    try:
        f = float(x)
        if f != f or isnan(f):  # NaN check
            return None
        return f
    except Exception:
        return None


def _safe_int(value: Any) -> int | None:
    """Safely coerce a value to int, returning None if conversion fails."""
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(float(str(value).strip()))
    except Exception:
        return None


def _row_payload(row: Any) -> dict[str, Any]:
    """
    Extract a mutable payload dictionary from Row or mapping-based inputs.

    Returns a shallow copy to avoid mutating the original structures.
    """
    if isinstance(row, Row):
        return dict(row.data)
    if isinstance(row, Mapping):
        data = row.get("data")
        if isinstance(data, Mapping):
            return dict(data)
        return dict(row)
    return {}


def share_of_total(
    rows: list[dict[str, Any]],
    value_key: str,
    group_key: str,
    out_key: str = "share_percent",
) -> list[dict[str, Any]]:
    """
    Compute 100 * value/sum(value) within each group.

    Groups data by 'year' field (if present) and calculates the percentage
    share of each row's value relative to the group total.

    Args:
        rows: List of rows with structure [{'data': {...}}]
        value_key: Key in data dict containing the value to aggregate
        group_key: Key in data dict used for grouping (currently uses 'year')
        out_key: Key for storing computed share percentage

    Returns:
        New list of rows with share_percent field added to each data dict

    Examples:
        >>> rows = [{"data": {"year": 2023, "v": 60}}, {"data": {"year": 2023, "v": 40}}]
        >>> result = share_of_total(rows, value_key="v", group_key="year")
        >>> result[0]["data"]["share_percent"]
        60.0
    """
    # Group by all keys except value_key
    # Simple strategy: group by year if present
    buckets: dict[Any, float] = {}
    for r in rows:
        d = _row_payload(r)
        g = d.get(group_key)
        v = _val(d.get(value_key))
        if v is not None:
            buckets[g] = buckets.get(g, 0.0) + v
    out: list[dict[str, Any]] = []
    for r in rows:
        d = _row_payload(r)
        g = d.get(group_key)
        v = _val(d.get(value_key))
        denom = buckets.get(g, 0.0) or 0.0
        d[out_key] = 100.0 * v / denom if (v is not None and denom > 0) else None
        out.append({"data": d})
    return out


def yoy_growth(
    rows: list[dict[str, Any]], value_key: str, out_key: str = "yoy_percent"
) -> list[dict[str, Any]]:
    """
    Compute year-over-year growth rate: (val_t - val_t-1) / val_t-1 * 100.

    Requires rows to contain a 'year' field. Calculates growth relative
    to the previous year's value.

    Args:
        rows: List of rows with structure [{'data': {'year': ..., value_key: ...}}]
        value_key: Key in data dict containing the value
        out_key: Key for storing computed YoY growth percentage

    Returns:
        New list of rows with yoy_percent field added to each data dict

    Examples:
        >>> rows = [{"data": {"year": 2022, "v": 100}}, {"data": {"year": 2023, "v": 110}}]
        >>> result = yoy_growth(rows, value_key="v")
        >>> result[1]["data"]["yoy_percent"]
        10.0
    """
    index: dict[int, float | None] = {}
    for r in rows:
        d = _row_payload(r)
        year = _safe_int(d.get("year"))
        if year is not None:
            index[year] = _val(d.get(value_key))
    out: list[dict[str, Any]] = []
    for r in rows:
        d = _row_payload(r)
        raw_year = d.get("year")
        year = _safe_int(raw_year)
        if year is None:
            d[out_key] = None
        else:
            prev = index.get(year - 1)
            cur = _val(d.get(value_key))
            if cur is not None and prev is not None and prev != 0.0:
                d[out_key] = ((cur - prev) / prev) * 100.0
            else:
                d[out_key] = None
        out.append({"data": d})
    return out


def cagr(start_value: float, end_value: float, years: int) -> float | None:
    """
    Calculate Compound Annual Growth Rate in percent.

    Formula: ((end_value / start_value)^(1/years) - 1) * 100

    Args:
        start_value: Initial value (must be positive)
        end_value: Final value (must be positive)
        years: Number of years (must be positive)

    Returns:
        CAGR as a percentage, or None for invalid inputs

    Examples:
        >>> cagr(100, 121, 2)
        10.0
    """
    if years <= 0 or start_value <= 0 or end_value <= 0:
        return None
    try:
        return float(((end_value / start_value) ** (1.0 / years) - 1.0) * 100.0)
    except Exception:
        return None
