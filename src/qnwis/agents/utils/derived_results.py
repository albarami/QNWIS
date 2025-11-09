"""
Utilities for wrapping computed/derived data into QueryResult format.

This ensures all agent outputs (even calculated statistics) can be verified
through the deterministic data layer verification system.
"""

from __future__ import annotations

import hashlib
import logging
from collections.abc import Mapping, Sequence
from datetime import date, datetime
from typing import Any

logger = logging.getLogger(__name__)

from ...data.deterministic.models import Freshness, Provenance, QueryResult, Row


def make_derived_query_result(
    operation: str,
    params: dict[str, Any],
    rows: list[dict[str, Any]],
    sources: list[str],
    freshness_like: (
        Freshness
        | Sequence[Freshness | datetime]
        | Mapping[str, datetime]
        | None
    ) = None,
    unit: str = "unknown",
) -> QueryResult:
    """
    Wrap computed/derived data into a verifiable QueryResult.

    Creates a stable query_id based on the operation and parameters, allowing
    the verification system to trace computed metrics back to their sources.

    Args:
        operation: Name of the computation (e.g., "pearson_correlation", "z_score_anomaly")
        params: Dictionary of parameters used in the computation
        rows: List of data rows (dicts) representing the computed results
        sources: List of source query_ids that were used in the computation
        freshness_like:
            Optional freshness inputs used to copy `asof_date`/`updated_at`.
            Accepts a single Freshness object, a sequence of Freshness/datetime
            objects, or a mapping of identifiers to datetimes.
        unit: Unit type for the result (default "unknown")

    Returns:
        QueryResult with stable query_id and full provenance

    Examples:
        >>> result = make_derived_query_result(
        ...     operation="correlation_analysis",
        ...     params={"method": "spearman", "sector": "Finance"},
        ...     rows=[{"variable_a": "retention", "variable_b": "salary", "correlation": 0.73}],
        ...     sources=["q_retention_by_sector", "q_salary_by_sector"],
        ... )
        >>> result.query_id
        'derived_correlation_analysis_...'
    """
    # Create stable query_id from operation and params
    param_str = "_".join(f"{k}={v}" for k, v in sorted(params.items()))
    composite = f"{operation}_{param_str}"

    # Use short hash to keep query_id manageable
    hash_suffix = hashlib.sha256(composite.encode("utf-8")).hexdigest()[:8]
    query_id = f"derived_{operation}_{hash_suffix}"

    # Build provenance documenting the computation
    source_desc = ", ".join(sources) if sources else "none"
    locator = f"computed from [{source_desc}] via {operation}"

    # Extract field names from first row if available
    fields = list(rows[0].keys()) if rows else []

    def _collect_freshness_inputs(
        freshness_input: (
            Freshness
            | Sequence[Freshness | datetime]
            | Mapping[str, datetime]
            | None
        )
    ) -> tuple[list[date], list[datetime]]:
        asof_dates: list[date] = []
        updated_at_values: list[datetime] = []

        def _add_datetime(value: datetime) -> None:
            asof_dates.append(value.date())
            updated_at_values.append(value)

        def _add_freshness(value: Freshness) -> None:
            try:
                asof_dates.append(date.fromisoformat(value.asof_date))
            except (TypeError, ValueError) as exc:
                logger.debug(
                    "Skipping invalid asof_date=%r in freshness: %s",
                    getattr(value, "asof_date", None),
                    exc,
                )
            if value.updated_at:
                try:
                    updated_at_values.append(datetime.fromisoformat(value.updated_at))
                except (TypeError, ValueError) as exc:
                    logger.debug(
                        "Skipping invalid updated_at=%r in freshness: %s",
                        getattr(value, "updated_at", None),
                        exc,
                    )

        if isinstance(freshness_input, Freshness):
            _add_freshness(freshness_input)
        elif isinstance(freshness_input, Mapping):
            for dt in freshness_input.values():
                if isinstance(dt, datetime):
                    _add_datetime(dt)
        elif isinstance(freshness_input, Sequence) and not isinstance(
            freshness_input, (str, bytes)
        ):
            for item in freshness_input:
                if isinstance(item, Freshness):
                    _add_freshness(item)
                elif isinstance(item, datetime):
                    _add_datetime(item)

        return asof_dates, updated_at_values

    asof_dates, updated_values = _collect_freshness_inputs(freshness_like)
    if asof_dates:
        asof_date = min(asof_dates).isoformat()
    else:
        asof_date = datetime.now().strftime("%Y-%m-%d")

    if updated_values:
        updated_at = max(updated_values).isoformat()
    else:
        updated_at = datetime.now().isoformat()

    return QueryResult(
        query_id=query_id,
        rows=[Row(data=row) for row in rows],
        unit=unit,  # type: ignore[arg-type]
        provenance=Provenance(
            source="csv",  # Mark as derived computation, not external source
            dataset_id=f"derived_{operation}",
            locator=locator,
            fields=fields,
            license="Computed from QNWIS deterministic layer",
        ),
        freshness=Freshness(
            asof_date=asof_date,
            updated_at=updated_at,
        ),
        metadata={
            "operation": operation,
            "params": params,
            "sources": list(sources),
            "row_count": len(rows),
        },
        warnings=[],
    )
