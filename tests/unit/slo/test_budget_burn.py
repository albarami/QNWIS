from __future__ import annotations

import time

from src.qnwis.slo.budget import (
    WindowCounts,
    remaining_budget_minutes,
    remaining_budget_pct,
    snapshot_budget,
    window_minutes,
)
from src.qnwis.slo.burn import (
    allowed_error_fraction,
    burn_rate_from_counts,
    multi_window_burn,
)
from src.qnwis.slo.models import SLIKind, SLOTarget


def test_allowed_error_fraction_rules():
    avail = SLOTarget(objective=99.9, window_days=14, sli=SLIKind.AVAILABILITY_PCT)
    err = SLOTarget(objective=1.0, window_days=30, sli=SLIKind.ERROR_RATE_PCT)
    lat = SLOTarget(objective=200.0, window_days=7, sli=SLIKind.LATENCY_MS_P95)

    assert allowed_error_fraction(avail) == (100.0 - 99.9) / 100.0
    assert allowed_error_fraction(err) == 0.01
    assert allowed_error_fraction(lat) == 0.05


def test_burn_rate_and_budget_math():
    target = SLOTarget(objective=99.0, window_days=14, sli=SLIKind.AVAILABILITY_PCT)
    # 5xx / total
    fast = WindowCounts(bad=2, total=1000)
    slow = WindowCounts(bad=20, total=10000)
    burn_fast = burn_rate_from_counts(target, fast.bad, fast.total)
    burn_slow = burn_rate_from_counts(target, slow.bad, slow.total)
    assert 0.0 <= burn_fast <= 10.0
    assert 0.0 <= burn_slow <= 10.0

    # Window budget
    total_min = window_minutes(target)
    assert total_min == 14 * 24 * 60
    rem_min = remaining_budget_minutes(target, window_error_fraction_so_far=0.0001)
    rem_pct = remaining_budget_pct(target, window_error_fraction_so_far=0.0001)
    assert rem_min >= 0.0
    assert 0.0 <= rem_pct <= 100.0

    snap = snapshot_budget(target, fast, slow, 0.0001)
    assert snap.minutes_left >= 0.0
    assert snap.remaining_pct >= 0.0
    assert snap.burn_fast == round(burn_fast, 6)
    assert snap.burn_slow == round(burn_slow, 6)


def test_multi_window_burn():
    target = SLOTarget(objective=99.5, window_days=14, sli=SLIKind.AVAILABILITY_PCT)
    rates = multi_window_burn(target, fast_bad=5, fast_total=2000, slow_bad=50, slow_total=20000)
    assert rates.fast >= 0.0 and rates.slow >= 0.0


def test_budget_microbench_under_50ms():
    times = []
    for _ in range(100):
        target = SLOTarget(objective=99.9, window_days=14, sli=SLIKind.AVAILABILITY_PCT)
        start = time.perf_counter()
        snapshot_budget(target, WindowCounts(1, 1000), WindowCounts(10, 10000), 0.0001)
        times.append((time.perf_counter() - start) * 1000.0)
    times.sort()
    p95 = times[int(round(0.95 * (len(times) - 1)))] if times else 0.0
    assert p95 < 50.0, f"p95 exceeded: {p95:.2f}ms"
