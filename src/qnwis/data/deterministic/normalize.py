"""
Deterministic normalization utilities for query parameters and result rows.

This module provides transformation functions that enforce deterministic
behavior for column naming, parameter coercion, and row structure.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from contextlib import suppress
from typing import Any

from .models import Row

_SNAKE_RE = re.compile(r"[^0-9a-zA-Z]+")


def to_snake_case(name: str) -> str:
    """
    Convert arbitrary column name to lower snake_case deterministically.

    Args:
        name: Column name to convert

    Returns:
        Lowercase snake_case version of the input

    Examples:
        >>> to_snake_case("Male Percent")
        'male_percent'
        >>> to_snake_case("GDP(QAR)")
        'gdp_qar'
    """
    s = _SNAKE_RE.sub("_", name).strip("_")
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s).lower()


def normalize_params(params: dict[str, Any]) -> dict[str, Any]:
    """
    Deterministically normalize known query parameters.

    Applies the following transformations:
    - Coerces 'year' to int if numeric string
    - Coerces 'timeout_s' and 'max_rows' to int if string
    - Ensures 'to_percent' is a list[str] if present
    - Leaves unknown keys untouched

    Args:
        params: Raw parameter dictionary

    Returns:
        Normalized parameter dictionary
    """
    out: dict[str, Any] = dict(params)
    if "year" in out:
        with suppress(Exception):
            out["year"] = int(float(str(out["year"]).strip()))
    for k in ("timeout_s", "max_rows"):
        if k in out:
            with suppress(Exception):
                out[k] = int(float(str(out[k]).strip()))
    if "to_percent" in out and not isinstance(out["to_percent"], list):
        out["to_percent"] = [str(out["to_percent"])]
    return out


def _extract_row_payload(row: Any) -> Mapping[str, Any] | None:
    """Return the underlying data mapping for a heterogeneous row input."""
    if isinstance(row, Row):
        return row.data
    if isinstance(row, Mapping):
        data = row.get("data")
        if isinstance(data, Mapping):
            return data
        if "data" in row:
            return {}  # Malformed shape; return empty payload instead of raising.
        return row
    return None


def normalize_rows(rows: Sequence[Any]) -> list[dict[str, Any]]:
    """
    Normalize row keys to snake_case and ensure consistent structure.

    Transforms all column names to lowercase snake_case, trims string values,
    and ensures uniform output format: [{'data': {...}}]. Accepts mixed inputs
    (Row models, mappings with or without the 'data' wrapper) and is idempotent.

    Args:
        rows: Iterable of row-like objects (Row, Mapping, or dict)

    Returns:
        Normalized rows in consistent format [{'data': {...}}]
    """
    norm: list[dict[str, Any]] = []
    for row in rows:
        payload = _extract_row_payload(row) or {}
        normalized_data: dict[str, Any] = {}
        for key, value in payload.items():
            norm_key = to_snake_case(key) if isinstance(key, str) else key
            if isinstance(value, str):
                value = value.strip()
            normalized_data[norm_key] = value
        norm.append({"data": normalized_data})
    return norm
