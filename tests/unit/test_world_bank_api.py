"""Unit tests for World Bank Indicators API Connector"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.data.apis.world_bank_api import WorldBankAPI


@pytest.fixture
def wb_connector():
    return WorldBankAPI()


@pytest.fixture
def mock_wb_response():
    """Mock World Bank API response format"""
    return [
        {
            "page": 1,
            "pages": 1,
            "per_page": 100,
            "total": 3
        },
        [
            {
                "indicator": {"id": "NV.IND.TOTL.ZS", "value": "Industry value added (% of GDP)"},
                "country": {"id": "QAT", "value": "Qatar"},
                "value": 52.3,
                "date": "2023"
            },
            {
                "indicator": {"id": "NV.IND.TOTL.ZS", "value": "Industry value added (% of GDP)"},
                "country": {"id": "QAT", "value": "Qatar"},
                "value": 53.1,
                "date": "2022"
            },
            {
                "indicator": {"id": "NV.IND.TOTL.ZS", "value": "Industry value added (% of GDP)"},
                "country": {"id": "QAT", "value": "Qatar"},
                "value": None,
                "date": "2021"
            }
        ]
    ]


@pytest.mark.asyncio
async def test_get_indicator_success(wb_connector, mock_wb_response):
    """Test successful indicator retrieval"""
    with patch.object(wb_connector.client, 'get') as mock_get:
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value=mock_wb_response)
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        
        result = await wb_connector.get_indicator("NV.IND.TOTL.ZS", "QAT")
        
        assert result["indicator_code"] == "NV.IND.TOTL.ZS"
        assert result["country_code"] == "QAT"
        assert "values" in result
        assert len(result["values"]) == 2  # Excludes null value
        assert result["values"]["2023"] == 52.3
        assert result["source"] == "World Bank Indicators API"


@pytest.mark.asyncio
async def test_get_latest_value(wb_connector, mock_wb_response):
    """Test getting most recent value"""
    with patch.object(wb_connector.client, 'get') as mock_get:
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value=mock_wb_response)
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        
        latest = await wb_connector.get_latest_value("NV.IND.TOTL.ZS", "QAT")
        assert latest == 52.3


@pytest.mark.asyncio
async def test_get_sector_gdp_breakdown(wb_connector, mock_wb_response):
    """Test sector GDP breakdown (CRITICAL feature)"""
    with patch.object(wb_connector, 'get_latest_value') as mock_latest:
        # Mock different values for each sector
        async def mock_get_latest(code, country):
            values = {
                "NV.IND.TOTL.ZS": 52.3,
                "NV.SRV.TOTL.ZS": 45.2,
                "NV.AGR.TOTL.ZS": 2.5
            }
            return values.get(code)
        
        mock_latest.side_effect = mock_get_latest
        
        result = await wb_connector.get_sector_gdp_breakdown("QAT")
        
        assert "sector_breakdown" in result
        assert "Industry" in result["sector_breakdown"]
        assert "Services" in result["sector_breakdown"]
        assert "Agriculture" in result["sector_breakdown"]
        assert result["sector_breakdown"]["Industry"]["percentage_of_gdp"] == 52.3
        assert result["country_code"] == "QAT"


@pytest.mark.asyncio
async def test_close_client(wb_connector):
    """Test client cleanup"""
    with patch.object(wb_connector.client, 'aclose') as mock_close:
        await wb_connector.close()
        mock_close.assert_called_once()


@pytest.mark.asyncio
async def test_empty_response(wb_connector):
    """Test handling of empty response"""
    empty_response = [{"page": 1}, []]
    
    with patch.object(wb_connector.client, 'get') as mock_get:
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value=empty_response)
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        
        result = await wb_connector.get_indicator("INVALID_CODE", "QAT")
        
        assert result["values"] == {}
        assert result["indicator_code"] == "INVALID_CODE"
