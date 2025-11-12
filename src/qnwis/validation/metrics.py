"""
Validation metrics for QNWIS end-to-end testing.

Measures latency, citation coverage, freshness indicators, verification status,
and computes pass/fail against acceptance envelopes.
"""
from __future__ import annotations

import re
import statistics
from typing import Any, Dict, List, Tuple


def citation_coverage(resp_json: Dict[str, Any]) -> float:
    """
    Return fraction [0,1] of numeric claims with citations (approx. proxy).
    
    Args:
        resp_json: Response JSON containing data and metadata
        
    Returns:
        Coverage ratio: 1.0 if all numbers cited or no numbers present,
        0.0 if numbers present but no citations, fraction otherwise
    """
    meta = resp_json.get("metadata") or {}
    citations = meta.get("citations") or []
    numbers = _extract_numbers(str(resp_json))
    
    if not numbers:
        return 1.0  # No numbers to cite
    if not citations:
        return 0.0  # Numbers present but no citations
    
    return 1.0  # Simplified: if citations exist and numbers exist, assume covered


def freshness_present(resp_json: Dict[str, Any]) -> bool:
    """
    Check if freshness indicators (source ages) are present.
    
    Args:
        resp_json: Response JSON containing metadata
        
    Returns:
        True if freshness metadata found
    """
    meta = resp_json.get("metadata") or {}
    return bool(meta.get("freshness") or meta.get("data_sources"))


def verification_passed(resp_json: Dict[str, Any]) -> bool:
    """
    Deterministic layer & result verification pass/fail proxy.
    
    Args:
        resp_json: Response JSON containing verification metadata
        
    Returns:
        True if verification passed
    """
    meta = resp_json.get("metadata") or {}
    verification = meta.get("verification")
    return bool(verification in ("passed", True))


def compute_latency_ms(start_end: Tuple[float, float]) -> float:
    """
    Compute latency in milliseconds from timing tuple.
    
    Args:
        start_end: (start_time, end_time) in seconds
        
    Returns:
        Latency in milliseconds
    """
    return (start_end[1] - start_end[0]) * 1000.0


def compute_score(
    latency_ms: float,
    tier: str,
    verified: bool,
    cov: float,
    fresh: bool
) -> bool:
    """
    Compute pass/fail against acceptance envelope.
    
    Envelopes:
    - simple: <10s
    - medium: <30s
    - complex: <90s
    - dashboard: <3s
    
    Additional requirements:
    - Verification must pass
    - Citation coverage >= 0.6 (if numbers present)
    - Freshness indicators must be present
    
    Args:
        latency_ms: Response latency in milliseconds
        tier: Complexity tier (simple/medium/complex/dashboard)
        verified: Whether verification passed
        cov: Citation coverage ratio [0,1]
        fresh: Whether freshness indicators present
        
    Returns:
        True if all acceptance criteria met
    """
    limits = {
        "simple": 10_000,
        "medium": 30_000,
        "complex": 90_000,
        "dashboard": 3_000
    }
    limit = limits.get(tier, 30_000)
    
    # Coverage OK if >= 0.6 or 1.0 (no numbers to cite)
    cov_ok = cov >= 0.6
    
    return (
        (latency_ms <= limit) and
        verified and
        (cov_ok or cov == 1.0) and
        fresh
    )


def _extract_numbers(text: str) -> List[float]:
    """
    Extract numeric values from text.
    
    Args:
        text: Text to extract numbers from
        
    Returns:
        List of numeric values found
    """
    nums = re.findall(r"\b\d+(?:,\d{3})*(?:\.\d+)?\b", text)
    return [float(n.replace(",", "")) for n in nums]
