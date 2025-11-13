"""
FastAPI router for multi-agent council endpoints.

Exposes HTTP API for executing the council of agents with deterministic
data access and numeric verification.
"""

from __future__ import annotations

import logging
import warnings
from typing import Any

from fastapi import APIRouter

from ...orchestration.council import CouncilConfig, run_council

router = APIRouter(tags=["council-legacy"])
logger = logging.getLogger(__name__)


@router.post("/council/run")
def council_run(queries_dir: str | None = None, ttl_s: int = 300) -> dict[str, Any]:
    """
    [DEPRECATED] Legacy deterministic council.

    Use /api/v1/council/run-llm for the LLM multi-agent workflow.

    This endpoint executes the legacy council with deterministic data access.
    It is maintained for backward compatibility but will be removed in a future version.

    Args:
        queries_dir: Optional path to query definitions directory
        ttl_s: Cache TTL in seconds (default: 300)

    Returns:
        Dictionary containing:
            - status: "deprecated"
            - message: Deprecation notice
            - council: CouncilReport with findings (legacy mode)
            - verification: Agent-level verification results (legacy mode)
    """
    warnings.warn(
        "DEPRECATED: /v1/council/run → use /v1/council/run-llm",
        DeprecationWarning,
        stacklevel=2,
    )

    # Execute legacy deterministic council
    cfg = CouncilConfig(queries_dir=queries_dir, ttl_s=ttl_s)
    try:
        result = run_council(cfg)
    except Exception:
        logger.exception("Legacy council execution failed; returning placeholder")
        result = {"council": None, "verification": None}

    # Wrap result with deprecation metadata
    return {
        "status": "deprecated",
        "message": "Use /api/v1/council/run-llm for LLM-powered analysis.",
        **result,
    }
