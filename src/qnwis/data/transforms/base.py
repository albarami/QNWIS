"""
Pure transform functions for post-processing query results.

All functions operate on List[Dict[str, Any]] and return modified copies.
No side effects, no I/O, deterministic behavior only.
"""

from __future__ import annotations

from collections import defaultdict
from statistics import mean
from typing import Any


def select(rows: list[dict[str, Any]], columns: list[str]) -> list[dict[str, Any]]:
    """
    Select subset of columns from each row.

    Args:
        rows: Input rows
        columns: List of column names to keep

    Returns:
        Rows with only specified columns (missing columns become None)
    """
    return [{k: r.get(k) for k in columns} for r in rows]


def filter_equals(
    rows: list[dict[str, Any]], where: dict[str, Any]
) -> list[dict[str, Any]]:
    """
    Filter rows where all specified columns equal given values.

    Args:
        rows: Input rows
        where: Dictionary of column_name -> expected_value

    Returns:
        Rows matching all conditions
    """

    def matches(r: dict[str, Any]) -> bool:
        return all(r.get(k) == v for k, v in where.items())

    return [r for r in rows if matches(r)]


def rename_columns(
    rows: list[dict[str, Any]], mapping: dict[str, str]
) -> list[dict[str, Any]]:
    """
    Rename columns according to mapping.

    Args:
        rows: Input rows
        mapping: Dictionary of old_name -> new_name

    Returns:
        Rows with renamed columns (unmapped columns keep original names)
    """
    return [{mapping.get(k, k): v for k, v in r.items()} for r in rows]


def to_percent(
    rows: list[dict[str, Any]],
    columns: list[str],
    scale: float = 100.0,
) -> list[dict[str, Any]]:
    """
    Convert numeric columns to percentages by multiplying by scale.

    Args:
        rows: Input rows
        columns: Column names to convert
        scale: Multiplier (default 100.0)

    Returns:
        Rows with scaled numeric values in specified columns
    """
    out = []
    for r in rows:
        rr = dict(r)
        for c in columns:
            v = rr.get(c)
            if isinstance(v, (int, float)):
                rr[c] = float(v) * scale
        out.append(rr)
    return out


def top_n(
    rows: list[dict[str, Any]],
    sort_key: str,
    n: int,
    descending: bool = True,
) -> list[dict[str, Any]]:
    """
    Return top N rows sorted by specified key.

    Args:
        rows: Input rows
        sort_key: Column name to sort by
        n: Number of rows to return
        descending: Sort descending (default True)

    Returns:
        Up to N rows in sorted order
    """
    try:
        limit = int(n)
    except (TypeError, ValueError) as exc:
        raise TypeError("top_n parameter 'n' must be an integer") from exc

    limit = max(0, limit)
    order_descending = True if descending is None else bool(descending)

    def sort_key_func(r: dict[str, Any]) -> tuple[int, Any]:
        """Sort key that handles None values."""
        val = r.get(sort_key, 0)
        # Put None values at the end regardless of sort direction
        if val is None:
            return (1, 0)
        return (0, val)

    return sorted(
        rows,
        key=sort_key_func,
        reverse=order_descending,
    )[:limit]


def share_of_total(
    rows: list[dict[str, Any]],
    group_keys: list[str],
    value_key: str,
    out_key: str = "share_percent",
) -> list[dict[str, Any]]:
    """
    Compute share of total within groups as percentage.

    Groups rows by group_keys and computes 100 * value / sum(value in group).

    Args:
        rows: Input rows
        group_keys: Columns defining groups
        value_key: Numeric column to compute share of
        out_key: Output column name (default "share_percent")

    Returns:
        Rows with added share_percent column
    """
    # Compute group totals
    groups: dict[tuple[Any, ...], float] = defaultdict(float)
    for r in rows:
        if isinstance(r.get(value_key), (int, float)):
            g = tuple(r.get(k) for k in group_keys)
            groups[g] += float(r[value_key])

    # Compute shares
    out = []
    for r in rows:
        g = tuple(r.get(k) for k in group_keys)
        denom = groups.get(g, 0.0)
        rr = dict(r)
        if denom == 0.0:
            rr[out_key] = 0.0
        else:
            rr[out_key] = 100.0 * float(r.get(value_key, 0.0)) / denom
        out.append(rr)
    return out


def yoy(
    rows: list[dict[str, Any]],
    key: str,
    sort_keys: list[str],
    out_key: str = "yoy_percent",
) -> list[dict[str, Any]]:
    """
    Compute year-over-year percentage change.

    Sorts rows by sort_keys and computes (current - previous) / previous * 100.
    First row gets None for YoY.

    Args:
        rows: Input rows
        key: Numeric column to compute YoY for
        sort_keys: Columns to sort by (typically ["year"])
        out_key: Output column name (default "yoy_percent")

    Returns:
        Rows with added yoy_percent column
    """
    out = []
    prev = None

    for r in sorted(rows, key=lambda d: tuple(d.get(k) for k in sort_keys)):
        rr = dict(r)
        v = rr.get(key)

        if (
            prev is None
            or not isinstance(prev, (int, float))
            or not isinstance(v, (int, float))
            or prev == 0
        ):
            rr[out_key] = None
        else:
            rr[out_key] = round((float(v) - float(prev)) / float(prev) * 100.0, 2)

        out.append(rr)
        prev = v if isinstance(v, (int, float)) else None

    return out


def rolling_avg(
    rows: list[dict[str, Any]],
    key: str,
    sort_keys: list[str],
    window: int = 3,
    out_key: str = "rolling_avg",
) -> list[dict[str, Any]]:
    """
    Compute rolling average over specified window.

    Sorts rows by sort_keys and computes mean of last N values.
    Returns None until window is filled.

    Args:
        rows: Input rows
        key: Numeric column to average
        sort_keys: Columns to sort by
        window: Window size (default 3)
        out_key: Output column name (default "rolling_avg")

    Returns:
        Rows with added rolling_avg column
    """
    out = []
    buf: list[float] = []

    for r in sorted(rows, key=lambda d: tuple(d.get(k) for k in sort_keys)):
        rr = dict(r)
        v = r.get(key)

        if isinstance(v, (int, float)):
            buf.append(float(v))

        if len(buf) > max(1, window):
            buf.pop(0)

        rr[out_key] = None if len(buf) < window else round(mean(buf), 2)
        out.append(rr)

    return out
