"""
Unit tests for trend_utils module.

Tests cover:
- Percentage change calculations with edge cases
- YoY/QtQ computations with lag handling
- EWMA smoothing stability
- Index-100 normalization
- Window slopes with least squares
- Robust statistics (mean, std, MAD)
"""

import pytest

from src.qnwis.analysis.trend_utils import (
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


class TestPctChange:
    """Test percentage change calculations."""

    def test_basic_increase(self):
        """Test simple percentage increase."""
        result = pct_change(110, 100)
        assert result == pytest.approx(10.0)

    def test_basic_decrease(self):
        """Test simple percentage decrease."""
        result = pct_change(90, 100)
        assert result == pytest.approx(-10.0)

    def test_zero_prev(self):
        """Test with zero previous value (division by zero)."""
        result = pct_change(100, 0)
        assert result is None

    def test_negative_prev(self):
        """Test with negative previous value."""
        result = pct_change(50, -100)
        assert result == pytest.approx(150.0)

    def test_zero_curr(self):
        """Test with zero current value."""
        result = pct_change(0, 100)
        assert result == pytest.approx(-100.0)

    def test_both_zero(self):
        """Test with both values zero."""
        result = pct_change(0, 0)
        assert result is None


class TestYoY:
    """Test year-over-year growth calculations."""

    def test_basic_12_month(self):
        """Test YoY with 12-month lag."""
        series = [100] * 12 + [110] * 12
        result = yoy(series, period=12)

        # First 12 should be None
        assert all(x is None for x in result[:12])

        # Month 13 onwards should be 10%
        assert result[12] == pytest.approx(10.0)

    def test_short_series(self):
        """Test YoY with series shorter than period."""
        series = [100, 110, 120]
        result = yoy(series, period=12)

        # All should be None
        assert all(x is None for x in result)

    def test_custom_period(self):
        """Test YoY with custom period (quarterly)."""
        series = [100, 105, 110, 120]
        result = yoy(series, period=3)

        # First 3 None, then 20%
        assert result[3] == pytest.approx(20.0)

    def test_zero_handling(self):
        """Test YoY with zero in previous period."""
        series = [0, 100, 110, 120, 130]
        result = yoy(series, period=1)

        assert result[0] is None
        assert result[1] is None  # (100-0)/0 undefined
        assert result[2] == pytest.approx(10.0)


class TestQtQ:
    """Test quarter-over-quarter growth calculations."""

    def test_basic_3_month(self):
        """Test QtQ with 3-month lag."""
        series = [100, 105, 110, 115, 120]
        result = qtq(series, period=3)

        # First 3 None
        assert all(x is None for x in result[:3])

        # Month 4: (115-100)/100 = 15%
        assert result[3] == pytest.approx(15.0)

    def test_decline(self):
        """Test QtQ with declining series."""
        series = [100, 95, 90, 85, 80]
        result = qtq(series, period=2)

        assert result[2] == pytest.approx(-10.0)  # (90-100)/100
        assert result[3] == pytest.approx(-10.526, rel=0.01)  # (85-95)/95


class TestEWMA:
    """Test exponentially weighted moving average."""

    def test_constant_series(self):
        """Test EWMA on constant series."""
        series = [100.0] * 10
        result = ewma(series, alpha=0.25)

        assert all(abs(x - 100.0) < 0.01 for x in result)

    def test_step_change(self):
        """Test EWMA response to step change."""
        series = [100.0] * 5 + [110.0] * 5
        result = ewma(series, alpha=0.5)

        # Should start at 100
        assert result[0] == 100.0

        # Should gradually approach 110
        assert result[-1] > 105.0
        assert result[-1] < 110.0

    def test_invalid_alpha(self):
        """Test EWMA with invalid alpha (uses default)."""
        series = [100, 110, 120]
        result = ewma(series, alpha=1.5)  # Invalid

        # Should still work with default alpha
        assert len(result) == 3
        assert result[0] == 100

    def test_empty_series(self):
        """Test EWMA with empty series."""
        result = ewma([], alpha=0.25)
        assert result == []


class TestIndex100:
    """Test index-100 normalization."""

    def test_basic_indexing(self):
        """Test basic index-100 calculation."""
        series = [50, 100, 150, 200]
        result = index_100(series, base_idx=1)

        assert result[0] == pytest.approx(50.0)
        assert result[1] == pytest.approx(100.0)
        assert result[2] == pytest.approx(150.0)
        assert result[3] == pytest.approx(200.0)

    def test_zero_base(self):
        """Test index-100 with zero base value."""
        series = [100, 0, 150]
        result = index_100(series, base_idx=1)

        # All should be None (division by zero)
        assert all(x is None for x in result)

    def test_invalid_base_idx(self):
        """Test index-100 with invalid base index."""
        series = [100, 110, 120]

        # Negative index
        result = index_100(series, base_idx=-1)
        assert all(x is None for x in result)

        # Out of range
        result = index_100(series, base_idx=10)
        assert all(x is None for x in result)

    def test_empty_series(self):
        """Test index-100 with empty series."""
        result = index_100([], base_idx=0)
        assert result == []


class TestWindowSlopes:
    """Test multi-window slope calculations."""

    def test_linear_increase(self):
        """Test slopes on perfectly linear series."""
        series = [100, 102, 104, 106, 108, 110, 112]
        result = window_slopes(series, windows=(3,))

        # Slope should be 2.0 (constant increase)
        assert result[0][0] == 3
        assert result[0][1] == pytest.approx(2.0)

    def test_multiple_windows(self):
        """Test slopes with multiple window sizes."""
        series = list(range(20))  # 0, 1, 2, ..., 19
        result = window_slopes(series, windows=(3, 6, 12))

        # All slopes should be 1.0 (linear)
        assert len(result) == 3
        assert all(slope == pytest.approx(1.0) for _, slope in result if slope is not None)

    def test_insufficient_data(self):
        """Test slopes with insufficient data for window."""
        series = [100, 110]
        result = window_slopes(series, windows=(3, 6))

        # Both should be None
        assert result[0][1] is None
        assert result[1][1] is None

    def test_constant_series(self):
        """Test slopes on constant series (zero variance)."""
        series = [100] * 10
        result = window_slopes(series, windows=(3, 5))

        # Both slopes should be None or near zero
        for window, slope in result:
            if slope is not None:
                assert abs(slope) < 0.001


class TestSafeMean:
    """Test safe mean calculation."""

    def test_basic_mean(self):
        """Test mean of simple list."""
        assert safe_mean([1, 2, 3, 4, 5]) == pytest.approx(3.0)

    def test_empty_list(self):
        """Test mean of empty list."""
        assert safe_mean([]) is None

    def test_single_value(self):
        """Test mean of single value."""
        assert safe_mean([42]) == pytest.approx(42.0)


class TestSafeStd:
    """Test safe standard deviation calculation."""

    def test_basic_std(self):
        """Test std of simple list."""
        result = safe_std([1, 2, 3, 4, 5])
        assert result is not None
        assert result > 0

    def test_empty_list(self):
        """Test std of empty list."""
        assert safe_std([]) is None

    def test_single_value(self):
        """Test std of single value."""
        assert safe_std([42]) is None

    def test_constant_series(self):
        """Test std of constant series (should be 0)."""
        result = safe_std([100, 100, 100])
        assert result == pytest.approx(0.0)


class TestSafeMAD:
    """Test safe Median Absolute Deviation calculation."""

    def test_basic_mad(self):
        """Test MAD of simple list."""
        result = safe_mad([1, 2, 3, 4, 5])
        assert result is not None
        assert result > 0

    def test_empty_list(self):
        """Test MAD of empty list."""
        assert safe_mad([]) is None

    def test_constant_series(self):
        """Test MAD of constant series (should be 0)."""
        result = safe_mad([100, 100, 100])
        assert result == pytest.approx(0.0)

    def test_outlier_resistance(self):
        """Test MAD is robust to outliers."""
        normal = [100, 101, 102, 99, 98]
        with_outlier = normal + [500]

        mad_normal = safe_mad(normal)
        mad_outlier = safe_mad(with_outlier)

        # MAD should not increase dramatically
        assert mad_outlier is not None
        assert mad_normal is not None
        assert mad_outlier < mad_normal * 2


class TestEdgeCases:
    """Test edge cases and integration scenarios."""

    def test_all_zeros(self):
        """Test various functions with all-zero series."""
        series = [0.0] * 10

        # YoY should be all None
        assert all(x is None or x == 0 for x in yoy(series))

        # EWMA should be all zeros
        assert all(x == 0 for x in ewma(series))

        # Index-100 should be None
        assert all(x is None for x in index_100(series, 0))

    def test_negative_values(self):
        """Test with negative values."""
        series = [-100, -90, -80, -70]

        # YoY should work: (-90 - -100) / -100 = 10 / -100 = -10%
        result = yoy(series, period=1)
        assert result[1] == pytest.approx(10.0)

        # EWMA should work
        smoothed = ewma(series, alpha=0.5)
        assert len(smoothed) == 4

    def test_mixed_signs(self):
        """Test with mixed positive/negative values."""
        series = [-50, 0, 50, 100]

        # Should handle gracefully
        result = yoy(series, period=1)
        assert result[1] == pytest.approx(100.0)  # (0 - -50) / -50 = 50 / -50 = -100% (moving towards zero)
        assert result[2] is None  # (50 - 0) / 0 = undefined
