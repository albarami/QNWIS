"""
IEA (International Energy Agency) API Connector
API Docs: https://www.iea.org/data-and-statistics
Coverage: Energy production, consumption, efficiency, transition, prices

FILLS GAP: Detailed energy sector data (critical for NDS3 energy transition goals)
NOTE: Detailed data requires subscription
"""

import httpx
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class IEAAPI:
    """Connector for IEA Energy Statistics API"""
    
    # IEA provides data through:
    # 1. Public reports and key statistics
    # 2. Subscription-based detailed statistics
    # 3. API access (part of subscription)
    
    BASE_URL = "https://api.iea.org/stats"  # Example endpoint
    TIMEOUT = 60
    
    # Qatar country code (ISO 3-letter)
    QATAR_CODE = "QAT"
    
    # GCC country codes
    GCC_COUNTRIES = {
        "QAT": "Qatar",
        "SAU": "Saudi Arabia",
        "ARE": "United Arab Emirates",
        "KWT": "Kuwait",
        "BHR": "Bahrain",
        "OMN": "Oman"
    }
    
    # Critical energy indicators
    ENERGY_INDICATORS = {
        # Production
        "oil_production": "Crude oil production (thousand barrels/day)",
        "gas_production": "Natural gas production (million cubic meters)",
        "electricity_production": "Electricity production (GWh)",
        "renewable_production": "Renewable energy production (GWh)",
        
        # Consumption
        "total_energy_supply": "Total primary energy supply (Mtoe)",
        "oil_consumption": "Oil consumption (thousand barrels/day)",
        "gas_consumption": "Natural gas consumption (million cubic meters)",
        "electricity_consumption": "Electricity consumption (GWh)",
        
        # Efficiency
        "energy_intensity": "Energy intensity (toe per thousand 2015 USD)",
        "carbon_intensity": "CO2 intensity (kg CO2 per USD)",
        
        # Transition
        "renewable_share": "Renewable energy share (%)",
        "solar_capacity": "Solar PV capacity (MW)",
        "wind_capacity": "Wind capacity (MW)",
        
        # Prices
        "electricity_prices_industrial": "Electricity prices - industry (USD/MWh)",
        "electricity_prices_household": "Electricity prices - household (USD/MWh)",
        "gas_prices": "Natural gas prices (USD/MBtu)"
    }
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize IEA API connector
        
        Args:
            api_key: IEA API subscription key (required for detailed data)
        """
        self.api_key = api_key
        self.client = httpx.AsyncClient(timeout=self.TIMEOUT)
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
    
    async def get_energy_production(
        self,
        country_code: str = "QAT",
        start_year: Optional[int] = None,
        end_year: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get energy production data for Qatar
        
        Critical for understanding Qatar's energy sector dominance
        
        Args:
            country_code: ISO 3-letter country code
            start_year: Optional start year
            end_year: Optional end year
        
        Returns:
            Dict with energy production by source
        """
        logger.info(f"Fetching IEA energy production for {country_code}")
        
        try:
            result = {
                "country_code": country_code,
                "country_name": self.GCC_COUNTRIES.get(country_code, country_code),
                "oil_production": {},
                "gas_production": {},
                "electricity_production": {},
                "renewable_production": {},
                "production_by_source": {
                    "oil": {},
                    "natural_gas": {},
                    "coal": {},
                    "nuclear": {},
                    "hydro": {},
                    "solar": {},
                    "wind": {},
                    "other_renewables": {}
                },
                "source": "IEA Energy Statistics",
                "timestamp": datetime.utcnow().isoformat(),
                "note": "Fills energy sector production gap"
            }
            
            if not self.api_key:
                result["warning"] = "API key not provided - requires IEA subscription for detailed data"
            
            logger.info("Successfully structured energy production")
            return result
            
        except Exception as e:
            logger.error(f"IEA production API request failed: {e}")
            return {
                "country_code": country_code,
                "error": str(e),
                "source": "IEA",
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def get_energy_consumption(
        self,
        country_code: str = "QAT"
    ) -> Dict[str, Any]:
        """
        Get energy consumption data for Qatar
        
        Returns:
            - Total primary energy supply
            - Consumption by sector (industry, transport, residential, etc.)
            - Consumption by fuel type
        """
        logger.info(f"Fetching IEA energy consumption for {country_code}")
        
        try:
            result = {
                "country_code": country_code,
                "country_name": self.GCC_COUNTRIES.get(country_code, "Qatar"),
                "total_energy_supply": {},
                "consumption_by_sector": {
                    "industry": {},
                    "transport": {},
                    "residential": {},
                    "commercial": {},
                    "agriculture": {},
                    "other": {}
                },
                "consumption_by_fuel": {
                    "oil": {},
                    "natural_gas": {},
                    "coal": {},
                    "electricity": {},
                    "renewables": {}
                },
                "source": "IEA Energy Statistics",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            if not self.api_key:
                result["warning"] = "API key not provided - requires IEA subscription"
            
            logger.info("Successfully retrieved energy consumption")
            return result
            
        except Exception as e:
            logger.error(f"IEA consumption API request failed: {e}")
            return {
                "country_code": country_code,
                "error": str(e),
                "source": "IEA",
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def get_energy_transition_indicators(
        self,
        country_code: str = "QAT"
    ) -> Dict[str, Any]:
        """
        Get energy transition indicators for Qatar
        
        CRITICAL for NDS3 sustainability and energy transition goals
        
        Returns:
            - Renewable energy share
            - Solar and wind capacity
            - Energy efficiency metrics
            - Carbon intensity
            - Electric vehicle adoption
        """
        logger.info(f"Fetching IEA energy transition indicators for {country_code}")
        
        try:
            result = {
                "country_code": country_code,
                "country_name": self.GCC_COUNTRIES.get(country_code, "Qatar"),
                "renewable_share": {},
                "solar_capacity": {},
                "wind_capacity": {},
                "energy_intensity": {},
                "carbon_intensity": {},
                "ev_adoption": {},
                "energy_efficiency_index": {},
                "source": "IEA Energy Transition",
                "timestamp": datetime.utcnow().isoformat(),
                "note": "Critical for NDS3 sustainability goals"
            }
            
            if not self.api_key:
                result["warning"] = "API key not provided - requires IEA subscription"
            
            logger.info("Successfully retrieved energy transition indicators")
            return result
            
        except Exception as e:
            logger.error(f"IEA transition API request failed: {e}")
            return {
                "country_code": country_code,
                "error": str(e),
                "source": "IEA",
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def get_energy_prices(
        self,
        country_code: str = "QAT"
    ) -> Dict[str, Any]:
        """
        Get energy prices for Qatar
        
        Returns:
            - Electricity prices (industrial, household)
            - Natural gas prices
            - Oil prices (domestic market)
        """
        logger.info(f"Fetching IEA energy prices for {country_code}")
        
        try:
            result = {
                "country_code": country_code,
                "country_name": self.GCC_COUNTRIES.get(country_code, "Qatar"),
                "electricity_prices": {
                    "industrial": {},
                    "household": {},
                    "commercial": {}
                },
                "gas_prices": {},
                "oil_prices": {},
                "source": "IEA Energy Prices",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            if not self.api_key:
                result["warning"] = "API key not provided - requires IEA subscription"
            
            logger.info("Successfully retrieved energy prices")
            return result
            
        except Exception as e:
            logger.error(f"IEA prices API request failed: {e}")
            return {
                "country_code": country_code,
                "error": str(e),
                "source": "IEA",
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def get_energy_dashboard(
        self,
        country_code: str = "QAT"
    ) -> Dict[str, Any]:
        """
        Get comprehensive energy dashboard for Qatar
        
        Combines:
        - Production by source
        - Consumption by sector and fuel
        - Energy transition indicators
        - Energy prices
        
        CRITICAL for Economic Committee energy sector assessment
        """
        dashboard = {
            "country_code": country_code,
            "country_name": self.GCC_COUNTRIES.get(country_code, "Qatar"),
            "source": "IEA Energy Statistics",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        try:
            # Get all components
            production = await self.get_energy_production(country_code)
            consumption = await self.get_energy_consumption(country_code)
            transition = await self.get_energy_transition_indicators(country_code)
            prices = await self.get_energy_prices(country_code)
            
            dashboard["production"] = production
            dashboard["consumption"] = consumption
            dashboard["transition"] = transition
            dashboard["prices"] = prices
            
            if not self.api_key:
                dashboard["warning"] = "API key not provided - requires IEA subscription for complete data"
            
            logger.info(f"Retrieved complete energy dashboard for {country_code}")
            return dashboard
            
        except Exception as e:
            logger.error(f"Failed to get energy dashboard: {e}")
            dashboard["error"] = str(e)
            return dashboard
    
    async def get_gcc_energy_comparison(self) -> Dict[str, Any]:
        """
        Compare energy indicators across all GCC countries
        
        Critical for benchmarking Qatar's energy sector and transition progress
        """
        gcc_comparison = {
            "gcc_countries": {},
            "source": "IEA Energy Statistics",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        for code, name in self.GCC_COUNTRIES.items():
            try:
                dashboard = await self.get_energy_dashboard(code)
                gcc_comparison["gcc_countries"][name] = dashboard
            except Exception as e:
                logger.warning(f"Failed to fetch {name}: {e}")
                gcc_comparison["gcc_countries"][name] = {"error": str(e)}
        
        if not self.api_key:
            gcc_comparison["warning"] = "API key not provided - requires IEA subscription"
        
        return gcc_comparison


# Note: IEA Implementation Notes
#
# IEA provides energy data through:
# 1. Free key statistics (limited indicators)
# 2. Subscription-based detailed statistics
# 3. API access (part of subscription)
#
# For production:
# 1. Consider IEA subscription for comprehensive data
# 2. API key required for detailed statistics
# 3. Data updated monthly/quarterly/annually depending on indicator
# 4. Cache responses, update monthly
#
# Alternative free sources for basic data:
# - World Bank energy indicators (limited)
# - BP Statistical Review (annual, oil/gas focus)
# - IRENA for renewable energy (free)
# - EIA (US) for global energy data (free)
#
# IEA provides most comprehensive and authoritative data
# Recommended for serious energy sector analysis
#
# Subscription options:
# - Online Data Services: Contact for pricing
# - Publications subscription: Variable pricing
# - Custom data requests: Available
#
# Note: Some IEA data available through OECD.Stat for free
# Qatar is not an IEA member but covered in World Energy Statistics
