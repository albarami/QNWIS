"""Reusable numeric validation rules for cross-source verification."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

SUM_TOL = 0.5  # percent tolerance (align with deterministic number verifier)
YOY_MIN = -100.0  # %
YOY_MAX = 200.0  # %
PCT_MIN = 0.0
PCT_MAX = 100.0


@dataclass
class RuleIssue:
    """A single validation issue found by a rule."""

    code: str  # e.g. "sum_to_one", "percent_bounds", "yoy_outlier"
    detail: str  # human-readable explanation
    severity: str  # "warn" | "error"


def check_percent_bounds(key: str, value: Any) -> list[RuleIssue]:
    """
    If metric key ends with '_percent' ensure the value lies within [0, 100].

    Args:
        key: Metric key name.
        value: Metric value.

    Returns:
        List of RuleIssue if bounds violated, else empty list.
    """
    issues: list[RuleIssue] = []
    if (
        key.endswith("_percent")
        and isinstance(value, (int, float))
        and (value < PCT_MIN or value > PCT_MAX)
    ):
        issues.append(RuleIssue("percent_bounds", f"{key}={value}", "warn"))
    return issues


def check_sum_to_one(
    male: float | None,
    female: float | None,
    total: float | None,
) -> list[RuleIssue]:
    """
    Validate that male + female ~= total within tolerance.

    Args:
        male: Male percentage value.
        female: Female percentage value.
        total: Total percentage value.

    Returns:
        List of RuleIssue if sum check fails, else empty list.
    """
    if None in (male, female, total):
        return []
    assert male is not None and female is not None and total is not None
    delta = (male + female) - total
    if abs(delta) > SUM_TOL:
        return [
            RuleIssue(
                "sum_to_one",
                f"male+female={male + female:.3f} vs total={total:.3f} (delta={delta:.3f})",
                "warn",
            )
        ]
    return []


def check_yoy_bounds(yoy: float | None) -> list[RuleIssue]:
    """
    Validate year-over-year growth is within reasonable bounds.

    Args:
        yoy: Year-over-year percentage change.

    Returns:
        List of RuleIssue if outlier detected, else empty list.
    """
    if yoy is None:
        return []
    if yoy < YOY_MIN or yoy > YOY_MAX:
        return [RuleIssue("yoy_outlier", f"yoy_percent={yoy}", "warn")]
    return []


def check_qatarization_formula(
    qataris: float | None,
    non_qataris: float | None,
    pct: float | None,
) -> list[RuleIssue]:
    """
    Validate pct ~= 100*qataris/(qataris+non_qataris) within tolerance.

    Args:
        qataris: Count of Qatari employees.
        non_qataris: Count of non-Qatari employees.
        pct: Reported Qatarization percentage.

    Returns:
        List of RuleIssue if formula check fails, else empty list.
    """
    if None in (qataris, non_qataris, pct):
        return []
    assert qataris is not None and non_qataris is not None and pct is not None
    denominator = qataris + non_qataris
    if denominator <= 0:
        return []
    expected = 100.0 * qataris / denominator
    delta = abs(expected - pct)
    if delta > SUM_TOL:
        return [
            RuleIssue(
                "qatarization_mismatch",
                f"expected={expected:.2f}, pct={pct:.2f}, delta={delta:.2f}",
                "warn",
            )
        ]
    return []


def check_ewi_vs_yoy_sign(
    ewi_drop_pct: float | None,
    yoy_pct: float | None,
) -> list[RuleIssue]:
    """
    Flag cases where a high EWI drop conflicts with positive YoY employment.

    Args:
        ewi_drop_pct: EWI employment drop percentage.
        yoy_pct: Year-over-year employment change percentage.

    Returns:
        List of RuleIssue if incoherence detected, else empty list.
    """
    if ewi_drop_pct is None or yoy_pct is None:
        return []
    if ewi_drop_pct > 3.0 and yoy_pct > 0.0:
        return [
            RuleIssue(
                "ewi_incoherence",
                f"ewi_drop={ewi_drop_pct} but yoy={yoy_pct} (>0)",
                "warn",
            )
        ]
    return []
