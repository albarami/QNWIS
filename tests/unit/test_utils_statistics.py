"""
Unit tests for pure Python statistical utilities.

Tests cover correctness, edge cases, and zero-variance handling.
"""

from __future__ import annotations

import pytest

from src.qnwis.agents.utils.statistics import pearson, spearman, winsorize, z_scores


class TestPearson:
    """Test Pearson correlation coefficient calculation."""

    def test_perfect_positive_correlation(self):
        """Perfect linear positive relationship should give r=1.0."""
        x = [1, 2, 3, 4, 5]
        y = [2, 4, 6, 8, 10]
        assert abs(pearson(x, y) - 1.0) < 0.001

    def test_perfect_negative_correlation(self):
        """Perfect linear negative relationship should give r=-1.0."""
        x = [1, 2, 3, 4, 5]
        y = [10, 8, 6, 4, 2]
        assert abs(pearson(x, y) - (-1.0)) < 0.001

    def test_no_correlation(self):
        """Uncorrelated data should give r≈0."""
        x = [1, 2, 3, 4, 5]
        y = [3, 3, 3, 3, 3]  # Constant
        # Zero variance in y → returns 0.0
        assert pearson(x, y) == 0.0

    def test_zero_variance_x(self):
        """Zero variance in X should return 0.0 gracefully."""
        x = [5, 5, 5, 5]
        y = [1, 2, 3, 4]
        assert pearson(x, y) == 0.0

    def test_zero_variance_both(self):
        """Zero variance in both should return 0.0."""
        x = [5, 5, 5]
        y = [3, 3, 3]
        assert pearson(x, y) == 0.0

    def test_length_mismatch_raises(self):
        """Different length sequences should raise ValueError."""
        x = [1, 2, 3]
        y = [1, 2]
        with pytest.raises(ValueError, match="equal length"):
            pearson(x, y)

    def test_insufficient_data_raises(self):
        """Fewer than 2 points should raise ValueError."""
        x = [1]
        y = [2]
        with pytest.raises(ValueError, match="at least 2"):
            pearson(x, y)

    def test_known_correlation(self):
        """Test against known correlation value."""
        # Data with known r ≈ 0.8
        x = [1, 2, 3, 4, 5, 6]
        y = [2, 3, 5, 6, 8, 9]
        r = pearson(x, y)
        assert 0.95 < r < 1.0  # Strong positive


class TestSpearman:
    """Test Spearman rank correlation calculation."""

    def test_perfect_monotonic_increasing(self):
        """Perfect monotonic increasing should give rho=1.0."""
        x = [1, 2, 3, 4, 5]
        y = [2, 4, 6, 8, 10]
        assert abs(spearman(x, y) - 1.0) < 0.001

    def test_perfect_monotonic_decreasing(self):
        """Perfect monotonic decreasing should give rho=-1.0."""
        x = [1, 2, 3, 4, 5]
        y = [10, 8, 6, 4, 2]
        assert abs(spearman(x, y) - (-1.0)) < 0.001

    def test_robust_to_outliers(self):
        """Spearman should be robust to extreme outliers."""
        x = [1, 2, 3, 4, 100]  # Extreme outlier
        y = [2, 4, 6, 8, 10]
        rho = spearman(x, y)
        # Still strong positive correlation (ranks preserved)
        assert rho > 0.8

    def test_tied_ranks(self):
        """Handle tied values correctly (average ranks)."""
        x = [1, 2, 2, 3]  # Tie in middle
        y = [1, 2, 3, 4]
        rho = spearman(x, y)
        # Should still be very high correlation
        assert rho > 0.9

    def test_zero_variance(self):
        """Zero variance should return 0.0."""
        x = [5, 5, 5, 5]
        y = [1, 2, 3, 4]
        assert spearman(x, y) == 0.0


class TestZScores:
    """Test z-score standardization."""

    def test_standardization(self):
        """Z-scores should have mean≈0 and std≈1."""
        values = [10, 12, 14, 16, 18]
        z = z_scores(values)

        mean_z = sum(z) / len(z)
        assert abs(mean_z) < 0.001  # Mean ≈ 0

        variance = sum((zi - mean_z) ** 2 for zi in z) / len(z)
        std = variance ** 0.5
        assert abs(std - 1.0) < 0.001  # Std ≈ 1

    def test_symmetry(self):
        """Symmetric data should have symmetric z-scores."""
        values = [10, 15, 20, 25, 30]
        z = z_scores(values)
        # Should be symmetric around 0
        assert abs(z[0] + z[4]) < 0.001
        assert abs(z[1] + z[3]) < 0.001
        assert abs(z[2]) < 0.001  # Middle value

    def test_zero_variance_returns_zeros(self):
        """Zero variance should return all zeros."""
        values = [5.0, 5.0, 5.0]
        result = z_scores(values)
        assert result == [0.0, 0.0, 0.0]

    def test_single_value(self):
        """Single value should return zero."""
        values = [42.0]
        result = z_scores(values)
        assert result == [0.0]

    def test_empty_list(self):
        """Empty list should return empty list."""
        assert z_scores([]) == []

    def test_known_values(self):
        """Test against manually calculated z-scores."""
        values = [10, 20, 30]
        z = z_scores(values)
        # Mean = 20, std = 8.165
        # z_10 = (10-20)/8.165 ≈ -1.225
        # z_20 = 0
        # z_30 = +1.225
        assert abs(z[0] - (-1.225)) < 0.01
        assert abs(z[1]) < 0.001
        assert abs(z[2] - 1.225) < 0.01


class TestWinsorize:
    """Test winsorization (outlier clipping)."""

    def test_clip_extreme_high(self):
        """Extreme high value should be clipped."""
        values = [1, 2, 3, 4, 5, 6, 7, 8, 9, 100]
        clipped = winsorize(values, p=0.10)
        # Top 10% (last value) should be clipped to 90th percentile
        # With n=10, upper_idx = int(10 * 0.90) = 9, so upper_bound = sorted[9] = 100
        # Need p=0.05 to clip: upper_idx = int(10 * 0.95) = 9 still...
        # Use n=11 or more aggressive p
        values = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 100]
        clipped = winsorize(values, p=0.10)
        # With n=11, p=0.10: upper_idx = int(11*0.90) = 9, upper_bound = 10
        assert clipped[-1] == 10

    def test_clip_extreme_low(self):
        """Extreme low value should be clipped."""
        values = [-100, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        clipped = winsorize(values, p=0.10)
        # With n=11, p=0.10: lower_idx = int(11*0.10) = 1, lower_bound = 1
        assert clipped[0] == 1

    def test_symmetric_clipping(self):
        """Both extremes should be clipped symmetrically."""
        # Use 20 values so p=0.05 clips 1 value from each end
        values = list(range(1, 20)) + [1000]
        clipped = winsorize(values, p=0.05)
        # With n=20, p=0.05: lower_idx = int(20*0.05) = 1, upper_idx = int(20*0.95) = 19
        # But index 19 is 1000, so no upper clip. Use int(20*0.95) = 19 but n-1 = 19
        # Need n=21 to clip
        values = [0] + list(range(1, 20)) + [1000]
        clipped = winsorize(values, p=0.05)
        # n=21, lower_idx=int(21*0.05)=1, upper_idx=int(21*0.95)=19
        # lower_bound=sorted[1]=1, upper_bound=sorted[19]=19
        assert clipped[0] == 1  # 0 clipped to 1
        assert clipped[-1] == 19  # 1000 clipped to 19

    def test_no_change_normal_data(self):
        """Normal data without extremes should be unchanged."""
        values = [10, 20, 30, 40, 50]
        clipped = winsorize(values, p=0.01)
        # With small p and no extremes, should be same
        assert clipped == values

    def test_single_value_unchanged(self):
        """Single value should return unchanged."""
        values = [42.0]
        assert winsorize(values, p=0.01) == [42.0]

    def test_empty_list(self):
        """Empty list should return empty."""
        assert winsorize([]) == []

    def test_invalid_p_raises(self):
        """Invalid percentile should raise ValueError."""
        with pytest.raises(ValueError, match="range"):
            winsorize([1, 2, 3], p=0.0)
        with pytest.raises(ValueError, match="range"):
            winsorize([1, 2, 3], p=0.5)
        with pytest.raises(ValueError, match="range"):
            winsorize([1, 2, 3], p=1.0)

    def test_deterministic(self):
        """Winsorization should be deterministic."""
        values = [1, 5, 10, 15, 20, 25, 30, 35, 100]
        result1 = winsorize(values, p=0.10)
        result2 = winsorize(values, p=0.10)
        assert result1 == result2


class TestRankHelper:
    """Test internal ranking function (via spearman)."""

    def test_rank_stability(self):
        """Ranking should be stable across multiple calls."""
        x = [3, 1, 4, 1, 5, 9, 2, 6]
        y = [1, 1, 1, 1, 1, 1, 1, 1]

        # Call multiple times
        r1 = spearman(x, y)
        r2 = spearman(x, y)
        assert r1 == r2

    def test_tied_ranks_average(self):
        """Tied values should get average rank."""
        # Test indirectly via spearman with known ties
        x = [1, 2, 2, 3]
        y = [1, 2, 2, 3]
        rho = spearman(x, y)
        # Perfect match even with ties
        assert abs(rho - 1.0) < 0.001
