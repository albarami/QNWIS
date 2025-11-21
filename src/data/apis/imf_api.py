"""
IMF (International Monetary Fund) Data API Connector
API Docs: https://www.imf.org/external/datamapper/api/v1/
No authentication required - completely free
"""

import httpx
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class IMFConnector:
    """Connector for IMF Data Mapper API"""
    
    BASE_URL = "https://www.imf.org/external/datamapper/api/v1"
    TIMEOUT = 30
    
    # IMF indicator codes
    INDICATORS = {
        "gdp_growth": "NGDP_RPCH",           # Real GDP growth (%)
        "govt_debt": "GGXWDG_NGDP",          # Government debt (% GDP)
        "govt_revenue": "GGR_NGDP",          # Government revenue (% GDP)
        "govt_expenditure": "GGX_NGDP",      # Government expenditure (% GDP)
        "current_account": "BCA_NGDPD",      # Current account balance (% GDP)
        "inflation": "PCPIPCH",              # Inflation (%)
        "unemployment": "LUR",               # Unemployment rate (%)
        "fiscal_balance": "GGXCNL_NGDP",     # Fiscal balance (% GDP)
    }
    
    # GCC country codes
    GCC_COUNTRIES = {
        "QAT": "Qatar",
        "SAU": "Saudi Arabia",
        "ARE": "United Arab Emirates",
        "KWT": "Kuwait",
        "BHR": "Bahrain",
        "OMN": "Oman"
    }
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=self.TIMEOUT)
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
    
    async def get_indicator(
        self,
        indicator_code: str,
        country_code: str = "QAT",
        start_year: Optional[int] = None,
        end_year: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get IMF indicator data for a country
        
        Args:
            indicator_code: IMF indicator code (e.g., "NGDP_RPCH")
            country_code: ISO 3-letter country code
            start_year: Optional start year
            end_year: Optional end year
        
        Returns:
            Dict with values, metadata, source, timestamp
        """
        url = f"{self.BASE_URL}/{indicator_code}/{country_code}"
        
        logger.info(f"Fetching IMF indicator: {indicator_code} for {country_code}")
        
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            data = response.json()
            
            # Extract values
            values = data.get("values", {}).get(indicator_code, {}).get(country_code, {})
            
            # Filter by year range
            if start_year or end_year:
                filtered_values = {}
                for year_str, value in values.items():
                    year = int(year_str)
                    if start_year and year < start_year:
                        continue
                    if end_year and year > end_year:
                        continue
                    filtered_values[year_str] = value
                values = filtered_values
            
            result = {
                "values": values,
                "metadata": {
                    "indicator_code": indicator_code,
                    "country_code": country_code,
                    "country_name": self.GCC_COUNTRIES.get(country_code, country_code),
                    "description": self._get_indicator_description(indicator_code)
                },
                "source": "IMF",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Successfully fetched {len(values)} data points from IMF")
            return result
            
        except httpx.HTTPError as e:
            logger.error(f"IMF API request failed: {e}")
            raise
    
    async def get_qatar_dashboard(self) -> Dict[str, Any]:
        """Get all key indicators for Qatar"""
        logger.info("Fetching Qatar economic dashboard from IMF")
        
        results = {}
        for name, code in self.INDICATORS.items():
            try:
                data = await self.get_indicator(code, "QAT")
                results[name] = data
            except Exception as e:
                logger.warning(f"Failed to fetch {name} ({code}): {e}")
                results[name] = {
                    "error": str(e),
                    "source": "IMF",
                    "timestamp": datetime.utcnow().isoformat()
                }
        
        return results
    
    async def get_gcc_comparison(self, indicator_code: str) -> Dict[str, Dict[str, Any]]:
        """Compare indicator across all GCC countries"""
        logger.info(f"Fetching GCC comparison for indicator: {indicator_code}")
        
        results = {}
        for code, name in self.GCC_COUNTRIES.items():
            try:
                data = await self.get_indicator(indicator_code, code)
                results[name] = data
            except Exception as e:
                logger.warning(f"Failed to fetch {name} data: {e}")
                results[name] = {
                    "error": str(e),
                    "source": "IMF",
                    "timestamp": datetime.utcnow().isoformat()
                }
        
        return results
    
    async def get_latest_value(
        self,
        indicator_code: str,
        country_code: str = "QAT"
    ) -> Optional[float]:
        """Get most recent value for an indicator"""
        try:
            data = await self.get_indicator(indicator_code, country_code)
            values = data.get("values", {})
            
            if not values:
                return None
            
            latest_year = max(values.keys(), key=lambda x: int(x))
            return values[latest_year]
            
        except Exception as e:
            logger.error(f"Failed to get latest value: {e}")
            return None
    
    def _get_indicator_description(self, indicator_code: str) -> str:
        """Get human-readable description"""
        descriptions = {
            "NGDP_RPCH": "Real GDP growth rate (annual %)",
            "GGXWDG_NGDP": "General government gross debt (% of GDP)",
            "GGR_NGDP": "General government revenue (% of GDP)",
            "GGX_NGDP": "General government total expenditure (% of GDP)",
            "BCA_NGDPD": "Current account balance (% of GDP)",
            "PCPIPCH": "Inflation, average consumer prices (annual %)",
            "LUR": "Unemployment rate (%)",
            "GGXCNL_NGDP": "General government net lending/borrowing (% of GDP)"
        }
        return descriptions.get(indicator_code, f"IMF Indicator {indicator_code}")
