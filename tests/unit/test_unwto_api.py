"""Unit tests for UNWTO Tourism API Connector"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.data.apis.unwto_api import UNWTOAPI


@pytest.fixture
def unwto_connector():
    return UNWTOAPI()


@pytest.fixture
def unwto_connector_with_key():
    return UNWTOAPI(api_key="test_api_key")


@pytest.mark.asyncio
async def test_get_tourism_arrivals(unwto_connector):
    """Test tourism arrivals retrieval"""
    result = await unwto_connector.get_tourism_arrivals("QAT")
    
    assert result["country_code"] == "QAT"
    assert result["country_name"] == "Qatar"
    assert "international_arrivals" in result
    assert "overnight_visitors" in result
    assert "arrivals_by_purpose" in result
    assert result["source"] == "UNWTO Tourism Statistics"
    assert "warning" in result  # No API key


@pytest.mark.asyncio
async def test_get_tourism_receipts(unwto_connector):
    """Test tourism receipts and expenditure"""
    result = await unwto_connector.get_tourism_receipts_expenditure("QAT")
    
    assert result["country_code"] == "QAT"
    assert "tourism_receipts" in result
    assert "tourism_expenditure" in result
    assert "tourism_balance" in result
    assert result["source"] == "UNWTO Tourism Economics"


@pytest.mark.asyncio
async def test_get_accommodation_statistics(unwto_connector):
    """Test accommodation statistics"""
    result = await unwto_connector.get_accommodation_statistics("QAT")
    
    assert result["country_code"] == "QAT"
    assert "establishments" in result
    assert "rooms" in result
    assert "occupancy_rate" in result
    assert result["source"] == "UNWTO Accommodation Statistics"


@pytest.mark.asyncio
async def test_get_tourism_employment(unwto_connector):
    """Test tourism employment data"""
    result = await unwto_connector.get_tourism_employment("QAT")
    
    assert result["country_code"] == "QAT"
    assert "tourism_employment" in result
    assert "employment_by_industry" in result
    assert "accommodation" in result["employment_by_industry"]
    assert result["source"] == "UNWTO Tourism Employment"


@pytest.mark.asyncio
async def test_get_tourism_dashboard(unwto_connector):
    """Test comprehensive tourism dashboard"""
    result = await unwto_connector.get_tourism_dashboard("QAT")
    
    assert result["country_code"] == "QAT"
    assert "arrivals" in result
    assert "economics" in result
    assert "accommodation" in result
    assert "employment" in result
    assert result["source"] == "UNWTO Tourism Statistics"


@pytest.mark.asyncio
async def test_get_gcc_comparison(unwto_connector):
    """Test GCC tourism comparison"""
    result = await unwto_connector.get_gcc_tourism_comparison()
    
    assert "gcc_countries" in result
    assert len(result["gcc_countries"]) == 6
    assert "Qatar" in result["gcc_countries"]


@pytest.mark.asyncio
async def test_with_api_key(unwto_connector_with_key):
    """Test with API key provided"""
    result = await unwto_connector_with_key.get_tourism_arrivals("QAT")
    
    assert "warning" not in result
    assert result["country_code"] == "QAT"


@pytest.mark.asyncio
async def test_close_client(unwto_connector):
    """Test client cleanup"""
    with patch.object(unwto_connector.client, 'aclose') as mock_close:
        await unwto_connector.close()
        mock_close.assert_called_once()


@pytest.mark.asyncio
async def test_gcc_country_codes(unwto_connector):
    """Test GCC country code mapping"""
    assert unwto_connector.GCC_COUNTRIES["QAT"] == "Qatar"
    assert unwto_connector.GCC_COUNTRIES["SAU"] == "Saudi Arabia"
    assert len(unwto_connector.GCC_COUNTRIES) == 6
