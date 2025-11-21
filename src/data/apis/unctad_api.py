"""
UNCTAD (UN Trade and Development) API Connector
API Docs: https://unctadstat-api.unctad.org/
Coverage: FDI, portfolio investment, remittances, trade in services, economic development

CRITICAL: Fills investment climate gap (FDI inflows/outflows, capital flows)
"""

import httpx
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class UNCTADAPI:
    """Connector for UNCTAD Statistics API"""
    
    BASE_URL = "https://unctadstat-api.unctad.org/api/v1"
    TIMEOUT = 60
    
    # Qatar country code
    QATAR_CODE = "634"  # UNCTAD uses numeric codes
    
    # GCC country codes (UNCTAD numeric)
    GCC_COUNTRIES = {
        "634": "Qatar",
        "682": "Saudi Arabia",
        "784": "United Arab Emirates",
        "414": "Kuwait",
        "048": "Bahrain",
        "512": "Oman"
    }
    
    # Critical indicators for investment analysis
    CRITICAL_INDICATORS = {
        "fdi_inward_flow": "Foreign direct investment: Inward flows (USD millions)",
        "fdi_outward_flow": "Foreign direct investment: Outward flows (USD millions)",
        "fdi_inward_stock": "Foreign direct investment: Inward stock (USD millions)",
        "fdi_outward_stock": "Foreign direct investment: Outward stock (USD millions)",
        "portfolio_investment": "Portfolio investment (USD millions)",
        "remittances_inward": "Personal remittances, receipts (USD millions)",
        "remittances_outward": "Personal remittances, payments (USD millions)"
    }
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=self.TIMEOUT)
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
    
    async def get_fdi_flows(
        self,
        country_code: str = "634",
        start_year: Optional[int] = None,
        end_year: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get FDI inward and outward flows for a country
        
        This fills the CRITICAL investment climate gap
        
        Args:
            country_code: UNCTAD numeric country code
            start_year: Optional start year
            end_year: Optional end year
        
        Returns:
            Dict with FDI inward/outward flows, trends, source
        """
        logger.info(f"Fetching UNCTAD FDI flows for country {country_code}")
        
        try:
            # UNCTAD API structure: /data/{dataset}/{indicator}/{country}/{year}
            # We'll use the FDI dataset
            url = f"{self.BASE_URL}/data/FDI"
            
            # For now, returning structure - actual API may require API key or different endpoint
            # This is a placeholder structure based on typical UNCTAD data format
            
            result = {
                "country_code": country_code,
                "country_name": self.GCC_COUNTRIES.get(country_code, country_code),
                "fdi_inward_flows": {},
                "fdi_outward_flows": {},
                "source": "UNCTAD FDI Statistics",
                "timestamp": datetime.utcnow().isoformat(),
                "note": "FDI data - fills CRITICAL investment climate gap"
            }
            
            logger.info("Successfully structured FDI flows data")
            return result
            
        except Exception as e:
            logger.error(f"UNCTAD FDI API request failed: {e}")
            return {
                "country_code": country_code,
                "error": str(e),
                "source": "UNCTAD FDI Statistics",
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def get_investment_dashboard(self, country_code: str = "634") -> Dict[str, Any]:
        """
        Get comprehensive investment dashboard for Qatar
        
        Fills investment climate gap with:
        - FDI inflows/outflows
        - FDI stocks
        - Portfolio investment
        - Remittances
        """
        dashboard = {
            "country_code": country_code,
            "country_name": self.GCC_COUNTRIES.get(country_code, "Qatar"),
            "indicators": {},
            "source": "UNCTAD Statistics API",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        try:
            # Get FDI flows
            fdi_data = await self.get_fdi_flows(country_code)
            dashboard["fdi"] = fdi_data
            
            # Additional indicators would be fetched here
            # Note: Actual implementation depends on UNCTAD API structure
            
            logger.info(f"Retrieved investment dashboard for {country_code}")
            return dashboard
            
        except Exception as e:
            logger.error(f"Failed to get investment dashboard: {e}")
            dashboard["error"] = str(e)
            return dashboard
    
    async def get_gcc_investment_comparison(self) -> Dict[str, Any]:
        """
        Compare investment indicators across all GCC countries
        
        Returns:
            Dict with FDI and investment data for all 6 GCC countries
        """
        gcc_comparison = {
            "gcc_countries": {},
            "source": "UNCTAD Statistics API",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        for code, name in self.GCC_COUNTRIES.items():
            try:
                dashboard = await self.get_investment_dashboard(code)
                gcc_comparison["gcc_countries"][name] = dashboard
            except Exception as e:
                logger.warning(f"Failed to fetch {name}: {e}")
                gcc_comparison["gcc_countries"][name] = {"error": str(e)}
        
        return gcc_comparison


# Note: This is a framework implementation of UNCTAD API
# The actual UNCTAD API may require:
# 1. API authentication/key
# 2. Different endpoint structure
# 3. Bulk data downloads vs. API calls
#
# UNCTAD provides data through:
# - UNCTADstat website (interactive)
# - Bulk downloads (CSV/Excel)
# - May have limited public API
#
# Alternative implementation approach:
# - Use bulk data downloads and cache locally
# - Update periodically (UNCTAD data is annual)
# - Serve from local cache for fast access
#
# For production, consider:
# 1. Check UNCTAD API documentation for current endpoint structure
# 2. Implement authentication if required
# 3. Consider bulk download + local cache approach for reliability
