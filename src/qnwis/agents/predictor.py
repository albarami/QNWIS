"""
Predictor Agent - Baseline forecasting and early-warning system.

Provides deterministic time-series forecasting with prediction intervals and
risk scoring for LMIS labour market metrics.
"""

from __future__ import annotations

import logging
import math
from collections.abc import Mapping, Sequence
from datetime import date
from typing import Any

from ..analysis.change_points import cusum_breaks
from ..data.deterministic.models import QueryResult
from ..forecast.backtest import choose_baseline, rolling_origin_backtest
from ..forecast.baselines import (
    build_forecast_table,
    clamp_nonnegative,
    ewma_forecast,
    mad_interval,
    residuals_in_sample,
    robust_trend_forecast,
    rolling_mean_forecast,
    seasonal_naive,
)
from ..forecast.early_warning import band_breach, risk_score, slope_reversal, volatility_spike
from .base import DataClient
from .utils.derived_results import make_derived_query_result

logger = logging.getLogger(__name__)

MIN_TRAIN_POINTS = 24
DEFAULT_SEASONAL_WIN_DELTA = 0.1
CUSUM_K = 1.0
CUSUM_H = 5.0


class PredictorAgent:
    """
    Deterministic forecast baselines and early-warning signals over LMIS time-series.

    Capabilities:
    - forecast_baseline: Select method via backtest, generate forecast with intervals
    - early_warning: Compute risk score and flag potential issues
    - scenario_compare: Compare multiple methods' forecasts and backtests
    """

    REQUIRED_DATA_TYPES = ["time_series_employment"]

    def can_analyze(self, query_context: dict[str, Any]) -> bool:
        """Check if agent has necessary data before attempting analysis."""
        available_data = query_context.get("available_data_types", [])
        
        has_required_data = any(
            data_type in available_data 
            for data_type in self.REQUIRED_DATA_TYPES
        )
        
        if not has_required_data:
            logger.info(f"{self.__class__.__name__} skipping: insufficient data")
            return False
        
        return True

    def __init__(
        self,
        client: DataClient,
        series_map: Mapping[str, str] | None = None,
        *,
        seasonal_win_delta: float = DEFAULT_SEASONAL_WIN_DELTA,
        min_train_points: int = MIN_TRAIN_POINTS,
    ) -> None:
        """
        Initialize the Predictor Agent.

        Args:
            client: DataClient instance for accessing deterministic queries
            series_map: Optional mapping from metric name to deterministic query_id
            seasonal_win_delta: Minimum MAE gap to declare seasonality dominance
            min_train_points: Minimum points required for training/backtesting
        """
        self.client = client
        self.series_map = {k.lower(): v for k, v in (series_map or {}).items()}
        self.seasonal_win_delta = seasonal_win_delta
        self.min_train_points = min_train_points

    def _extract_time_series(
        self,
        result: QueryResult,
        metric_field: str,
        date_field: str = "month",
    ) -> tuple[list[float], list[str]]:
        """
        Extract time series from QueryResult.

        Args:
            result: QueryResult with time-series data
            metric_field: Field name containing metric values
            date_field: Field name containing dates (default "month")

        Returns:
            Tuple of (values, dates) ordered chronologically
        """
        rows_with_dates = []
        for row in result.rows:
            dt = row.data.get(date_field)
            val = row.data.get(metric_field)
            if dt is None or val is None:
                continue
            try:
                numeric_val = float(val)
            except (ValueError, TypeError):
                continue
            if not math.isfinite(numeric_val):
                continue
            rows_with_dates.append((dt, numeric_val))

        # Sort by date
        rows_with_dates.sort(key=lambda x: x[0])

        values = [v for _, v in rows_with_dates]
        dates = [str(d) for d, _ in rows_with_dates]
        return values, dates

    def _available_query_ids(self) -> dict[str, str]:
        """Return registry query_ids keyed by lowercase for lookup."""
        registry = getattr(self.client, "registry", None)
        if registry is None:
            return {}
        try:
            ids = registry.all_ids()
        except Exception:
            return {}
        return {qid.lower(): qid for qid in ids}

    def _resolve_query_id(self, metric: str) -> str:
        """Resolve metric string to deterministic query_id."""
        key = metric.strip().lower()
        if key in self.series_map:
            return self.series_map[key]

        registry_ids = self._available_query_ids()
        candidates = [
            key,
            f"{key}_timeseries",
            f"{key}_time_series",
            f"{key}_by_sector",
            f"syn_{key}",
            f"ts_{key}_by_sector",
        ]
        for candidate in candidates:
            canonical = candidate.lower()
            if canonical in registry_ids:
                return registry_ids[canonical]

        # Fallback pattern for compatibility with synthetic tests
        return f"ts_{key}_by_sector"

    def _apply_stability_guard(
        self,
        values: list[float],
        dates: list[str],
    ) -> tuple[list[float], str | None]:
        """
        If change-points exist, return tail after last break with rationale.
        """
        if len(values) < self.min_train_points:
            return values, None

        break_indices = sorted(cusum_breaks(values, k=CUSUM_K, h=CUSUM_H))
        if not break_indices:
            return values, None

        last_break = break_indices[-1]
        tail = values[last_break:]
        tail_dates = dates[last_break:] if last_break < len(dates) else []
        if len(tail) < self.min_train_points:
            reason = (
                f"Detected change-point near {dates[last_break]} "
                f"but tail has only {len(tail)} points; retained full history."
            )
            return values, reason

        marker = tail_dates[0] if tail_dates else dates[last_break]
        reason = f"Detected change-point near {marker}; training on post-break tail of {len(tail)} points."
        return tail, reason

    @staticmethod
    def _confidence_hint_line(confidence_hint: dict[str, Any] | None) -> str | None:
        """Format Step-22 confidence hint for footer display."""
        if not confidence_hint:
            return None
        score = confidence_hint.get("score")
        if score is None:
            return None
        try:
            score_value = float(score)
        except (TypeError, ValueError):
            return None
        if score_value <= 1.0:
            score_value *= 100.0
        band = confidence_hint.get("band")
        if band:
            return f"Confidence hint (Step 22): {score_value:.0f}/100 ({band})."
        return f"Confidence hint (Step 22): {score_value:.0f}/100."

    def forecast_baseline(
        self,
        metric: str,
        sector: str | None,
        start: date,
        end: date,
        horizon_months: int = 6,
        season: int = 12,
        confidence_hint: dict[str, Any] | None = None,
    ) -> str:
        """
        Generate baseline forecast with prediction intervals.

        Selects best method via backtest, computes forecast and intervals,
        returns citation-ready narrative.

        Args:
            metric: Labour market metric (e.g., "retention", "qatarization")
            sector: Sector filter (None for "All")
            start: Start date for training data
            end: End date for training data
            horizon_months: Forecast horizon (default 6, max 12)
            season: Seasonal period for seasonal_naive (default 12)
            confidence_hint: Optional Step-22 confidence payload for footer display

        Returns:
            Formatted narrative with forecast table, intervals, backtest metrics, and QID citations

        Raises:
            ValueError: If horizon_months > 12 or insufficient data
        """
        if horizon_months > 12:
            raise ValueError("horizon_months must be ≤ 12")

        logger.info(
            "forecast_baseline: metric=%s sector=%s start=%s end=%s horizon=%d",
            metric,
            sector,
            start,
            end,
            horizon_months,
        )

        query_id = self._resolve_query_id(metric)

        try:
            res = self.client.run(query_id)
        except Exception as exc:
            logger.error("Failed to fetch time series: %s", exc)
            return f"Error: Unable to fetch data for {metric}. Query '{query_id}' not found."

        # Extract time series
        series, dates = self._extract_time_series(res, metric_field=metric)

        if len(series) < self.min_train_points:
            return (
                f"Insufficient data: {len(series)} points available "
                f"(need ≥ {self.min_train_points} for baseline forecast)."
            )

        train_series, stability_reason = self._apply_stability_guard(series, dates)
        selection = choose_baseline(
            train_series,
            season=season,
            min_train=self.min_train_points,
            seasonal_win_delta=self.seasonal_win_delta,
        )
        method_name = selection.method
        logger.info("Selected method: %s", method_name)

        # Map method name to function
        method_map = {
            "seasonal_naive": (seasonal_naive, {"season": season}),
            "ewma": (ewma_forecast, {"alpha": 0.3}),
            "rolling_mean": (rolling_mean_forecast, {"window": 12}),
            "robust_trend": (robust_trend_forecast, {"window": 24}),
        }

        method_func, method_params = method_map[method_name]

        # Generate forecast
        forecast = method_func(train_series, horizon=horizon_months, **method_params)

        # Backtest to compute intervals
        backtest_metrics = rolling_origin_backtest(
            train_series,
            method_func,
            horizon=1,
            min_train=self.min_train_points,
            **method_params,
        )

        # In-sample fit for MAD interval
        fitted_full = method_func(train_series, horizon=len(train_series), **method_params)
        residuals = residuals_in_sample(train_series, fitted_full)
        half_width = mad_interval(residuals, z=1.96)

        # Clamp forecast for non-negative metrics
        forecast_clamped = clamp_nonnegative(forecast)

        # Build forecast table
        forecast_table = build_forecast_table(
            method=method_name,
            history=series,
            forecast=forecast_clamped,
            half_width=half_width,
            start_idx=len(series),
        )

        # Wrap as derived QueryResult
        derived_forecast = make_derived_query_result(
            operation="forecast_baseline",
            params={
                "metric": metric,
                "sector": sector or "All",
                "method": method_name,
                "horizon_months": horizon_months,
                "start": str(start),
                "end": str(end),
                "season": season,
                "train_points": len(train_series),
            },
            rows=forecast_table,
            sources=[res.query_id],
            freshness_like=res.freshness,
            unit="unknown",
        )

        # Backtest metrics as derived result
        derived_backtest = make_derived_query_result(
            operation="backtest_metrics",
            params={
                "method": method_name,
                "metric": metric,
                "season": season,
                "train_points": len(train_series),
            },
            rows=[backtest_metrics],
            sources=[res.query_id],
            freshness_like=res.freshness,
            unit="unknown",
        )

        method_reasons: list[str] = []
        if stability_reason:
            method_reasons.append(stability_reason)
        method_reasons.extend(selection.reasons)

        # Format narrative
        narrative = self._format_forecast_narrative(
            metric=metric,
            sector=sector or "All",
            method=method_name,
            horizon=horizon_months,
            forecast_table=forecast_table,
            backtest_metrics=backtest_metrics,
            forecast_qid=derived_forecast.query_id,
            backtest_qid=derived_backtest.query_id,
            freshness_date=res.freshness.asof_date,
            data_qid=res.query_id,
            method_reasons=method_reasons,
            confidence_hint=confidence_hint,
        )

        return narrative

    def _format_forecast_narrative(
        self,
        metric: str,
        sector: str,
        method: str,
        horizon: int,
        forecast_table: list[dict[str, float]],
        backtest_metrics: dict[str, float],
        forecast_qid: str,
        backtest_qid: str,
        freshness_date: str,
        data_qid: str,
        method_reasons: Sequence[str] | None = None,
        confidence_hint: dict[str, Any] | None = None,
    ) -> str:
        """Format forecast output as citation-ready narrative."""
        lines = [
            "## Executive Summary",
            f"- **Metric**: {metric}",
            f"- **Sector**: {sector}",
            f"- **Horizon**: {horizon} months",
            f"- **Method selected**: {method} (MAE={backtest_metrics['mae']:.4f}) (QID={backtest_qid})",
            f"- **Data source**: (QID={data_qid})",
            "",
            "## Forecast with 95% Prediction Intervals",
            "| h | yhat | lo | hi |",
            "|---|------|----|----|",
        ]

        for row in forecast_table:
            lines.append(
                f"| {int(row['h'])} | {row['yhat']:.2f} | {row['lo']:.2f} | {row['hi']:.2f} |"
            )

        lines.extend(
            [
                f"(QID={forecast_qid})",
                "",
                "## Backtest Performance",
                f"- **MAE**: {backtest_metrics['mae']:.4f} (QID={backtest_qid})",
                f"- **MAPE**: {backtest_metrics['mape']:.2f}% (QID={backtest_qid})",
                f"- **RMSE**: {backtest_metrics['rmse']:.4f} (QID={backtest_qid})",
                f"- **Method**: {method}",
                f"- **Test points**: {int(backtest_metrics['n'])}",
            ]
        )

        if method_reasons:
            lines.extend(["", "## Method Rationale"])
            for reason in method_reasons:
                lines.append(f"- {reason}")

        lines.extend(
            [
                "",
                "## Freshness",
                f"- **Data as of**: {freshness_date} (QID={data_qid})",
                "",
                "## Reproducibility",
                "```python",
                f'DataClient.run("{data_qid}")',
                f'PredictorAgent.forecast_baseline(metric="{metric}", sector="{sector}", horizon_months={horizon})',
                "```",
            ]
        )

        confidence_line = self._confidence_hint_line(confidence_hint)
        if confidence_line:
            lines.extend(["", f"> {confidence_line}"])

        return "\n".join(lines)

    def early_warning(
        self,
        metric: str,
        sector: str | None,
        end: date,
        horizon_months: int = 3,
        confidence_hint: dict[str, Any] | None = None,
    ) -> str:
        """Compute early-warning risk score with active flags."""
        logger.info(
            "early_warning: metric=%s sector=%s end=%s horizon=%d",
            metric,
            sector,
            end,
            horizon_months,
        )

        query_id = self._resolve_query_id(metric)
        try:
            res = self.client.run(query_id)
        except Exception as exc:
            logger.error("Failed to fetch time series: %s", exc)
            return f"Error: Unable to fetch data for {metric}."

        series, dates = self._extract_time_series(res, metric_field=metric)
        if len(series) < 12:
            return f"Insufficient data for early warning: {len(series)} points (need ≥ 12)."
        if len(series) < 2:
            return "Need at least 2 observations to compute early-warning signals."

        history = series[:-1]
        history_dates = dates[:-1]
        train_series, stability_reason = self._apply_stability_guard(history, history_dates)
        selection = choose_baseline(
            train_series,
            season=12,
            min_train=self.min_train_points,
            seasonal_win_delta=self.seasonal_win_delta,
        )
        method_name = selection.method
        method_map = {
            "seasonal_naive": (seasonal_naive, {"season": 12}),
            "ewma": (ewma_forecast, {"alpha": 0.3}),
            "rolling_mean": (rolling_mean_forecast, {"window": 12}),
            "robust_trend": (robust_trend_forecast, {"window": 24}),
        }
        method_func, method_params = method_map[method_name]

        forecast = method_func(train_series, horizon=horizon_months, **method_params)
        actual_latest = float(series[-1])
        if not math.isfinite(actual_latest):
            actual_latest = 0.0
        if forecast and forecast[0] is not None and math.isfinite(forecast[0]):
            yhat_latest = float(forecast[0])
        else:
            yhat_latest = actual_latest

        fitted = method_func(train_series, horizon=len(train_series), **method_params)
        residuals = residuals_in_sample(train_series, fitted)
        half_width = mad_interval(residuals, z=1.96)

        flags = {
            "band_breach": band_breach(actual_latest, yhat_latest, half_width),
            "slope_reversal": slope_reversal(series, window=3),
            "volatility_spike": volatility_spike(series, lookback=6, z=2.5),
        }

        weights = {
            "band_breach": 0.5,
            "slope_reversal": 0.3,
            "volatility_spike": 0.2,
        }
        risk_value = risk_score(flags, weights)

        derived_warning = make_derived_query_result(
            operation="early_warning",
            params={
                "metric": metric,
                "sector": sector or "All",
                "end": str(end),
                "method": method_name,
                "season": 12,
                "train_points": len(train_series),
            },
            rows=[
                {
                    "risk_score": risk_value,
                    "band_breach": flags["band_breach"],
                    "slope_reversal": flags["slope_reversal"],
                    "volatility_spike": flags["volatility_spike"],
                    "actual": actual_latest,
                    "forecast": yhat_latest,
                    "half_width": half_width,
                }
            ],
            sources=[res.query_id],
            freshness_like=res.freshness,
            unit="unknown",
        )

        method_reasons: list[str] = []
        if stability_reason:
            method_reasons.append(stability_reason)
        method_reasons.extend(selection.reasons)

        narrative = self._format_early_warning_narrative(
            metric=metric,
            sector=sector or "All",
            risk_value=risk_value,
            flags=flags,
            actual=actual_latest,
            forecast=yhat_latest,
            half_width=half_width,
            warning_qid=derived_warning.query_id,
            data_qid=res.query_id,
            freshness_date=res.freshness.asof_date,
            method=method_name,
            method_reasons=method_reasons,
            confidence_hint=confidence_hint,
        )

        return narrative

    def _format_early_warning_narrative(
        self,
        metric: str,
        sector: str,
        risk_value: float,
        flags: dict[str, bool],
        actual: float,
        forecast: float,
        half_width: float,
        warning_qid: str,
        data_qid: str,
        freshness_date: str,
        method: str,
        method_reasons: Sequence[str] | None = None,
        confidence_hint: dict[str, Any] | None = None,
    ) -> str:
        """Format early-warning output as citation-ready narrative."""
        active_flags = [name for name, active in flags.items() if active]
        flags_str = ", ".join(active_flags) if active_flags else "None"

        lines = [
            "## Risk Assessment",
            f"- **Risk Score**: {risk_value:.1f}/100 (QID={warning_qid})",
            f"- **Active Flags**: {flags_str}",
            f"- **Metric**: {metric}",
            f"- **Sector**: {sector}",
            f"- **Evaluation date**: {freshness_date}",
            f"- **Baseline method**: {method}",
            "",
            "## Flag Details",
            f"- **Band Breach**: {'Yes' if flags['band_breach'] else 'No'} - "
            f"Actual {actual:.2f} vs forecast {forecast:.2f} +/- {half_width:.2f} (QID={warning_qid})",
            f"- **Slope Reversal**: {'Yes' if flags['slope_reversal'] else 'No'} (QID={data_qid})",
            f"- **Volatility Spike**: {'Yes' if flags['volatility_spike'] else 'No'} (QID={data_qid})",
        ]

        if method_reasons:
            lines.extend(["", "## Method Rationale"])
            for reason in method_reasons:
                lines.append(f"- {reason}")

        lines.extend(
            [
                "",
                "## Recommended Actions",
            ]
        )

        recommendations = self._generate_recommendations(metric, sector, flags)
        for i, rec in enumerate(recommendations, 1):
            lines.append(f"{i}. {rec}")

        lines.extend(
            [
                "",
                "## Freshness",
                f"- **Data as of**: {freshness_date} (QID={data_qid})",
                "",
                "## Reproducibility",
                "```python",
                f'PredictorAgent.early_warning(metric="{metric}", sector="{sector}", end=date.today())',
                "```",
            ]
        )

        confidence_line = self._confidence_hint_line(confidence_hint)
        if confidence_line:
            lines.extend(["", f"> {confidence_line}"])

        return "\n".join(lines)

    def _generate_recommendations(
        self, metric: str, sector: str, flags: dict[str, bool]
    ) -> list[str]:
        """Generate concrete actions based on active flags."""
        recommendations = []

        if flags.get("band_breach"):
            recommendations.append(
                f"Investigate {metric} deviation in {sector}: review recent policy changes, "
                "economic shocks, or measurement errors."
            )

        if flags.get("slope_reversal"):
            recommendations.append(
                f"Monitor {metric} trend reversal in {sector}: assess if this indicates "
                "structural shift or temporary fluctuation."
            )

        if flags.get("volatility_spike"):
            recommendations.append(
                f"Address {metric} volatility in {sector}: implement stabilization measures "
                "or investigate data quality issues."
            )

        # Default recommendations if no flags
        if not any(flags.values()):
            recommendations.extend(
                [
                    f"Continue monitoring {metric} in {sector} with current baseline.",
                    f"Update forecast model quarterly to reflect latest {metric} patterns.",
                    f"Establish early-warning thresholds for {sector}-specific risks.",
                ]
            )

        return recommendations[:3]  # Return max 3 recommendations

    def scenario_compare(
        self,
        metric: str,
        sector: str | None,
        start: date,
        end: date,
        horizon_months: int,
        methods: list[str],
        confidence_hint: dict[str, Any] | None = None,
    ) -> str:
        """Compare multiple baseline methods via forecasts and backtests."""
        logger.info(
            "scenario_compare: metric=%s sector=%s methods=%s horizon=%d",
            metric,
            sector,
            methods,
            horizon_months,
        )

        query_id = self._resolve_query_id(metric)
        try:
            res = self.client.run(query_id)
        except Exception as exc:
            logger.error("Failed to fetch time series: %s", exc)
            return f"Error: Unable to fetch data for {metric}."

        series, _ = self._extract_time_series(res, metric_field=metric)
        if len(series) < self.min_train_points:
            return (
                f"Insufficient data for comparison: {len(series)} points "
                f"(need >= {self.min_train_points})."
            )

        method_map = {
            "seasonal_naive": (seasonal_naive, {"season": 12}),
            "ewma": (ewma_forecast, {"alpha": 0.3}),
            "rolling_mean": (rolling_mean_forecast, {"window": 12}),
            "robust_trend": (robust_trend_forecast, {"window": 24}),
        }

        requested = [m.strip() for m in methods if m.strip()]
        selected_methods = [m for m in requested if m in method_map]
        if not selected_methods:
            selected_methods = list(method_map.keys())

        results: dict[str, dict[str, Any]] = {}
        backtest_rows: list[dict[str, float]] = []
        forecast_rows: list[dict[str, float]] = []

        for method_name in selected_methods:
            method_func, method_params = method_map[method_name]
            forecast_values = method_func(series, horizon=horizon_months, **method_params)
            backtest_metrics = rolling_origin_backtest(
                series,
                method_func,
                horizon=1,
                min_train=self.min_train_points,
                **method_params,
            )
            results[method_name] = {
                "forecast": forecast_values,
                "backtest": backtest_metrics,
            }
            backtest_rows.append(
                {
                    "method": method_name,
                    "mae": backtest_metrics.get("mae"),
                    "mape": backtest_metrics.get("mape"),
                    "rmse": backtest_metrics.get("rmse"),
                    "n": backtest_metrics.get("n"),
                }
            )
            for h, value in enumerate(forecast_values, start=1):
                if value is None or not isinstance(value, (int, float)):
                    continue
                val = float(value)
                if not math.isfinite(val):
                    continue
                forecast_rows.append(
                    {
                        "method": method_name,
                        "h": float(h),
                        "yhat": val,
                    }
                )

        derived_backtests = make_derived_query_result(
            operation="scenario_backtests",
            params={
                "metric": metric,
                "sector": sector or "All",
                "horizon_months": horizon_months,
                "methods": selected_methods,
            },
            rows=backtest_rows,
            sources=[res.query_id],
            freshness_like=res.freshness,
            unit="unknown",
        )

        derived_forecasts = make_derived_query_result(
            operation="scenario_forecasts",
            params={
                "metric": metric,
                "sector": sector or "All",
                "horizon_months": horizon_months,
                "methods": selected_methods,
            },
            rows=forecast_rows,
            sources=[res.query_id],
            freshness_like=res.freshness,
            unit="unknown",
        )

        narrative = self._format_scenario_narrative(
            metric=metric,
            sector=sector or "All",
            horizon=horizon_months,
            results=results,
            data_qid=res.query_id,
            freshness_date=res.freshness.asof_date,
            backtest_qid=derived_backtests.query_id,
            forecast_qid=derived_forecasts.query_id,
            confidence_hint=confidence_hint,
        )

        return narrative

    def _format_scenario_narrative(
        self,
        metric: str,
        sector: str,
        horizon: int,
        results: dict[str, dict[str, Any]],
        data_qid: str,
        freshness_date: str,
        backtest_qid: str,
        forecast_qid: str,
        confidence_hint: dict[str, Any] | None = None,
    ) -> str:
        """Format scenario comparison as citation-ready narrative."""
        method_names = list(results.keys())
        if not method_names:
            return "No methods available for comparison."

        def _fmt(value: Any, precision: int = 4, suffix: str = "") -> str:
            if isinstance(value, (int, float)) and math.isfinite(float(value)):
                return f"{float(value):.{precision}f}{suffix}"
            return "nan"

        lines = [
            "## Method Comparison",
            f"- **Metric**: {metric}",
            f"- **Sector**: {sector}",
            f"- **Horizon**: {horizon} months",
            f"- **Source data**: (QID={data_qid})",
            "",
            "### Backtest Performance",
            "| Method | MAE | MAPE | RMSE | QID |",
            "|--------|-----|------|------|-----|",
        ]

        for method_name in method_names:
            bt = results[method_name]["backtest"]
            lines.append(
                "| {method} | {mae} | {mape} | {rmse} | (QID={qid}) |".format(
                    method=method_name,
                    mae=_fmt(bt.get("mae")),
                    mape=_fmt(bt.get("mape"), precision=2, suffix="%"),
                    rmse=_fmt(bt.get("rmse")),
                    qid=backtest_qid,
                )
            )

        lines.extend(
            [
                "",
                f"### Forecast Comparison (QID={forecast_qid})",
                "| h | " + " | ".join(method_names) + " | Max Delta |",
                "|---|" + "|".join(["------"] * (len(method_names) + 1)) + "|",
            ]
        )

        for h in range(1, horizon + 1):
            row_vals = []
            horizon_values: list[float] = []
            for method_name in method_names:
                forecast = results[method_name]["forecast"]
                val = forecast[h - 1] if h <= len(forecast) else None
                if (
                    val is None
                    or not isinstance(val, (int, float))
                    or not math.isfinite(float(val))
                ):
                    row_vals.append("na")
                else:
                    num = float(val)
                    row_vals.append(f"{num:.2f}")
                    horizon_values.append(num)
            max_delta = (
                max(horizon_values) - min(horizon_values) if len(horizon_values) >= 2 else 0.0
            )
            row_vals.append(f"{max_delta:.2f}")
            lines.append(f"| {h} | " + " | ".join(row_vals) + " |")

        lines.extend(
            [
                "",
                "## Key Takeaways",
                "- Backtest metrics highlight relative accuracy across deterministic baselines.",
                "- Forecast rows capture divergence at each horizon (Max Delta column).",
                f"- All comparisons reference deterministic query (QID={data_qid}).",
                "",
                "## Freshness",
                f"- **Data as of**: {freshness_date} (QID={data_qid})",
                "",
                "## Reproducibility",
                "```python",
                f'PredictorAgent.scenario_compare(metric="{metric}", sector="{sector}", methods={method_names}, horizon_months={horizon})',
                "```",
            ]
        )

        confidence_line = self._confidence_hint_line(confidence_hint)
        if confidence_line:
            lines.extend(["", f"> {confidence_line}"])

        return "\n".join(lines)
