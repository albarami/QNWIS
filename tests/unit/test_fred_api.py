"""Unit tests for FRED API Connector"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.data.apis.fred_api import FREDConnector


@pytest.fixture
def fred_connector():
    return FREDConnector(api_key="test_key")


@pytest.fixture
def mock_fred_response():
    return {
        "observations": [
            {"date": "2023-01-01", "value": "3.5"},
            {"date": "2023-04-01", "value": "3.7"},
            {"date": "2023-07-01", "value": "."},  # Missing value
            {"date": "2023-10-01", "value": "3.9"}
        ]
    }


@pytest.mark.asyncio
async def test_get_series_success(fred_connector, mock_fred_response):
    """Test successful series retrieval"""
    with patch.object(fred_connector.client, 'get') as mock_get:
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value=mock_fred_response)
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        
        result = await fred_connector.get_series("UNRATE")
        
        assert result["source"] == "FRED"
        assert "values" in result
        assert len(result["values"]) == 3  # Excludes missing value


@pytest.mark.asyncio
async def test_get_latest_value(fred_connector, mock_fred_response):
    """Test getting most recent value"""
    with patch.object(fred_connector.client, 'get') as mock_get:
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value=mock_fred_response)
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        
        latest = await fred_connector.get_latest_value("UNRATE")
        assert latest == 3.9


@pytest.mark.asyncio
async def test_missing_api_key():
    """Test error when API key missing"""
    connector = FREDConnector(api_key=None)
    
    with pytest.raises(ValueError, match="FRED API key required"):
        await connector.get_series("GDP")
