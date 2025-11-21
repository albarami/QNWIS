"""Unit tests for UN Comtrade API Connector"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.data.apis.un_comtrade_api import UNComtradeConnector


@pytest.fixture
def comtrade_connector():
    return UNComtradeConnector()


@pytest.fixture
def mock_comtrade_response():
    return {
        "data": [
            {"primaryValue": 1000000, "partnerDesc": "India"},
            {"primaryValue": 500000, "partnerDesc": "Brazil"}
        ]
    }


@pytest.mark.asyncio
async def test_get_imports_success(comtrade_connector, mock_comtrade_response):
    """Test successful import data retrieval"""
    with patch.object(comtrade_connector.client, 'get') as mock_get:
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value=mock_comtrade_response)
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        
        result = await comtrade_connector.get_imports("02", 2023)
        
        assert "data" in result
        assert len(result["data"]) == 2


@pytest.mark.asyncio
async def test_get_top_import_partners(comtrade_connector, mock_comtrade_response):
    """Test getting top import partners"""
    with patch.object(comtrade_connector.client, 'get') as mock_get:
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value=mock_comtrade_response)
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        
        result = await comtrade_connector.get_top_import_partners("02", 2023, 2)
        
        assert len(result) == 2
        assert result[0]["primaryValue"] == 1000000


@pytest.mark.asyncio
async def test_close_client(comtrade_connector):
    """Test client cleanup"""
    with patch.object(comtrade_connector.client, 'aclose') as mock_close:
        await comtrade_connector.close()
        mock_close.assert_called_once()
