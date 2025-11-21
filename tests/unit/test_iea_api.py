"""Unit tests for IEA Energy API Connector"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.data.apis.iea_api import IEAAPI


@pytest.fixture
def iea_connector():
    return IEAAPI()


@pytest.fixture
def iea_connector_with_key():
    return IEAAPI(api_key="test_api_key")


@pytest.mark.asyncio
async def test_get_energy_production(iea_connector):
    """Test energy production retrieval"""
    result = await iea_connector.get_energy_production("QAT")
    
    assert result["country_code"] == "QAT"
    assert result["country_name"] == "Qatar"
    assert "oil_production" in result
    assert "gas_production" in result
    assert "production_by_source" in result
    assert result["source"] == "IEA Energy Statistics"
    assert "warning" in result  # No API key


@pytest.mark.asyncio
async def test_get_energy_consumption(iea_connector):
    """Test energy consumption retrieval"""
    result = await iea_connector.get_energy_consumption("QAT")
    
    assert result["country_code"] == "QAT"
    assert "total_energy_supply" in result
    assert "consumption_by_sector" in result
    assert "consumption_by_fuel" in result
    assert result["source"] == "IEA Energy Statistics"


@pytest.mark.asyncio
async def test_get_energy_transition_indicators(iea_connector):
    """Test energy transition indicators"""
    result = await iea_connector.get_energy_transition_indicators("QAT")
    
    assert result["country_code"] == "QAT"
    assert "renewable_share" in result
    assert "solar_capacity" in result
    assert "carbon_intensity" in result
    assert "NDS3 sustainability" in result["note"]


@pytest.mark.asyncio
async def test_get_energy_prices(iea_connector):
    """Test energy prices"""
    result = await iea_connector.get_energy_prices("QAT")
    
    assert result["country_code"] == "QAT"
    assert "electricity_prices" in result
    assert "gas_prices" in result
    assert result["source"] == "IEA Energy Prices"


@pytest.mark.asyncio
async def test_get_energy_dashboard(iea_connector):
    """Test comprehensive energy dashboard"""
    result = await iea_connector.get_energy_dashboard("QAT")
    
    assert result["country_code"] == "QAT"
    assert "production" in result
    assert "consumption" in result
    assert "transition" in result
    assert "prices" in result
    assert result["source"] == "IEA Energy Statistics"


@pytest.mark.asyncio
async def test_get_gcc_comparison(iea_connector):
    """Test GCC energy comparison"""
    result = await iea_connector.get_gcc_energy_comparison()
    
    assert "gcc_countries" in result
    assert len(result["gcc_countries"]) == 6
    assert "Qatar" in result["gcc_countries"]


@pytest.mark.asyncio
async def test_with_api_key(iea_connector_with_key):
    """Test with API key provided"""
    result = await iea_connector_with_key.get_energy_production("QAT")
    
    assert "warning" not in result
    assert result["country_code"] == "QAT"


@pytest.mark.asyncio
async def test_close_client(iea_connector):
    """Test client cleanup"""
    with patch.object(iea_connector.client, 'aclose') as mock_close:
        await iea_connector.close()
        mock_close.assert_called_once()


@pytest.mark.asyncio
async def test_gcc_country_codes(iea_connector):
    """Test GCC country code mapping"""
    assert iea_connector.GCC_COUNTRIES["QAT"] == "Qatar"
    assert iea_connector.GCC_COUNTRIES["SAU"] == "Saudi Arabia"
    assert len(iea_connector.GCC_COUNTRIES) == 6
