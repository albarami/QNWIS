"""
Seasonal baseline and anomaly detection for Time Machine module.

Computes seasonal baselines using phase-averaged means and robust bands (MAD-based).
All functions handle edge cases and guard against zeros/NaNs.
"""


from .trend_utils import safe_mad, safe_mean


def seasonal_baseline(
    series: list[float],
    season: int = 12
) -> dict[str, list[float]]:
    """
    Compute seasonal baseline and anomaly bands.

    Args:
        series: Time series values (must be >= season length)
        season: Seasonal period (default 12 for monthly data)

    Returns:
        Dictionary with:
        - mean_per_phase: Average value for each phase (e.g., Jan, Feb, ...)
        - baseline: Seasonal mean repeated to match series length
        - upper_band: baseline + 1.5*MAD (robust upper bound)
        - lower_band: baseline - 1.5*MAD (robust lower bound)

    Example:
        >>> result = seasonal_baseline([100, 110, 105, 100, 110, 105], season=3)
        >>> len(result['baseline'])
        6
    """
    if len(series) < season:
        # Insufficient data for seasonal decomposition
        return {
            'mean_per_phase': [0.0] * season,
            'baseline': series,
            'upper_band': series,
            'lower_band': series
        }

    # Group by seasonal phase
    phase_groups: list[list[float]] = [[] for _ in range(season)]

    for i, val in enumerate(series):
        phase = i % season
        phase_groups[phase].append(val)

    # Compute mean for each phase
    mean_per_phase = []
    for phase_vals in phase_groups:
        phase_mean = safe_mean(phase_vals)
        mean_per_phase.append(phase_mean if phase_mean is not None else 0.0)

    # Repeat seasonal pattern to match series length
    baseline = []
    for i in range(len(series)):
        phase = i % season
        baseline.append(mean_per_phase[phase])

    # Compute robust bands using MAD
    deviations = [series[i] - baseline[i] for i in range(len(series))]
    mad = safe_mad(deviations)

    if mad is None or mad == 0:
        # No variation, bands equal baseline
        upper_band = baseline[:]
        lower_band = baseline[:]
    else:
        # Use 1.5*MAD for band width (robust alternative to 1.5*std)
        band_width = 1.5 * mad
        upper_band = [b + band_width for b in baseline]
        lower_band = [max(0, b - band_width) for b in baseline]  # Clamp at 0

    return {
        'mean_per_phase': mean_per_phase,
        'baseline': baseline,
        'upper_band': upper_band,
        'lower_band': lower_band
    }


def anomaly_gaps(
    series: list[float],
    baseline: list[float]
) -> list[float | None]:
    """
    Compute percentage gaps between actual values and baseline.

    Args:
        series: Actual time series values
        baseline: Baseline (expected) values

    Returns:
        List of percentage differences: (series - baseline) / baseline * 100
        Returns None for positions where baseline is 0

    Example:
        >>> anomaly_gaps([110, 90], [100, 100])
        [10.0, -10.0]
    """
    if len(series) != len(baseline):
        # Mismatched lengths, return zeros
        return [None] * len(series)

    gaps = []

    for i in range(len(series)):
        if baseline[i] == 0:
            gaps.append(None)
        else:
            gap_pct = (series[i] - baseline[i]) / baseline[i] * 100
            gaps.append(gap_pct)

    return gaps


def detect_seasonal_anomalies(
    series: list[float],
    season: int = 12,
    threshold_mad: float = 2.0
) -> list[int]:
    """
    Detect points that deviate significantly from seasonal baseline.

    Args:
        series: Time series values
        season: Seasonal period
        threshold_mad: Number of MADs beyond which a point is anomalous

    Returns:
        List of indices that are seasonal anomalies

    Example:
        >>> detect_seasonal_anomalies([100, 100, 200, 100], season=2, threshold_mad=1.5)
        [2]
    """
    if len(series) < season:
        return []

    baseline_result = seasonal_baseline(series, season)
    baseline = baseline_result['baseline']

    # Compute deviations
    deviations = [series[i] - baseline[i] for i in range(len(series))]
    mad = safe_mad(deviations)

    if mad is None or mad == 0:
        return []  # No variation, no anomalies

    # Find points beyond threshold
    anomalies = []
    for i, dev in enumerate(deviations):
        if abs(dev) > threshold_mad * mad:
            anomalies.append(i)

    return anomalies


def trend_adjusted_baseline(
    series: list[float],
    season: int = 12,
    trend_window: int = 3
) -> dict[str, list[float]]:
    """
    Compute seasonal baseline with linear trend adjustment.

    Useful for series with strong underlying trend + seasonality.

    Args:
        series: Time series values
        season: Seasonal period
        trend_window: Window for computing local trend

    Returns:
        Dictionary with 'baseline' and 'trend_component'
    """
    if len(series) < season + trend_window:
        # Insufficient data
        return {
            'baseline': series,
            'trend_component': [0.0] * len(series)
        }

    # First pass: compute simple seasonal baseline
    base_result = seasonal_baseline(series, season)
    simple_baseline = base_result['baseline']

    # Detrend: compute residuals
    residuals = [series[i] - simple_baseline[i] for i in range(len(series))]

    # Compute rolling average of residuals as trend
    trend_component = []
    for i in range(len(series)):
        if i < trend_window:
            trend_component.append(0.0)
        else:
            window_residuals = residuals[i-trend_window:i]
            trend = safe_mean(window_residuals)
            trend_component.append(trend if trend is not None else 0.0)

    # Adjusted baseline = seasonal + trend
    adjusted_baseline = [
        simple_baseline[i] + trend_component[i]
        for i in range(len(series))
    ]

    return {
        'baseline': adjusted_baseline,
        'trend_component': trend_component
    }


def summarize_baseline_fit(
    series: list[float],
    baseline: list[float]
) -> dict[str, float | None]:
    """
    Compute fit statistics for baseline vs actual series.

    Args:
        series: Actual time series values
        baseline: Baseline values

    Returns:
        Dictionary with:
        - mean_abs_error: Average absolute difference
        - mean_pct_error: Average percentage difference (where baseline != 0)
        - max_abs_error: Maximum absolute difference
        - r_squared: Proportion of variance explained (0-1)
    """
    if len(series) != len(baseline) or not series:
        return {
            'mean_abs_error': None,
            'mean_pct_error': None,
            'max_abs_error': None,
            'r_squared': None
        }

    # Absolute errors
    abs_errors = [abs(series[i] - baseline[i]) for i in range(len(series))]
    mean_abs_error = safe_mean(abs_errors)
    max_abs_error = max(abs_errors) if abs_errors else None

    # Percentage errors (where baseline != 0)
    pct_errors = []
    for i in range(len(series)):
        if baseline[i] != 0:
            pct_err = abs((series[i] - baseline[i]) / baseline[i] * 100)
            pct_errors.append(pct_err)

    mean_pct_error = safe_mean(pct_errors) if pct_errors else None

    # R-squared
    series_mean = safe_mean(series)
    if series_mean is None:
        r_squared = None
    else:
        ss_tot = sum((series[i] - series_mean) ** 2 for i in range(len(series)))
        ss_res = sum((series[i] - baseline[i]) ** 2 for i in range(len(series)))

        r_squared = None if ss_tot == 0 else max(0.0, 1.0 - ss_res / ss_tot)

    return {
        'mean_abs_error': mean_abs_error,
        'mean_pct_error': mean_pct_error,
        'max_abs_error': max_abs_error,
        'r_squared': r_squared
    }
