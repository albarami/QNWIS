"""
LLM configuration for QNWIS.

Manages provider selection, model configuration, and API keys.
Supports: Anthropic Claude, OpenAI GPT, and Azure OpenAI.
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
    """LLM configuration supporting Anthropic, OpenAI, and Azure OpenAI."""
    
    provider: str  # "anthropic", "openai", or "azure"
    anthropic_model: Optional[str]
    openai_model: Optional[str]
    azure_model: Optional[str]  # Azure OpenAI deployment name
    anthropic_api_key: Optional[str]
    openai_api_key: Optional[str]
    azure_api_key: Optional[str]
    azure_endpoint: Optional[str]
    azure_api_version: str
    timeout_seconds: int
    max_retries: int
    anthropic_model_choices: tuple[str, ...] = field(default_factory=tuple)
    openai_model_choices: tuple[str, ...] = field(default_factory=tuple)
    azure_model_choices: tuple[str, ...] = field(default_factory=tuple)
    
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
        if p == "azure":
            if not self.azure_model:
                raise ValueError(
                    "QNWIS_AZURE_MODEL (or QNWIS_AZURE_MODELS) must be set "
                    "when using the Azure OpenAI provider"
                )
            return self.azure_model
        if p == "stub":
            # Stub provider for testing - no real model needed
            return "stub-model"
        raise ValueError(
            f"Unknown provider: {p}. "
            "Use 'anthropic', 'openai', 'azure', or 'stub'."
        )
    
    def get_api_key(self, provider: Optional[str] = None) -> Optional[str]:
        """Get API key for specified provider."""
        p = (provider or self.provider).lower()
        if p == "anthropic":
            return self.anthropic_api_key
        if p == "openai":
            return self.openai_api_key
        if p == "azure":
            return self.azure_api_key
        if p == "stub":
            # Stub provider for testing - no API key needed
            return None
        raise ValueError(
            f"Unknown provider: {p}. "
            "Use 'anthropic', 'openai', 'azure', or 'stub'."
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
        if self.azure_model_choices:
            models["azure"] = list(self.azure_model_choices)
        elif self.azure_model:
            models["azure"] = [self.azure_model]
        return models


def get_llm_config() -> LLMConfig:
    """
    Load LLM configuration from environment.
    
    Environment variables:
    - QNWIS_LLM_PROVIDER: "anthropic", "openai", or "azure" (default: anthropic)
    
    Anthropic:
    - QNWIS_ANTHROPIC_MODEL: Anthropic model name (required if provider=anthropic)
    - QNWIS_ANTHROPIC_MODELS: CSV list of allowed Anthropic models (optional)
    - ANTHROPIC_API_KEY: Anthropic API key
    
    OpenAI:
    - QNWIS_OPENAI_MODEL: OpenAI model name (required if provider=openai)
    - QNWIS_OPENAI_MODELS: CSV list of allowed OpenAI models (optional)
    - OPENAI_API_KEY: OpenAI API key
    
    Azure OpenAI:
    - QNWIS_AZURE_MODEL: Azure OpenAI deployment name (required if provider=azure)
    - QNWIS_AZURE_MODELS: CSV list of allowed Azure models (optional)
    - AZURE_OPENAI_API_KEY: Azure OpenAI API key
    - AZURE_OPENAI_ENDPOINT: Azure OpenAI endpoint URL
    - AZURE_OPENAI_API_VERSION: API version (default: 2024-08-01-preview)
    
    General:
    - QNWIS_LLM_TIMEOUT: Timeout in seconds (default: 60)
    - QNWIS_LLM_MAX_RETRIES: Max retries for retryable errors (default: 3)
    
    Returns:
        LLMConfig instance
    """
    provider = os.getenv("QNWIS_LLM_PROVIDER", "anthropic").lower()
    
    # Anthropic config
    anthropic_choices = _split_models(os.getenv("QNWIS_ANTHROPIC_MODELS"))
    anthropic_model = os.getenv("QNWIS_ANTHROPIC_MODEL") or (
        anthropic_choices[0] if anthropic_choices else None
    )
    
    # OpenAI config
    openai_choices = _split_models(os.getenv("QNWIS_OPENAI_MODELS"))
    openai_model = os.getenv("QNWIS_OPENAI_MODEL") or (
        openai_choices[0] if openai_choices else None
    )
    
    # Azure OpenAI config
    azure_choices = _split_models(os.getenv("QNWIS_AZURE_MODELS"))
    azure_model = os.getenv("QNWIS_AZURE_MODEL") or (
        azure_choices[0] if azure_choices else None
    )
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    azure_api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview")
    
    # Timeout and retries
    timeout = min(int(os.getenv("QNWIS_LLM_TIMEOUT", "60")), 180)  # Allow up to 3 min for complex queries
    max_retries = max(0, int(os.getenv("QNWIS_LLM_MAX_RETRIES", "3")))
    
    return LLMConfig(
        provider=provider,
        anthropic_model=anthropic_model,
        openai_model=openai_model,
        azure_model=azure_model,
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        azure_api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        azure_endpoint=azure_endpoint,
        azure_api_version=azure_api_version,
        timeout_seconds=timeout,
        max_retries=max_retries,
        anthropic_model_choices=anthropic_choices,
        openai_model_choices=openai_choices,
        azure_model_choices=azure_choices,
    )
