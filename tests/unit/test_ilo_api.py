"""Unit tests for ILO ILOSTAT API Connector"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.data.apis.ilo_api import ILOAPI


@pytest.fixture
def ilo_connector():
    return ILOAPI()


@pytest.mark.asyncio
async def test_get_employment_stats(ilo_connector):
    """Test employment statistics retrieval"""
    result = await ilo_connector.get_employment_stats("QAT")
    
    assert result["country_code"] == "QAT"
    assert "employment_by_sector" in result
    assert "employment_by_occupation" in result
    assert result["source"] == "ILO ILOSTAT"
    assert "international labor benchmark" in result["note"]


@pytest.mark.asyncio
async def test_get_wage_benchmarks(ilo_connector):
    """Test wage benchmarks retrieval"""
    result = await ilo_connector.get_wage_benchmarks("QAT")
    
    assert result["country_code"] == "QAT"
    assert result["country_name"] == "Qatar"
    assert "mean_monthly_earnings" in result
    assert "wage_by_sector" in result
    assert result["source"] == "ILO ILOSTAT"


@pytest.mark.asyncio
async def test_get_labor_dashboard(ilo_connector):
    """Test labor market dashboard"""
    result = await ilo_connector.get_labor_dashboard("QAT")
    
    assert result["country_code"] == "QAT"
    assert "employment" in result
    assert "wages" in result
    assert result["source"] == "ILO ILOSTAT"


@pytest.mark.asyncio
async def test_get_gcc_comparison(ilo_connector):
    """Test GCC labor market comparison"""
    result = await ilo_connector.get_gcc_labor_comparison()
    
    assert "gcc_countries" in result
    assert len(result["gcc_countries"]) == 6
    assert "Qatar" in result["gcc_countries"]
    assert result["source"] == "ILO ILOSTAT"


@pytest.mark.asyncio
async def test_close_client(ilo_connector):
    """Test client cleanup"""
    with patch.object(ilo_connector.client, 'aclose') as mock_close:
        await ilo_connector.close()
        mock_close.assert_called_once()


@pytest.mark.asyncio
async def test_gcc_country_codes(ilo_connector):
    """Test GCC country code mapping"""
    assert ilo_connector.GCC_COUNTRIES["QAT"] == "Qatar"
    assert ilo_connector.GCC_COUNTRIES["SAU"] == "Saudi Arabia"
    assert len(ilo_connector.GCC_COUNTRIES) == 6
