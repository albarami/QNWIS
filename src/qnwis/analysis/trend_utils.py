"""
Time-series trend utilities for Time Machine module.

Pure-Python implementations of growth rates, smoothing, indexing, and slope calculations.
All functions guard against edge cases (zeros, small samples, NaNs).
"""


def pct_change(curr: float, prev: float) -> float | None:
    """
    Calculate percentage change between two values.

    Args:
        curr: Current value
        prev: Previous value

    Returns:
        Percentage change (curr - prev) / abs(prev) * 100, or None if prev is 0

    Example:
        >>> pct_change(110, 100)
        10.0
        >>> pct_change(100, 0)
        None
    """
    if prev == 0:
        return None
    return (curr - prev) / abs(prev) * 100


def yoy(series: list[float], period: int = 12) -> list[float | None]:
    """
    Compute year-over-year percentage changes.

    Args:
        series: Time series values
        period: Lag period (default 12 for monthly data)

    Returns:
        List of YoY % changes aligned to input, padded with None for first 'period' values

    Example:
        >>> yoy([100, 110, 120, 105], period=2)
        [None, None, 20.0, -4.545...]
    """
    result: list[float | None] = [None] * period

    for i in range(period, len(series)):
        change = pct_change(series[i], series[i - period])
        result.append(change)

    return result


def qtq(series: list[float], period: int = 3) -> list[float | None]:
    """
    Compute quarter-over-quarter percentage changes.

    Args:
        series: Time series values
        period: Lag period (default 3 for quarterly)

    Returns:
        List of QtQ % changes aligned to input, padded with None for first 'period' values

    Example:
        >>> qtq([100, 105, 110, 115], period=3)
        [None, None, None, 15.0]
    """
    result: list[float | None] = [None] * period

    for i in range(period, len(series)):
        change = pct_change(series[i], series[i - period])
        result.append(change)

    return result


def ewma(series: list[float], alpha: float = 0.25) -> list[float]:
    """
    Compute exponentially weighted moving average.

    Args:
        series: Time series values
        alpha: Smoothing factor (0 < alpha <= 1). Lower = more smoothing.

    Returns:
        EWMA series aligned to input

    Example:
        >>> ewma([100, 110, 105, 115], alpha=0.5)
        [100.0, 105.0, 105.0, 110.0]
    """
    if not series:
        return []

    if not (0 < alpha <= 1):
        alpha = 0.25  # Safe default

    result = [series[0]]

    for i in range(1, len(series)):
        smoothed = alpha * series[i] + (1 - alpha) * result[-1]
        result.append(smoothed)

    return result


def index_100(series: list[float], base_idx: int) -> list[float | None]:
    """
    Normalize series to index 100 at a base period.

    Args:
        series: Time series values
        base_idx: Index to use as base (will be 100)

    Returns:
        Indexed series where series[base_idx] = 100, or None where base value is 0

    Example:
        >>> index_100([50, 100, 150, 200], base_idx=1)
        [50.0, 100.0, 150.0, 200.0]
    """
    if not series or base_idx < 0 or base_idx >= len(series):
        return [None] * len(series)

    base_value = series[base_idx]

    if base_value == 0:
        return [None] * len(series)

    return [100.0 * val / base_value for val in series]


def window_slopes(
    series: list[float], windows: tuple[int, ...] = (3, 6, 12)
) -> list[tuple[int, float | None]]:
    """
    Compute linear slopes over trailing windows using least squares.

    Args:
        series: Time series values
        windows: Tuple of window sizes to compute slopes for

    Returns:
        List of (window_size, slope) tuples. Slope is None if insufficient data.

    Example:
        >>> window_slopes([100, 102, 104, 106, 108], windows=(3,))
        [(3, 2.0)]
    """
    results = []
    n = len(series)

    for w in windows:
        if n < w or w < 2:
            results.append((w, None))
            continue

        # Use last 'w' points for linear regression
        x_vals = list(range(w))
        y_vals = series[-w:]

        # Compute slope using least squares: slope = cov(x,y) / var(x)
        x_mean = sum(x_vals) / w
        y_mean = sum(y_vals) / w

        numerator = sum((x_vals[i] - x_mean) * (y_vals[i] - y_mean) for i in range(w))
        denominator = sum((x_vals[i] - x_mean) ** 2 for i in range(w))

        if denominator == 0:
            results.append((w, None))
        else:
            slope = numerator / denominator
            results.append((w, slope))

    return results


def safe_mean(values: list[float]) -> float | None:
    """
    Compute mean of a list, returning None for empty lists.

    Args:
        values: List of numeric values

    Returns:
        Mean value or None if list is empty
    """
    if not values:
        return None
    return sum(values) / len(values)


def safe_std(values: list[float]) -> float | None:
    """
    Compute standard deviation, returning None for empty/single-element lists.

    Args:
        values: List of numeric values

    Returns:
        Standard deviation or None if insufficient data
    """
    if len(values) < 2:
        return None

    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
    return variance**0.5


def safe_mad(values: list[float]) -> float | None:
    """
    Compute Median Absolute Deviation (robust alternative to std).

    Args:
        values: List of numeric values

    Returns:
        MAD value or None if insufficient data
    """
    if not values:
        return None

    # Compute median
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    if n % 2 == 0:
        median = (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2
    else:
        median = sorted_vals[n // 2]

    # Compute absolute deviations
    deviations = [abs(x - median) for x in values]

    # Return median of deviations
    sorted_devs = sorted(deviations)
    if n % 2 == 0:
        return (sorted_devs[n // 2 - 1] + sorted_devs[n // 2]) / 2
    else:
        return sorted_devs[n // 2]
