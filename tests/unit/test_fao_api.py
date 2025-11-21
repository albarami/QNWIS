"""Unit tests for FAO STAT API Connector"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.data.apis.fao_api import FAOAPI


@pytest.fixture
def fao_connector():
    return FAOAPI()


@pytest.mark.asyncio
async def test_get_food_balance(fao_connector):
    """Test food balance sheet retrieval"""
    result = await fao_connector.get_food_balance("634")
    
    assert result["country_code"] == "634"
    assert result["country_name"] == "Qatar"
    assert "food_balance" in result
    assert result["source"] == "FAO STAT Food Balance Sheets"
    assert "agriculture/food security gap" in result["note"]


@pytest.mark.asyncio
async def test_get_food_security_indicators(fao_connector):
    """Test food security indicators retrieval"""
    result = await fao_connector.get_food_security_indicators("634")
    
    assert result["country_code"] == "634"
    assert "food_security_indicators" in result
    assert result["source"] == "FAO STAT Food Security"
    assert "NDS3 food security" in result["note"]


@pytest.mark.asyncio
async def test_get_agricultural_production(fao_connector):
    """Test agricultural production data"""
    result = await fao_connector.get_agricultural_production("634")
    
    assert result["country_code"] == "634"
    assert "crops" in result
    assert "livestock" in result
    assert result["source"] == "FAO STAT Crops and Livestock"


@pytest.mark.asyncio
async def test_get_food_trade(fao_connector):
    """Test food trade data"""
    result = await fao_connector.get_food_trade("634")
    
    assert result["country_code"] == "634"
    assert "food_imports" in result
    assert "food_exports" in result
    assert "trade_balance" in result
    assert result["source"] == "FAO STAT Trade"


@pytest.mark.asyncio
async def test_get_food_security_dashboard(fao_connector):
    """Test comprehensive food security dashboard"""
    result = await fao_connector.get_food_security_dashboard("634")
    
    assert result["country_code"] == "634"
    assert "food_balance" in result
    assert "food_security" in result
    assert "production" in result
    assert "trade" in result
    assert result["source"] == "FAO STAT"


@pytest.mark.asyncio
async def test_get_gcc_comparison(fao_connector):
    """Test GCC food security comparison"""
    result = await fao_connector.get_gcc_food_security_comparison()
    
    assert "gcc_countries" in result
    assert len(result["gcc_countries"]) == 6
    assert "Qatar" in result["gcc_countries"]
    assert "Saudi Arabia" in result["gcc_countries"]


@pytest.mark.asyncio
async def test_close_client(fao_connector):
    """Test client cleanup"""
    with patch.object(fao_connector.client, 'aclose') as mock_close:
        await fao_connector.close()
        mock_close.assert_called_once()


@pytest.mark.asyncio
async def test_gcc_country_codes(fao_connector):
    """Test GCC country code mapping"""
    assert fao_connector.GCC_COUNTRIES["634"] == "Qatar"
    assert fao_connector.GCC_COUNTRIES["682"] == "Saudi Arabia"
    assert len(fao_connector.GCC_COUNTRIES) == 6
