from __future__ import annotations

from ..deterministic.models import QueryResult, QuerySpec

SUM_PERCENT_TOLERANCE = 0.5


def verify_result(spec: QuerySpec, res: QueryResult) -> list[str]:
    """Derive deterministic data quality warnings for a query result."""
    warnings: list[str] = []
    if spec.expected_unit != "unknown" and res.unit != spec.expected_unit:
        warnings.append(f"unit_mismatch:{res.unit}!={spec.expected_unit}")

    if spec.constraints.get("sum_to_one"):
        # Check that male + female ~= total within tolerance
        # DO NOT sum all percent columns (that would include total itself)
        for row in res.rows:
            male = row.data.get("male_percent") or row.data.get("male")
            female = row.data.get("female_percent") or row.data.get("female")
            total_val = row.data.get("total_percent") or row.data.get("total")
            
            if all(isinstance(v, (int, float)) for v in [male, female, total_val]):
                computed_total = float(male) + float(female)  # type: ignore
                delta = abs(computed_total - float(total_val))  # type: ignore
                if delta > SUM_PERCENT_TOLERANCE:
                    warnings.append(
                        f"sum_to_one_violation:male({male})+female({female})={computed_total:.2f} vs total={total_val} (delta={delta:.2f})"
                    )

    return warnings
