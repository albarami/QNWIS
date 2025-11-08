"""
Unit tests for backtesting framework.

Tests rolling-origin validation and method selection logic.
"""

from __future__ import annotations

import math

from src.qnwis.forecast.backtest import choose_baseline, rolling_origin_backtest
from src.qnwis.forecast.baselines import ewma_forecast


class TestRollingOriginBacktest:
    """Test walk-forward backtesting."""

    def test_sufficient_data(self) -> None:
        """Backtest with sufficient data returns valid metrics."""
        series = [10.0 + i * 0.5 for i in range(50)]  # Linear trend
        metrics = rolling_origin_backtest(
            series, ewma_forecast, horizon=1, min_train=24, alpha=0.3
        )

        assert "mae" in metrics
        assert "mape" in metrics
        assert "rmse" in metrics
        assert "n" in metrics

        assert metrics["n"] > 0
        assert math.isfinite(metrics["mae"])
        assert math.isfinite(metrics["rmse"])
        assert metrics["mae"] >= 0
        assert metrics["rmse"] >= 0

    def test_insufficient_data(self) -> None:
        """Backtest with insufficient data returns NaN."""
        series = [10.0, 12.0, 14.0]  # Only 3 points
        metrics = rolling_origin_backtest(
            series, ewma_forecast, horizon=1, min_train=24, alpha=0.3
        )

        assert math.isnan(metrics["mae"])
        assert math.isnan(metrics["rmse"])
        assert metrics["n"] == 0

    def test_mae_computation(self) -> None:
        """MAE computed correctly."""
        # Series with known errors
        series = [10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0, 18.0, 19.0, 20.0] * 3
        metrics = rolling_origin_backtest(
            series, ewma_forecast, horizon=1, min_train=10, alpha=0.3
        )

        # For a trending series, EWMA should have non-zero but reasonable MAE
        assert 0 < metrics["mae"] < 5.0

    def test_mape_safe_with_zeros(self) -> None:
        """MAPE handles near-zero actuals safely."""
        series = [0.0, 0.001, 0.002, 0.001, 0.0] * 6
        metrics = rolling_origin_backtest(
            series, ewma_forecast, horizon=1, min_train=5, alpha=0.3
        )

        # Should not crash; MAPE may be NaN if all actuals near zero
        assert "mape" in metrics

    def test_method_failure_handling(self) -> None:
        """Backtest handles method failures gracefully."""

        def failing_method(series, horizon, **kwargs):
            raise ValueError("Intentional failure")

        series = [10.0] * 30
        metrics = rolling_origin_backtest(
            series, failing_method, horizon=1, min_train=10
        )

        # Should return NaN metrics without crashing
        assert math.isnan(metrics["mae"])
        assert metrics["n"] == 0

    def test_multi_horizon(self) -> None:
        """Backtest with horizon > 1 uses first forecast point."""
        series = [10.0 + i for i in range(40)]
        metrics = rolling_origin_backtest(
            series, ewma_forecast, horizon=3, min_train=20, alpha=0.3
        )

        # Should complete successfully
        assert metrics["n"] > 0
        assert math.isfinite(metrics["mae"])


class TestChooseBaseline:
    """Test automatic method selection."""

    def test_sufficient_data(self) -> None:
        """Method selection with sufficient data returns valid method."""
        series = [10.0 + i * 0.3 for i in range(50)]  # Linear trend
        result = choose_baseline(series, season=12)

        assert result.method in ["seasonal_naive", "ewma", "rolling_mean", "robust_trend"]
        assert isinstance(result.leaderboard, dict)
        assert isinstance(result.reasons, list)
        assert len(result.reasons) > 0

    def test_insufficient_data_defaults_ewma(self) -> None:
        """Method selection with insufficient data defaults to EWMA."""
        series = [10.0, 12.0, 14.0]  # Less than 24 points
        result = choose_baseline(series, season=12)

        assert result.method == "ewma"
        assert len(result.leaderboard) == 0
        assert any("Insufficient history" in r for r in result.reasons)

    def test_selects_lowest_mae(self) -> None:
        """Method selection picks lowest MAE method."""
        # Create series where robust_trend should win (clear linear trend)
        series = [10.0 + i * 2.0 for i in range(50)]
        result = choose_baseline(series, season=12)

        # Robust trend or EWMA should be selected for linear trend
        assert result.method in ["robust_trend", "ewma"]
        assert len(result.leaderboard) > 0
        assert any("lowest MAE" in r for r in result.reasons)

    def test_handles_all_failures(self) -> None:
        """Method selection with all failures defaults to EWMA."""
        # Edge case: series that might cause issues
        series = [float("nan")] * 30
        result = choose_baseline(series, season=12)

        # Should default to EWMA without crashing
        assert result.method == "ewma"

    def test_seasonal_data_prefers_seasonal(self) -> None:
        """Method selection with seasonal data may prefer seasonal_naive."""
        # Create series with strong seasonality
        import math

        series = [10.0 + 5.0 * math.sin(i * 2 * math.pi / 12) for i in range(60)]
        result = choose_baseline(series, season=12)

        # Should be one of the valid methods
        assert result.method in ["seasonal_naive", "ewma", "rolling_mean", "robust_trend"]
        # For strong seasonal pattern, seasonal_naive should win
        if result.method == "seasonal_naive":
            assert any("seasonality" in r.lower() for r in result.reasons)

    def test_flat_series(self) -> None:
        """Method selection with flat series works."""
        series = [15.0] * 40
        result = choose_baseline(series, season=12)

        # Any method should work for flat series
        assert result.method in ["seasonal_naive", "ewma", "rolling_mean", "robust_trend"]
        assert len(result.leaderboard) > 0
