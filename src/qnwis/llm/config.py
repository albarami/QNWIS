"""
LLM configuration for QNWIS.

Manages provider selection, model configuration, and API keys.
Supports: Anthropic Claude, OpenAI GPT, and Azure OpenAI.

All fields are populated from environment variables automatically
via pydantic-settings BaseSettings.
"""

from __future__ import annotations

from typing import Optional

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _split_models(raw: Optional[str]) -> tuple[str, ...]:
    """Split a comma-separated list of model IDs from the environment."""
    if not raw:
        return ()
    return tuple(part.strip() for part in raw.split(",") if part.strip())


class LLMConfig(BaseSettings):
    """LLM configuration supporting Anthropic, OpenAI, and Azure OpenAI.

    Environment variables are mapped automatically:
      QNWIS_LLM_PROVIDER          -> provider
      QNWIS_ANTHROPIC_MODEL       -> anthropic_model
      QNWIS_OPENAI_MODEL          -> openai_model
      QNWIS_AZURE_MODEL           -> azure_model
      ANTHROPIC_API_KEY            -> anthropic_api_key
      OPENAI_API_KEY               -> openai_api_key
      AZURE_OPENAI_API_KEY         -> azure_api_key
      AZURE_OPENAI_ENDPOINT        -> azure_endpoint
      AZURE_OPENAI_API_VERSION     -> azure_api_version
      QNWIS_LLM_TIMEOUT           -> timeout_seconds
      QNWIS_LLM_MAX_RETRIES       -> max_retries
      QNWIS_ANTHROPIC_MODELS      -> anthropic_models_csv
      QNWIS_OPENAI_MODELS         -> openai_models_csv
      QNWIS_AZURE_MODELS          -> azure_models_csv
    """

    model_config = SettingsConfigDict(
        env_prefix="",
        case_sensitive=False,
        extra="ignore",
    )

    provider: str = Field(
        default="anthropic",
        validation_alias="QNWIS_LLM_PROVIDER",
    )
    anthropic_model: Optional[str] = Field(
        default=None,
        validation_alias="QNWIS_ANTHROPIC_MODEL",
    )
    openai_model: Optional[str] = Field(
        default=None,
        validation_alias="QNWIS_OPENAI_MODEL",
    )
    azure_model: Optional[str] = Field(
        default=None,
        validation_alias="QNWIS_AZURE_MODEL",
    )
    anthropic_api_key: Optional[str] = Field(
        default=None,
        validation_alias="ANTHROPIC_API_KEY",
    )
    openai_api_key: Optional[str] = Field(
        default=None,
        validation_alias="OPENAI_API_KEY",
    )
    azure_api_key: Optional[str] = Field(
        default=None,
        validation_alias="AZURE_OPENAI_API_KEY",
    )
    azure_endpoint: Optional[str] = Field(
        default=None,
        validation_alias="AZURE_OPENAI_ENDPOINT",
    )
    azure_api_version: str = Field(
        default="2024-08-01-preview",
        validation_alias="AZURE_OPENAI_API_VERSION",
    )
    timeout_seconds: int = Field(
        default=120,
        validation_alias="QNWIS_LLM_TIMEOUT",
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        validation_alias="QNWIS_LLM_MAX_RETRIES",
    )

    # CSV lists of allowed models per provider (parsed from env)
    anthropic_models_csv: Optional[str] = Field(
        default=None,
        validation_alias="QNWIS_ANTHROPIC_MODELS",
    )
    openai_models_csv: Optional[str] = Field(
        default=None,
        validation_alias="QNWIS_OPENAI_MODELS",
    )
    azure_models_csv: Optional[str] = Field(
        default=None,
        validation_alias="QNWIS_AZURE_MODELS",
    )

    # Derived tuple fields populated by validator
    anthropic_model_choices: tuple[str, ...] = Field(default=(), exclude=True)
    openai_model_choices: tuple[str, ...] = Field(default=(), exclude=True)
    azure_model_choices: tuple[str, ...] = Field(default=(), exclude=True)

    @model_validator(mode="after")
    def _derive_model_choices(self) -> LLMConfig:
        """Parse CSV model lists and fill in model defaults from first choice."""
        self.provider = self.provider.lower()

        self.anthropic_model_choices = _split_models(self.anthropic_models_csv)
        self.openai_model_choices = _split_models(self.openai_models_csv)
        self.azure_model_choices = _split_models(self.azure_models_csv)

        if not self.anthropic_model and self.anthropic_model_choices:
            self.anthropic_model = self.anthropic_model_choices[0]
        if not self.openai_model and self.openai_model_choices:
            self.openai_model = self.openai_model_choices[0]
        if not self.azure_model and self.azure_model_choices:
            self.azure_model = self.azure_model_choices[0]

        return self

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
        raise ValueError(
            f"Unknown provider: {p}. "
            "Use 'anthropic', 'openai', or 'azure'."
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
        raise ValueError(
            f"Unknown provider: {p}. "
            "Use 'anthropic', 'openai', or 'azure'."
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

    BaseSettings reads env vars automatically; this factory function
    is retained for backwards-compatible call-sites.

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
    - QNWIS_LLM_TIMEOUT: Timeout in seconds (default: 120)
    - QNWIS_LLM_MAX_RETRIES: Max retries for retryable errors (default: 3)

    Returns:
        LLMConfig instance
    """
    return LLMConfig()
