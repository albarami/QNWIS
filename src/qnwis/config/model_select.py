"""
Robust LLM model resolver with fallbacks driven entirely by environment config.
"""

from __future__ import annotations

import logging
from typing import Callable, Tuple, TypeVar

from src.qnwis.llm.config import get_llm_config

logger = logging.getLogger(__name__)

T = TypeVar("T")


def resolve_models() -> Tuple[str, str]:
    """
    Return (primary_model, fallback_model) for LLM operations.
    
    Models are fully environment-driven. If a model is not configured, we fall back
    to the stub identifier so diagnostics remain readable without leaking defaults.
    """
    config = get_llm_config()
    primary = config.anthropic_model or "stub-model"
    fallback = config.openai_model or "stub-model"
    
    if primary == "stub-model":
        logger.warning(
            "QNWIS_ANTHROPIC_MODEL not set; primary model defaults to stub-model."
        )
    if fallback == "stub-model":
        logger.warning(
            "QNWIS_OPENAI_MODEL not set; fallback model defaults to stub-model."
        )
    
    return primary, fallback


def get_anthropic_model() -> str:
    """
    Get the configured Anthropic model.
    
    Returns:
        Anthropic model identifier
    """
    primary, _ = resolve_models()
    return primary


def get_openai_model() -> str:
    """
    Get the configured OpenAI model.
    
    Returns:
        OpenAI model identifier
    """
    _, fallback = resolve_models()
    return fallback


def get_model_provider(model_id: str) -> str:
    """
    Determine the provider for a given model ID.
    
    Args:
        model_id: Model identifier
        
    Returns:
        Provider name: "anthropic" or "openai"
    """
    if model_id.startswith("claude"):
        return "anthropic"
    elif model_id.startswith("gpt"):
        return "openai"
    else:
        logger.warning(f"Unknown model provider for: {model_id}, defaulting to openai")
        return "openai"


def call_with_model_fallback(
    primary_call: Callable[[], T],
    fallback_call: Callable[[], T]
) -> Tuple[T, bool]:
    """
    Execute a primary model call with automatic fallback handling.
    
    Args:
        primary_call: Callable invoking the preferred provider
        fallback_call: Callable invoking the backup provider
        
    Returns:
        Tuple of (result, fallback_used_flag)
    """
    try:
        return primary_call(), False
    except Exception as exc:
        status_code = getattr(getattr(exc, "response", None), "status_code", None)
        if status_code == 404:
            logger.warning("Primary model returned 404. Falling back to backup provider.")
        else:
            logger.warning("Primary model failed (%s). Falling back to backup provider.", exc)
        return fallback_call(), True
