"""
ILO (International Labour Organization) Statistics API Client.

Fetches labour market indicators, employment statistics, and working conditions
data from ILOSTAT - the world's largest repository of labour market data.

API Documentation: https://ilostat.ilo.org/data/api/
Base URL: https://www.ilo.org/sdmx/rest/data/

Key Indicators:
- Unemployment rates by demographics
- Labour force participation
- Working conditions and wages
- Employment by sector/occupation
- Youth and informal employment
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import pandas as pd
from ._http import http_get

logger = logging.getLogger(__name__)

# ILO SDMX REST API
ILO_BASE_URL = "https://www.ilo.org/sdmx/rest/data"
ILO_METADATA_URL = "https://www.ilo.org/sdmx/rest/datastructure"

# Common ILO indicators
ILO_INDICATORS = {
    # Unemployment
    "UNE_DEAP_SEX_AGE_RT": "Unemployment rate by sex and age (%)",
    "UNE_TUNE_SEX_AGE_NB": "Unemployment by sex and age (thousands)",
    
    # Employment
    "EMP_TEMP_SEX_AGE_NB": "Employment by sex and age (thousands)",
    "EMP_TEMP_SEX_ECO_NB": "Employment by sex and economic activity (thousands)",
    "EMP_TEMP_SEX_OCU_NB": "Employment by sex and occupation (thousands)",
    
    # Labour Force
    "EAP_TEAP_SEX_AGE_NB": "Labour force by sex and age (thousands)",
    "EAP_DWAP_SEX_AGE_RT": "Labour force participation rate by sex and age (%)",
    
    # Youth Employment
    "EMP_NIFL_SEX_AGE_RT": "Youth not in employment, education or training (NEET) rate (%)",
    "UNE_DEAP_SEX_AGE_RT_A": "Youth unemployment rate (%)",
    
    # Working Time
    "HOW_TEMP_SEX_ECO_NB": "Mean weekly hours actually worked per employed person",
    
    # Earnings
    "EAR_4MTH_SEX_ECO_CUR": "Mean nominal monthly earnings of employees",
    "EAR_INEE_SEX_ECO_CUR": "Mean real monthly earnings of employees",
    
    # Informal Employment
    "EMP_NIFL_SEX_AGE_NB": "Informal employment (thousands)",
    "EMP_NIFL_SEX_AGE_RT": "Informal employment rate (%)",
}

# GCC Countries codes
GCC_COUNTRIES = {
    "QAT": "Qatar",
    "SAU": "Saudi Arabia",
    "ARE": "United Arab Emirates",
    "KWT": "Kuwait",
    "BHR": "Bahrain",
    "OMN": "Oman",
}


class ILOStatsClient:
    """
    Client for ILO Statistics API.
    
    Provides access to international labour market data for comparative analysis.
    """
    
    def __init__(self, cache_dir: str | None = None):
        """
        Initialize ILO Stats client.
        
        Args:
            cache_dir: Optional directory for caching responses
        """
        self.base_url = ILO_BASE_URL
        self.cache_dir = cache_dir
        
    def get_indicator(
        self,
        indicator_code: str,
        country_codes: list[str] | None = None,
        start_year: int | None = None,
        end_year: int | None = None,
    ) -> pd.DataFrame:
        """
        Fetch ILO indicator data.
        
        Args:
            indicator_code: ILO indicator code (e.g., "UNE_DEAP_SEX_AGE_RT")
            country_codes: List of ISO 3-letter country codes (default: GCC countries)
            start_year: Start year for data (default: 2010)
            end_year: End year for data (default: current year)
            
        Returns:
            DataFrame with columns: country_code, country_name, indicator_code,
                                    indicator_name, year, value, sex, age_group
        """
        if country_codes is None:
            country_codes = list(GCC_COUNTRIES.keys())
        
        if start_year is None:
            start_year = 2010
        if end_year is None:
            end_year = datetime.now().year
            
        logger.info(f"Fetching ILO indicator {indicator_code} for {len(country_codes)} countries")
        
        # Build SDMX query
        # Format: /data/{dataflow}/{key}?startPeriod={start}&endPeriod={end}
        countries_param = "+".join(country_codes)
        url = f"{self.base_url}/ILO,DF_{indicator_code}/..{countries_param}..."
        
        params = {
            "startPeriod": str(start_year),
            "endPeriod": str(end_year),
            "format": "jsondata",  # JSON-stat format
        }
        
        try:
            response = http_get(url, params=params, timeout=30)
            
            if response.status_code != 200:
                logger.warning(f"ILO API returned status {response.status_code} for {indicator_code}")
                return pd.DataFrame()
            
            data = response.json()
            return self._parse_sdmx_response(data, indicator_code)
            
        except Exception as e:
            logger.error(f"Error fetching ILO indicator {indicator_code}: {e}")
            return pd.DataFrame()
    
    def _parse_sdmx_response(self, data: dict[str, Any], indicator_code: str) -> pd.DataFrame:
        """Parse SDMX JSON response into DataFrame."""
        try:
            # SDMX JSON-stat structure
            if "dataSets" not in data or not data["dataSets"]:
                return pd.DataFrame()
            
            dataset = data["dataSets"][0]
            structure = data.get("structure", {})
            dimensions = structure.get("dimensions", {}).get("observation", [])
            
            # Extract dimension information
            dim_info = {}
            for dim in dimensions:
                dim_id = dim.get("id")
                values = {v["id"]: v["name"] for v in dim.get("values", [])}
                dim_info[dim_id] = values
            
            # Parse observations
            observations = dataset.get("observations", {})
            records = []
            
            for key, value_list in observations.items():
                # Key format: "0:1:2:3" maps to dimension indices
                indices = [int(i) for i in key.split(":")]
                
                record = {
                    "indicator_code": indicator_code,
                    "indicator_name": ILO_INDICATORS.get(indicator_code, indicator_code),
                    "value": value_list[0] if value_list else None,
                }
                
                # Map indices to dimension values
                for i, dim in enumerate(dimensions):
                    dim_id = dim.get("id")
                    dim_values = dim.get("values", [])
                    
                    if i < len(indices) and indices[i] < len(dim_values):
                        value_obj = dim_values[indices[i]]
                        
                        if dim_id == "ref_area":
                            record["country_code"] = value_obj.get("id")
                            record["country_name"] = GCC_COUNTRIES.get(value_obj.get("id"), value_obj.get("name"))
                        elif dim_id == "time":
                            record["year"] = int(value_obj.get("id"))
                        elif dim_id == "sex":
                            record["sex"] = value_obj.get("name")
                        elif dim_id == "classif1":  # Age group or economic activity
                            record["age_group"] = value_obj.get("name")
                        elif dim_id == "classif2":  # Education level
                            record["education_level"] = value_obj.get("name")
                
                records.append(record)
            
            df = pd.DataFrame(records)
            
            # Clean up
            if not df.empty:
                # Fill missing dimensions
                if "sex" not in df.columns:
                    df["sex"] = "Total"
                if "age_group" not in df.columns:
                    df["age_group"] = "Total"
                if "education_level" not in df.columns:
                    df["education_level"] = None
                
                # Add metadata
                df["source"] = "ILO"
                df["last_updated"] = datetime.now()
            
            return df
            
        except Exception as e:
            logger.error(f"Error parsing ILO SDMX response: {e}")
            return pd.DataFrame()
    
    def get_unemployment_rate_gcc(
        self,
        start_year: int = 2015,
        end_year: int | None = None
    ) -> pd.DataFrame:
        """
        Get unemployment rates for all GCC countries.
        
        Args:
            start_year: Start year (default: 2015)
            end_year: End year (default: current year)
            
        Returns:
            DataFrame with unemployment rates by country, year, sex, and age
        """
        return self.get_indicator(
            "UNE_DEAP_SEX_AGE_RT",
            country_codes=list(GCC_COUNTRIES.keys()),
            start_year=start_year,
            end_year=end_year
        )
    
    def get_labour_force_participation_gcc(
        self,
        start_year: int = 2015,
        end_year: int | None = None
    ) -> pd.DataFrame:
        """
        Get labour force participation rates for all GCC countries.
        
        Args:
            start_year: Start year (default: 2015)
            end_year: End year (default: current year)
            
        Returns:
            DataFrame with participation rates by country, year, sex, and age
        """
        return self.get_indicator(
            "EAP_DWAP_SEX_AGE_RT",
            country_codes=list(GCC_COUNTRIES.keys()),
            start_year=start_year,
            end_year=end_year
        )
    
    def get_youth_neet_rate_gcc(
        self,
        start_year: int = 2015,
        end_year: int | None = None
    ) -> pd.DataFrame:
        """
        Get youth NEET (Not in Employment, Education, or Training) rates for GCC.
        
        Args:
            start_year: Start year (default: 2015)
            end_year: End year (default: current year)
            
        Returns:
            DataFrame with NEET rates by country and year
        """
        return self.get_indicator(
            "EMP_NIFL_SEX_AGE_RT",
            country_codes=list(GCC_COUNTRIES.keys()),
            start_year=start_year,
            end_year=end_year
        )
    
    def get_all_gcc_indicators(
        self,
        start_year: int = 2015,
        end_year: int | None = None
    ) -> dict[str, pd.DataFrame]:
        """
        Fetch all major labour indicators for GCC countries.
        
        Args:
            start_year: Start year (default: 2015)
            end_year: End year (default: current year)
            
        Returns:
            Dictionary mapping indicator codes to DataFrames
        """
        indicators = {
            "unemployment_rate": "UNE_DEAP_SEX_AGE_RT",
            "labour_force_participation": "EAP_DWAP_SEX_AGE_RT",
            "employment": "EMP_TEMP_SEX_AGE_NB",
            "youth_neet": "EMP_NIFL_SEX_AGE_RT",
        }
        
        results = {}
        for name, code in indicators.items():
            logger.info(f"Fetching {name}...")
            df = self.get_indicator(code, start_year=start_year, end_year=end_year)
            if not df.empty:
                results[name] = df
        
        return results


def fetch_ilo_data_for_database(start_year: int = 2015) -> pd.DataFrame:
    """
    Fetch ILO data formatted for database insertion.
    
    Args:
        start_year: Start year for data collection
        
    Returns:
        DataFrame ready for insertion into ilo_labour_data table
    """
    client = ILOStatsClient()
    
    logger.info("Fetching comprehensive ILO data for GCC countries...")
    all_data = client.get_all_gcc_indicators(start_year=start_year)
    
    # Combine all indicators
    combined = pd.concat(all_data.values(), ignore_index=True)
    
    if combined.empty:
        logger.warning("No ILO data fetched")
        return pd.DataFrame()
    
    # Format for database
    combined = combined.rename(columns={
        "last_updated": "created_at"
    })
    
    # Ensure required columns
    required_cols = [
        "country_code", "country_name", "indicator_code", "indicator_name",
        "year", "value", "sex", "age_group", "education_level", "source"
    ]
    
    for col in required_cols:
        if col not in combined.columns:
            combined[col] = None
    
    combined = combined[required_cols + ["created_at"]]
    
    logger.info(f"Fetched {len(combined)} ILO records")
    return combined
