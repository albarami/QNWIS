"""
Change-point detection for Time Machine module.

Pure-Python implementations of CUSUM and z-score outlier detection.
All functions guard against edge cases (constant series, small samples).
"""


from src.qnwis.analysis.trend_utils import safe_mean, safe_std


def cusum_breaks(
    series: list[float],
    k: float = 1.0,
    h: float = 5.0
) -> list[int]:
    """
    Detect change points using CUSUM (Cumulative Sum) algorithm.
    
    Two-sided CUSUM detects both upward and downward shifts in mean.
    
    Args:
        series: Time series values
        k: Drift parameter (allowance for noise). Typical: 0.5 to 2.0
        h: Threshold for detection. Typical: 4.0 to 6.0
        
    Returns:
        List of indices where structural breaks are detected
        
    Example:
        >>> cusum_breaks([100]*10 + [150]*10, k=1.0, h=3.0)
        [10]
    """
    if len(series) < 3:
        return []

    # Compute mean and std for normalization
    mean = safe_mean(series)
    std = safe_std(series)

    if mean is None or std is None or std == 0:
        return []  # Constant series or insufficient data

    # Normalize series
    normalized = [(x - mean) / std for x in series]

    # Initialize CUSUM statistics
    s_high = 0.0  # Cumulative sum for upward shifts
    s_low = 0.0   # Cumulative sum for downward shifts
    breaks = []

    for i, val in enumerate(normalized):
        # Update CUSUM statistics
        s_high = max(0, s_high + val - k)
        s_low = max(0, s_low - val - k)

        # Check for threshold breach
        if s_high > h or s_low > h:
            breaks.append(i)
            # Reset after detection
            s_high = 0.0
            s_low = 0.0

    return breaks


def zscore_outliers(series: list[float], z: float = 2.5) -> list[int]:
    """
    Detect outliers using z-score method.
    
    Args:
        series: Time series values
        z: Z-score threshold (typical: 2.0 to 3.0)
        
    Returns:
        List of indices where |z-score| >= threshold
        
    Example:
        >>> zscore_outliers([100, 102, 101, 200, 99], z=2.0)
        [3]
    """
    if len(series) < 3:
        return []

    mean = safe_mean(series)
    std = safe_std(series)

    if mean is None or std is None or std == 0:
        return []  # Constant series or insufficient data

    outliers = []

    for i, val in enumerate(series):
        z_score = abs((val - mean) / std)
        if z_score >= z:
            outliers.append(i)

    return outliers


def summarize_breaks(series: list[float]) -> dict[str, float | None]:
    """
    Summarize structural breaks and outliers in a series.
    
    Args:
        series: Time series values
        
    Returns:
        Dictionary with:
        - first_break_idx: Index of first CUSUM break (or None)
        - n_breaks: Number of CUSUM breaks detected
        - max_jump_abs: Largest absolute jump between consecutive points
        - max_jump_pct: Largest percentage jump (or None if prev is 0)
        
    Example:
        >>> summarize_breaks([100, 102, 150, 152])
        {'first_break_idx': 2, 'n_breaks': 1, 'max_jump_abs': 48.0, 'max_jump_pct': 47.06}
    """
    if len(series) < 2:
        return {
            'first_break_idx': None,
            'n_breaks': 0,
            'max_jump_abs': None,
            'max_jump_pct': None
        }

    # Detect breaks
    breaks = cusum_breaks(series, k=1.0, h=5.0)

    # Find maximum jumps
    max_jump_abs = 0.0
    max_jump_pct = None

    for i in range(1, len(series)):
        jump_abs = abs(series[i] - series[i-1])
        if jump_abs > max_jump_abs:
            max_jump_abs = jump_abs

        if series[i-1] != 0:
            jump_pct = abs((series[i] - series[i-1]) / series[i-1] * 100)
            if max_jump_pct is None or jump_pct > max_jump_pct:
                max_jump_pct = jump_pct

    return {
        'first_break_idx': breaks[0] if breaks else None,
        'n_breaks': len(breaks),
        'max_jump_abs': max_jump_abs if max_jump_abs > 0 else None,
        'max_jump_pct': max_jump_pct
    }


def rolling_variance_breaks(
    series: list[float],
    window: int = 12,
    threshold: float = 2.0
) -> list[int]:
    """
    Detect changes in volatility using rolling variance.
    
    Args:
        series: Time series values
        window: Window size for computing rolling variance
        threshold: Multiplier for detecting variance breaks
        
    Returns:
        List of indices where variance changes significantly
    """
    if len(series) < window * 2:
        return []

    variances = []

    # Compute rolling variance
    for i in range(window, len(series) + 1):
        window_data = series[i-window:i]
        var = safe_std(window_data)
        if var is not None:
            variances.append(var ** 2)
        else:
            variances.append(0.0)

    if not variances:
        return []

    # Find breaks in variance
    mean_var = safe_mean(variances)
    if mean_var is None or mean_var == 0:
        return []

    breaks = []
    for i in range(1, len(variances)):
        ratio = variances[i] / mean_var
        if ratio > threshold or ratio < (1.0 / threshold):
            breaks.append(i + window - 1)  # Adjust for window offset

    return breaks
