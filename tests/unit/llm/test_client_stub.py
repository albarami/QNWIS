"""
Unit tests for LLM client stub provider.

Tests deterministic token streaming with configurable delays.
"""

import asyncio
import pytest
from src.qnwis.llm.client import LLMClient
from src.qnwis.llm.config import LLMConfig


def make_stub_config(**kwargs):
    """Helper to create stub config with defaults."""
    defaults = {
        "provider": "stub",
        "anthropic_model": None,
        "openai_model": None,
        "anthropic_api_key": None,
        "openai_api_key": None,
        "timeout_seconds": 60,
        "max_retries": 3,
        "stub_token_delay_ms": 0
    }
    defaults.update(kwargs)
    return LLMConfig(**defaults)


@pytest.mark.asyncio
async def test_stub_client_initialization():
    """Test stub client initializes without API keys."""
    config = make_stub_config()
    client = LLMClient(config=config)

    assert client.provider == "stub"
    assert client.client is None  # Stub has no real client


@pytest.mark.asyncio
async def test_stub_streams_deterministic_tokens():
    """Test stub provider streams tokens deterministically."""
    config = make_stub_config()
    client = LLMClient(config=config)

    tokens = []
    async for token in client.generate_stream(prompt="test"):
        tokens.append(token)

    # Should stream complete JSON response
    response_text = "".join(tokens)
    assert "title" in response_text
    assert "Test Finding" in response_text
    assert "confidence" in response_text
    assert len(tokens) > 10  # Multiple tokens


@pytest.mark.asyncio
async def test_stub_respects_delay_configuration():
    """Test stub respects configured token delay."""
    # Fast stub (no delay)
    config_fast = make_stub_config(stub_token_delay_ms=0)
    client_fast = LLMClient(config=config_fast)

    start = asyncio.get_event_loop().time()
    tokens_fast = []
    async for token in client_fast.generate_stream(prompt="test"):
        tokens_fast.append(token)
    duration_fast = asyncio.get_event_loop().time() - start

    # Slow stub (with delay)
    config_slow = make_stub_config(stub_token_delay_ms=1)
    client_slow = LLMClient(config=config_slow)

    start = asyncio.get_event_loop().time()
    tokens_slow = []
    async for token in client_slow.generate_stream(prompt="test"):
        tokens_slow.append(token)
    duration_slow = asyncio.get_event_loop().time() - start

    # Same tokens, different durations
    assert "".join(tokens_fast) == "".join(tokens_slow)
    assert duration_slow > duration_fast


@pytest.mark.asyncio
async def test_stub_generate_complete_response():
    """Test stub non-streaming generation."""
    config = make_stub_config()
    client = LLMClient(config=config)

    response = await client.generate(prompt="test", system="system")

    assert isinstance(response, str)
    assert len(response) > 0
    assert "title" in response
    assert "Test Finding" in response


@pytest.mark.asyncio
async def test_stub_produces_valid_json():
    """Test stub produces parseable JSON."""
    import json

    config = make_stub_config()
    client = LLMClient(config=config)

    response = await client.generate(prompt="test")

    # Should be valid JSON
    data = json.loads(response)
    assert "title" in data
    assert "summary" in data
    assert "confidence" in data
    assert isinstance(data["confidence"], float)
    assert 0.0 <= data["confidence"] <= 1.0


@pytest.mark.asyncio
async def test_stub_includes_required_fields():
    """Test stub response includes all required fields."""
    import json

    config = make_stub_config()
    client = LLMClient(config=config)

    response = await client.generate(prompt="test")
    data = json.loads(response)

    required_fields = [
        "title",
        "summary",
        "metrics",
        "analysis",
        "recommendations",
        "confidence",
        "citations",
        "data_quality_notes",
    ]

    for field in required_fields:
        assert field in data, f"Missing required field: {field}"


@pytest.mark.asyncio
async def test_list_models_returns_stub_info():
    """Test list_models returns stub provider info."""
    config = make_stub_config()
    client = LLMClient(config=config)

    info = await client.list_models()

    assert info["provider"] == "stub"
    assert "current_model" in info
    assert "configured_models" in info
    assert "timeouts" in info
