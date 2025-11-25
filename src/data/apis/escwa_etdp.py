"""
UN ESCWA Economic and Trade Data Platform (ETDP) Connector.

Provides access to detailed trade statistics for Arab countries:
- Export/Import data from 2012-present
- 6-digit HS code product detail
- Bilateral trade flows
- Economic grouping breakdowns

Portal: https://etdp.unescwa.org/
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

import httpx
import pandas as pd

from .rate_limiter import (
    RateLimiter,
    ExponentialBackoff,
    CheckpointManager,
    RateLimitExceeded,
    get_rate_limiter,
    get_checkpoint_manager,
)

logger = logging.getLogger(__name__)


class ESCWATradeAPI:
    """
    UN ESCWA Economic and Trade Data Platform connector.
    
    Provides access to detailed trade statistics for Qatar and other Arab countries.
    """
    
    BASE_URL = "https://etdp.unescwa.org"
    
    # Country codes
    COUNTRIES = {
        "QAT": "Qatar",
        "SAU": "Saudi Arabia",
        "ARE": "United Arab Emirates",
        "KWT": "Kuwait",
        "BHR": "Bahrain",
        "OMN": "Oman",
        "EGY": "Egypt",
        "JOR": "Jordan",
        "LBN": "Lebanon",
    }
    
    # Strategic commodity codes for Qatar analysis
    STRATEGIC_COMMODITIES = {
        # Food Security
        "02": "Meat and edible meat offal",
        "03": "Fish and crustaceans",
        "04": "Dairy produce; eggs; honey",
        "07": "Edible vegetables",
        "08": "Edible fruit and nuts",
        "10": "Cereals",
        "11": "Milling products",
        
        # Industrial Materials
        "72": "Iron and steel",
        "73": "Iron/steel articles",
        "84": "Machinery",
        "85": "Electrical machinery",
        "87": "Vehicles",
        "90": "Optical, medical instruments",
        
        # Energy Transition
        "27": "Mineral fuels (exports)",
        "8541": "Solar cells",
    }
    
    def __init__(
        self,
        timeout: int = 60,
        rate_limiter: Optional[RateLimiter] = None,
    ):
        """
        Initialize ESCWA API client.
        
        Args:
            timeout: Request timeout in seconds
            rate_limiter: Optional custom rate limiter
        """
        self.client = httpx.AsyncClient(timeout=timeout)
        self.rate_limiter = rate_limiter or get_rate_limiter(
            requests_per_minute=30,
            requests_per_day=2000
        )
        self.backoff = ExponentialBackoff(max_retries=3)
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
    
    async def get_trade_data(
        self,
        reporter: str = "QAT",
        partner: Optional[str] = None,
        flow: str = "export",
        year: int = 2023,
        commodity_code: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Get trade data for a country.
        
        Args:
            reporter: Reporting country code
            partner: Partner country code (None for all partners)
            flow: Trade flow ('export' or 'import')
            year: Year of data
            commodity_code: HS code (None for all commodities)
            
        Returns:
            DataFrame with trade data
        """
        await self.rate_limiter.wait_if_needed()
        
        # Note: ESCWA uses bulk downloads rather than API
        # This is a placeholder for when API access is available
        # For now, we'll return structured placeholder data
        
        logger.info(f"Fetching ESCWA trade data: {reporter} {flow} {year}")
        
        # Return placeholder structure
        data = {
            "reporter_code": reporter,
            "reporter_name": self.COUNTRIES.get(reporter, reporter),
            "partner_code": partner or "WLD",
            "flow": flow,
            "year": year,
            "commodity_code": commodity_code or "TOTAL",
            "value_usd": None,
            "source": "UN ESCWA ETDP",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return pd.DataFrame([data])
    
    async def get_qatar_exports(
        self,
        year: int = 2023,
        partner: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get Qatar export data by partner and product.
        
        Args:
            year: Year of data
            partner: Partner country (None for all)
            
        Returns:
            Dictionary with export data
        """
        df = await self.get_trade_data(
            reporter="QAT",
            partner=partner,
            flow="export",
            year=year
        )
        
        return {
            "country": "Qatar",
            "flow": "export",
            "year": year,
            "partner": partner or "World",
            "data": df.to_dict(orient="records"),
            "source": "UN ESCWA ETDP",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def get_qatar_imports(
        self,
        year: int = 2023,
        partner: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get Qatar import data by partner and product.
        
        Args:
            year: Year of data
            partner: Partner country (None for all)
            
        Returns:
            Dictionary with import data
        """
        df = await self.get_trade_data(
            reporter="QAT",
            partner=partner,
            flow="import",
            year=year
        )
        
        return {
            "country": "Qatar",
            "flow": "import",
            "year": year,
            "partner": partner or "World",
            "data": df.to_dict(orient="records"),
            "source": "UN ESCWA ETDP",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def get_trade_balance(
        self,
        country: str = "QAT",
        start_year: int = 2018,
        end_year: int = 2023,
    ) -> Dict[str, Any]:
        """
        Calculate trade balance trends for a country.
        
        Args:
            country: Country code
            start_year: Start year for trend
            end_year: End year for trend
            
        Returns:
            Dictionary with trade balance data
        """
        balance_data = []
        
        for year in range(start_year, end_year + 1):
            exports = await self.get_trade_data(country, flow="export", year=year)
            imports = await self.get_trade_data(country, flow="import", year=year)
            
            balance_data.append({
                "year": year,
                "exports": exports.get("value_usd"),
                "imports": imports.get("value_usd"),
                "balance": None  # Would calculate if data available
            })
        
        return {
            "country": self.COUNTRIES.get(country, country),
            "country_code": country,
            "period": f"{start_year}-{end_year}",
            "data": balance_data,
            "source": "UN ESCWA ETDP",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def get_strategic_commodities(
        self,
        country: str = "QAT",
        flow: str = "import",
        year: int = 2023,
    ) -> Dict[str, Any]:
        """
        Get trade data for strategic commodity categories.
        
        Args:
            country: Country code
            flow: Trade flow ('export' or 'import')
            year: Year of data
            
        Returns:
            Dictionary with strategic commodity trade data
        """
        commodities_data = []
        
        for code, description in self.STRATEGIC_COMMODITIES.items():
            data = await self.get_trade_data(
                reporter=country,
                flow=flow,
                year=year,
                commodity_code=code
            )
            
            commodities_data.append({
                "commodity_code": code,
                "description": description,
                "value_usd": data.get("value_usd"),
            })
        
        return {
            "country": self.COUNTRIES.get(country, country),
            "flow": flow,
            "year": year,
            "commodities": commodities_data,
            "source": "UN ESCWA ETDP",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def get_available_countries(self) -> Dict[str, str]:
        """Get dict of supported country codes and names."""
        return self.COUNTRIES.copy()
    
    def get_strategic_commodity_codes(self) -> Dict[str, str]:
        """Get dict of strategic commodity codes and descriptions."""
        return self.STRATEGIC_COMMODITIES.copy()


# Singleton instance
_client: Optional[ESCWATradeAPI] = None


def get_escwa_client() -> ESCWATradeAPI:
    """Get or create shared ESCWA client instance."""
    global _client
    if _client is None:
        _client = ESCWATradeAPI()
    return _client


async def close_escwa_client():
    """Close the shared ESCWA client."""
    global _client
    if _client:
        await _client.close()
        _client = None

