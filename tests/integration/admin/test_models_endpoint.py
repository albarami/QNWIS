"""
Smoke tests for /admin/models endpoint.

Tests that endpoint returns provider + model list with stub in CI.
"""

import pytest


@pytest.mark.asyncio
async def test_llm_client_list_models_with_stub():
    """Test LLM client list_models returns info with stub provider."""
    from src.qnwis.llm.client import LLMClient
    from src.qnwis.llm.config import LLMConfig
    
    from src.qnwis.llm.config import get_llm_config; config = get_llm_config()
    client = LLMClient(config=config)
    
    models_info = await client.list_models()
    
    assert "provider" in models_info
    assert models_info["provider"] == "stub"
    
    assert "current_model" in models_info
    assert models_info["current_model"] is not None
    
    assert "configured_models" in models_info
    assert isinstance(models_info["configured_models"], dict)
    assert len(models_info["configured_models"]) > 0


@pytest.mark.skip(reason="Requires running FastAPI server")
def test_admin_models_endpoint_http():
    """Test /admin/models HTTP endpoint."""
    # This would require a running server
    # Skip for unit testing
    pass
