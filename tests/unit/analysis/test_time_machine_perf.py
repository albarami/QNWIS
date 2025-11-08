"""
Micro-benchmark to ensure Step 23 math stays fast on 8-year monthly series.
"""

from __future__ import annotations

import time

from src.qnwis.analysis.baselines import seasonal_baseline
from src.qnwis.analysis.change_points import cusum_breaks
from src.qnwis.analysis.trend_utils import ewma, qtq, yoy


def test_time_machine_core_math_under_50ms():
    """Core seasonal/trend/break computations must stay under 50 ms."""
    months = 8 * 12
    series = [
        100 + (i * 0.4) + 3 * ((i % 12) - 6) for i in range(months)
    ]  # slow trend plus seasonal wiggle

    start = time.perf_counter()
    seasonal_baseline(series, season=12)
    yoy(series, period=12)
    qtq(series, period=3)
    ewma(series, alpha=0.3)
    cusum_breaks(series, k=1.0, h=5.0)
    duration_ms = (time.perf_counter() - start) * 1000

    assert duration_ms < 50, f"Core computations exceeded 50 ms ({duration_ms:.2f} ms)"
