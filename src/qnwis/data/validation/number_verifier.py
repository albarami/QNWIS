from __future__ import annotations

from ..deterministic.models import QueryResult, QuerySpec

SUM_PERCENT_TOLERANCE = 0.5


def verify_result(spec: QuerySpec, res: QueryResult) -> list[str]:
    """Derive deterministic data quality warnings for a query result."""
    warnings: list[str] = []
    if spec.expected_unit != "unknown" and res.unit != spec.expected_unit:
        warnings.append(f"unit_mismatch:{res.unit}!={spec.expected_unit}")

    if spec.constraints.get("sum_to_one"):
        total = 0.0
        for row in res.rows:
            for key, value in row.data.items():
                if isinstance(value, (int, float)) and key.lower().endswith(
                    ("%", "percent", "pct")
                ):
                    total += float(value)
        if abs(total - 100.0) > SUM_PERCENT_TOLERANCE:
            warnings.append(f"sum_to_one_violation:{total}")

    return warnings
