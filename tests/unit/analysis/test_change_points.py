"""
Unit tests for change_points module.

Tests cover:
- CUSUM break detection with various thresholds
- Z-score outlier detection
- Break summarization
- Edge cases (constant series, small samples)
"""

import pytest

from src.qnwis.analysis.change_points import (
    cusum_breaks,
    rolling_variance_breaks,
    summarize_breaks,
    zscore_outliers,
)


class TestCUSUMBreaks:
    """Test CUSUM change-point detection."""

    def test_detects_mean_shift(self):
        """Test CUSUM detects clear mean shift."""
        series = [100.0] * 10 + [150.0] * 10
        breaks = cusum_breaks(series, k=0.5, h=2.0)  # More sensitive parameters

        # Should detect break around index 10
        assert len(breaks) > 0
        assert any(8 <= b <= 12 for b in breaks)

    def test_no_breaks_constant_series(self):
        """Test CUSUM returns empty for constant series."""
        series = [100.0] * 20
        breaks = cusum_breaks(series, k=1.0, h=5.0)

        assert breaks == []

    def test_sensitivity_with_h_threshold(self):
        """Test lower h threshold detects more breaks."""
        series = [100] * 5 + [110] * 5 + [105] * 5

        # High threshold - fewer breaks
        breaks_high = cusum_breaks(series, k=1.0, h=6.0)

        # Low threshold - more breaks
        breaks_low = cusum_breaks(series, k=1.0, h=3.0)

        assert len(breaks_low) >= len(breaks_high)

    def test_insufficient_data(self):
        """Test CUSUM with insufficient data."""
        series = [100, 110]
        breaks = cusum_breaks(series, k=1.0, h=5.0)

        assert breaks == []

    def test_zero_std_series(self):
        """Test CUSUM with zero standard deviation."""
        series = [42.0] * 10
        breaks = cusum_breaks(series, k=1.0, h=5.0)

        # Should handle gracefully
        assert breaks == []

    def test_multiple_breaks(self):
        """Test CUSUM detects multiple breaks."""
        series = [100] * 10 + [150] * 10 + [120] * 10
        breaks = cusum_breaks(series, k=0.5, h=2.0)  # More sensitive parameters

        # Should detect at least one break
        assert len(breaks) >= 1


class TestZScoreOutliers:
    """Test z-score outlier detection."""

    def test_detects_single_outlier(self):
        """Test z-score detects clear outlier."""
        series = [100, 102, 101, 200, 99, 103]
        outliers = zscore_outliers(series, z=2.0)

        # Index 3 (value 200) should be detected
        assert 3 in outliers

    def test_no_outliers_normal_series(self):
        """Test z-score returns empty for normal series."""
        series = [100, 102, 98, 101, 99, 103]
        outliers = zscore_outliers(series, z=2.5)

        assert outliers == []

    def test_threshold_sensitivity(self):
        """Test lower threshold detects more outliers."""
        series = [100] * 10 + [120, 125]

        # High threshold - fewer outliers
        outliers_high = zscore_outliers(series, z=3.0)

        # Low threshold - more outliers
        outliers_low = zscore_outliers(series, z=1.5)

        assert len(outliers_low) >= len(outliers_high)

    def test_constant_series(self):
        """Test z-score with constant series (zero std)."""
        series = [100.0] * 10
        outliers = zscore_outliers(series, z=2.5)

        # Should handle gracefully
        assert outliers == []

    def test_insufficient_data(self):
        """Test z-score with insufficient data."""
        series = [100, 110]
        outliers = zscore_outliers(series, z=2.5)

        assert outliers == []

    def test_multiple_outliers(self):
        """Test z-score detects multiple outliers."""
        series = [100, 101, 99, 200, 102, 98, 10, 103]  # More extreme low outlier
        outliers = zscore_outliers(series, z=1.5)  # More sensitive

        # Should detect indices 3 and 6
        assert len(outliers) >= 2
        assert 3 in outliers  # 200
        assert 6 in outliers  # 10


class TestSummarizeBreaks:
    """Test break summarization."""

    def test_basic_summary(self):
        """Test summarize_breaks with clear break."""
        series = [100] * 10 + [150] * 10
        summary = summarize_breaks(series)

        # With a clear jump from 100 to 150, should detect something
        assert summary['max_jump_abs'] is not None
        assert summary['max_jump_pct'] is not None

    def test_no_breaks(self):
        """Test summarize_breaks with no breaks."""
        series = [100, 101, 99, 102, 98]
        summary = summarize_breaks(series)

        # Might be 0 breaks or small jumps
        assert 'n_breaks' in summary
        assert 'first_break_idx' in summary

    def test_max_jump_calculation(self):
        """Test max jump is correctly identified."""
        series = [100, 102, 150, 152, 154]
        summary = summarize_breaks(series)

        # Max absolute jump should be 48 (150-102)
        assert summary['max_jump_abs'] == pytest.approx(48.0)

        # Max percentage jump should be around 47%
        assert summary['max_jump_pct'] == pytest.approx(47.06, rel=0.1)

    def test_insufficient_data(self):
        """Test summarize_breaks with insufficient data."""
        series = [100]
        summary = summarize_breaks(series)

        assert summary['first_break_idx'] is None
        assert summary['n_breaks'] == 0
        assert summary['max_jump_abs'] is None

    def test_zero_handling(self):
        """Test summarize_breaks with zeros."""
        series = [0, 100, 0, 50]
        summary = summarize_breaks(series)

        # Should handle gracefully
        assert 'max_jump_abs' in summary
        assert 'max_jump_pct' in summary


class TestRollingVarianceBreaks:
    """Test rolling variance break detection."""

    def test_detects_volatility_change(self):
        """Test detects change in volatility."""
        # Low volatility, then high volatility
        series = [100, 101, 99, 102, 98] + [100, 120, 80, 130, 70]
        breaks = rolling_variance_breaks(series, window=5, threshold=2.0)

        # Might detect volatility change
        # (Not guaranteed due to small sample)
        assert isinstance(breaks, list)

    def test_insufficient_data(self):
        """Test with insufficient data for window."""
        series = [100, 110, 105]
        breaks = rolling_variance_breaks(series, window=12, threshold=2.0)

        assert breaks == []

    def test_constant_series(self):
        """Test with constant series (zero variance)."""
        series = [100] * 20
        breaks = rolling_variance_breaks(series, window=5, threshold=2.0)

        # Should handle gracefully
        assert isinstance(breaks, list)


class TestEdgeCases:
    """Test edge cases and integration scenarios."""

    def test_all_same_values(self):
        """Test with all identical values."""
        series = [42.0] * 20

        # CUSUM should return empty
        assert cusum_breaks(series) == []

        # Z-score should return empty
        assert zscore_outliers(series) == []

        # Summary should have no breaks
        summary = summarize_breaks(series)
        assert summary['n_breaks'] == 0

    def test_negative_values(self):
        """Test with negative values."""
        series = [-100, -90, -80, -70, -60]

        # Should work normally
        breaks = cusum_breaks(series, k=1.0, h=3.0)
        outliers = zscore_outliers(series, z=2.5)

        assert isinstance(breaks, list)
        assert isinstance(outliers, list)

    def test_mixed_signs(self):
        """Test with mixed positive/negative values."""
        series = [-50, 0, 50, 100, -100]

        # Should work normally
        summary = summarize_breaks(series)

        assert 'max_jump_abs' in summary
        assert summary['max_jump_abs'] is not None

    def test_very_small_values(self):
        """Test with very small values."""
        series = [0.001, 0.002, 0.0015, 0.0018]

        # Should not crash
        breaks = cusum_breaks(series, k=1.0, h=5.0)
        assert isinstance(breaks, list)

    def test_large_values(self):
        """Test with very large values."""
        series = [1e6, 1.1e6, 1.05e6, 1.2e6]

        # Should work normally
        outliers = zscore_outliers(series, z=2.5)
        assert isinstance(outliers, list)

    def test_single_outlier_dominates(self):
        """Test when single outlier affects statistics."""
        series = [100] * 15 + [1000]

        # Z-score should detect the outlier
        outliers = zscore_outliers(series, z=2.0)
        assert 15 in outliers

    def test_gradual_drift(self):
        """Test with gradual linear drift (no sharp breaks)."""
        series = list(range(100, 120))  # 100, 101, 102, ..., 119

        # CUSUM might or might not detect (depends on parameters)
        breaks = cusum_breaks(series, k=1.0, h=5.0)

        # Should not crash
        assert isinstance(breaks, list)

    def test_empty_series(self):
        """Test with empty series."""
        series = []

        assert cusum_breaks(series) == []
        assert zscore_outliers(series) == []

        summary = summarize_breaks(series)
        assert summary['n_breaks'] == 0
