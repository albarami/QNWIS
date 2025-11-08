"""
Unit tests for baseline forecasting methods.

Tests cover expected behavior, edge cases, and failure modes for all
deterministic forecasters.
"""

from __future__ import annotations

import math

import pytest

from src.qnwis.forecast.baselines import (
    build_forecast_table,
    clamp_nonnegative,
    ewma_forecast,
    mad_interval,
    residuals_in_sample,
    robust_trend_forecast,
    rolling_mean_forecast,
    seasonal_naive,
)


class TestSeasonalNaive:
    """Test seasonal naive forecaster."""

    def test_sufficient_history(self) -> None:
        """Seasonal naive with sufficient history returns correct values."""
        series = [10.0, 12.0, 15.0, 11.0, 13.0, 16.0, 10.5, 12.5, 15.5, 11.5, 13.5, 16.5, 11.0]
        forecast = seasonal_naive(series, season=12, horizon=3)

        assert len(forecast) == 3
        assert forecast[0] == 12.0  # t-12
        assert forecast[1] == 15.0  # t-11
        assert forecast[2] == 11.0  # t-10

    def test_insufficient_history(self) -> None:
        """Seasonal naive with insufficient history returns None."""
        series = [10.0, 12.0, 15.0]  # Less than season=12
        forecast = seasonal_naive(series, season=12, horizon=3)

        assert len(forecast) == 3
        assert all(v is None for v in forecast)

    def test_exact_season_length(self) -> None:
        """Seasonal naive with exactly season points works."""
        series = list(range(12))
        forecast = seasonal_naive(series, season=12, horizon=2)

        assert len(forecast) == 2
        assert forecast[0] == 0  # t-12
        assert forecast[1] == 1  # t-11

    def test_empty_series(self) -> None:
        """Seasonal naive with empty series returns None."""
        series: list[float] = []
        forecast = seasonal_naive(series, season=12, horizon=3)

        assert len(forecast) == 3
        assert all(v is None for v in forecast)


class TestEWMAForecast:
    """Test exponentially weighted moving average forecaster."""

    def test_normal_forecast(self) -> None:
        """EWMA produces flat forecast from last smoothed value."""
        series = [10.0, 12.0, 11.0, 13.0]
        forecast = ewma_forecast(series, alpha=0.3, horizon=3)

        assert len(forecast) == 3
        # All forecast values should be equal (flat)
        assert forecast[0] == forecast[1] == forecast[2]
        # Should be between min and max of series
        assert min(series) <= forecast[0] <= max(series)

    def test_high_alpha_responsive(self) -> None:
        """EWMA with high alpha is more responsive to recent values."""
        series = [10.0, 10.0, 10.0, 20.0]  # Sudden jump
        forecast_high = ewma_forecast(series, alpha=0.9, horizon=1)[0]
        forecast_low = ewma_forecast(series, alpha=0.1, horizon=1)[0]

        # High alpha should be closer to 20.0
        assert forecast_high > forecast_low
        assert forecast_high > 15.0
        assert forecast_low < 15.0

    def test_invalid_alpha_raises(self) -> None:
        """EWMA with alpha outside (0, 1] raises ValueError."""
        series = [10.0, 12.0, 11.0]

        with pytest.raises(ValueError, match="alpha must be in"):
            ewma_forecast(series, alpha=0.0, horizon=3)

        with pytest.raises(ValueError, match="alpha must be in"):
            ewma_forecast(series, alpha=1.5, horizon=3)

    def test_empty_series(self) -> None:
        """EWMA with empty series returns zeros."""
        series: list[float] = []
        forecast = ewma_forecast(series, alpha=0.3, horizon=3)

        assert len(forecast) == 3
        assert all(v == 0.0 for v in forecast)

    def test_single_point(self) -> None:
        """EWMA with single point returns that value."""
        series = [42.0]
        forecast = ewma_forecast(series, alpha=0.3, horizon=3)

        assert len(forecast) == 3
        assert all(v == 42.0 for v in forecast)


class TestRollingMeanForecast:
    """Test rolling mean forecaster."""

    def test_sufficient_window(self) -> None:
        """Rolling mean with sufficient data returns mean of last window."""
        series = [10.0, 12.0, 14.0, 16.0, 18.0, 20.0]
        forecast = rolling_mean_forecast(series, window=3, horizon=2)

        expected_mean = (14.0 + 16.0 + 18.0 + 20.0) / 4  # Wait, window=3 means last 3
        expected_mean = (16.0 + 18.0 + 20.0) / 3
        assert len(forecast) == 2
        assert forecast[0] == pytest.approx(expected_mean)
        assert forecast[1] == pytest.approx(expected_mean)

    def test_insufficient_window(self) -> None:
        """Rolling mean with insufficient data returns None."""
        series = [10.0, 12.0]
        forecast = rolling_mean_forecast(series, window=5, horizon=2)

        assert len(forecast) == 2
        assert all(v is None for v in forecast)

    def test_exact_window_length(self) -> None:
        """Rolling mean with exact window length works."""
        series = [10.0, 20.0, 30.0]
        forecast = rolling_mean_forecast(series, window=3, horizon=1)

        assert len(forecast) == 1
        assert forecast[0] == 20.0  # Mean of all three


class TestRobustTrendForecast:
    """Test robust trend (Theil-Sen) forecaster."""

    def test_linear_trend(self) -> None:
        """Robust trend extrapolates linear trend correctly."""
        series = [10.0, 12.0, 14.0, 16.0, 18.0, 20.0]  # Perfect linear
        forecast = robust_trend_forecast(series, window=6, horizon=3)

        assert len(forecast) == 3
        # Should extrapolate with slope ≈ 2.0
        assert forecast[0] == pytest.approx(22.0, abs=0.1)
        assert forecast[1] == pytest.approx(24.0, abs=0.1)
        assert forecast[2] == pytest.approx(26.0, abs=0.1)

    def test_flat_series(self) -> None:
        """Robust trend with flat series returns constant."""
        series = [15.0] * 10
        forecast = robust_trend_forecast(series, window=10, horizon=3)

        assert len(forecast) == 3
        assert all(v == pytest.approx(15.0) for v in forecast)

    def test_with_outlier(self) -> None:
        """Robust trend is resilient to outliers."""
        series = [10.0, 12.0, 14.0, 100.0, 16.0, 18.0, 20.0]  # Outlier at index 3
        forecast = robust_trend_forecast(series, window=7, horizon=1)

        # Should still detect slope ≈ 2.0 despite outlier
        assert 20.0 < forecast[0] < 25.0

    def test_insufficient_data(self) -> None:
        """Robust trend with < 2 points returns last value."""
        series = [42.0]
        forecast = robust_trend_forecast(series, window=24, horizon=3)

        assert len(forecast) == 3
        assert all(v == 42.0 for v in forecast)

    def test_empty_series(self) -> None:
        """Robust trend with empty series returns zeros."""
        series: list[float] = []
        forecast = robust_trend_forecast(series, window=24, horizon=3)

        assert len(forecast) == 3
        assert all(v == 0.0 for v in forecast)


class TestResidualsInSample:
    """Test residual computation."""

    def test_aligned_residuals(self) -> None:
        """Residuals computed correctly for aligned series."""
        series = [10.0, 12.0, 14.0]
        fitted = [9.5, 12.5, 13.5]
        residuals = residuals_in_sample(series, fitted)

        assert len(residuals) == 3
        assert residuals[0] == pytest.approx(0.5)
        assert residuals[1] == pytest.approx(-0.5)
        assert residuals[2] == pytest.approx(0.5)

    def test_skip_none_fitted(self) -> None:
        """Residuals skip positions where fitted is None."""
        series = [10.0, 12.0, 14.0]
        fitted = [9.5, None, 13.5]  # type: ignore
        residuals = residuals_in_sample(series, fitted)

        assert len(residuals) == 2
        assert residuals[0] == pytest.approx(0.5)
        assert residuals[1] == pytest.approx(0.5)

    def test_mismatched_lengths(self) -> None:
        """Residuals handle mismatched lengths by using minimum."""
        series = [10.0, 12.0, 14.0, 16.0]
        fitted = [9.5, 12.5]
        residuals = residuals_in_sample(series, fitted)

        assert len(residuals) == 2


class TestMADInterval:
    """Test MAD-based prediction interval computation."""

    def test_normal_residuals(self) -> None:
        """MAD interval computed correctly for normal residuals."""
        residuals = [1.0, -1.0, 2.0, -2.0, 0.5, -0.5]
        half_width = mad_interval(residuals, z=1.96)

        # MAD ≈ 1.0, σ ≈ 1.4826, half_width ≈ 2.906
        assert half_width > 0
        assert 2.0 < half_width < 4.0

    def test_zero_residuals(self) -> None:
        """MAD interval with zero residuals returns zero."""
        residuals = [0.0] * 10
        half_width = mad_interval(residuals, z=1.96)

        assert half_width == 0.0

    def test_empty_residuals(self) -> None:
        """MAD interval with empty residuals returns zero."""
        residuals: list[float] = []
        half_width = mad_interval(residuals, z=1.96)

        assert half_width == 0.0

    def test_finite_clamping(self) -> None:
        """MAD interval clamps non-finite values to zero."""
        # This is a safety check; normal computation shouldn't produce inf
        residuals = [1.0, 2.0, 3.0]
        half_width = mad_interval(residuals, z=1.96)

        assert math.isfinite(half_width)


class TestClampNonnegative:
    """Test non-negative clamping."""

    def test_clamp_negatives(self) -> None:
        """Negative values clamped to zero."""
        values = [10.0, -5.0, 0.0, 15.0, -2.0]
        clamped = clamp_nonnegative(values)

        assert clamped == [10.0, 0.0, 0.0, 15.0, 0.0]

    def test_preserve_none(self) -> None:
        """None values preserved."""
        values = [10.0, None, -5.0, 15.0]
        clamped = clamp_nonnegative(values)

        assert clamped == [10.0, None, 0.0, 15.0]

    def test_all_positive(self) -> None:
        """All positive values unchanged."""
        values = [10.0, 20.0, 30.0]
        clamped = clamp_nonnegative(values)

        assert clamped == values


class TestBuildForecastTable:
    """Test forecast table builder."""

    def test_standard_table(self) -> None:
        """Forecast table built correctly."""
        forecast = [10.0, 12.0, 14.0]
        table = build_forecast_table(
            method="ewma",
            history=[1.0, 2.0, 3.0],
            forecast=forecast,
            half_width=2.0,
            start_idx=3,
        )

        assert len(table) == 3
        assert table[0]["h"] == 1.0
        assert table[0]["yhat"] == 10.0
        assert table[0]["lo"] == 8.0
        assert table[0]["hi"] == 12.0
        assert table[0]["t_idx"] == 4.0

    def test_skip_none_forecast(self) -> None:
        """Forecast table skips None values."""
        forecast = [10.0, None, 14.0]
        table = build_forecast_table(
            method="seasonal_naive",
            history=[],
            forecast=forecast,
            half_width=1.0,
            start_idx=0,
        )

        assert len(table) == 2
        assert table[0]["h"] == 1.0
        assert table[1]["h"] == 3.0

    def test_clamp_lower_bound(self) -> None:
        """Lower bound clamped to zero for negative intervals."""
        forecast = [2.0]
        table = build_forecast_table(
            method="test",
            history=[],
            forecast=forecast,
            half_width=5.0,  # Would give lo = -3
            start_idx=0,
        )

        assert table[0]["lo"] == 0.0
        assert table[0]["hi"] == 7.0
