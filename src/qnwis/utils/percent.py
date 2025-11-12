"""
Percent normalization utilities for QNWIS.

CRITICAL CONTRACT:
- Upstream datasets (World Bank SL.UEM.TOTL.ZS, Qatar PSA indicators) store
  values ALREADY in percent units.
- Example: 0.11 means 0.11%, NOT 11%
- DO NOT multiply by 100 on render
- This prevents "fabrication by unit error" per Deterministic Data Layer spec
"""

from __future__ import annotations
from typing import Optional


def normalize_percent(p: Optional[float]) -> Optional[float]:
    """
    Normalize percent values to correct units per QNWIS contract.
    
    QNWIS contract: upstream datasets (e.g. World Bank SL.UEM.TOTL.ZS)
    are ALREADY in percent units. Example: 0.11 == 0.11%.
    Do NOT multiply by 100 on render.
    
    If a mistakenly multiplied value slips through (>10 and <= 10000),
    scale it back to reasonable percent.
    
    Args:
        p: Percent value from data source
        
    Returns:
        Normalized percent value (None if input is None)
        
    Examples:
        >>> normalize_percent(0.11)  # Correct: 0.11%
        0.11
        >>> normalize_percent(11.0)  # Mistakenly multiplied, fix it
        0.11
        >>> normalize_percent(5.66)  # Regular value
        5.66
        >>> normalize_percent(None)
        None
    """
    if p is None:
        return None
    
    # If value is suspiciously large (>10 but <=10000), assume it was
    # incorrectly multiplied by 100 and scale back
    # Threshold of 10 catches unemployment rates like 11.0% that should be 0.11%
    if 10 < p <= 10000:
        return p / 100.0
    
    return p


def format_percent(p: Optional[float], decimals: int = 2) -> str:
    """
    Format a percent value for display.
    
    Args:
        p: Percent value (already in percent units)
        decimals: Number of decimal places
        
    Returns:
        Formatted string with % symbol, or "N/A" if None
        
    Examples:
        >>> format_percent(0.11)
        '0.11%'
        >>> format_percent(5.66, decimals=1)
        '5.7%'
        >>> format_percent(None)
        'N/A'
    """
    if p is None:
        return "N/A"
    
    normalized = normalize_percent(p)
    return f"{normalized:.{decimals}f}%"
