"""
Backtesting framework for baseline forecasters.

Implements rolling-origin (walk-forward) backtesting to evaluate forecast accuracy
and method selection heuristics with deterministic tie-breaking.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, cast

from .baselines import (
    ewma_forecast,
    robust_trend_forecast,
    rolling_mean_forecast,
    seasonal_naive,
)

ForecastFn = Callable[..., list[float | None]]
EPSILON = 1e-6
DEFAULT_MIN_TRAIN = 24


@dataclass(frozen=True)
class MethodSelection:
    """
    Result of the automatic baseline selection routine.

    Attributes:
        method: Name of the chosen method.
        leaderboard: Mapping of method -> metric dictionary (mae/mape/rmse/n).
        reasons: Deterministic rationale strings explaining the decision.
    """

    method: str
    leaderboard: dict[str, dict[str, float]]
    reasons: list[str]


def _clean_series(series: list[float]) -> list[float]:
    """Return series with non-finite values removed."""
    return [
        float(value)
        for value in series
        if isinstance(value, (int, float)) and math.isfinite(float(value))
    ]


def rolling_origin_backtest(
    series: list[float],
    method: ForecastFn,
    horizon: int = 1,
    min_train: int = DEFAULT_MIN_TRAIN,
    **method_kwargs: Any,
) -> dict[str, float]:
    """
    Perform rolling-origin (walk-forward) backtest for a forecast method.

    Iteratively trains on expanding window and tests one-step-ahead forecast.

    Args:
        series: Full time series
        method: Forecasting function (must accept series and horizon)
        horizon: Forecast horizon (default 1 for one-step-ahead)
        min_train: Minimum training window size
        **method_kwargs: Additional arguments passed to method

    Returns:
        Dict with keys: mae, mape, rmse, n (number of test points)
    """
    clean_series = _clean_series(series)
    if len(clean_series) < min_train + horizon:
        return {"mae": float("nan"), "mape": float("nan"), "rmse": float("nan"), "n": 0}

    errors: list[float] = []
    abs_pct_errors: list[float] = []
    squared_errors: list[float] = []

    # Walk forward: start with min_train, expand by 1 each iteration
    for t in range(min_train, len(clean_series) - horizon + 1):
        train = clean_series[:t]
        actual = clean_series[t : t + horizon]

        # Generate forecast
        try:
            forecast = method(train, horizon=horizon, **method_kwargs)
        except Exception:
            continue  # Skip this fold if method fails

        # Compare first forecast point (one-step-ahead)
        if not forecast or forecast[0] is None:
            continue
        yhat = forecast[0]
        y = actual[0]
        if not math.isfinite(yhat) or not math.isfinite(y):
            continue

        # Compute errors
        error = y - yhat
        errors.append(abs(error))
        squared_errors.append(error**2)

        # Safe MAPE computation (avoid division by zero)
        denom = max(EPSILON, abs(y))
        abs_pct_errors.append(abs(error) / denom * 100.0)

    if not errors:
        return {"mae": float("nan"), "mape": float("nan"), "rmse": float("nan"), "n": 0}

    # Compute metrics
    mae = sum(errors) / len(errors)
    rmse = math.sqrt(sum(squared_errors) / len(squared_errors))
    mape = sum(abs_pct_errors) / len(abs_pct_errors) if abs_pct_errors else float("nan")

    return {
        "mae": round(mae, 4),
        "mape": round(mape, 4) if math.isfinite(mape) else float("nan"),
        "rmse": round(rmse, 4),
        "n": len(errors),
    }


def _finite_metric(value: float) -> float:
    """Convert NaN to +inf for deterministic comparisons."""
    if not math.isfinite(value):
        return math.inf
    return value


def choose_baseline(
    series: list[float],
    season: int = 12,
    *,
    min_train: int = DEFAULT_MIN_TRAIN,
    seasonal_win_delta: float = 0.1,
) -> MethodSelection:
    """
    Heuristic method selection via backtesting comparison.

    Backtests all baseline methods and selects the one with lowest MAE,
    tie-breaking deterministically via RMSE, then MAPE, then method name.

    Args:
        series: Historical time series
        season: Seasonal period for seasonal_naive (default 12)
        min_train: Minimum history required before running backtests
        seasonal_win_delta: Minimum MAE gap required to declare strong seasonality

    Returns:
        MethodSelection with the winning method, leaderboard, and rationale.
    """
    clean_series = _clean_series(series)
    reasons: list[str] = []
    if len(clean_series) < min_train:
        reasons.append(
            f"Insufficient history ({len(clean_series)} < {min_train}); defaulting to ewma."
        )
        return MethodSelection(
            method="ewma",
            leaderboard={},
            reasons=reasons,
        )

    methods: dict[str, tuple[ForecastFn, dict[str, Any]]] = {
        "seasonal_naive": (cast(ForecastFn, seasonal_naive), {"season": season}),
        "ewma": (cast(ForecastFn, ewma_forecast), {"alpha": 0.3}),
        "rolling_mean": (cast(ForecastFn, rolling_mean_forecast), {"window": 12}),
        "robust_trend": (cast(ForecastFn, robust_trend_forecast), {"window": 24}),
    }

    leaderboard: dict[str, dict[str, float]] = {}

    for name, (func, kwargs) in methods.items():
        try:
            metrics = rolling_origin_backtest(
                clean_series, func, horizon=1, min_train=min_train, **kwargs
            )
        except Exception:
            continue  # Skip methods that fail
        mae = metrics.get("mae", float("nan"))
        if math.isfinite(mae):
            leaderboard[name] = metrics

    if not leaderboard:
        reasons.append("All method backtests failed; defaulting to ewma.")
        return MethodSelection(method="ewma", leaderboard={}, reasons=reasons)

    def sort_key(item: tuple[str, dict[str, float]]) -> tuple[float, float, float, str]:
        name, metrics = item
        return (
            _finite_metric(metrics.get("mae", math.inf)),
            _finite_metric(metrics.get("rmse", math.inf)),
            _finite_metric(metrics.get("mape", math.inf)),
            name,
        )

    ranked = sorted(leaderboard.items(), key=sort_key)
    winner, winner_metrics = ranked[0]
    reasons.append(
        f"{winner} achieved lowest MAE={winner_metrics['mae']:.4f} among tested baselines."
    )

    if len(ranked) > 1:
        runner_name, runner_metrics = ranked[1]
        mae_gap = runner_metrics["mae"] - winner_metrics["mae"]
        if mae_gap > 0:
            reasons.append(
                f"MAE gap vs {runner_name}: {mae_gap:.4f} ({runner_metrics['mae']:.4f} - {winner_metrics['mae']:.4f})."
            )
        else:
            # Tie on MAE, explain tie-breaker
            winner_rmse = winner_metrics.get("rmse", math.inf)
            runner_rmse = runner_metrics.get("rmse", math.inf)
            if not math.isclose(winner_rmse, runner_rmse, rel_tol=1e-6):
                reasons.append(
                    f"Tie on MAE; resolved via RMSE {winner_rmse:.4f} < {runner_rmse:.4f}."
                )
            else:
                winner_mape = winner_metrics.get("mape", math.inf)
                runner_mape = runner_metrics.get("mape", math.inf)
                if math.isfinite(winner_mape) and math.isfinite(runner_mape):
                    if not math.isclose(winner_mape, runner_mape, rel_tol=1e-6):
                        reasons.append(
                            f"Tie on MAE/RMSE; resolved via lower MAPE {winner_mape:.4f} vs {runner_mape:.4f}."
                        )
                    else:
                        reasons.append(
                            f"All metrics tied; selected {winner} deterministically via method name ordering."
                        )

    if (
        winner == "seasonal_naive"
        and len(clean_series) >= 36
        and len(ranked) > 1
    ):
        runner_mae = ranked[1][1]["mae"]
        mae_gap = runner_mae - winner_metrics["mae"]
        if mae_gap >= seasonal_win_delta:
            reasons.append(
                f"Detected strong seasonality: seasonal_naive beat next best by {mae_gap:.4f} "
                f">= delta={seasonal_win_delta:.4f}."
            )

    return MethodSelection(method=winner, leaderboard=leaderboard, reasons=reasons)
