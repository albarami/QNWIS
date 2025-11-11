from __future__ import annotations

from dataclasses import dataclass

from .models import SLIKind, SLOTarget


def allowed_error_fraction(target: SLOTarget) -> float:
    if target.sli == SLIKind.AVAILABILITY_PCT:
        return max(0.0, (100.0 - target.objective) / 100.0)
    if target.sli == SLIKind.ERROR_RATE_PCT:
        return max(0.0, target.objective / 100.0)
    if target.sli == SLIKind.LATENCY_MS_P95:
        return 0.05
    return 0.0


def error_rate(bad: int, total: int) -> float:
    if total <= 0:
        return 0.0
    if bad <= 0:
        return 0.0
    br = bad / float(total)
    return max(0.0, min(1.0, br))


def burn_rate_from_counts(target: SLOTarget, bad: int, total: int) -> float:
    budget = allowed_error_fraction(target)
    if budget <= 0.0:
        return 0.0
    return error_rate(bad, total) / budget


@dataclass(frozen=True)
class BurnRates:
    fast: float
    slow: float


def multi_window_burn(
    target: SLOTarget,
    fast_bad: int,
    fast_total: int,
    slow_bad: int,
    slow_total: int,
) -> BurnRates:
    fast = burn_rate_from_counts(target, fast_bad, fast_total)
    slow = burn_rate_from_counts(target, slow_bad, slow_total)
    return BurnRates(fast=fast, slow=slow)
