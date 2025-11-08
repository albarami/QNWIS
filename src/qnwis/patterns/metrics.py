"""
Deterministic statistical metrics for pattern mining.

All functions are pure Python implementations without external dependencies
for reproducibility and performance. No numpy/scipy to keep deployment simple.
"""

from __future__ import annotations

import math


def pearson(xs: list[float], ys: list[float]) -> float:
    """
    Compute Pearson correlation coefficient between two variables.

    Pure Python implementation without numpy. Handles edge cases
    with zero variance gracefully. Pearson assumes a linear relationship
    between centered variables and is sensitive to outliers.

    Args:
        xs: First variable values
        ys: Second variable values (must match length of xs)

    Returns:
        Correlation coefficient in [-1, 1], or 0.0 if either has zero variance

    Examples:
        >>> pearson([1.0, 2.0, 3.0], [2.0, 4.0, 6.0])
        1.0
        >>> pearson([1.0, 2.0, 3.0], [3.0, 2.0, 1.0])
        -1.0
    """
    if len(xs) != len(ys) or len(xs) < 2:
        return 0.0

    n = len(xs)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n

    # Compute covariance and variances
    cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    var_x = sum((x - mean_x) ** 2 for x in xs)
    var_y = sum((y - mean_y) ** 2 for y in ys)

    # Handle zero variance
    if var_x == 0.0 or var_y == 0.0:
        return 0.0

    return cov / math.sqrt(var_x * var_y)


def spearman(xs: list[float], ys: list[float]) -> float:
    """
    Compute Spearman rank correlation coefficient.

    Spearman measures monotonic association by ranking each series before
    applying Pearson on the ranks, which makes it robust to outliers and
    non-linear but monotonic relationships.

    Args:
        xs: First variable values
        ys: Second variable values (must match length of xs)

    Returns:
        Rank correlation coefficient in [-1, 1]

    Examples:
        >>> spearman([1.0, 2.0, 3.0], [2.0, 4.0, 6.0])
        1.0
    """
    if len(xs) != len(ys) or len(xs) < 2:
        return 0.0

    # Convert to ranks (1-based, average ranks for ties)
    rank_x = _rank_values(xs)
    rank_y = _rank_values(ys)

    # Compute Pearson on ranks
    return pearson(rank_x, rank_y)


def _rank_values(values: list[float]) -> list[float]:
    """
    Convert values to ranks, handling ties with average rank.

    Args:
        values: Input values

    Returns:
        List of ranks (1-based, floats to handle tie averages)
    """
    n = len(values)
    # Create (value, original_index) pairs
    indexed = [(v, i) for i, v in enumerate(values)]
    # Sort by value
    indexed.sort(key=lambda x: x[0])

    # Assign ranks (1-based)
    ranks = [0.0] * n
    i = 0
    while i < n:
        # Find all tied values
        j = i
        while j < n and indexed[j][0] == indexed[i][0]:
            j += 1
        # Average rank for tied values
        avg_rank = (i + j + 1) / 2.0  # +1 for 1-based indexing
        for k in range(i, j):
            ranks[indexed[k][1]] = avg_rank
        i = j

    return ranks


def slope(xs: list[float], ys: list[float]) -> float:
    """
    Compute OLS regression slope with x as time index (0..n-1).

    This is useful for trend analysis where we want the rate of change
    over sequential observations.

    Args:
        xs: Time indices (typically 0, 1, 2, ...)
        ys: Observed values at each time point

    Returns:
        Slope coefficient (units of y per time step)

    Examples:
        >>> slope([0.0, 1.0, 2.0], [10.0, 15.0, 20.0])
        5.0
    """
    if len(xs) != len(ys) or len(xs) < 2:
        return 0.0

    n = len(xs)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n

    numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    denominator = sum((x - mean_x) ** 2 for x in xs)

    if denominator == 0.0:
        return 0.0

    return numerator / denominator


def lift(a: list[float], b: list[float]) -> float:
    """
    Compute percentage lift between two groups.

    Measures relative difference: (mean(a) - mean(b)) / |mean(b)| * 100
    Safe for zero baselines (returns 0.0 instead of dividing by zero).

    Args:
        a: Treatment or comparison group values
        b: Baseline group values

    Returns:
        Percentage lift (positive = a > b, negative = a < b)

    Examples:
        >>> lift([120.0, 130.0], [100.0, 110.0])  # 20% lift
        20.0
        >>> lift([80.0, 90.0], [100.0, 110.0])   # -20% drop
        -19.04761...
    """
    if not a or not b:
        return 0.0

    mean_a = sum(a) / len(a)
    mean_b = sum(b) / len(b)

    if mean_b == 0.0:
        return 0.0  # Avoid division by zero

    raw = ((mean_a - mean_b) / abs(mean_b)) * 100.0
    # Guardrail: lift should remain within +/-500% to avoid runaway deltas
    return max(-500.0, min(500.0, raw))


def stability(values: list[float], windows: tuple[int, ...] = (3, 6, 12)) -> float:
    """
    Compute stability score from inverse variance of windowed slopes.

    Higher stability (closer to 1.0) indicates consistent slopes across
    rolling windows. Lower stability approaches 0.0 as slope variance grows.

    Args:
        values: Time series values
        windows: Window sizes to compute slopes over

    Returns:
        Stability score in [0, 1] where 1 = very stable

    Examples:
        >>> stability([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])  # Perfect linear
        1.0
        >>> stability([1.0, 10.0, 2.0, 11.0, 3.0, 12.0])  # Volatile
        < 0.5
    """
    if len(values) < max(windows):
        # Not enough data for stability analysis
        return 0.5

    slopes: list[float] = []

    # Compute slopes for each window size
    for w in windows:
        if w > len(values):
            continue

        # Multiple overlapping windows of size w
        for i in range(len(values) - w + 1):
            window = values[i : i + w]
            time_idx = list(range(w))
            s = slope([float(t) for t in time_idx], window)
            slopes.append(s)

    if not slopes or len(slopes) < 2:
        return 0.5

    mean_slope = sum(slopes) / len(slopes)
    variance_sum = sum((s - mean_slope) ** 2 for s in slopes)

    # Inverse-variance scaling: 1 / (1 + variance_sum) keeps the score in [0, 1]
    stability_score = 1.0 / (1.0 + variance_sum)

    return max(0.0, min(1.0, stability_score))


def support(n_points: int, min_required: int) -> float:
    """
    Compute data support score.

    Measures whether we have sufficient observations for reliable inference.
    Returns 1.0 when n_points >= min_required, scales linearly below.

    Args:
        n_points: Number of observations
        min_required: Minimum required for full support

    Returns:
        Support score in [0, 1] where 1 = sufficient data

    Examples:
        >>> support(24, 12)  # Double the minimum
        1.0
        >>> support(6, 12)   # Half the minimum
        0.5
        >>> support(0, 12)   # No data
        0.0
    """
    if min_required <= 0:
        return 1.0

    if n_points >= min_required:
        return 1.0

    return max(0.0, n_points / min_required)
