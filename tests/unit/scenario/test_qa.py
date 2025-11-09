"""
Unit tests for scenario QA functions.

Tests cover:
- MAE, MAPE, SMAPE calculations
- backtest_forecast function
- stability_check function
- sla_benchmark function
- Edge cases and error handling
"""

import pytest

from src.qnwis.scenario.qa import (
    backtest_forecast,
    mean_absolute_error,
    mean_absolute_percentage_error,
    sla_benchmark,
    stability_check,
    symmetric_mean_absolute_percentage_error,
)


class TestErrorMetrics:
    """Test error metric calculations."""

    def test_mean_absolute_error(self):
        """Test MAE calculation."""
        actual = [100.0, 105.0, 110.0]
        predicted = [98.0, 106.0, 112.0]
        mae = mean_absolute_error(actual, predicted)
        # |100-98| + |105-106| + |110-112| = 2 + 1 + 2 = 5, avg = 5/3
        assert mae == pytest.approx(5.0 / 3.0)

    def test_mean_absolute_error_perfect_fit(self):
        """Test MAE with perfect fit returns 0."""
        actual = [100.0, 105.0, 110.0]
        predicted = [100.0, 105.0, 110.0]
        mae = mean_absolute_error(actual, predicted)
        assert mae == 0.0

    def test_mean_absolute_error_length_mismatch(self):
        """Test MAE with length mismatch raises error."""
        actual = [100.0, 105.0]
        predicted = [98.0]
        with pytest.raises(ValueError, match="Length mismatch"):
            mean_absolute_error(actual, predicted)

    def test_mean_absolute_error_empty_lists(self):
        """Test MAE with empty lists raises error."""
        with pytest.raises(ValueError, match="empty"):
            mean_absolute_error([], [])

    def test_mean_absolute_percentage_error(self):
        """Test MAPE calculation."""
        actual = [100.0, 200.0]
        predicted = [90.0, 210.0]
        # |100-90|/100 = 0.10, |200-210|/200 = 0.05
        # avg = (10% + 5%) / 2 = 7.5%
        mape = mean_absolute_percentage_error(actual, predicted)
        assert mape == pytest.approx(7.5)

    def test_mean_absolute_percentage_error_with_epsilon(self):
        """Test MAPE skips near-zero actuals."""
        actual = [0.001, 100.0]
        predicted = [10.0, 110.0]
        # First value should be skipped (near zero)
        # Only |100-110|/100 = 10% used
        mape = mean_absolute_percentage_error(actual, predicted, eps=1.0)
        assert mape == pytest.approx(10.0)

    def test_symmetric_mean_absolute_percentage_error(self):
        """Test SMAPE calculation."""
        actual = [100.0, 200.0]
        predicted = [110.0, 180.0]
        # SMAPE = 100 * |actual - predicted| / ((|actual| + |predicted|) / 2)
        # For 100 vs 110: 100 * 10 / 105 = 9.52%
        # For 200 vs 180: 100 * 20 / 190 = 10.53%
        # avg = (9.52 + 10.53) / 2 ≈ 10.03%
        smape = symmetric_mean_absolute_percentage_error(actual, predicted)
        assert smape == pytest.approx(10.0, abs=0.1)

    def test_symmetric_mean_absolute_percentage_error_both_zero(self):
        """Test SMAPE with both values near zero."""
        actual = [0.0, 100.0]
        predicted = [0.0, 100.0]
        smape = symmetric_mean_absolute_percentage_error(actual, predicted, eps=1e-10)
        assert smape == 0.0


class TestBacktestForecast:
    """Test backtest_forecast function."""

    def test_backtest_forecast_basic(self):
        """Test backtest with basic data."""
        actual = [100.0, 105.0, 110.0]
        predicted = [98.0, 106.0, 112.0]
        metrics = backtest_forecast(actual, predicted)

        assert "mae" in metrics
        assert "mape" in metrics
        assert "smape" in metrics
        assert metrics["n"] == 3
        assert metrics["mae"] > 0

    def test_backtest_forecast_perfect_fit(self):
        """Test backtest with perfect predictions."""
        actual = [100.0, 105.0, 110.0]
        predicted = [100.0, 105.0, 110.0]
        metrics = backtest_forecast(actual, predicted)

        assert metrics["mae"] == 0.0
        assert metrics["mape"] == 0.0
        assert metrics["smape"] == 0.0

    def test_backtest_forecast_length_mismatch(self):
        """Test backtest with length mismatch raises error."""
        actual = [100.0, 105.0]
        predicted = [98.0]
        with pytest.raises(ValueError, match="Length mismatch"):
            backtest_forecast(actual, predicted)

    def test_backtest_forecast_empty_data(self):
        """Test backtest with empty data raises error."""
        with pytest.raises(ValueError, match="empty"):
            backtest_forecast([], [])


class TestStabilityCheck:
    """Test stability_check function."""

    def test_stability_check_stable(self):
        """Test stability check with stable forecast."""
        values = [100.0, 102.0, 104.0, 106.0, 108.0, 110.0]
        result = stability_check(values)

        assert result["stable"] is True
        assert len(result["flags"]) == 0
        assert result["cv"] < 0.5
        assert result["reason"] == "OK"

    def test_stability_check_high_volatility(self):
        """Test stability check detects high volatility."""
        values = [100.0, 50.0, 200.0, 30.0, 180.0, 60.0]
        result = stability_check(values)

        assert result["stable"] is False
        assert "high_volatility" in result["flags"]
        assert result["cv"] > 0.5

    def test_stability_check_frequent_reversals(self):
        """Test stability check detects frequent reversals."""
        values = [100.0, 110.0, 105.0, 115.0, 108.0, 120.0, 110.0]
        result = stability_check(values)

        assert result["stable"] is False
        assert "frequent_reversals" in result["flags"]

    def test_stability_check_range_explosion(self):
        """Test stability check detects range explosion."""
        # Need enough values for window size (default 6)
        values = [10.0, 15.0, 12.0, 100.0, 95.0, 105.0]  # Ratio = 10.5 > 5
        result = stability_check(values)

        assert result["stable"] is False
        assert "range_explosion" in result["flags"]
        assert result["range_ratio"] > 5.0

    def test_stability_check_insufficient_data(self):
        """Test stability check with insufficient data."""
        values = [100.0, 105.0]
        result = stability_check(values, window=6)

        assert result["stable"] is True
        assert "Insufficient data" in result["reason"]


class TestSLABenchmark:
    """Test sla_benchmark function."""

    def test_sla_benchmark_compliant(self):
        """Test SLA benchmark with compliant function."""
        series = [100.0] * 96  # 8-year monthly series

        def fast_transform(s):
            return [v * 1.1 for v in s]

        result = sla_benchmark(series, fast_transform, iterations=5)

        assert result["sla_compliant"] is True
        assert result["latency_p50"] is not None
        assert result["latency_p95"] is not None
        assert result["latency_max"] is not None
        assert result["iterations"] == 5
        assert result["series_length"] == 96

    def test_sla_benchmark_with_error(self):
        """Test SLA benchmark with failing function."""
        series = [100.0] * 96

        def failing_transform(s):
            raise ValueError("Test error")

        result = sla_benchmark(series, failing_transform, iterations=5)

        assert result["sla_compliant"] is False
        assert "Function error" in result["reason"]
        assert result["latency_p50"] is None

    def test_sla_benchmark_custom_threshold(self):
        """Test SLA benchmark with custom threshold."""
        series = [100.0] * 10

        def simple_transform(s):
            return [v * 1.1 for v in s]

        result = sla_benchmark(
            series, simple_transform, iterations=5, threshold_ms=1.0
        )

        # Function should complete in <1ms, so it should be compliant
        # (unless system is extremely slow)
        assert "latency_p95" in result
        assert "latency_max" in result
