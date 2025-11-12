from __future__ import annotations

import json

import pytest

from qnwis.llm.client import LLMClient
from qnwis.llm.config import LLMConfig


def _stub_config(max_retries: int = 2) -> LLMConfig:
    return LLMConfig(
        provider="stub",
        anthropic_model=None,
        openai_model=None,
        anthropic_api_key=None,
        openai_api_key=None,
        timeout_seconds=5,
        max_retries=max_retries,
        stub_token_delay_ms=0,
        anthropic_model_choices=(),
        openai_model_choices=(),
    )


@pytest.mark.asyncio
async def test_stub_client_stream_is_deterministic():
    client = LLMClient(provider="stub", config=_stub_config())
    raw = await client.generate(prompt="deterministic please")
    payload = json.loads(raw)
    assert payload["title"] == "Test Finding"
    assert payload["citations"] == ["test_query_id"]


class _RateLimitedStub(LLMClient):
    def __init__(self) -> None:
        super().__init__(provider="stub", config=_stub_config(max_retries=3))
        self._calls = 0

    async def _stream_stub(self, prompt: str):
        self._calls += 1
        if self._calls < 3:
            error = RuntimeError("rate limit")
            setattr(error, "status_code", 429)
            raise error
        yield "O"
        yield "K"


@pytest.mark.asyncio
async def test_llm_client_retries_on_rate_limit(monkeypatch: pytest.MonkeyPatch):
    # Make retries deterministic
    monkeypatch.setattr("qnwis.llm.client.random.uniform", lambda *_args, **_kwargs: 0.0)
    client = _RateLimitedStub()
    text = await client.generate(prompt="retry please")
    assert text == "OK"
    assert client._calls == 3
