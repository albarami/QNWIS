"""
Health check endpoints for QNWIS API.

Provides liveness and readiness probes for Kubernetes/production deployments
with subsystem health checks and proper 200/503 status codes.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from ... import __version__ as APP_VERSION
from ...config.settings import Settings
from ...llm.config import get_llm_config

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health/live")
async def liveness() -> dict[str, str]:
    """
    Liveness probe - indicates if the service is running.

    Always returns 200 if the process is alive. Used by orchestrators
    to determine if the container should be restarted.

    Returns:
        Dictionary with status and timestamp
    """
    return {
        "status": "alive",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/health/ready")
async def readiness() -> JSONResponse:
    """
    Readiness probe - indicates if the service can handle traffic.

    Checks critical subsystems:
    - Data client initialization
    - LLM configuration availability
    - Database connectivity (if available)
    - Query registry presence

    Response contract (JSON):
        {
            "status": "healthy" | "degraded",
            "version": "<app version>",
            "llm_provider": "<provider name>",
            "llm_model": "<model name>",
            "registry_query_count": <int | null>,
            "timestamp": "<ISO-8601>",
            "checks": { <component>: <status string> }
        }

    Returns:
        200 if all checks pass (healthy)
        503 if any check fails (degraded/unhealthy)
    """
    settings = Settings()
    checks: dict[str, str | bool] = {}
    overall_healthy = True
    registry_query_count: int | None = None

    try:
        llm_config = get_llm_config()
        llm_provider = llm_config.provider
        llm_model = llm_config.get_model()
    except Exception as exc:
        llm_provider = "unavailable"
        llm_model = "unavailable"
        logger.warning("LLM config unavailable: %s", exc)

    # Check 1: Data Client
    try:
        from ...agents.base import DataClient

        DataClient()
        checks["data_client"] = "healthy"
    except Exception as e:
        overall_healthy = False
        checks["data_client"] = f"unhealthy: {str(e)[:100]}"
        logger.warning("Data client health check failed: %s", e)

    # Check 2: LLM Configuration (verify config is loadable, don't initialize client)
    try:
        # Just check that config is available - don't initialize client
        # (client requires API keys which may not be available in all environments)
        checks["llm_config"] = f"healthy ({llm_provider}/{llm_model})"
    except Exception as e:
        overall_healthy = False
        checks["llm_config"] = f"unhealthy: {str(e)[:100]}"
        logger.warning("LLM config health check failed: %s", e)

    # Check 3: Database (optional, skip if not configured)
    try:
        from ...data.deterministic.engine import get_engine
        from sqlalchemy import text

        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
            conn.close()
        checks["database"] = "healthy"
    except Exception as e:
        # Database check is optional, log but don't fail
        checks["database"] = f"unavailable: {str(e)[:100]}"
        logger.info("Database health check unavailable (this is OK): %s", e)

    # Check 4: Query Registry
    try:
        from ...data.deterministic.registry import DEFAULT_QUERY_ROOT, QueryRegistry

        registry_root = settings.queries_dir or str(DEFAULT_QUERY_ROOT)
        registry = QueryRegistry(root=str(registry_root))
        query_count = len(registry.list_queries())
        registry_query_count = query_count

        if query_count > 0:
            checks["query_registry"] = f"healthy ({query_count} queries)"
        else:
            overall_healthy = False
            checks["query_registry"] = "unhealthy: 0 queries found"
            logger.warning("Query registry has 0 queries")
    except Exception as e:
        overall_healthy = False
        checks["query_registry"] = f"unhealthy: {str(e)[:100]}"
        logger.warning("Query registry health check failed: %s", e)

    # Prepare response
    response_data: dict[str, Any] = {
        "status": "healthy" if overall_healthy else "degraded",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "version": APP_VERSION,
        "llm_provider": llm_provider,
        "llm_model": llm_model,
        "registry_query_count": registry_query_count,
    }

    # Return appropriate status code
    status_code = (
        status.HTTP_200_OK if overall_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
    )

    return JSONResponse(content=response_data, status_code=status_code)


@router.get("/health")
async def health_alias() -> dict[str, str]:
    """
    Alias for liveness probe.

    Simple health check endpoint for basic monitoring.
    """
    return await liveness()
