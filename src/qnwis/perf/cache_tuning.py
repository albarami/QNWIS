"""
Adaptive cache TTL strategies for QNWIS.

Provides intelligent TTL calculation based on operation type,
result size, and data volatility characteristics.
"""

from __future__ import annotations

import hashlib
from typing import Dict, Optional


# Operation stability profiles (seconds)
# Stable data → longer TTL; volatile data → shorter TTL
OPERATION_PROFILES: Dict[str, int] = {
    # Static reference data
    "get_occupations": 3600,  # 1 hour
    "get_nationalities": 3600,
    "get_education_levels": 3600,
    "get_industries": 1800,  # 30 min
    
    # Semi-static aggregates
    "get_salary_statistics": 900,  # 15 min
    "get_employment_trends": 600,  # 10 min
    "get_demographic_breakdown": 600,
    
    # Dynamic/volatile data
    "get_job_postings": 300,  # 5 min
    "get_active_applications": 180,  # 3 min
    "get_recent_hires": 300,
    
    # Real-time data
    "get_current_vacancies": 60,  # 1 min
    "get_live_metrics": 30,
}


def ttl_for(
    operation: str,
    row_count: int,
    base: int = 600,
    min_ttl: int = 60,
    max_ttl: int = 3600,
) -> int:
    """
    Calculate adaptive TTL based on operation and result characteristics.
    
    Strategy:
    1. Start with operation-specific base TTL (if known)
    2. Adjust based on result size (larger → longer TTL)
    3. Clamp to min/max bounds
    
    Args:
        operation: Operation name (e.g., "get_salary_statistics")
        row_count: Number of rows in result
        base: Default TTL if operation not in profile (seconds)
        min_ttl: Minimum TTL (seconds)
        max_ttl: Maximum TTL (seconds)
        
    Returns:
        TTL in seconds
        
    Example:
        >>> ttl_for("get_salary_statistics", 1000)
        900
        >>> ttl_for("get_job_postings", 50)
        300
        >>> ttl_for("unknown_operation", 100, base=300)
        330
    """
    # Get operation-specific base or use default
    op_base = OPERATION_PROFILES.get(operation, base)
    
    # Adjust for result size
    # Larger results → more expensive to recompute → longer TTL
    if row_count < 10:
        multiplier = 0.8  # Small result, may be volatile
    elif row_count < 100:
        multiplier = 1.0  # Normal
    elif row_count < 1000:
        multiplier = 1.2  # Larger result
    else:
        multiplier = 1.5  # Very large result
    
    ttl = int(op_base * multiplier)
    
    # Clamp to bounds
    return max(min_ttl, min(ttl, max_ttl))


def cache_key(
    operation: str,
    query_id: str,
    params: Optional[Dict[str, str]] = None,
) -> str:
    """
    Generate deterministic cache key from operation parameters.
    
    Args:
        operation: Operation name
        query_id: Query identifier
        params: Optional query parameters
        
    Returns:
        Cache key string (hex hash)
        
    Example:
        >>> cache_key("get_salary", "sal_001", {"year": "2024"})
        'get_salary:sal_001:a1b2c3d4...'
    """
    parts = [operation, query_id]
    
    if params:
        # Sort params for determinism
        param_str = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        parts.append(param_str)
    
    key_input = ":".join(parts)
    
    # Hash for compact key
    key_hash = hashlib.sha256(key_input.encode()).hexdigest()[:16]
    
    return f"{operation}:{query_id}:{key_hash}"


def should_cache(operation: str, row_count: int, duration_ms: float) -> bool:
    """
    Determine if a result should be cached based on cost/benefit.
    
    Cache if:
    - Result is expensive to compute (>100ms)
    - Result is not too small (<5 rows often not worth caching)
    - Operation is cacheable (not in exclusion list)
    
    Args:
        operation: Operation name
        row_count: Number of rows in result
        duration_ms: Query execution time in milliseconds
        
    Returns:
        True if result should be cached
        
    Example:
        >>> should_cache("get_salary_statistics", 500, 250.0)
        True
        >>> should_cache("get_single_record", 1, 5.0)
        False
    """
    # Don't cache operations that are explicitly excluded
    EXCLUDE_OPS = {
        "get_audit_log",  # Always fresh
        "get_user_session",  # User-specific
        "validate_token",  # Security-sensitive
    }
    
    if operation in EXCLUDE_OPS:
        return False
    
    # Don't cache very small results (overhead not worth it)
    if row_count < 5:
        return False
    
    # Cache if query took significant time
    if duration_ms > 100:
        return True
    
    # Cache moderate queries with decent result size
    if duration_ms > 50 and row_count > 20:
        return True
    
    return False
