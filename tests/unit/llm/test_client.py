"""Real LLM client tests — uses live Azure OpenAI infrastructure."""

from __future__ import annotations

import os

import pytest
from dotenv import load_dotenv

load_dotenv()

AZURE_KEY = os.getenv("AZURE_OPENAI_API_KEY")
SKIP_NO_AZURE = pytest.mark.skipif(not AZURE_KEY, reason="AZURE_OPENAI_API_KEY not set")


@SKIP_NO_AZURE
class TestLLMClientRealProvider:
    """Test LLMClient with the real Azure provider."""

    def test_client_initializes_with_env_config(self):
        from src.qnwis.llm.client import LLMClient

        client = LLMClient()
        assert client.provider == "azure"
        assert client.model is not None
        assert client.timeout_s > 0
        assert client.timeout_s != 7200

    def test_explicit_timeout_is_preserved(self):
        from src.qnwis.llm.client import LLMClient

        client = LLMClient(timeout_s=42)
        assert client.timeout_s == 42

    @pytest.mark.asyncio
    async def test_real_generate_returns_text(self):
        from src.qnwis.llm.client import LLMClient

        client = LLMClient(timeout_s=30)
        result = await client.generate(
            system="Reply with exactly one word.",
            prompt="What is the capital of Qatar?",
        )
        assert isinstance(result, str)
        assert len(result) > 0
