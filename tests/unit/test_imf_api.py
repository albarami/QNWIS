"""Unit tests for IMF API Connector"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.data.apis.imf_api import IMFConnector


@pytest.fixture
def imf_connector():
    return IMFConnector()


@pytest.fixture
def mock_imf_response():
    return {
        "values": {
            "NGDP_RPCH": {
                "QAT": {
                    "2020": 1.5,
                    "2021": 1.6,
                    "2022": 3.4,
                    "2023": 2.1,
                    "2024": 2.4
                }
            }
        }
    }


@pytest.mark.asyncio
async def test_get_indicator_success(imf_connector, mock_imf_response):
    """Test successful indicator retrieval"""
    with patch.object(imf_connector.client, 'get') as mock_get:
        mock_response = AsyncMock()
        mock_response.json.return_value = mock_imf_response
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        
        result = await imf_connector.get_indicator("NGDP_RPCH", "QAT")
        
        assert result["source"] == "IMF"
        assert "values" in result
        assert "2023" in result["values"]
        assert result["values"]["2023"] == 2.1


@pytest.mark.asyncio
async def test_get_indicator_with_year_filter(imf_connector, mock_imf_response):
    """Test indicator retrieval with year filter"""
    with patch.object(imf_connector.client, 'get') as mock_get:
        mock_response = AsyncMock()
        mock_response.json.return_value = mock_imf_response
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        
        result = await imf_connector.get_indicator(
            "NGDP_RPCH", "QAT", start_year=2022, end_year=2023
        )
        
        values = result["values"]
        assert "2022" in values
        assert "2023" in values
        assert "2020" not in values


@pytest.mark.asyncio
async def test_get_latest_value(imf_connector, mock_imf_response):
    """Test getting most recent value"""
    with patch.object(imf_connector.client, 'get') as mock_get:
        mock_response = AsyncMock()
        mock_response.json.return_value = mock_imf_response
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        
        latest = await imf_connector.get_latest_value("NGDP_RPCH", "QAT")
        assert latest == 2.4


@pytest.mark.asyncio
async def test_close_client(imf_connector):
    """Test client cleanup"""
    with patch.object(imf_connector.client, 'aclose') as mock_close:
        await imf_connector.close()
        mock_close.assert_called_once()
