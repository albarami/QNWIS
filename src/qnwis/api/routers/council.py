"""
FastAPI router for multi-agent council endpoints.

Exposes HTTP API for executing the council of agents with deterministic
data access and numeric verification.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from ...orchestration.council import CouncilConfig, run_council

router = APIRouter(tags=["council"])


@router.post("/v1/council/run")
def council_run(queries_dir: str | None = None, ttl_s: int = 300) -> dict[str, Any]:
    """
    Execute multi-agent council with deterministic data access.

    Runs all 5 agents sequentially, verifies outputs against numeric
    invariants, and synthesizes a unified council report with consensus metrics.

    Args:
        queries_dir: Optional path to query definitions directory
        ttl_s: Cache TTL in seconds (default: 300)

    Returns:
        Dictionary containing:
            - council: CouncilReport with findings, consensus, warnings
            - verification: Agent-level verification results
    """
    cfg = CouncilConfig(queries_dir=queries_dir, ttl_s=ttl_s)
    return run_council(cfg)
