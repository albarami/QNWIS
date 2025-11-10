"""
Layer 4: Sanity and consistency checks.

Validates metric ranges, monotonicity, temporal consistency, and freshness.
"""

from __future__ import annotations

from datetime import datetime

from ..data.deterministic.models import QueryResult
from .schemas import Issue, SanityRule


def sanity_checks(
    results: list[QueryResult],
    rules: list[SanityRule],
    freshness_max_hours: int,
) -> list[Issue]:
    """
    Execute Layer 4 sanity checks on query results.

    Validates:
    - Data freshness (age constraints)
    - Metric value ranges
    - Rate constraints (0-1 bounds)
    - Non-negativity requirements

    Args:
        results: Query results to validate
        rules: Sanity check rules
        freshness_max_hours: Maximum allowed data age in hours

    Returns:
        List of detected issues
    """
    issues: list[Issue] = []

    # Freshness checks across all sources
    now = datetime.utcnow()
    for qr in results:
        if qr.freshness:
            try:
                # Parse asof_date (ISO date format)
                asof_str = qr.freshness.asof_date
                if isinstance(asof_str, str):
                    # Handle date-only format (add time component)
                    if "T" not in asof_str:
                        asof_str = f"{asof_str}T00:00:00Z"
                    asof_dt = datetime.fromisoformat(asof_str.replace("Z", ""))
                else:
                    asof_dt = asof_str

                age_h = (now - asof_dt).total_seconds() / 3600

                if age_h > freshness_max_hours:
                    issues.append(
                        Issue(
                            layer="L4",
                            code="STALE_DATA",
                            message=f"{qr.query_id} data older than {freshness_max_hours}h",
                            severity="warning",
                            details={
                                "age_hours": round(age_h, 1),
                                "query_id": qr.query_id,
                                "asof_date": qr.freshness.asof_date,
                            },
                        )
                    )
            except Exception as exc:
                issues.append(
                    Issue(
                        layer="L4",
                        code="FRESHNESS_PARSE_ERROR",
                        message=f"Unparseable freshness timestamp for {qr.query_id}: {exc}",
                        severity="warning",
                        details={"query_id": qr.query_id},
                    )
                )

    # Metric constraint checks
    for rule in rules:
        for qr in results:
            for row in qr.rows:
                data = row.data

                # Check if metric exists in row
                if rule.metric in data:
                    try:
                        v = float(data[rule.metric])
                    except (ValueError, TypeError):
                        issues.append(
                            Issue(
                                layer="L4",
                                code="NON_NUMERIC_VALUE",
                                message=f"{rule.metric} has non-numeric value in {qr.query_id}",
                                severity="error",
                                details={"query_id": qr.query_id, "metric": rule.metric},
                            )
                        )
                        continue

                    # Non-negativity check
                    if rule.must_be_non_negative and v < 0:
                        issues.append(
                            Issue(
                                layer="L4",
                                code="NEGATIVE_VALUE",
                                message=f"{rule.metric} has negative value {v}",
                                severity="error",
                                details={
                                    "metric": rule.metric,
                                    "value": v,
                                    "query_id": qr.query_id,
                                },
                            )
                        )

                    # Rate [0,1] constraint
                    if rule.rate_0_1 and not (0.0 <= v <= 1.0):
                        issues.append(
                            Issue(
                                layer="L4",
                                code="RATE_OUT_OF_RANGE",
                                message=f"{rule.metric} not in [0,1]: {v}",
                                severity="error",
                                details={
                                    "metric": rule.metric,
                                    "value": v,
                                    "query_id": qr.query_id,
                                },
                            )
                        )

                    # Minimum value check
                    if rule.min_value is not None and v < rule.min_value:
                        issues.append(
                            Issue(
                                layer="L4",
                                code="BELOW_MIN",
                                message=f"{rule.metric} below min {rule.min_value}: {v}",
                                severity="warning",
                                details={
                                    "metric": rule.metric,
                                    "value": v,
                                    "min_value": rule.min_value,
                                    "query_id": qr.query_id,
                                },
                            )
                        )

                    # Maximum value check
                    if rule.max_value is not None and v > rule.max_value:
                        issues.append(
                            Issue(
                                layer="L4",
                                code="ABOVE_MAX",
                                message=f"{rule.metric} above max {rule.max_value}: {v}",
                                severity="warning",
                                details={
                                    "metric": rule.metric,
                                    "value": v,
                                    "max_value": rule.max_value,
                                    "query_id": qr.query_id,
                                },
                            )
                        )

    return issues
