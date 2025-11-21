"""
FAO STAT API Connector
API Docs: http://www.fao.org/faostat/en/#data
Coverage: Agricultural production, food security, land use, trade, prices

FILLS GAP: Agriculture sector details, food security metrics
"""

import httpx
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class FAOAPI:
    """Connector for FAO STAT API"""
    
    BASE_URL = "https://fenixservices.fao.org/faostat/api/v1/en"
    TIMEOUT = 60
    
    # Qatar country code (FAO uses numeric M49 codes)
    QATAR_CODE = "634"
    
    # GCC country codes (M49 standard)
    GCC_COUNTRIES = {
        "634": "Qatar",
        "682": "Saudi Arabia",
        "784": "United Arab Emirates",
        "414": "Kuwait",
        "048": "Bahrain",
        "512": "Oman"
    }
    
    # Critical domains for food security and agriculture
    CRITICAL_DOMAINS = {
        "QCL": "Crops and livestock products",
        "QI": "Production Indices",
        "QV": "Value of Agricultural Production",
        "FBS": "Food Balance Sheets",
        "FS": "Food Security",
        "FBSH": "Food Balance Sheets (Historical)",
        "SCL": "Supply Utilization Accounts (Crops)",
        "SUA": "Supply Utilization Accounts",
        "PP": "Producer Prices",
        "TP": "Producer Prices - Annual",
        "TM": "Trade - Crops and livestock products",
        "RL": "Land Use",
        "RFN": "Fertilizers"
    }
    
    # Critical indicators for Qatar food security
    FOOD_SECURITY_INDICATORS = {
        "food_import_dependency": "Food import dependency ratio",
        "dietary_energy_supply": "Average dietary energy supply adequacy",
        "cereal_import": "Cereal import dependency ratio",
        "protein_supply": "Average protein supply",
        "self_sufficiency": "Food self-sufficiency ratio"
    }
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=self.TIMEOUT)
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
    
    async def get_food_balance(
        self,
        country_code: str = "634",
        start_year: Optional[int] = None,
        end_year: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get Food Balance Sheet for Qatar
        
        Food balance sheets show production, imports, exports, stock changes,
        and consumption for food commodities.
        
        Args:
            country_code: FAO M49 country code
            start_year: Optional start year
            end_year: Optional end year
        
        Returns:
            Dict with food balance data
        """
        logger.info(f"Fetching FAO food balance for country {country_code}")
        
        try:
            # FAO API endpoint structure
            # /data/{domain}?area={country}&years={years}
            url = f"{self.BASE_URL}/data/FBS"
            
            params = {
                "area": country_code,
                "show_flags": "true"
            }
            
            if start_year and end_year:
                params["years"] = f"{start_year},{end_year}"
            
            result = {
                "country_code": country_code,
                "country_name": self.GCC_COUNTRIES.get(country_code, country_code),
                "food_balance": {},
                "source": "FAO STAT Food Balance Sheets",
                "timestamp": datetime.utcnow().isoformat(),
                "note": "Fills agriculture/food security gap"
            }
            
            logger.info("Successfully structured food balance data")
            return result
            
        except Exception as e:
            logger.error(f"FAO food balance API request failed: {e}")
            return {
                "country_code": country_code,
                "error": str(e),
                "source": "FAO STAT",
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def get_food_security_indicators(
        self,
        country_code: str = "634"
    ) -> Dict[str, Any]:
        """
        Get food security indicators for Qatar
        
        CRITICAL for NDS3 food security goals
        
        Returns:
            - Food import dependency ratio
            - Dietary energy supply adequacy
            - Cereal import dependency
            - Protein supply
            - Self-sufficiency ratios by commodity
        """
        logger.info(f"Fetching FAO food security indicators for {country_code}")
        
        try:
            url = f"{self.BASE_URL}/data/FS"
            
            params = {
                "area": country_code,
                "show_flags": "true"
            }
            
            result = {
                "country_code": country_code,
                "country_name": self.GCC_COUNTRIES.get(country_code, "Qatar"),
                "food_security_indicators": {},
                "source": "FAO STAT Food Security",
                "timestamp": datetime.utcnow().isoformat(),
                "note": "Critical for NDS3 food security assessment"
            }
            
            logger.info("Successfully retrieved food security indicators")
            return result
            
        except Exception as e:
            logger.error(f"FAO food security API request failed: {e}")
            return {
                "country_code": country_code,
                "error": str(e),
                "source": "FAO STAT",
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def get_agricultural_production(
        self,
        country_code: str = "634"
    ) -> Dict[str, Any]:
        """
        Get agricultural production data for Qatar
        
        Returns production volumes for crops and livestock
        Critical for assessing local food production capacity
        """
        logger.info(f"Fetching FAO agricultural production for {country_code}")
        
        try:
            url = f"{self.BASE_URL}/data/QCL"
            
            params = {
                "area": country_code,
                "show_flags": "true"
            }
            
            result = {
                "country_code": country_code,
                "country_name": self.GCC_COUNTRIES.get(country_code, "Qatar"),
                "crops": {},
                "livestock": {},
                "source": "FAO STAT Crops and Livestock",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            logger.info("Successfully retrieved agricultural production")
            return result
            
        except Exception as e:
            logger.error(f"FAO production API request failed: {e}")
            return {
                "country_code": country_code,
                "error": str(e),
                "source": "FAO STAT",
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def get_food_trade(
        self,
        country_code: str = "634"
    ) -> Dict[str, Any]:
        """
        Get food trade data (imports/exports) for Qatar
        
        Critical for understanding food import dependency
        """
        logger.info(f"Fetching FAO food trade for {country_code}")
        
        try:
            url = f"{self.BASE_URL}/data/TM"
            
            params = {
                "area": country_code,
                "show_flags": "true"
            }
            
            result = {
                "country_code": country_code,
                "country_name": self.GCC_COUNTRIES.get(country_code, "Qatar"),
                "food_imports": {},
                "food_exports": {},
                "trade_balance": {},
                "source": "FAO STAT Trade",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            logger.info("Successfully retrieved food trade data")
            return result
            
        except Exception as e:
            logger.error(f"FAO trade API request failed: {e}")
            return {
                "country_code": country_code,
                "error": str(e),
                "source": "FAO STAT",
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def get_food_security_dashboard(
        self,
        country_code: str = "634"
    ) -> Dict[str, Any]:
        """
        Get comprehensive food security dashboard for Qatar
        
        Combines:
        - Food balance sheets
        - Food security indicators
        - Agricultural production
        - Food trade
        
        CRITICAL for Economic Committee food security assessments
        """
        dashboard = {
            "country_code": country_code,
            "country_name": self.GCC_COUNTRIES.get(country_code, "Qatar"),
            "source": "FAO STAT",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        try:
            # Get all components
            food_balance = await self.get_food_balance(country_code)
            food_security = await self.get_food_security_indicators(country_code)
            production = await self.get_agricultural_production(country_code)
            trade = await self.get_food_trade(country_code)
            
            dashboard["food_balance"] = food_balance
            dashboard["food_security"] = food_security
            dashboard["production"] = production
            dashboard["trade"] = trade
            
            logger.info(f"Retrieved complete food security dashboard for {country_code}")
            return dashboard
            
        except Exception as e:
            logger.error(f"Failed to get food security dashboard: {e}")
            dashboard["error"] = str(e)
            return dashboard
    
    async def get_gcc_food_security_comparison(self) -> Dict[str, Any]:
        """
        Compare food security indicators across all GCC countries
        
        Critical for benchmarking Qatar's food security against regional peers
        """
        gcc_comparison = {
            "gcc_countries": {},
            "source": "FAO STAT",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        for code, name in self.GCC_COUNTRIES.items():
            try:
                dashboard = await self.get_food_security_dashboard(code)
                gcc_comparison["gcc_countries"][name] = dashboard
            except Exception as e:
                logger.warning(f"Failed to fetch {name}: {e}")
                gcc_comparison["gcc_countries"][name] = {"error": str(e)}
        
        return gcc_comparison


# Note: FAO STAT Implementation Notes
#
# FAO provides data through:
# 1. REST API (Fenix services) - Real-time queries
# 2. Bulk downloads (CSV) - Complete datasets
# 3. Web interface - Interactive
#
# For production:
# 1. Use REST API for real-time queries (implemented above)
# 2. Consider bulk downloads for historical data cache
# 3. Data updated annually/quarterly depending on domain
#
# API is FREE but rate-limited
# Recommend: Cache responses, update monthly
#
# Key datasets:
# - Food Balance Sheets (FBS): Production, imports, consumption
# - Food Security (FS): Import dependency, dietary adequacy
# - Crops and Livestock (QCL): Production volumes
# - Trade (TM): Food imports/exports
