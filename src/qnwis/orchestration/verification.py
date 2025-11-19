"""
Numeric verification harness for agent outputs.

Provides deterministic validation of metrics against sane bounds:
- Percent values in [0, 100]
- Year-over-year growth in [-100, 200]
- Sum-to-one constraints for related percentages
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

from ..agents.base import AgentReport, Insight

SUM_TOL = 0.5  # align with number verifier tolerance


@dataclass
class VerificationIssue:
    """
    A single validation issue discovered during verification.

    Attributes:
        level: Severity level ("warn" or "error")
        code: Issue type code (e.g., "percent_range", "sum_to_one")
        detail: Human-readable description of the issue
    """

    level: str  # "warn" | "error"
    code: str  # e.g., "percent_range", "sum_to_one"
    detail: str


@dataclass
class VerificationResult:
    """
    Result of verification run containing all discovered issues.

    Attributes:
        issues: List of VerificationIssue objects
    """

    issues: list[VerificationIssue]


def _is_num(x: Any) -> bool:
    """Check if value is numeric (int or float)."""
    return isinstance(x, (int, float))


def _check_percent_bounds(metrics: dict[str, Any]) -> list[VerificationIssue]:
    """
    Verify that percent values are within [0, 100] range.

    Args:
        metrics: Dictionary of metric key-value pairs

    Returns:
        List of VerificationIssue for out-of-bounds percentages
    """
    out: list[VerificationIssue] = []
    for k, v in metrics.items():
        # Skip yoy_percent - it has its own check with wider bounds
        if k.endswith("_percent") and k != "yoy_percent" and _is_num(v) and (v < 0.0 or v > 100.0):
            out.append(VerificationIssue("warn", "percent_range", f"{k}={v}"))
    return out


def _check_yoy(metrics: dict[str, Any]) -> list[VerificationIssue]:
    """
    Verify year-over-year growth is within sane bounds.

    Args:
        metrics: Dictionary of metric key-value pairs

    Returns:
        List of VerificationIssue for extreme YoY values
    """
    out: list[VerificationIssue] = []
    v = metrics.get("yoy_percent")
    if not _is_num(v):
        return out
    # v is now known to be float
    v_float = cast(float, v)
    if v_float < -100.0 or v_float > 200.0:  # wide but finite bound
        out.append(VerificationIssue("warn", "yoy_outlier", f"yoy_percent={v_float}"))
    return out


def _check_sum_to_one(metrics: dict[str, Any]) -> list[VerificationIssue]:
    """
    Verify that male + female percentages sum to total within tolerance.

    Args:
        metrics: Dictionary of metric key-value pairs

    Returns:
        List of VerificationIssue for sum violations
    """
    keys = [k for k in metrics if k in ("male_percent", "female_percent", "total_percent")]
    if not {"male_percent", "female_percent", "total_percent"}.issubset(set(keys)):
        return []
    male = metrics.get("male_percent")
    female = metrics.get("female_percent")
    total = metrics.get("total_percent")
    if not all(_is_num(x) for x in (male, female, total)):
        return []
    # All three are now known to be float
    assert isinstance(male, float) and isinstance(female, float) and isinstance(total, float)
    if abs((male + female) - total) > SUM_TOL:
        return [
            VerificationIssue("warn", "sum_to_one", f"male+female={male+female} vs total={total}")
        ]
    return []


def verify_insight(ins: Insight) -> VerificationResult:
    """
    Verify a single insight's metrics against numeric invariants.

    Args:
        ins: Insight object to verify

    Returns:
        VerificationResult with list of discovered issues
    """
    issues: list[VerificationIssue] = []
    # Handle both dict and dataclass Insight objects
    if isinstance(ins, dict):
        metrics = ins.get('metrics') or {}
    else:
        metrics = ins.metrics or {}
    issues += _check_percent_bounds(metrics)
    issues += _check_yoy(metrics)
    issues += _check_sum_to_one(metrics)
    return VerificationResult(issues=issues)


def verify_report(rep: AgentReport) -> VerificationResult:
    """
    Verify all insights in an agent report.

    Args:
        rep: AgentReport object to verify

    Returns:
        VerificationResult with aggregated issues from all insights
    """
    issues: list[VerificationIssue] = []
    # Handle both dict and dataclass AgentReport
    findings = rep.get("findings", []) if isinstance(rep, dict) else rep.findings
    for ins in findings:
        issues += verify_insight(ins).issues
    return VerificationResult(issues=issues)
