"""
Admin diagnostics endpoints for LLM configuration and health.
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from ...llm.client import LLMClient
from ...security import Principal
from ...security.rbac import require_roles

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


def _get_llm_client(request: Request) -> LLMClient:
    """Return a cached LLM client for admin diagnostics."""
    client = getattr(request.app.state, "admin_llm_client", None)
    if isinstance(client, LLMClient):
        return client
    try:
        client = LLMClient()
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Failed to initialize LLM client for admin endpoints: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="LLM client misconfigured",
        ) from exc
    request.app.state.admin_llm_client = client
    return client


@router.get("/models", response_model=dict)
async def list_models(
    _principal: Annotated[Principal, Depends(require_roles("admin", "service"))],
    client: LLMClient = Depends(_get_llm_client),
) -> dict:
    """
    Return configured models per provider along with timeout configuration.
    """
    return await client.list_models()


@router.get("/health/llm", response_model=dict)
async def llm_health(
    _principal: Annotated[Principal, Depends(require_roles("admin", "service"))],
    client: LLMClient = Depends(_get_llm_client),
) -> dict:
    """
    Provide LLM health diagnostics: key presence, configured models, and provider in use.
    """
    models_payload = await client.list_models()
    config = client.config
    api_keys = {
        "anthropic": bool(config.anthropic_api_key),
        "openai": bool(config.openai_api_key),
    }
    
    missing: list[str] = []
    if client.provider == "anthropic" and not api_keys["anthropic"]:
        missing.append("ANTHROPIC_API_KEY")
    if client.provider == "openai" and not api_keys["openai"]:
        missing.append("OPENAI_API_KEY")
    
    status_value = "ok"
    reasons: list[str] = []
    
    if missing:
        status_value = "degraded"
        reasons.append(f"missing_keys={','.join(missing)}")
    if client.provider != "stub" and client.model == "stub-model":
        status_value = "degraded"
        reasons.append("model_not_configured")
    
    return {
        "status": status_value,
        "provider": client.provider,
        "model": client.model,
        "api_keys": api_keys,
        "missing": missing,
        "configured_models": models_payload.get("configured_models", {}),
        "timeouts": models_payload.get("timeouts", {}),
        "reasons": reasons,
    }
