"""
Robust LLM model resolver with fallbacks.

Provides model selection with environment variable overrides and automatic fallback
when primary models are unavailable.
"""

import logging
import os
from typing import Callable, Tuple, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Model hierarchy (in order of preference)
ANTHROPIC_MODELS = [
    "claude-sonnet-4-5-20250929",  # Latest Sonnet 4.5
    "claude-3-5-sonnet-20241022",  # Sonnet 3.5 (deprecated but may work)
    "claude-3-opus-20240229",      # Opus 3 fallback
]

OPENAI_MODELS = [
    "gpt-4o",                      # GPT-4 Optimized
    "gpt-4-turbo",                 # GPT-4 Turbo
    "gpt-4",                       # GPT-4 base
]


def resolve_models() -> Tuple[str, str]:
    """
    Return (primary_model, fallback_model) for LLM operations.
    
    Selection logic:
      1. Use QNWIS_ANTHROPIC_MODEL env var if set
      2. Else try first available Anthropic model
      3. Fallback: Use QNWIS_OPENAI_MODEL env var or first OpenAI model
    
    Returns:
        Tuple of (primary_model_id, fallback_model_id)
        
    Examples:
        >>> os.environ['QNWIS_ANTHROPIC_MODEL'] = 'claude-sonnet-4-5-20250929'
        >>> primary, fallback = resolve_models()
        >>> primary
        'claude-sonnet-4-5-20250929'
        >>> fallback
        'gpt-4o'
    """
    # Primary model selection
    primary = os.getenv("QNWIS_ANTHROPIC_MODEL")
    if primary:
        logger.info(f"Using primary model from env: {primary}")
    else:
        primary = ANTHROPIC_MODELS[0]
        logger.info(f"Using default primary model: {primary}")
    
    # Fallback model selection
    fallback = os.getenv("QNWIS_OPENAI_MODEL")
    if fallback:
        logger.info(f"Using fallback model from env: {fallback}")
    else:
        fallback = OPENAI_MODELS[0]
        logger.info(f"Using default fallback model: {fallback}")
    
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
