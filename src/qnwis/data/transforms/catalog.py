"""
Transform catalog registry.

Maps transform names to callable functions for dynamic lookup.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from . import base

# Registry of all available transforms
CATALOG: dict[str, Callable[..., list[dict[str, Any]]]] = {
    "select": base.select,
    "filter_equals": base.filter_equals,
    "rename_columns": base.rename_columns,
    "to_percent": base.to_percent,
    "top_n": base.top_n,
    "share_of_total": base.share_of_total,
    "yoy": base.yoy,
    "rolling_avg": base.rolling_avg,
}


def get_transform(name: str) -> Callable[..., list[dict[str, Any]]]:
    """
    Get transform function by name.

    Args:
        name: Transform name (must exist in CATALOG)

    Returns:
        Transform function

    Raises:
        KeyError: If transform name not found
    """
    fn = CATALOG.get(name)
    if not fn:
        raise KeyError(f"Unknown transform: {name}")
    return fn


def list_transforms() -> tuple[str, ...]:
    """
    Return available transform names in sorted order.
    """
    return tuple(sorted(CATALOG))
