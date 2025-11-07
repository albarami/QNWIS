"""
Deterministic cache key generation and TTL policy.

Provides canonical key construction for QueryResult caching with
stable hashing of parameters and dataset-specific TTL policies.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Tuple

# Dataset-specific TTL policy (seconds)
TTL_POLICY: Dict[str, int] = {
    "get_retention_by_company": 24 * 3600,
    "get_salary_statistics": 24 * 3600,
    "get_employee_transitions": 12 * 3600,
    "get_qatarization_rates": 7 * 24 * 3600,
    "get_gcc_indicator": 30 * 24 * 3600,
    "get_world_bank_indicator": 30 * 24 * 3600,
}


def stable_params_hash(params: Dict[str, Any]) -> str:
    """
    Deterministic SHA256 over JSON with sorted keys + ISO dates.

    Args:
        params: Dictionary of parameters to hash

    Returns:
        16-character hex digest for compact key representation
    """

    def normalize(x: Any) -> Any:
        if isinstance(x, dict):
            return {k: normalize(x[k]) for k in sorted(x)}
        if isinstance(x, list):
            return [normalize(v) for v in x]
        if hasattr(x, "isoformat"):
            return x.isoformat()
        return x

    payload = json.dumps(normalize(params), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def make_cache_key(
    op: str, query_id: str, params: Dict[str, Any], version: str = "v1"
) -> Tuple[str, int]:
    """
    Build deterministic cache key and TTL for a query operation.

    Key format: qr:{op}:{query_id}:{hash}:{version}
    TTL: By operation via TTL_POLICY (default 24h)

    Args:
        op: Operation name (e.g., 'get_retention_by_company')
        query_id: Deterministic query identifier
        params: Query parameters dictionary
        version: Cache version string for schema evolution

    Returns:
        Tuple of (cache_key, ttl_seconds)
    """
    if not isinstance(query_id, str) or not query_id.strip():
        raise ValueError("query_id must be a non-empty string.")
    h = stable_params_hash(params)
    ttl = TTL_POLICY.get(op, 24 * 3600)
    return f"qr:{op}:{query_id}:{h}:{version}", ttl
