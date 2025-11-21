"""Unit tests for UNCTAD API Connector"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.data.apis.unctad_api import UNCTADAPI


@pytest.fixture
def unctad_connector():
    return UNCTADAPI()


@pytest.mark.asyncio
async def test_get_fdi_flows(unctad_connector):
    """Test FDI flows retrieval"""
    result = await unctad_connector.get_fdi_flows("634")
    
    assert result["country_code"] == "634"
    assert "fdi_inward_flows" in result
    assert "fdi_outward_flows" in result
    assert result["source"] == "UNCTAD FDI Statistics"
    assert "fills CRITICAL investment climate gap" in result["note"]


@pytest.mark.asyncio
async def test_get_investment_dashboard(unctad_connector):
    """Test investment dashboard retrieval"""
    result = await unctad_connector.get_investment_dashboard("634")
    
    assert result["country_code"] == "634"
    assert result["country_name"] == "Qatar"
    assert "fdi" in result
    assert result["source"] == "UNCTAD Statistics API"


@pytest.mark.asyncio
async def test_get_gcc_comparison(unctad_connector):
    """Test GCC investment comparison"""
    result = await unctad_connector.get_gcc_investment_comparison()
    
    assert "gcc_countries" in result
    assert len(result["gcc_countries"]) == 6
    assert "Qatar" in result["gcc_countries"]
    assert "Saudi Arabia" in result["gcc_countries"]
    assert result["source"] == "UNCTAD Statistics API"


@pytest.mark.asyncio
async def test_close_client(unctad_connector):
    """Test client cleanup"""
    with patch.object(unctad_connector.client, 'aclose') as mock_close:
        await unctad_connector.close()
        mock_close.assert_called_once()


@pytest.mark.asyncio
async def test_country_codes(unctad_connector):
    """Test GCC country code mapping"""
    assert unctad_connector.GCC_COUNTRIES["634"] == "Qatar"
    assert unctad_connector.GCC_COUNTRIES["682"] == "Saudi Arabia"
    assert unctad_connector.GCC_COUNTRIES["784"] == "United Arab Emirates"
    assert len(unctad_connector.GCC_COUNTRIES) == 6
