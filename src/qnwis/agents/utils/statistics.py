"""
Pure-Python deterministic statistical functions for agent analytics.

All functions avoid external dependencies and produce deterministic results
suitable for verification in the deterministic data layer.
"""

from __future__ import annotations

from collections.abc import Iterable
from math import sqrt
from statistics import mean


def pearson(xs: Iterable[float], ys: Iterable[float]) -> float:
    """
    Calculate Pearson correlation coefficient between two sequences.

    Returns 0.0 if either sequence has zero variance (to avoid division by zero).

    Args:
        xs: First sequence of numeric values
        ys: Second sequence of numeric values (must match length of xs)

    Returns:
        Pearson r coefficient in range [-1.0, 1.0], or 0.0 if variance is zero

    Raises:
        ValueError: If sequences have different lengths or fewer than 2 elements
    """
    x_list = list(xs)
    y_list = list(ys)

    if len(x_list) != len(y_list):
        raise ValueError("Sequences must have equal length")
    if len(x_list) < 2:
        raise ValueError("Need at least 2 data points for correlation")

    n = len(x_list)
    mean_x = mean(x_list)
    mean_y = mean(y_list)

    # Calculate covariance and standard deviations
    cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(x_list, y_list)) / n
    var_x = sum((x - mean_x) ** 2 for x in x_list) / n
    var_y = sum((y - mean_y) ** 2 for y in y_list) / n

    # Avoid division by zero
    if var_x == 0.0 or var_y == 0.0:
        return 0.0

    return cov / sqrt(var_x * var_y)


def _rank(values: list[float]) -> list[float]:
    """
    Compute stable average-ties ranks (1-based) for a list of values.

    Uses average rank for ties to ensure stability and fairness.

    Args:
        values: List of numeric values

    Returns:
        List of ranks (1-based, with tied values receiving average rank)
    """
    if not values:
        return []

    # Create indexed pairs and sort by value (stable sort)
    indexed = [(v, i) for i, v in enumerate(values)]
    indexed.sort(key=lambda pair: pair[0])

    # Assign ranks with tie averaging
    ranks = [0.0] * len(values)
    i = 0
    while i < len(indexed):
        # Find all values equal to current value
        j = i
        while j < len(indexed) and indexed[j][0] == indexed[i][0]:
            j += 1

        # Average rank for ties (1-based)
        avg_rank = (i + 1 + j) / 2.0

        # Assign average rank to all tied positions
        for k in range(i, j):
            original_idx = indexed[k][1]
            ranks[original_idx] = avg_rank

        i = j

    return ranks


def spearman(xs: Iterable[float], ys: Iterable[float]) -> float:
    """
    Calculate Spearman rank correlation coefficient between two sequences.

    Returns 0.0 if either ranked sequence has zero variance.

    Args:
        xs: First sequence of numeric values
        ys: Second sequence of numeric values (must match length of xs)

    Returns:
        Spearman rho coefficient in range [-1.0, 1.0], or 0.0 if variance is zero

    Raises:
        ValueError: If sequences have different lengths or fewer than 2 elements
    """
    x_list = list(xs)
    y_list = list(ys)

    # Rank the values
    x_ranks = _rank(x_list)
    y_ranks = _rank(y_list)

    # Apply Pearson to the ranks
    return pearson(x_ranks, y_ranks)


def z_scores(values: list[float]) -> list[float]:
    """
    Calculate z-scores (standardized values) for a list of numbers.

    Returns list of zeros if standard deviation is zero.

    Args:
        values: List of numeric values

    Returns:
        List of z-scores with same length as input
    """
    if not values:
        return []

    if len(values) == 1:
        return [0.0]

    mean_val = mean(values)

    # Calculate standard deviation
    variance = sum((x - mean_val) ** 2 for x in values) / len(values)

    if variance == 0.0:
        return [0.0] * len(values)

    std_dev = sqrt(variance)

    return [(x - mean_val) / std_dev for x in values]


def winsorize(values: list[float], p: float = 0.01) -> list[float]:
    """
    Winsorize (clip) extreme values at specified percentiles.

    Replaces values below p-th percentile with that percentile value,
    and values above (1-p)-th percentile with that percentile value.

    Args:
        values: List of numeric values
        p: Percentile fraction (0 < p < 0.5) for clipping (default 0.01 = 1%)

    Returns:
        List of winsorized values with same length as input

    Raises:
        ValueError: If p is not in range (0, 0.5)
    """
    if not 0 < p < 0.5:
        raise ValueError("Percentile p must be in range (0, 0.5)")

    if not values:
        return []

    if len(values) == 1:
        return list(values)

    sorted_vals = sorted(values)
    n = len(sorted_vals)

    # Calculate percentile indices
    lower_idx = max(0, int(n * p))
    upper_idx = min(n - 1, int(n * (1 - p)))

    lower_bound = sorted_vals[lower_idx]
    upper_bound = sorted_vals[upper_idx]

    # Clip values
    return [
        lower_bound if v < lower_bound else upper_bound if v > upper_bound else v
        for v in values
    ]
