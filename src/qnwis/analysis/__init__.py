"""
Time-series analysis utilities for QNWIS.

This package provides pure-Python implementations of:
- Trend analysis (YoY, QtQ, EWMA, slopes)
- Seasonal baselines and anomaly detection
- Change-point detection (CUSUM, z-score)

All functions guard against edge cases (zeros, NaNs, small samples).
"""

from .baselines import (
    anomaly_gaps,
    detect_seasonal_anomalies,
    seasonal_baseline,
    summarize_baseline_fit,
    trend_adjusted_baseline,
)
from .change_points import (
    cusum_breaks,
    rolling_variance_breaks,
    summarize_breaks,
    zscore_outliers,
)
from .trend_utils import (
    ewma,
    index_100,
    pct_change,
    qtq,
    safe_mad,
    safe_mean,
    safe_std,
    window_slopes,
    yoy,
)

__all__ = [
    # Trend utilities
    "pct_change",
    "yoy",
    "qtq",
    "ewma",
    "index_100",
    "window_slopes",
    "safe_mean",
    "safe_std",
    "safe_mad",
    # Change points
    "cusum_breaks",
    "zscore_outliers",
    "summarize_breaks",
    "rolling_variance_breaks",
    # Baselines
    "seasonal_baseline",
    "anomaly_gaps",
    "detect_seasonal_anomalies",
    "trend_adjusted_baseline",
    "summarize_baseline_fit",
]
