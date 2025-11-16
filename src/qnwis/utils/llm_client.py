"""
Lightweight Anthropic client wrapper with async support.
"""

from __future__ import annotations

import asyncio
from typing import Any

try:
    from anthropic import Anthropic
except ImportError:  # pragma: no cover - optional dependency
    Anthropic = None  # type: ignore[assignment]


class _StubAnthropic:  # pragma: no cover - testing fallback
    """Minimal stub used when anthropic package is unavailable."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.messages = self

    def create(self, **kwargs: Any) -> Any:
        class _Response:
            content = [type("Msg", (), {"text": "Stub LLM response"})]

        return _Response()


class LLMClient:
    """Simple synchronous/async Anthropic client wrapper."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        if not api_key:
            raise ValueError("Anthropic API key is required")
        client_cls = Anthropic or _StubAnthropic
        self.client = client_cls(api_key=api_key)
        self.model = model

    def invoke(self, prompt: str) -> str:
        """Synchronous invocation."""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text

    async def ainvoke(self, prompt: str) -> str:
        """Asynchronous invocation."""
        return await asyncio.to_thread(self.invoke, prompt)


__all__ = ["LLMClient"]
