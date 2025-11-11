from __future__ import annotations

from dataclasses import dataclass

from .burn import allowed_error_fraction
from .models import ErrorBudgetSnapshot, SLOTarget


def window_minutes(target: SLOTarget) -> int:
    """Return total minutes for the SLO evaluation window."""
    return int(target.window_days * 24 * 60)


def remaining_budget_minutes(target: SLOTarget, window_error_fraction_so_far: float) -> float:
    """Compute remaining error budget minutes for the current window.

    Args:
        target: SLO target
        window_error_fraction_so_far: Fraction of bad events across the SLO window [0,1]

    Returns:
        Remaining minutes of error budget (>=0)
    """
    total_min = window_minutes(target)
    allowed_frac = allowed_error_fraction(target)
    consumed_min = max(0.0, min(1.0, window_error_fraction_so_far)) * total_min
    allowed_min = allowed_frac * total_min
    return max(0.0, allowed_min - consumed_min)


def remaining_budget_pct(target: SLOTarget, window_error_fraction_so_far: float) -> float:
    """Compute remaining error budget percentage [0,100]."""
    allowed_frac = allowed_error_fraction(target)
    if allowed_frac <= 0.0:
        return 0.0
    consumed_over_budget = max(0.0, min(1.0, window_error_fraction_so_far / allowed_frac))
    return max(0.0, 100.0 * (1.0 - consumed_over_budget))


@dataclass(frozen=True)
class WindowCounts:
    """Aggregated event counts for a time window."""

    bad: int
    total: int


def snapshot_budget(
    target: SLOTarget,
    fast_counts: WindowCounts,
    slow_counts: WindowCounts,
    window_error_fraction_so_far: float,
) -> ErrorBudgetSnapshot:
    """Build an ErrorBudgetSnapshot using window counts and SLO target.

    Args:
        target: SLO target configuration
        fast_counts: Counts in fast window (e.g., 5m)
        slow_counts: Counts in slow window (e.g., 60m)
        window_error_fraction_so_far: Error fraction across the entire SLO window

    Returns:
        ErrorBudgetSnapshot with remaining percent, minutes left and burn rates
    """
    from .burn import burn_rate_from_counts

    remaining_min = remaining_budget_minutes(target, window_error_fraction_so_far)
    remaining_pct = remaining_budget_pct(target, window_error_fraction_so_far)

    burn_fast = burn_rate_from_counts(target, fast_counts.bad, fast_counts.total)
    burn_slow = burn_rate_from_counts(target, slow_counts.bad, slow_counts.total)

    return ErrorBudgetSnapshot(
        remaining_pct=round(remaining_pct, 6),
        minutes_left=round(float(remaining_min), 6),
        burn_fast=round(float(burn_fast), 6),
        burn_slow=round(float(burn_slow), 6),
    )
