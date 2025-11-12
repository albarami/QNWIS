"""
Unit normalization utilities for QNWIS.

Handles percent/ratio normalization to prevent double-scaling bugs.
"""

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

# World Bank indicators that are already in percent (0-100 scale)
PERCENT_INDICATORS = {
    "SL.UEM.TOTL.ZS",  # Unemployment rate
    "SL.UEM.TOTL.FE.ZS",  # Unemployment, female
    "SL.UEM.TOTL.MA.ZS",  # Unemployment, male
    "SL.TLF.CACT.FE.ZS",  # Labor force participation, female
    "SL.TLF.CACT.MA.ZS",  # Labor force participation, male
    "SL.TLF.CACT.ZS",  # Labor force participation
    "SP.POP.GROW",  # Population growth
    "NY.GDP.MKTP.KD.ZG",  # GDP growth
}


def normalize_percent_value(
    value: Any,
    indicator_id: Optional[str] = None,
    metadata: Optional[dict] = None
) -> float:
    """
    Normalize percent values to consistent scale.
    
    World Bank indicators ending in _ZS are already in percent (0-100).
    Other sources may use decimal (0-1) or percent (0-100).
    
    Args:
        value: Raw value
        indicator_id: Indicator ID (e.g., "SL.UEM.TOTL.ZS")
        metadata: Optional metadata with unit information
        
    Returns:
        Normalized value in percent (0-100 scale)
    """
    if not isinstance(value, (int, float)):
        return value
    
    # Check metadata for explicit unit
    if metadata and 'unit' in metadata:
        unit = metadata['unit'].lower()
        if unit == 'percent' or unit == '%':
            # Already in percent
            return float(value)
        elif unit == 'decimal' or unit == 'ratio':
            # Convert decimal to percent
            return float(value) * 100.0
    
    # Check if indicator is known to be in percent
    if indicator_id and indicator_id in PERCENT_INDICATORS:
        # Already in percent (0-100)
        return float(value)
    
    # Heuristic: if value is between 0 and 1, assume decimal
    if 0.0 <= value <= 1.0:
        logger.debug(f"Converting decimal {value} to percent")
        return float(value) * 100.0
    
    # Otherwise assume already in percent
    return float(value)


def is_percent_indicator(indicator_id: str) -> bool:
    """
    Check if indicator is already in percent scale.
    
    Args:
        indicator_id: Indicator ID
        
    Returns:
        True if indicator is in percent (0-100)
    """
    return indicator_id in PERCENT_INDICATORS


def format_percent(value: float, decimals: int = 2) -> str:
    """
    Format percent value for display.
    
    Args:
        value: Percent value (0-100 scale)
        decimals: Number of decimal places
        
    Returns:
        Formatted string (e.g., "11.50%")
    """
    return f"{value:.{decimals}f}%"


def validate_percent_range(value: float, allow_over_100: bool = False) -> bool:
    """
    Validate that percent value is in valid range.
    
    Args:
        value: Percent value to validate
        allow_over_100: Allow values over 100 (for growth rates)
        
    Returns:
        True if valid
    """
    if allow_over_100:
        return value >= 0.0
    else:
        return 0.0 <= value <= 100.0
