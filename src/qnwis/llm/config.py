"""
LLM configuration for QNWIS.

Manages provider selection, model configuration, and API keys.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional


def _split_models(raw: Optional[str]) -> tuple[str, ...]:
    """Split a comma-separated list of model IDs from the environment."""
    if not raw:
        return ()
    return tuple(part.strip() for part in raw.split(",") if part.strip())


@dataclass
class LLMConfig:
    """LLM configuration."""
    
    provider: str  # "anthropic" or "openai"
    anthropic_model: Optional[str]
    openai_model: Optional[str]
    anthropic_api_key: Optional[str]
    openai_api_key: Optional[str]
    timeout_seconds: int
    max_retries: int
    anthropic_model_choices: tuple[str, ...] = field(default_factory=tuple)
    openai_model_choices: tuple[str, ...] = field(default_factory=tuple)
    
    def get_model(self, provider: Optional[str] = None) -> str:
        """Get model for specified provider."""
        p = (provider or self.provider).lower()
        if p == "anthropic":
            if not self.anthropic_model:
                raise ValueError(
                    "QNWIS_ANTHROPIC_MODEL (or QNWIS_ANTHROPIC_MODELS) must be set "
                    "when using the Anthropic provider"
                )
            return self.anthropic_model
        if p == "openai":
            if not self.openai_model:
                raise ValueError(
                    "QNWIS_OPENAI_MODEL (or QNWIS_OPENAI_MODELS) must be set "
                    "when using the OpenAI provider"
                )
            return self.openai_model
        raise ValueError(
            f"Unknown provider: {p}. "
            "Use 'anthropic' or 'openai'. Stub mode is deleted."
        )
    
    def get_api_key(self, provider: Optional[str] = None) -> Optional[str]:
        """Get API key for specified provider."""
        p = (provider or self.provider).lower()
        if p == "anthropic":
            return self.anthropic_api_key
        if p == "openai":
            return self.openai_api_key
        raise ValueError(
            f"Unknown provider: {p}. "
            "Use 'anthropic' or 'openai'. Stub mode is deleted."
        )
    
    def configured_models(self) -> dict[str, list[str]]:
        """Return configured models per provider (for diagnostics)."""
        models: dict[str, list[str]] = {}
        if self.anthropic_model_choices:
            models["anthropic"] = list(self.anthropic_model_choices)
        elif self.anthropic_model:
            models["anthropic"] = [self.anthropic_model]
        if self.openai_model_choices:
            models["openai"] = list(self.openai_model_choices)
        elif self.openai_model:
            models["openai"] = [self.openai_model]
        return models


def get_llm_config() -> LLMConfig:
    """
    Load LLM configuration from environment.
    
    Environment variables:
    - QNWIS_LLM_PROVIDER: "anthropic" or "openai" (default: anthropic)
    - QNWIS_ANTHROPIC_MODEL: Anthropic model name (required if provider=anthropic)
    - QNWIS_ANTHROPIC_MODELS: CSV list of allowed Anthropic models (optional)
    - QNWIS_OPENAI_MODEL: OpenAI model name (required if provider=openai)
    - QNWIS_OPENAI_MODELS: CSV list of allowed OpenAI models (optional)
    - ANTHROPIC_API_KEY: Anthropic API key
    - OPENAI_API_KEY: OpenAI API key
    - QNWIS_LLM_TIMEOUT: Timeout in seconds (default: 60, capped at 60)
    - QNWIS_LLM_MAX_RETRIES: Max retries for retryable errors (default: 3)
    
    Returns:
        LLMConfig instance
    """
    provider = os.getenv("QNWIS_LLM_PROVIDER", "anthropic").lower()
    anthropic_choices = _split_models(os.getenv("QNWIS_ANTHROPIC_MODELS"))
    openai_choices = _split_models(os.getenv("QNWIS_OPENAI_MODELS"))
    
    anthropic_model = os.getenv("QNWIS_ANTHROPIC_MODEL") or (
        anthropic_choices[0] if anthropic_choices else None
    )
    openai_model = os.getenv("QNWIS_OPENAI_MODEL") or (
        openai_choices[0] if openai_choices else None
    )
    
    timeout = min(int(os.getenv("QNWIS_LLM_TIMEOUT", "60")), 60)
    max_retries = max(0, int(os.getenv("QNWIS_LLM_MAX_RETRIES", "3")))
    
    return LLMConfig(
        provider=provider,
        anthropic_model=anthropic_model,
        openai_model=openai_model,
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        timeout_seconds=timeout,
        max_retries=max_retries,
        anthropic_model_choices=anthropic_choices,
        openai_model_choices=openai_choices,
    )
