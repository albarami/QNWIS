"""
Baseline forecasting methods for LMIS time-series.

All implementations are deterministic, pure-Python, and guard against
degenerate inputs (NaN, infinities, and insufficient history).
"""

from __future__ import annotations

import math

MAD_TO_SIGMA = 1.4826


def seasonal_naive(
    series: list[float],
    season: int = 12,
    horizon: int = 6,
) -> list[float | None]:
    """
    Repeat value from t-season periods ago (naive seasonal forecast).

    Args:
        series: Historical time series (ordered oldest to newest)
        season: Seasonal period length (default 12 for monthly data)
        horizon: Number of periods to forecast

    Returns:
        List of forecasted values (length=horizon), None if insufficient history
    """
    if len(series) < season:
        return [None] * horizon

    forecast: list[float | None] = []
    for h in range(horizon):
        # For h=0, use last value; for h >= season, cycle seasonal pattern
        idx = -season + (h % season)
        if -idx > len(series):
            forecast.append(None)
        else:
            forecast.append(float(series[idx]))

    return forecast


def ewma_forecast(
    series: list[float],
    alpha: float = 0.3,
    horizon: int = 6,
) -> list[float]:
    """
    Exponentially weighted moving average recursive forecast.

    EWMA formula: S_t = α*y_t + (1-α)*S_(t-1)
    Forecast: yhat_(t+h) = S_t for all h (flat forecast from last smoothed value).

    Args:
        series: Historical time series
        alpha: Smoothing parameter (0 < α <= 1); higher = more responsive
        horizon: Number of periods to forecast

    Returns:
        List of forecasted values (length=horizon)
    """
    if not series:
        return [0.0] * horizon

    if not (0 < alpha <= 1):
        raise ValueError(f"alpha must be in (0, 1], got {alpha}")

    # Compute EWMA up to last observation
    s = float(series[0])
    for val in series[1:]:
        s = alpha * float(val) + (1 - alpha) * s

    # Flat forecast: all future values = last smoothed level
    return [s] * horizon


def rolling_mean_forecast(
    series: list[float],
    window: int = 12,
    horizon: int = 6,
) -> list[float | None]:
    """
    Simple moving average over last 'window' points, projected forward.

    Args:
        series: Historical time series
        window: Number of recent points to average
        horizon: Number of periods to forecast

    Returns:
        List of forecasted values (length=horizon), None if insufficient data
    """
    if len(series) < window:
        return [None] * horizon

    recent = [float(v) for v in series[-window:]]
    mean_val = sum(recent) / len(recent)
    return [mean_val] * horizon


def robust_trend_forecast(
    series: list[float],
    window: int = 24,
    horizon: int = 6,
) -> list[float]:
    """
    Robust linear trend via Theil-Sen estimator (median of pairwise slopes).

    Uses last 'window' points to estimate slope, anchors intercept at last value,
    then extrapolates linearly.

    Args:
        series: Historical time series
        window: Number of recent points for trend estimation (default 24)
        horizon: Number of periods to forecast

    Returns:
        List of forecasted values (length=horizon)
    """
    if not series:
        return [0.0] * horizon

    history = series[-window:] if len(series) >= window else list(series)
    recent = [
        float(v) for v in history if isinstance(v, (int, float)) and math.isfinite(v)
    ]
    if len(recent) < 2:
        last = float(series[-1])
        return [last] * horizon

    n = len(recent)
    slopes: list[float] = []
    for i in range(n):
        for j in range(i + 1, n):
            delta = j - i
            if delta == 0:
                continue
            slopes.append((recent[j] - recent[i]) / delta)

    if not slopes:
        last = float(recent[-1])
        return [last] * horizon

    slopes.sort()
    mid = len(slopes) // 2
    if len(slopes) % 2 == 0:
        slope = (slopes[mid - 1] + slopes[mid]) / 2.0
    else:
        slope = slopes[mid]

    last_val = float(recent[-1])
    return [last_val + slope * h for h in range(1, horizon + 1)]


def residuals_in_sample(series: list[float], fitted: list[float]) -> list[float]:
    """
    Compute aligned residuals: actual - fitted, skipping non-finite entries.

    Args:
        series: Actual values
        fitted: Fitted/predicted values (must align with series)

    Returns:
        List of residuals; skips where fitted is None or non-finite
    """
    residuals: list[float] = []
    min_len = min(len(series), len(fitted))

    for i in range(min_len):
        estimate = fitted[i]
        actual = series[i]
        if estimate is None:
            continue
        if not isinstance(actual, (int, float)) or not isinstance(estimate, (int, float)):
            continue
        if not math.isfinite(actual) or not math.isfinite(estimate):
            continue
        residuals.append(float(actual) - float(estimate))

    return residuals


def mad_interval(residuals: list[float], z: float = 1.96) -> float:
    """
    Compute prediction interval half-width using MAD (Median Absolute Deviation).

    MAD is robust to outliers. Scale factor 1.4826 converts MAD to σ under normality.
    Half-width = z * σ, clamped to finite, non-negative values.

    Args:
        residuals: In-sample residuals
        z: Z-score for desired coverage (default 1.96 for 95% CI)

    Returns:
        Half-width for prediction interval (non-negative)
    """
    finite_residuals = [
        float(r)
        for r in residuals
        if isinstance(r, (int, float)) and math.isfinite(float(r))
    ]
    if not finite_residuals:
        return 0.0

    abs_residuals = sorted(abs(r) for r in finite_residuals)
    n = len(abs_residuals)
    if n % 2 == 0:
        mad = (abs_residuals[n // 2 - 1] + abs_residuals[n // 2]) / 2.0
    else:
        mad = abs_residuals[n // 2]

    sigma = MAD_TO_SIGMA * mad
    half_width = z * sigma
    if not math.isfinite(half_width):
        return 0.0
    return max(0.0, half_width)


def clamp_nonnegative(values: list[float | None]) -> list[float | None]:
    """
    Clamp negative values to 0 (for metrics that cannot be negative).

    Args:
        values: List of forecast/interval values

    Returns:
        Clamped list with negatives replaced by 0 and non-finite values as None.
    """
    clamped: list[float | None] = []
    for value in values:
        if value is None:
            clamped.append(None)
            continue
        if not isinstance(value, (int, float)):
            clamped.append(None)
            continue
        if not math.isfinite(value):
            clamped.append(None)
            continue
        clamped.append(max(0.0, float(value)))
    return clamped


def build_forecast_table(
    method: str,
    history: list[float],
    forecast: list[float | None],
    half_width: float,
    start_idx: int,
) -> list[dict[str, float]]:
    """
    Build a citation-ready forecast table with intervals.

    Args:
        method: Forecasting method name (unused but kept for compatibility)
        history: Historical series (unused, maintained for API stability)
        forecast: Point forecasts (length=horizon)
        half_width: Prediction interval half-width
        start_idx: Time index of first forecast (e.g., len(history))

    Returns:
        List of dicts with keys: h, yhat, lo, hi, t_idx
        Each row represents one forecast horizon step.
    """
    table: list[dict[str, float]] = []
    interval = half_width if math.isfinite(half_width) else 0.0
    interval = max(0.0, interval)

    for h, yhat in enumerate(forecast, start=1):
        if yhat is None:
            continue  # Skip insufficient history cases
        if not isinstance(yhat, (int, float)) or not math.isfinite(yhat):
            continue
        point = float(yhat)
        lo = max(0.0, point - interval)
        hi = point + interval

        table.append(
            {
                "h": float(h),
                "yhat": round(point, 4),
                "lo": round(lo, 4),
                "hi": round(hi, 4),
                "t_idx": float(start_idx + h),
            }
        )

    return table
