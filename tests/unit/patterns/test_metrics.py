"""
Unit tests for pattern mining statistical metrics.

Tests pure Python implementations of correlation, trend, and quality metrics.
"""

from __future__ import annotations

import pytest

from src.qnwis.patterns import metrics


class TestPearson:
    """Test Pearson correlation coefficient."""

    def test_perfect_positive_correlation(self):
        """Perfect positive linear relationship."""
        xs = [1.0, 2.0, 3.0, 4.0, 5.0]
        ys = [2.0, 4.0, 6.0, 8.0, 10.0]
        result = metrics.pearson(xs, ys)
        assert result == pytest.approx(1.0, abs=1e-6)

    def test_perfect_negative_correlation(self):
        """Perfect negative linear relationship."""
        xs = [1.0, 2.0, 3.0, 4.0, 5.0]
        ys = [10.0, 8.0, 6.0, 4.0, 2.0]
        result = metrics.pearson(xs, ys)
        assert result == pytest.approx(-1.0, abs=1e-6)

    def test_zero_correlation(self):
        """No linear relationship."""
        xs = [1.0, 2.0, 3.0, 4.0, 5.0]
        ys = [3.0, 3.0, 3.0, 3.0, 3.0]  # Constant
        result = metrics.pearson(xs, ys)
        assert result == 0.0

    def test_zero_variance_x(self):
        """X has zero variance."""
        xs = [2.0, 2.0, 2.0, 2.0]
        ys = [1.0, 2.0, 3.0, 4.0]
        result = metrics.pearson(xs, ys)
        assert result == 0.0

    def test_zero_variance_y(self):
        """Y has zero variance."""
        xs = [1.0, 2.0, 3.0, 4.0]
        ys = [5.0, 5.0, 5.0, 5.0]
        result = metrics.pearson(xs, ys)
        assert result == 0.0

    def test_moderate_positive_correlation(self):
        """Moderate positive correlation."""
        xs = [1.0, 2.0, 3.0, 4.0, 5.0]
        ys = [2.0, 3.0, 5.0, 6.0, 8.0]
        result = metrics.pearson(xs, ys)
        assert 0.9 < result < 1.0

    def test_mismatched_lengths(self):
        """Different lengths return 0."""
        xs = [1.0, 2.0, 3.0]
        ys = [1.0, 2.0]
        result = metrics.pearson(xs, ys)
        assert result == 0.0

    def test_insufficient_data(self):
        """Single point returns 0."""
        xs = [1.0]
        ys = [2.0]
        result = metrics.pearson(xs, ys)
        assert result == 0.0


class TestSpearman:
    """Test Spearman rank correlation coefficient."""

    def test_perfect_monotonic_increasing(self):
        """Perfect monotonic relationship."""
        xs = [1.0, 2.0, 3.0, 4.0, 5.0]
        ys = [10.0, 20.0, 30.0, 40.0, 50.0]
        result = metrics.spearman(xs, ys)
        assert result == pytest.approx(1.0, abs=1e-6)

    def test_perfect_monotonic_decreasing(self):
        """Perfect negative monotonic relationship."""
        xs = [1.0, 2.0, 3.0, 4.0, 5.0]
        ys = [50.0, 40.0, 30.0, 20.0, 10.0]
        result = metrics.spearman(xs, ys)
        assert result == pytest.approx(-1.0, abs=1e-6)

    def test_nonlinear_monotonic(self):
        """Non-linear but monotonic (quadratic)."""
        xs = [1.0, 2.0, 3.0, 4.0, 5.0]
        ys = [1.0, 4.0, 9.0, 16.0, 25.0]  # x^2
        result = metrics.spearman(xs, ys)
        assert result == pytest.approx(1.0, abs=1e-6)

    def test_outlier_robustness(self):
        """Spearman is robust to outliers."""
        xs = [1.0, 2.0, 3.0, 4.0, 5.0]
        ys = [2.0, 4.0, 6.0, 8.0, 1000.0]  # Outlier

        # Spearman should still be 1.0 (ranks unchanged)
        result = metrics.spearman(xs, ys)
        assert result == pytest.approx(1.0, abs=1e-6)

        # Pearson would be affected
        pearson_result = metrics.pearson(xs, ys)
        assert pearson_result < 0.9  # Significantly lower

    def test_tied_ranks(self):
        """Handle tied values correctly."""
        xs = [1.0, 2.0, 2.0, 4.0, 5.0]
        ys = [1.0, 3.0, 3.0, 4.0, 5.0]
        result = metrics.spearman(xs, ys)
        assert 0.9 < result <= 1.0

    def test_insufficient_data(self):
        """Single point returns 0."""
        xs = [1.0]
        ys = [2.0]
        result = metrics.spearman(xs, ys)
        assert result == 0.0


class TestSlope:
    """Test OLS regression slope."""

    def test_positive_linear_trend(self):
        """Increasing linear trend."""
        xs = [0.0, 1.0, 2.0, 3.0, 4.0]
        ys = [10.0, 15.0, 20.0, 25.0, 30.0]
        result = metrics.slope(xs, ys)
        assert result == pytest.approx(5.0, abs=1e-6)

    def test_negative_linear_trend(self):
        """Decreasing linear trend."""
        xs = [0.0, 1.0, 2.0, 3.0, 4.0]
        ys = [30.0, 25.0, 20.0, 15.0, 10.0]
        result = metrics.slope(xs, ys)
        assert result == pytest.approx(-5.0, abs=1e-6)

    def test_flat_trend(self):
        """No trend (horizontal line)."""
        xs = [0.0, 1.0, 2.0, 3.0, 4.0]
        ys = [20.0, 20.0, 20.0, 20.0, 20.0]
        result = metrics.slope(xs, ys)
        assert result == pytest.approx(0.0, abs=1e-6)

    def test_fractional_slope(self):
        """Fractional slope."""
        xs = [0.0, 1.0, 2.0, 3.0, 4.0]
        ys = [0.0, 0.5, 1.0, 1.5, 2.0]
        result = metrics.slope(xs, ys)
        assert result == pytest.approx(0.5, abs=1e-6)

    def test_zero_variance_x(self):
        """X has no variance."""
        xs = [2.0, 2.0, 2.0, 2.0]
        ys = [1.0, 2.0, 3.0, 4.0]
        result = metrics.slope(xs, ys)
        assert result == 0.0

    def test_insufficient_data(self):
        """Single point returns 0."""
        xs = [1.0]
        ys = [10.0]
        result = metrics.slope(xs, ys)
        assert result == 0.0


class TestLift:
    """Test lift calculation."""

    def test_positive_lift(self):
        """Positive lift scenario."""
        a = [120.0, 130.0, 140.0]
        b = [100.0, 110.0, 105.0]
        result = metrics.lift(a, b)
        assert result == pytest.approx(23.8095, abs=1e-4)

    def test_negative_lift(self):
        """Negative lift scenario."""
        a = [80.0, 90.0, 95.0]
        b = [100.0, 110.0, 105.0]
        result = metrics.lift(a, b)
        assert result == pytest.approx(-15.8730, abs=1e-3)

    def test_baseline_zero(self):
        """Zero baseline returns 0 to avoid division errors."""
        a = [100.0, 110.0]
        b = [0.0, 0.0]
        assert metrics.lift(a, b) == 0.0

    def test_negative_baseline(self):
        """Negative baseline."""
        a = [5.0, 10.0, 15.0]
        b = [-20.0, -10.0, -15.0]  # mean = -15
        result = metrics.lift(a, b)
        assert result == pytest.approx(166.67, abs=0.1)

    def test_empty_lists(self):
        """Empty inputs return 0."""
        assert metrics.lift([], [1.0, 2.0]) == 0.0
        assert metrics.lift([1.0, 2.0], []) == 0.0
        assert metrics.lift([], []) == 0.0

    def test_clamped_output(self):
        """Lift is clamped to +/-500%."""
        result = metrics.lift([2000.0, 2100.0], [100.0, 120.0])
        assert result == 500.0
        result = metrics.lift([-1000.0, -900.0], [100.0, 120.0])
        assert result == -500.0


class TestStability:
    """Test stability score calculation."""

    def test_perfect_linear_trend(self):
        """Perfectly consistent linear trend."""
        values = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0]
        result = metrics.stability(values)
        assert result == pytest.approx(1.0, abs=1e-3)

    def test_volatile_series(self):
        """Highly volatile series with inconsistent trends."""
        values = [1.0, 10.0, 2.0, 11.0, 3.0, 12.0, 4.0, 13.0, 5.0, 14.0, 6.0, 15.0]
        result = metrics.stability(values)
        assert result < 0.5

    def test_flat_series(self):
        """Flat series (zero slope everywhere)."""
        values = [5.0] * 12
        result = metrics.stability(values)
        assert result == 1.0

    def test_insufficient_data(self):
        """Not enough data for stability analysis."""
        values = [1.0, 2.0, 3.0]
        result = metrics.stability(values)
        assert result == 0.5

    def test_moderate_stability(self):
        """Moderate stability with some noise."""
        values = [1.0, 2.1, 3.0, 3.9, 5.0, 6.1, 7.0, 7.9, 9.0, 10.1, 11.0, 11.9]
        result = metrics.stability(values)
        assert 0.7 < result < 1.0

    def test_custom_windows(self):
        """Custom window sizes."""
        values = list(range(1, 25))
        result = metrics.stability(values, windows=(3, 6))
        assert result > 0.95

    def test_inverse_variance_behavior(self):
        """Series with larger slope variance should score lower."""
        base = list(range(1, 25))
        noisy = [val * (1.0 if i % 2 == 0 else 3.0) for i, val in enumerate(base)]
        stable_score = metrics.stability(base)
        noisy_score = metrics.stability(noisy)
        assert 0.0 <= noisy_score <= 1.0
        assert stable_score > noisy_score


class TestSupport:
    """Test data support score."""

    def test_full_support(self):
        """Sufficient observations."""
        result = metrics.support(24, 12)
        assert result == 1.0

    def test_double_required(self):
        """More than enough data."""
        result = metrics.support(30, 12)
        assert result == 1.0

    def test_half_required(self):
        """Half the minimum."""
        result = metrics.support(6, 12)
        assert result == pytest.approx(0.5, abs=1e-6)

    def test_quarter_required(self):
        """Quarter of minimum."""
        result = metrics.support(3, 12)
        assert result == pytest.approx(0.25, abs=1e-6)

    def test_zero_observations(self):
        """No data."""
        result = metrics.support(0, 12)
        assert result == 0.0

    def test_zero_required(self):
        """Edge case: zero minimum."""
        result = metrics.support(10, 0)
        assert result == 1.0

    def test_exact_minimum(self):
        """Exactly at threshold."""
        result = metrics.support(12, 12)
        assert result == 1.0


class TestRankValues:
    """Test internal rank conversion function."""

    def test_no_ties(self):
        """Simple ranking without ties."""
        values = [1.0, 3.0, 2.0, 5.0, 4.0]
        ranks = metrics._rank_values(values)
        assert ranks == [1.0, 3.0, 2.0, 5.0, 4.0]

    def test_tied_values(self):
        """Tied values get average rank."""
        values = [1.0, 2.0, 2.0, 4.0]
        ranks = metrics._rank_values(values)
        # Ranks: 1, (2+3)/2, (2+3)/2, 4 = [1.0, 2.5, 2.5, 4.0]
        assert ranks == [1.0, 2.5, 2.5, 4.0]

    def test_all_tied(self):
        """All values identical."""
        values = [5.0, 5.0, 5.0, 5.0]
        ranks = metrics._rank_values(values)
        # All get average rank: (1+2+3+4)/4 = 2.5
        assert ranks == [2.5, 2.5, 2.5, 2.5]

    def test_three_way_tie(self):
        """Three values tied."""
        values = [1.0, 3.0, 3.0, 3.0, 5.0]
        ranks = metrics._rank_values(values)
        # Ranks: 1, (2+3+4)/3, (2+3+4)/3, (2+3+4)/3, 5
        assert ranks == [1.0, 3.0, 3.0, 3.0, 5.0]
