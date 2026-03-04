"""
Real integration tests for the QNWIS LLM config module.

Verifies that get_llm_config() reads the actual environment variables
set in .env — NO mocks, NO synthetic data.
"""

from dotenv import load_dotenv

load_dotenv()

import os

import pytest

from src.qnwis.llm.config import get_llm_config

_HAS_AZURE_KEY = bool(os.getenv("AZURE_OPENAI_API_KEY"))
_SKIP_REASON = "AZURE_OPENAI_API_KEY not set — infrastructure unavailable"


# =========================================================================
# 1. get_llm_config() returns correct provider
# =========================================================================


class TestProviderFromEnv:
    """get_llm_config().provider reflects QNWIS_LLM_PROVIDER."""

    def test_provider_equals_env_var(self):
        cfg = get_llm_config()
        expected = os.getenv("QNWIS_LLM_PROVIDER", "anthropic").lower()
        assert cfg.provider == expected

    @pytest.mark.skipif(not _HAS_AZURE_KEY, reason=_SKIP_REASON)
    def test_provider_is_azure_when_env_says_azure(self):
        """With QNWIS_LLM_PROVIDER=azure the config must report 'azure'."""
        if os.getenv("QNWIS_LLM_PROVIDER", "").lower() != "azure":
            pytest.skip("Provider not set to azure in this environment")
        cfg = get_llm_config()
        assert cfg.provider == "azure"

    def test_provider_is_always_lowercase(self):
        cfg = get_llm_config()
        assert cfg.provider == cfg.provider.lower()


# =========================================================================
# 2. timeout_seconds defaults to 120 (not 7200)
# =========================================================================


class TestTimeoutDefault:
    """Default LLM timeout must be 120 s unless overridden by env."""

    def test_default_is_120_when_env_unset(self, monkeypatch):
        """Without QNWIS_LLM_TIMEOUT the timeout defaults to 120."""
        monkeypatch.delenv("QNWIS_LLM_TIMEOUT", raising=False)
        cfg = get_llm_config()
        assert cfg.timeout_seconds == 120

    def test_env_override_is_respected(self, monkeypatch):
        """QNWIS_LLM_TIMEOUT=90 → timeout_seconds == 90."""
        monkeypatch.setenv("QNWIS_LLM_TIMEOUT", "90")
        cfg = get_llm_config()
        assert cfg.timeout_seconds == 90

    def test_timeout_is_not_7200(self):
        """Regression guard: we never want a 2-hour default."""
        cfg = get_llm_config()
        assert cfg.timeout_seconds != 7200, (
            "timeout_seconds should NOT be 7200 — check QNWIS_LLM_TIMEOUT env var"
        )


# =========================================================================
# 3. azure_endpoint is read correctly from env
# =========================================================================


class TestAzureEndpoint:
    """get_llm_config().azure_endpoint mirrors AZURE_OPENAI_ENDPOINT."""

    @pytest.mark.skipif(not _HAS_AZURE_KEY, reason=_SKIP_REASON)
    def test_endpoint_matches_env(self):
        cfg = get_llm_config()
        assert cfg.azure_endpoint == os.getenv("AZURE_OPENAI_ENDPOINT")

    @pytest.mark.skipif(not _HAS_AZURE_KEY, reason=_SKIP_REASON)
    def test_endpoint_is_https_url(self):
        cfg = get_llm_config()
        assert cfg.azure_endpoint is not None
        assert cfg.azure_endpoint.startswith("https://")

    @pytest.mark.skipif(not _HAS_AZURE_KEY, reason=_SKIP_REASON)
    def test_azure_model_is_set(self):
        cfg = get_llm_config()
        assert cfg.azure_model is not None
        assert len(cfg.azure_model) > 0

    @pytest.mark.skipif(not _HAS_AZURE_KEY, reason=_SKIP_REASON)
    def test_azure_api_version_has_default(self):
        cfg = get_llm_config()
        assert cfg.azure_api_version is not None
        assert len(cfg.azure_api_version) > 0

    @pytest.mark.skipif(not _HAS_AZURE_KEY, reason=_SKIP_REASON)
    def test_get_model_returns_azure_deployment(self):
        """get_model('azure') returns the deployment name from env."""
        cfg = get_llm_config()
        model = cfg.get_model("azure")
        assert model == os.getenv("QNWIS_AZURE_MODEL")

    @pytest.mark.skipif(not _HAS_AZURE_KEY, reason=_SKIP_REASON)
    def test_get_api_key_returns_azure_key(self):
        """get_api_key('azure') returns the real key from env."""
        cfg = get_llm_config()
        key = cfg.get_api_key("azure")
        assert key is not None
        assert len(key) > 0
        assert key == os.getenv("AZURE_OPENAI_API_KEY")
