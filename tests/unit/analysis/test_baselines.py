"""
Unit tests for baselines module.

Tests cover:
- Seasonal baseline computation
- Anomaly gap calculations
- Seasonal anomaly detection
- Trend-adjusted baselines
- Baseline fit statistics
"""

import pytest

from src.qnwis.analysis.baselines import (
    anomaly_gaps,
    detect_seasonal_anomalies,
    seasonal_baseline,
    summarize_baseline_fit,
    trend_adjusted_baseline,
)


class TestSeasonalBaseline:
    """Test seasonal baseline computation."""

    def test_basic_12_month_pattern(self):
        """Test baseline with 12-month seasonal pattern."""
        # Create series with repeating pattern: 100, 110, 105
        series = [100, 110, 105] * 4  # 12 months
        result = seasonal_baseline(series, season=3)

        # Should have all expected keys
        assert 'mean_per_phase' in result
        assert 'baseline' in result
        assert 'upper_band' in result
        assert 'lower_band' in result

        # Mean per phase should be 100, 110, 105
        assert result['mean_per_phase'][0] == pytest.approx(100.0)
        assert result['mean_per_phase'][1] == pytest.approx(110.0)
        assert result['mean_per_phase'][2] == pytest.approx(105.0)

        # Baseline should repeat pattern
        assert len(result['baseline']) == 12

    def test_insufficient_data(self):
        """Test baseline with insufficient data."""
        series = [100, 110]
        result = seasonal_baseline(series, season=12)

        # Should return series as-is for baseline
        assert result['baseline'] == series

    def test_perfect_seasonal_pattern(self):
        """Test baseline with perfect repeating pattern."""
        series = [100, 200] * 6  # 12 months, perfect pattern
        result = seasonal_baseline(series, season=2)

        # Phase 0 should be 100, phase 1 should be 200
        assert result['mean_per_phase'][0] == pytest.approx(100.0)
        assert result['mean_per_phase'][1] == pytest.approx(200.0)

        # No deviation, so bands should be tight
        assert all(result['upper_band'][i] >= result['baseline'][i] for i in range(len(series)))

    def test_band_computation(self):
        """Test upper/lower band computation."""
        series = [100, 110, 90, 100, 110, 90]
        result = seasonal_baseline(series, season=3)

        # Bands should exist and be reasonable
        assert len(result['upper_band']) == len(series)
        assert len(result['lower_band']) == len(series)

        # Upper band should be >= baseline
        assert all(result['upper_band'][i] >= result['baseline'][i] for i in range(len(series)))

        # Lower band should be <= baseline (or 0)
        assert all(result['lower_band'][i] <= result['baseline'][i] for i in range(len(series)))

    def test_zero_variance_series(self):
        """Test baseline with constant series (zero variance)."""
        series = [100] * 12
        result = seasonal_baseline(series, season=12)

        # All phases should be 100
        assert all(phase == pytest.approx(100.0) for phase in result['mean_per_phase'])

        # Bands should equal baseline
        assert result['upper_band'] == result['baseline']
        assert result['lower_band'] == result['baseline']


class TestAnomalyGaps:
    """Test anomaly gap calculations."""

    def test_basic_gaps(self):
        """Test gap calculation with simple series."""
        series = [110, 90, 105]
        baseline = [100, 100, 100]

        gaps = anomaly_gaps(series, baseline)

        assert gaps[0] == pytest.approx(10.0)   # 10% above
        assert gaps[1] == pytest.approx(-10.0)  # 10% below
        assert gaps[2] == pytest.approx(5.0)    # 5% above

    def test_zero_baseline(self):
        """Test gap with zero baseline (division by zero)."""
        series = [100, 110, 120]
        baseline = [0, 100, 0]

        gaps = anomaly_gaps(series, baseline)

        assert gaps[0] is None  # Division by zero
        assert gaps[1] == pytest.approx(10.0)
        assert gaps[2] is None  # Division by zero

    def test_mismatched_lengths(self):
        """Test gap with mismatched series and baseline lengths."""
        series = [100, 110, 120]
        baseline = [100, 110]

        gaps = anomaly_gaps(series, baseline)

        # Should return all None
        assert all(g is None for g in gaps)

    def test_negative_values(self):
        """Test gap with negative values."""
        series = [-90, -110]
        baseline = [-100, -100]

        gaps = anomaly_gaps(series, baseline)

        # (-90 - -100) / -100 = 10 / -100 = -10% (closer to zero is "above" for negatives)
        # (-110 - -100) / -100 = -10 / -100 = 10% (further from zero is "below" for negatives)
        assert gaps[0] == pytest.approx(-10.0)
        assert gaps[1] == pytest.approx(10.0)


class TestDetectSeasonalAnomalies:
    """Test seasonal anomaly detection."""

    def test_detects_clear_anomaly(self):
        """Test detection of clear seasonal anomaly."""
        # Normal pattern with more variance and one clear outlier
        series = [100, 110, 105, 98, 112, 103, 101, 108, 106, 200]
        anomalies = detect_seasonal_anomalies(series, season=3, threshold_mad=2.0)

        # Should detect the outlier at index 9
        assert 9 in anomalies

    def test_no_anomalies_perfect_pattern(self):
        """Test no anomalies in perfect pattern."""
        series = [100, 110, 105] * 4
        anomalies = detect_seasonal_anomalies(series, season=3, threshold_mad=2.0)

        # Should detect no anomalies
        assert len(anomalies) == 0

    def test_insufficient_data(self):
        """Test with insufficient data."""
        series = [100, 110]
        anomalies = detect_seasonal_anomalies(series, season=12, threshold_mad=2.0)

        assert anomalies == []

    def test_threshold_sensitivity(self):
        """Test threshold affects detection."""
        series = [100] * 10 + [120, 125]

        # Low threshold - more anomalies
        anomalies_low = detect_seasonal_anomalies(series, season=12, threshold_mad=1.0)

        # High threshold - fewer anomalies
        anomalies_high = detect_seasonal_anomalies(series, season=12, threshold_mad=3.0)

        assert len(anomalies_low) >= len(anomalies_high)


class TestTrendAdjustedBaseline:
    """Test trend-adjusted baseline computation."""

    def test_basic_trend_adjustment(self):
        """Test baseline with linear trend."""
        # Series with upward trend
        series = list(range(100, 124))  # 100, 101, 102, ..., 123
        result = trend_adjusted_baseline(series, season=12, trend_window=3)

        assert 'baseline' in result
        assert 'trend_component' in result
        assert len(result['baseline']) == len(series)

    def test_insufficient_data(self):
        """Test with insufficient data."""
        series = [100, 110]
        result = trend_adjusted_baseline(series, season=12, trend_window=3)

        # Should return series as baseline
        assert result['baseline'] == series

    def test_no_trend(self):
        """Test with stationary series (no trend)."""
        series = [100, 110, 90] * 4
        result = trend_adjusted_baseline(series, season=3, trend_window=3)

        # Trend component should be near zero
        assert all(abs(t) < 10 for t in result['trend_component'])


class TestSummarizeBaselineFit:
    """Test baseline fit statistics."""

    def test_perfect_fit(self):
        """Test fit statistics with perfect match."""
        series = [100, 110, 120]
        baseline = [100, 110, 120]

        stats = summarize_baseline_fit(series, baseline)

        assert stats['mean_abs_error'] == pytest.approx(0.0)
        assert stats['max_abs_error'] == pytest.approx(0.0)
        assert stats['r_squared'] == pytest.approx(1.0)

    def test_basic_fit(self):
        """Test fit statistics with reasonable match."""
        series = [100, 110, 120, 130]
        baseline = [98, 108, 122, 132]

        stats = summarize_baseline_fit(series, baseline)

        assert stats['mean_abs_error'] is not None
        assert stats['mean_abs_error'] > 0
        assert stats['max_abs_error'] is not None
        assert stats['r_squared'] is not None
        assert 0 <= stats['r_squared'] <= 1

    def test_mismatched_lengths(self):
        """Test with mismatched lengths."""
        series = [100, 110, 120]
        baseline = [100, 110]

        stats = summarize_baseline_fit(series, baseline)

        # Should return None for all stats
        assert all(v is None for v in stats.values())

    def test_zero_baseline_handling(self):
        """Test percentage error with zero baseline."""
        series = [100, 110, 120]
        baseline = [0, 110, 120]

        stats = summarize_baseline_fit(series, baseline)

        # Mean percentage error should skip zero baseline
        assert stats['mean_pct_error'] is not None

    def test_constant_series(self):
        """Test with constant series (zero variance)."""
        series = [100, 100, 100]
        baseline = [100, 100, 100]

        stats = summarize_baseline_fit(series, baseline)

        # R-squared should be None (zero variance)
        assert stats['r_squared'] is None

    def test_empty_series(self):
        """Test with empty series."""
        series = []
        baseline = []

        stats = summarize_baseline_fit(series, baseline)

        assert all(v is None for v in stats.values())


class TestEdgeCases:
    """Test edge cases and integration scenarios."""

    def test_all_zeros(self):
        """Test with all-zero series."""
        series = [0.0] * 12
        result = seasonal_baseline(series, season=12)

        # Should handle gracefully
        assert len(result['baseline']) == 12
        assert all(b == 0.0 for b in result['baseline'])

    def test_negative_values(self):
        """Test with negative values."""
        series = [-100, -90, -110] * 4
        result = seasonal_baseline(series, season=3)

        # Should work normally
        assert len(result['baseline']) == 12
        assert result['mean_per_phase'][0] == pytest.approx(-100.0)

    def test_large_seasonal_period(self):
        """Test with large seasonal period."""
        series = list(range(100))
        result = seasonal_baseline(series, season=50)

        # Should work
        assert len(result['baseline']) == 100

    def test_seasonal_period_equals_length(self):
        """Test when season equals series length."""
        series = [100, 110, 105]
        result = seasonal_baseline(series, season=3)

        # Each phase appears once, mean = value
        assert result['mean_per_phase'][0] == pytest.approx(100.0)
        assert result['mean_per_phase'][1] == pytest.approx(110.0)
        assert result['mean_per_phase'][2] == pytest.approx(105.0)

    def test_integration_baseline_then_gaps(self):
        """Test integration: compute baseline then gaps."""
        series = [100, 110, 105, 95, 115, 100]

        # Compute baseline
        result = seasonal_baseline(series, season=3)
        baseline = result['baseline']

        # Compute gaps
        gaps = anomaly_gaps(series, baseline)

        # Should have gaps for all points
        assert len(gaps) == len(series)
        assert all(g is not None for g in gaps)

    def test_integration_baseline_then_anomalies(self):
        """Test integration: baseline then anomaly detection."""
        # More realistic series with variance
        series = [100, 110, 105, 98, 112, 103, 101, 108, 106, 500]

        anomalies = detect_seasonal_anomalies(series, season=3, threshold_mad=2.0)

        # Should detect the extreme outlier
        assert len(anomalies) > 0
        assert 9 in anomalies
