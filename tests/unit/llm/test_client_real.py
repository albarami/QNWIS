"""
Real integration tests for the QNWIS LLMClient.

Exercises the actual Azure OpenAI client with real credentials from .env.
NO mocks, NO stubs — requires AZURE_OPENAI_API_KEY to be set.
"""

from dotenv import load_dotenv

load_dotenv()

import os

import pytest

from src.qnwis.llm.client import LLMClient
from src.qnwis.llm.config import get_llm_config

_HAS_AZURE_KEY = bool(os.getenv("AZURE_OPENAI_API_KEY"))
_SKIP_REASON = "AZURE_OPENAI_API_KEY not set — cannot reach Azure OpenAI"

pytestmark = pytest.mark.skipif(not _HAS_AZURE_KEY, reason=_SKIP_REASON)


# =========================================================================
# 1. LLMClient initialises with real Azure config from environment
# =========================================================================


class TestLLMClientInit:
    """LLMClient picks up real Azure configuration from the environment."""

    def test_client_initialises_with_env_config(self):
        """LLMClient() with no args reads Azure config from env."""
        client = LLMClient()
        assert client.provider == "azure"
        assert client.model == os.getenv("QNWIS_AZURE_MODEL")
        assert client.config.azure_api_key == os.getenv("AZURE_OPENAI_API_KEY")
        assert client.config.azure_endpoint == os.getenv("AZURE_OPENAI_ENDPOINT")

    def test_client_exposes_timeout_and_retries(self):
        """Config-derived timeout_s and max_retries are set."""
        client = LLMClient()
        assert isinstance(client.timeout_s, int)
        assert client.timeout_s > 0
        assert isinstance(client.max_retries, int)
        assert client.max_retries >= 0

    def test_client_has_async_azure_client(self):
        """Internal client attribute is an AsyncAzureOpenAI instance."""
        from openai import AsyncAzureOpenAI

        client = LLMClient()
        assert isinstance(client.client, AsyncAzureOpenAI)


# =========================================================================
# 2. timeout_s parameter is respected (not overridden)
# =========================================================================


class TestTimeoutRespected:
    """Explicit timeout_s kwarg must survive initialisation."""

    def test_explicit_timeout_overrides_config(self):
        """Passing timeout_s=42 results in client.timeout_s == 42."""
        client = LLMClient(timeout_s=42)
        assert client.timeout_s == 42

    def test_default_timeout_from_config(self):
        """When timeout_s is omitted the config value is used."""
        cfg = get_llm_config()
        client = LLMClient()
        assert client.timeout_s == cfg.timeout_seconds

    def test_zero_timeout_is_preserved(self):
        """timeout_s=0 is a valid explicit value and must not be replaced."""
        client = LLMClient(timeout_s=0)
        assert client.timeout_s == 0


# =========================================================================
# 3. get_llm_config() reads real environment variables correctly
# =========================================================================


class TestGetLLMConfigReadsEnv:
    """get_llm_config() returns values matching what is set in the environment."""

    def test_provider_matches_env(self):
        cfg = get_llm_config()
        expected = os.getenv("QNWIS_LLM_PROVIDER", "anthropic").lower()
        assert cfg.provider == expected

    def test_azure_model_matches_env(self):
        cfg = get_llm_config()
        assert cfg.azure_model == os.getenv("QNWIS_AZURE_MODEL")

    def test_azure_endpoint_matches_env(self):
        cfg = get_llm_config()
        assert cfg.azure_endpoint == os.getenv("AZURE_OPENAI_ENDPOINT")

    def test_azure_api_key_matches_env(self):
        cfg = get_llm_config()
        assert cfg.azure_api_key == os.getenv("AZURE_OPENAI_API_KEY")


# =========================================================================
# 4. Real LLM call with a minimal prompt
# =========================================================================


class TestRealLLMCall:
    """Fire a real request against Azure OpenAI (minimal token usage)."""

    @pytest.mark.slow
    async def test_generate_returns_nonempty_string(self):
        """A simple prompt returns a non-empty response from the real LLM."""
        client = LLMClient()
        response = await client.generate(
            prompt="Reply with exactly one word: hello.",
            max_tokens=10,
            temperature=0.0,
        )
        assert isinstance(response, str)
        assert len(response.strip()) > 0

    @pytest.mark.slow
    async def test_generate_stream_yields_tokens(self):
        """generate_stream yields at least one non-empty chunk."""
        client = LLMClient()
        tokens: list[str] = []
        async for chunk in client.generate_stream(
            prompt="Say the word 'ok'.",
            max_tokens=5,
            temperature=0.0,
        ):
            tokens.append(chunk)
        assert len(tokens) > 0
        full = "".join(tokens)
        assert len(full.strip()) > 0
