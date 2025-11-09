"""
Scenario Application - Pure deterministic transforms for forecast adjustments.

Provides functions to apply scenario specifications to baseline forecasts,
producing derived QueryResults with full provenance tracking.
"""

from __future__ import annotations

import logging
import math
from typing import Any

from ..agents.utils.derived_results import make_derived_query_result
from ..data.deterministic.models import QueryResult
from .dsl import ScenarioSpec, Transform

logger = logging.getLogger(__name__)


def apply_additive(values: list[float], shift: float, start: int, end: int | None) -> list[float]:
    """
    Apply additive shift to values in specified range.

    Args:
        values: Input time series
        shift: Amount to add
        start: Start index (inclusive)
        end: End index (inclusive, None for all remaining)

    Returns:
        New list with additive shift applied
    """
    result = values[:]
    end_idx = len(values) if end is None else min(end + 1, len(values))

    for i in range(start, end_idx):
        if i < len(result):
            result[i] = result[i] + shift

    return result


def apply_multiplicative(
    values: list[float], rate: float, start: int, end: int | None
) -> list[float]:
    """
    Apply multiplicative growth rate to values in specified range.

    Args:
        values: Input time series
        rate: Growth rate (e.g., 0.10 for 10% increase)
        start: Start index (inclusive)
        end: End index (inclusive, None for all remaining)

    Returns:
        New list with multiplicative adjustment applied
    """
    result = values[:]
    end_idx = len(values) if end is None else min(end + 1, len(values))

    for i in range(start, end_idx):
        if i < len(result):
            result[i] = result[i] * (1.0 + rate)

    return result


def apply_growth_override(
    values: list[float], target_rate: float, start: int, end: int | None
) -> list[float]:
    """
    Override growth trajectory with fixed monthly rate.

    Args:
        values: Input time series
        target_rate: Target monthly growth rate
        start: Start index (inclusive)
        end: End index (inclusive, None for all remaining)

    Returns:
        New list with overridden growth trajectory
    """
    result = values[:]
    end_idx = len(values) if end is None else min(end + 1, len(values))

    if start >= len(result):
        return result

    # Use value at start-1 as base, or start value if at beginning
    base_value = result[start - 1] if start > 0 else result[start]

    for i in range(start, end_idx):
        if i < len(result):
            months_from_start = i - start
            result[i] = base_value * ((1.0 + target_rate) ** months_from_start)

    return result


def apply_clamp(values: list[float], min_val: float | None, max_val: float | None) -> list[float]:
    """
    Clamp values to specified range.

    Args:
        values: Input time series
        min_val: Minimum allowed value (None for no floor)
        max_val: Maximum allowed value (None for no ceiling)

    Returns:
        New list with clamped values
    """
    result = values[:]

    for i in range(len(result)):
        if min_val is not None and result[i] < min_val:
            result[i] = min_val
        if max_val is not None and result[i] > max_val:
            result[i] = max_val

    return result


def apply_transform(values: list[float], transform: Transform) -> list[float]:
    """
    Apply a single transform to a time series.

    Args:
        values: Input time series
        transform: Transform specification

    Returns:
        Transformed time series

    Raises:
        ValueError: If transform type is unknown
    """
    if transform.type == "additive":
        return apply_additive(
            values, transform.value, transform.start_month, transform.end_month
        )
    elif transform.type == "multiplicative":
        return apply_multiplicative(
            values, transform.value, transform.start_month, transform.end_month
        )
    elif transform.type == "growth_override":
        return apply_growth_override(
            values, transform.value, transform.start_month, transform.end_month
        )
    elif transform.type == "clamp":
        return apply_clamp(values, transform.value, None)
    else:
        raise ValueError(f"Unknown transform type: {transform.type}")


def apply_scenario(
    baseline: QueryResult,
    spec: ScenarioSpec,
    date_labels: list[str] | None = None,
) -> QueryResult:
    """
    Apply scenario specification to baseline forecast.

    This function applies transforms sequentially and wraps the result in a
    derived QueryResult with full provenance. All operations are deterministic
    and preserve row count.

    Args:
        baseline: Baseline forecast QueryResult
        spec: Scenario specification
        date_labels: Optional date labels for output rows (e.g., ["2024-01", "2024-02"])

    Returns:
        Derived QueryResult with scenario-adjusted forecast

    Raises:
        ValueError: If baseline data is invalid or insufficient

    Examples:
        >>> baseline_qr = QueryResult(...)  # From forecast agent
        >>> spec = ScenarioSpec(
        ...     name="Optimistic",
        ...     description="10% improvement",
        ...     metric="retention",
        ...     sector="Construction",
        ...     horizon_months=12,
        ...     transforms=[
        ...         Transform(type="multiplicative", value=0.10, start_month=0)
        ...     ]
        ... )
        >>> adjusted_qr = apply_scenario(baseline_qr, spec)
    """
    # Extract values from baseline
    if not baseline.rows:
        raise ValueError("Baseline forecast has no rows")

    # Try to extract 'yhat' or 'value' field
    value_field = None
    for field_name in ["yhat", "value", "forecast"]:
        if field_name in baseline.rows[0].data:
            value_field = field_name
            break

    if value_field is None:
        raise ValueError(
            "Baseline must contain 'yhat', 'value', or 'forecast' field"
        )

    values: list[float] = []
    for row in baseline.rows:
        val = row.data.get(value_field)
        if val is None:
            raise ValueError(f"Missing {value_field} in row: {row.data}")
        try:
            num_val = float(val)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Invalid numeric value for {value_field}: {val}"
            ) from exc
        if not math.isfinite(num_val):
            raise ValueError(f"Non-finite value in baseline: {num_val}")
        values.append(num_val)

    # Validate horizon
    if len(values) > spec.horizon_months:
        logger.warning(
            "Baseline has %d points but scenario horizon is %d, truncating",
            len(values),
            spec.horizon_months,
        )
        values = values[: spec.horizon_months]
    elif len(values) < spec.horizon_months:
        logger.warning(
            "Baseline has %d points but scenario horizon is %d",
            len(values),
            spec.horizon_months,
        )

    # Apply transforms sequentially
    adjusted_values = values[:]
    for i, transform in enumerate(spec.transforms):
        logger.debug(
            "Applying transform %d/%d: type=%s value=%s",
            i + 1,
            len(spec.transforms),
            transform.type,
            transform.value,
        )
        adjusted_values = apply_transform(adjusted_values, transform)

    # Apply final clamping if specified
    if spec.clamp_min is not None or spec.clamp_max is not None:
        adjusted_values = apply_clamp(adjusted_values, spec.clamp_min, spec.clamp_max)

    # Build output rows
    output_rows: list[dict[str, Any]] = []
    for i, adj_val in enumerate(adjusted_values):
        row_data = {
            "h": i + 1,
            "baseline": values[i] if i < len(values) else None,
            "adjusted": adj_val,
            "delta": adj_val - values[i] if i < len(values) else None,
            "delta_pct": (
                ((adj_val - values[i]) / values[i] * 100.0)
                if i < len(values) and values[i] != 0
                else None
            ),
        }

        # Add date label if provided
        if date_labels and i < len(date_labels):
            row_data["period"] = date_labels[i]

        output_rows.append(row_data)

    # Create derived QueryResult
    derived_qr = make_derived_query_result(
        operation="scenario_application",
        params={
            "scenario_name": spec.name,
            "metric": spec.metric,
            "sector": spec.sector or "all",
            "horizon_months": spec.horizon_months,
            "transforms_count": len(spec.transforms),
        },
        rows=output_rows,
        sources=[baseline.query_id],
        freshness_like=[baseline.freshness],
        unit=baseline.unit,
    )

    logger.info(
        "Applied scenario '%s': %d transforms, %d output rows (QID=%s)",
        spec.name,
        len(spec.transforms),
        len(output_rows),
        derived_qr.query_id,
    )

    return derived_qr


def cascade_sector_to_national(
    sector_results: dict[str, QueryResult],
    weights: dict[str, float] | None = None,
) -> QueryResult:
    """
    Aggregate sector-level scenario results to national level.

    Uses weighted averaging where weights represent sector employment shares
    or other relevant proportions.

    Args:
        sector_results: Map of sector name to scenario-adjusted QueryResult
        weights: Optional sector weights (default: equal weighting)

    Returns:
        National-level derived QueryResult

    Raises:
        ValueError: If sector results are inconsistent or empty
    """
    if not sector_results:
        raise ValueError("No sector results provided for aggregation")

    # Determine common horizon
    horizons = [len(qr.rows) for qr in sector_results.values()]
    if len(set(horizons)) > 1:
        raise ValueError(
            f"Inconsistent horizons across sectors: {horizons}"
        )
    horizon = horizons[0]

    # Default to equal weights if not provided
    if weights is None:
        weights = {sector: 1.0 / len(sector_results) for sector in sector_results}

    # Normalize weights
    total_weight = sum(weights.values())
    if total_weight <= 0:
        raise ValueError(f"Total weight must be positive, got {total_weight}")
    normalized_weights = {s: w / total_weight for s, w in weights.items()}

    # Aggregate adjusted values
    national_rows: list[dict[str, Any]] = []
    for h in range(horizon):
        weighted_sum = 0.0
        for sector, qr in sector_results.items():
            if h >= len(qr.rows):
                continue
            adjusted_val = qr.rows[h].data.get("adjusted")
            if adjusted_val is None:
                continue
            try:
                val = float(adjusted_val)
            except (TypeError, ValueError):
                continue
            weighted_sum += val * normalized_weights.get(sector, 0.0)

        national_rows.append({
            "h": h + 1,
            "adjusted": weighted_sum,
        })

    # Collect source QIDs
    source_qids = [qr.query_id for qr in sector_results.values()]

    # Use first result for freshness reference
    first_qr = next(iter(sector_results.values()))

    # Create derived national result
    national_qr = make_derived_query_result(
        operation="national_aggregation",
        params={
            "sectors": list(sector_results.keys()),
            "aggregation_method": "weighted_average",
        },
        rows=national_rows,
        sources=source_qids,
        freshness_like=[first_qr.freshness],
        unit=first_qr.unit,
    )

    logger.info(
        "Cascaded %d sectors to national: %d rows (QID=%s)",
        len(sector_results),
        len(national_rows),
        national_qr.query_id,
    )

    return national_qr
