"""
Early-warning detection for LMIS time-series.

Implements rule-based risk scoring:
- Band breach: actual exceeds prediction interval
- Slope reversal: recent trend opposes prior trend
- Volatility spike: recent change exceeds historical variability

All methods are deterministic and citation-ready.
"""

from __future__ import annotations

import math


def band_breach(actual: float, yhat: float, half_width: float) -> bool:
    """
    Detect if actual value breaches prediction interval.

    Args:
        actual: Observed value
        yhat: Point forecast
        half_width: Prediction interval half-width

    Returns:
        True if |actual - yhat| > half_width
    """
    return abs(actual - yhat) > half_width


def slope_reversal(recent: list[float], window: int = 3) -> bool:
    """
    Detect if recent slope opposes prior windowed slope.

    Computes slope over last 'window' points vs. slope of previous 'window' points.
    Reversal = sign change between these two slopes.

    Args:
        recent: Recent time series values (ordered oldest to newest)
        window: Window size for slope computation (default 3)

    Returns:
        True if slope sign reverses between windows
    """
    if len(recent) < 2 * window:
        return False  # Insufficient data

    # Split into prior and recent windows
    prior_window = recent[-2 * window : -window]
    recent_window = recent[-window:]

    def _simple_slope(values: list[float]) -> float:
        """Compute simple linear slope (last - first) / (n - 1)."""
        if len(values) < 2:
            return 0.0
        return (values[-1] - values[0]) / (len(values) - 1)

    prior_slope = _simple_slope(prior_window)
    recent_slope = _simple_slope(recent_window)

    # Check for sign reversal (excluding near-zero slopes)
    threshold = 1e-9
    if abs(prior_slope) < threshold or abs(recent_slope) < threshold:
        return False

    return (prior_slope * recent_slope) < 0


def volatility_spike(recent: list[float], lookback: int = 6, z: float = 2.5) -> bool:
    """
    Detect if most recent change exceeds historical volatility.

    Compares last absolute change against mean + z*std of prior changes.

    Args:
        recent: Recent time series values
        lookback: Number of historical changes to compare (default 6)
        z: Z-score threshold for spike detection (default 2.5)

    Returns:
        True if last change exceeds threshold
    """
    if len(recent) < lookback + 2:
        return False  # Insufficient history

    # Compute changes (first differences)
    changes = [recent[i] - recent[i - 1] for i in range(1, len(recent))]

    if len(changes) < lookback + 1:
        return False

    # Historical changes (excluding most recent)
    hist_changes = changes[-(lookback + 1) : -1]
    last_change = abs(changes[-1])

    # Compute mean and std of historical absolute changes
    abs_hist = [abs(c) for c in hist_changes]
    mean_change = sum(abs_hist) / len(abs_hist)

    # Safe std computation
    variance = sum((c - mean_change) ** 2 for c in abs_hist) / len(abs_hist)
    std_change = math.sqrt(variance) if variance > 0 else 0.0

    # Threshold: mean + z*std
    threshold = mean_change + z * std_change

    return last_change > threshold


def risk_score(flags: dict[str, bool], weights: dict[str, float]) -> float:
    """
    Compute weighted risk score from binary flags.

    Score = Σ(weight_i * flag_i) * 100, clamped to [0, 100].

    Args:
        flags: Dict mapping flag names to boolean values
        weights: Dict mapping flag names to weights (should sum to 1.0)

    Returns:
        Risk score in range [0, 100]
    """
    if not flags or not weights:
        return 0.0

    ordered_flags = sorted(flags.keys())
    normalized_weights: dict[str, float] = {}
    total_weight = 0.0
    for flag in ordered_flags:
        raw_weight = weights.get(flag, 0.0)
        if not isinstance(raw_weight, (int, float)) or not math.isfinite(raw_weight):
            weight = 0.0
        else:
            weight = max(0.0, float(raw_weight))
        normalized_weights[flag] = weight
        total_weight += weight

    if total_weight <= 0.0:
        return 0.0

    if abs(total_weight - 1.0) > 1e-6:
        for flag in normalized_weights:
            normalized_weights[flag] /= total_weight

    score = sum(
        normalized_weights[flag] * (1.0 if flags[flag] else 0.0)
        for flag in ordered_flags
    )

    return max(0.0, min(100.0, score * 100.0))
