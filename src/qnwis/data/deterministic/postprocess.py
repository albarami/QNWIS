"""
Postprocess pipeline executor for deterministic data layer.

Applies a sequence of transforms to query results without side effects.
"""

from __future__ import annotations

from typing import Any

from ..transforms.catalog import get_transform, list_transforms
from .models import Row, TransformStep


def apply_postprocess(rows: list[Row], steps: list[TransformStep]) -> tuple[list[Row], list[str]]:
    """
    Apply transform pipeline to query result rows.

    Converts Row objects to plain dicts, applies each transform in sequence,
    then converts back to Row objects. Returns the transformed rows along with
    the ordered list of transform names that were executed.

    Args:
        rows: Query result rows
        steps: Ordered list of transform steps to apply

    Returns:
        Tuple of (transformed rows wrapped in Row objects, transform trace)

    Raises:
        ValueError: If a transform name is not registered in the catalog
        TypeError: If a transform returns unexpected data
    """
    if not steps:
        return [Row(data=dict(r.data)) for r in rows], []

    # Convert to plain dicts for transforms
    data_rows: list[dict[str, Any]] = [dict(r.data) for r in rows]
    trace: list[str] = []

    # Apply each transform in sequence
    for index, step in enumerate(steps, start=1):
        try:
            fn = get_transform(step.name)
        except KeyError as exc:
            available = ", ".join(list_transforms())
            raise ValueError(
                f"Unknown transform step '{step.name}' at position {index}. "
                f"Available transforms: {available}"
            ) from exc

        params: dict[str, Any] = step.params or {}
        data_rows = fn(data_rows, **params)
        if not isinstance(data_rows, list):
            raise TypeError(
                f"Transform '{step.name}' returned {type(data_rows).__name__}; expected list of dict rows."
            )
        trace.append(step.name)

    # Convert back to Row objects
    transformed_rows = [Row(data=dict(d)) for d in data_rows]
    return transformed_rows, trace
