"""
Scenario QA - Backtest metrics, stability checks, and performance benchmarks.

Provides functions to validate forecast quality with standard error metrics
(MAPE/MAE/SMAPE) and SLA compliance checks.
"""

from __future__ import annotations

import logging
import math
import time
from typing import Any

logger = logging.getLogger(__name__)

# SLA threshold: <75ms for 8-year monthly series (96 points)
SLA_THRESHOLD_MS = 75.0
EPSILON = 1e-10  # For SMAPE denominator stability


def mean_absolute_error(actual: list[float], predicted: list[float]) -> float:
    """
    Calculate Mean Absolute Error (MAE).

    Args:
        actual: Actual values
        predicted: Predicted values

    Returns:
        MAE value

    Raises:
        ValueError: If lengths don't match or lists are empty
    """
    if len(actual) != len(predicted):
        raise ValueError(
            f"Length mismatch: actual={len(actual)}, predicted={len(predicted)}"
        )
    if not actual:
        raise ValueError("Cannot compute MAE on empty lists")

    errors = [abs(a - p) for a, p in zip(actual, predicted)]
    return sum(errors) / len(errors)


def mean_absolute_percentage_error(
    actual: list[float], predicted: list[float], eps: float = EPSILON
) -> float:
    """
    Calculate Mean Absolute Percentage Error (MAPE) with epsilon guard.

    Args:
        actual: Actual values
        predicted: Predicted values
        eps: Epsilon to prevent division by zero

    Returns:
        MAPE as percentage (0-100 scale)

    Raises:
        ValueError: If lengths don't match or lists are empty
    """
    if len(actual) != len(predicted):
        raise ValueError(
            f"Length mismatch: actual={len(actual)}, predicted={len(predicted)}"
        )
    if not actual:
        raise ValueError("Cannot compute MAPE on empty lists")

    percentage_errors = []
    for a, p in zip(actual, predicted):
        if abs(a) < eps:
            # Skip near-zero actuals to avoid explosion
            continue
        percentage_errors.append(abs((a - p) / a) * 100.0)

    if not percentage_errors:
        return 0.0

    return sum(percentage_errors) / len(percentage_errors)


def symmetric_mean_absolute_percentage_error(
    actual: list[float], predicted: list[float], eps: float = EPSILON
) -> float:
    """
    Calculate Symmetric MAPE (SMAPE) with epsilon guard.

    SMAPE addresses MAPE's asymmetry and is bounded [0, 100].

    Args:
        actual: Actual values
        predicted: Predicted values
        eps: Epsilon to prevent division by zero

    Returns:
        SMAPE as percentage (0-100 scale)

    Raises:
        ValueError: If lengths don't match or lists are empty
    """
    if len(actual) != len(predicted):
        raise ValueError(
            f"Length mismatch: actual={len(actual)}, predicted={len(predicted)}"
        )
    if not actual:
        raise ValueError("Cannot compute SMAPE on empty lists")

    smape_values = []
    for a, p in zip(actual, predicted):
        numerator = abs(a - p)
        denominator = (abs(a) + abs(p)) / 2.0
        if denominator < eps:
            # Both near zero, perfect match
            smape_values.append(0.0)
        else:
            smape_values.append((numerator / denominator) * 100.0)

    return sum(smape_values) / len(smape_values)


def backtest_forecast(
    actual: list[float],
    predicted: list[float],
    eps: float = EPSILON,
) -> dict[str, float]:
    """
    Compute backtest metrics for forecast validation.

    Args:
        actual: Actual observed values
        predicted: Predicted/forecast values
        eps: Epsilon for MAPE/SMAPE stability

    Returns:
        Dictionary with MAE, MAPE, SMAPE, and sample size

    Examples:
        >>> metrics = backtest_forecast(
        ...     actual=[100, 105, 110],
        ...     predicted=[98, 106, 112]
        ... )
        >>> metrics["mae"]
        2.0
    """
    if len(actual) != len(predicted):
        raise ValueError(
            f"Length mismatch: actual={len(actual)}, predicted={len(predicted)}"
        )
    if not actual:
        raise ValueError("Cannot compute backtest metrics on empty data")

    mae = mean_absolute_error(actual, predicted)
    mape = mean_absolute_percentage_error(actual, predicted, eps=eps)
    smape = symmetric_mean_absolute_percentage_error(actual, predicted, eps=eps)

    return {
        "mae": mae,
        "mape": mape,
        "smape": smape,
        "n": len(actual),
    }


def rolling_window_backtest(
    series: list[float],
    forecast_fn: Any,  # Callable[[list[float], int], list[float]]
    horizon: int = 1,
    min_train: int = 24,
) -> dict[str, float]:
    """
    Perform rolling window backtest on time series.

    Args:
        series: Historical time series
        forecast_fn: Forecast function (train_data, horizon) -> predictions
        horizon: Forecast horizon
        min_train: Minimum training points required

    Returns:
        Dictionary with aggregated backtest metrics

    Raises:
        ValueError: If insufficient data for rolling window
    """
    if len(series) < min_train + horizon:
        raise ValueError(
            f"Insufficient data: need at least {min_train + horizon} points, "
            f"got {len(series)}"
        )

    actual_list: list[float] = []
    predicted_list: list[float] = []

    # Rolling origin
    for i in range(min_train, len(series) - horizon + 1):
        train = series[:i]
        actual_horizon = series[i : i + horizon]

        try:
            forecast = forecast_fn(train, horizon)
        except Exception as exc:
            logger.warning("Forecast failed at split %d: %s", i, exc)
            continue

        # Take only the first h predictions
        forecast_horizon = forecast[:horizon]

        # Match lengths
        min_len = min(len(actual_horizon), len(forecast_horizon))
        actual_list.extend(actual_horizon[:min_len])
        predicted_list.extend(forecast_horizon[:min_len])

    if not actual_list:
        raise ValueError("No valid forecasts produced during rolling window")

    return backtest_forecast(actual_list, predicted_list)


def stability_check(values: list[float], window: int = 6) -> dict[str, Any]:
    """
    Check forecast stability across rolling windows.

    Stability flags:
    - High volatility: CV > 0.5
    - Trend reversals: Sign changes in differences
    - Range explosion: Max/min ratio > 5

    Args:
        values: Forecast values
        window: Window size for rolling statistics

    Returns:
        Dictionary with stability flags and diagnostics
    """
    if len(values) < window:
        return {
            "stable": True,
            "flags": [],
            "cv": 0.0,
            "reversals": 0,
            "range_ratio": 1.0,
            "reason": f"Insufficient data ({len(values)} < {window})",
        }

    flags: list[str] = []

    # Coefficient of variation (CV)
    mean_val = sum(values) / len(values)
    if mean_val == 0:
        cv = 0.0
    else:
        variance = sum((v - mean_val) ** 2 for v in values) / len(values)
        std_dev = math.sqrt(variance)
        cv = std_dev / abs(mean_val)

    if cv > 0.5:
        flags.append("high_volatility")

    # Trend reversals
    diffs = [values[i + 1] - values[i] for i in range(len(values) - 1)]
    reversals = 0
    for i in range(len(diffs) - 1):
        if diffs[i] * diffs[i + 1] < 0:  # Sign change
            reversals += 1

    if reversals > len(values) // 3:
        flags.append("frequent_reversals")

    # Range explosion
    min_val = min(values)
    max_val = max(values)
    if min_val > 0:
        range_ratio = max_val / min_val
        if range_ratio > 5.0:
            flags.append("range_explosion")
    else:
        range_ratio = float("inf") if max_val > 0 else 1.0

    stable = len(flags) == 0

    return {
        "stable": stable,
        "flags": flags,
        "cv": cv,
        "reversals": reversals,
        "range_ratio": range_ratio,
        "reason": "OK" if stable else f"Unstable: {', '.join(flags)}",
    }


def sla_benchmark(
    series: list[float],
    scenario_fn: Any,  # Callable[[list[float]], list[float]]
    iterations: int = 10,
    threshold_ms: float = SLA_THRESHOLD_MS,
) -> dict[str, Any]:
    """
    Benchmark scenario application latency against SLA.

    Tests whether scenario transforms meet the <75ms requirement for
    96-point (8-year monthly) series.

    Args:
        series: Time series to transform (typically 96 points)
        scenario_fn: Scenario application function
        iterations: Number of benchmark iterations
        threshold_ms: SLA threshold in milliseconds

    Returns:
        Dictionary with latency stats and SLA compliance

    Examples:
        >>> def simple_transform(s):
        ...     return [v * 1.1 for v in s]
        >>> result = sla_benchmark([100.0] * 96, simple_transform)
        >>> result["sla_compliant"]
        True
    """
    latencies_ms: list[float] = []

    for _ in range(iterations):
        start_time = time.perf_counter()
        try:
            _ = scenario_fn(series)
        except Exception as exc:
            logger.error("Scenario function failed during benchmark: %s", exc)
            return {
                "sla_compliant": False,
                "reason": f"Function error: {exc}",
                "latency_p50": None,
                "latency_p95": None,
                "latency_max": None,
            }
        end_time = time.perf_counter()
        latencies_ms.append((end_time - start_time) * 1000.0)

    latencies_ms.sort()
    n = len(latencies_ms)

    p50_idx = n // 2
    p95_idx = int(n * 0.95)

    p50 = latencies_ms[p50_idx]
    p95 = latencies_ms[p95_idx]
    max_latency = latencies_ms[-1]

    sla_compliant = p95 < threshold_ms

    return {
        "sla_compliant": sla_compliant,
        "reason": "OK" if sla_compliant else f"P95 {p95:.2f}ms exceeds {threshold_ms}ms",
        "latency_p50": p50,
        "latency_p95": p95,
        "latency_max": max_latency,
        "iterations": iterations,
        "series_length": len(series),
    }
