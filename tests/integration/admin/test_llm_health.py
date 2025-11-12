"""
Smoke tests for /admin/health/llm endpoint.

Tests that health check returns ok with stub provider.
"""

import pytest


@pytest.mark.asyncio
async def test_stub_llm_health_check():
    """Test stub LLM client is healthy."""
    from src.qnwis.llm.client import LLMClient
    from src.qnwis.llm.config import LLMConfig
    
    from src.qnwis.llm.config import get_llm_config; config = get_llm_config()
    client = LLMClient(config=config)
    
    # Test basic generation works
    response = await client.generate(prompt="health check", max_tokens=100)
    
    assert response is not None
    assert len(response) > 0
    assert isinstance(response, str)


@pytest.mark.asyncio
async def test_stub_provider_configuration():
    """Test stub provider is properly configured."""
    from src.qnwis.llm.client import LLMClient
    from src.qnwis.llm.config import LLMConfig
    
    from src.qnwis.llm.config import get_llm_config; config = get_llm_config()
    client = LLMClient(config=config)
    
    assert client.provider == "stub"
    assert client.client is None  # Stub has no real client
    assert client.timeout_s > 0
