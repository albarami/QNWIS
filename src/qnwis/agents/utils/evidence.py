"""
Formatting helpers for evidence tables included in agent outputs.

The deterministic layer stores evidence tables as lists of dictionaries;
these utilities ensure they are truncated predictably and maintain a fixed
column order so tests remain stable.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any


def format_evidence_table(
    rows: list[dict[str, Any]],
    *,
    max_rows: int = 10,
    column_order: Sequence[str] | None = None,
) -> list[dict[str, Any]]:
    """
    Return a truncated, deterministic copy of an evidence table.

    Args:
        rows: Source rows to format.
        max_rows: Maximum number of rows to retain before truncating (default 10).
        column_order: Optional explicit column ordering. When omitted the order
            follows the first-seen key order across all rows.

    Returns:
        New list of dictionaries containing at most max_rows entries plus an
        ellipsis row when truncation occurs. All dictionaries share the same
        key ordering to keep downstream rendering stable.
    """
    if not rows:
        return []

    if max_rows <= 0:
        raise ValueError("max_rows must be a positive integer.")

    columns: list[str] = list(column_order) if column_order is not None else []
    if not columns:
        seen: set[str] = set()
        for row in rows:
            for key in row:
                if key not in seen:
                    columns.append(key)
                    seen.add(key)

    formatted: list[dict[str, Any]] = []
    for row in rows[:max_rows]:
        formatted.append({column: row.get(column) for column in columns})

    remaining = len(rows) - max_rows
    if remaining > 0:
        ellipsis_row = dict.fromkeys(columns, "")
        primary_column = columns[0]
        ellipsis_row[primary_column] = f"... and {remaining} more"
        formatted.append(ellipsis_row)

    return formatted
