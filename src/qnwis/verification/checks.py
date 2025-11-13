"""
Data validation checks for QNWIS.

Fixes for sum-to-one validation and other consistency checks.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


def check_gender_sum_to_one(
    male_percent: float,
    female_percent: float,
    total_percent: float,
    tolerance_pp: float = 0.5
) -> tuple[bool, Optional[str]]:
    """
    Check that male + female = total within tolerance.
    
    FIXED: Previously incorrectly summed all three values.
    Now correctly computes: abs((male + female) - total)
    
    Args:
        male_percent: Male percentage
        female_percent: Female percentage
        total_percent: Total percentage
        tolerance_pp: Tolerance in percentage points (default 0.5pp)
        
    Returns:
        (is_valid, error_message)
    """
    # Compute the sum of male and female
    sum_mf = male_percent + female_percent
    
    # Compute deviation from total
    deviation = abs(sum_mf - total_percent)
    
    is_valid = deviation <= tolerance_pp
    
    if not is_valid:
        error_msg = (
            f"Gender sum validation failed: "
            f"male ({male_percent:.2f}%) + female ({female_percent:.2f}%) "
            f"= {sum_mf:.2f}%, expected {total_percent:.2f}% "
            f"(deviation: {deviation:.2f}pp, tolerance: {tolerance_pp}pp)"
        )
        logger.warning(error_msg)
        return False, error_msg
    
    return True, None


def get_utc_timestamp() -> str:
    """
    Get current UTC timestamp in ISO format.
    
    FIXED: Previously used epoch timestamps (1970).
    Now uses datetime.now(timezone.utc).isoformat()
    
    Returns:
        ISO format timestamp (e.g., "2025-11-12T14:30:00+00:00")
    """
    return datetime.now(timezone.utc).isoformat()


def validate_timestamp(timestamp_str: str) -> bool:
    """
    Validate that timestamp is in correct format and not epoch.
    
    Args:
        timestamp_str: Timestamp string to validate
        
    Returns:
        True if valid
    """
    try:
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        
        # Check it's not epoch (1970)
        if dt.year == 1970:
            logger.warning(f"Timestamp is epoch: {timestamp_str}")
            return False
        
        # Check it's not in the future (with 1 hour tolerance)
        now = datetime.now(timezone.utc)
        if dt > now:
            from datetime import timedelta
            if dt - now > timedelta(hours=1):
                logger.warning(f"Timestamp is in future: {timestamp_str}")
                return False
        
        return True
    
    except Exception as e:
        logger.error(f"Invalid timestamp format: {timestamp_str}: {e}")
        return False


def check_percentage_bounds(
    value: float,
    field_name: str,
    min_val: float = 0.0,
    max_val: float = 100.0
) -> tuple[bool, Optional[str]]:
    """
    Check that percentage value is within bounds.
    
    Args:
        value: Percentage value to check
        field_name: Name of field (for error messages)
        min_val: Minimum valid value (default 0.0)
        max_val: Maximum valid value (default 100.0)
        
    Returns:
        (is_valid, error_message)
    """
    if not min_val <= value <= max_val:
        error_msg = (
            f"{field_name} out of bounds: {value:.2f}% "
            f"(expected {min_val:.2f}% - {max_val:.2f}%)"
        )
        logger.warning(error_msg)
        return False, error_msg
    
    return True, None


def validate_data_freshness(
    asof_date: str,
    max_age_days: int = 365
) -> tuple[bool, Optional[str]]:
    """
    Validate that data is not too old.
    
    Args:
        asof_date: Data as-of date (ISO format)
        max_age_days: Maximum age in days
        
    Returns:
        (is_valid, warning_message)
    """
    try:
        data_date = datetime.fromisoformat(asof_date.replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        age_days = (now - data_date).days
        
        if age_days > max_age_days:
            warning_msg = (
                f"Data is {age_days} days old "
                f"(threshold: {max_age_days} days)"
            )
            logger.warning(warning_msg)
            return False, warning_msg
        
        return True, None
    
    except Exception as e:
        logger.error(f"Invalid date format: {asof_date}: {e}")
        return False, f"Invalid date format: {asof_date}"
