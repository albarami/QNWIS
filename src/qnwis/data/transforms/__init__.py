"""
Post-processing transforms for deterministic data layer.

Provides pure, composable transforms that operate on list[dict] rows.
All transforms are deterministic with no side effects.
"""

from .base import (
    filter_equals,
    rename_columns,
    rolling_avg,
    select,
    share_of_total,
    to_percent,
    top_n,
    yoy,
)
from .catalog import CATALOG, get_transform, list_transforms

__all__ = [
    "select",
    "filter_equals",
    "rename_columns",
    "to_percent",
    "top_n",
    "share_of_total",
    "yoy",
    "rolling_avg",
    "CATALOG",
    "get_transform",
    "list_transforms",
]
