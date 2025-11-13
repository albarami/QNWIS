"""
LMIS (Labour Market Information System) - Qatar Ministry of Labour API Client.

Official LMIS Dashboard API integration for real-time workforce data from
Qatar's Ministry of Labour.

Base URL: https://lmis-dashb-api.mol.gov.qa/api/
Authentication: Bearer token required

API Categories:
- Labor Market Indicators
- Economic Diversification and Growth
- Human Capital Development
- Skills-Based Forecasting and Nationalization
- Dynamic Labor Market Modeling
- Expat Labor Dynamics
- SMEs and Local Businesses
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any, Literal

import pandas as pd
import requests

logger = logging.getLogger(__name__)

# LMIS API Configuration
LMIS_BASE_URL = "https://lmis-dashb-api.mol.gov.qa/api"
LMIS_POWERBI_URL = f"{LMIS_BASE_URL}/power-bi"

# Sector types
SectorType = Literal["NDS3", "ISIC"]


class LMISAPIClient:
    """
    Client for Qatar Ministry of Labour LMIS Dashboard API.
    
    Provides access to official labour market data, workforce statistics,
    skills analysis, and economic indicators.
    """
    
    def __init__(self, api_token: str | None = None):
        """
        Initialize LMIS API client.
        
        Args:
            api_token: Bearer token for API authentication.
                      If not provided, reads from LMIS_API_TOKEN env variable.
        """
        self.base_url = LMIS_BASE_URL
        self.powerbi_url = LMIS_POWERBI_URL
        self.api_token = api_token or os.getenv("LMIS_API_TOKEN")
        
        if not self.api_token:
            logger.warning("LMIS_API_TOKEN not set - API calls may fail")
    
    def _get_headers(self, lang: str = "en") -> dict[str, str]:
        """Build request headers with authentication."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "*/*",
        }
        
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"
        
        return headers
    
    def _make_request(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        lang: str = "en"
    ) -> dict[str, Any] | list[dict[str, Any]] | None:
        """
        Make API request to LMIS.
        
        Args:
            endpoint: API endpoint path
            params: Query parameters
            lang: Language ('en' or 'ar')
            
        Returns:
            JSON response data or None if request fails
        """
        if params is None:
            params = {}
        
        params["lang"] = lang
        
        try:
            response = requests.get(
                endpoint,
                params=params,
                headers=self._get_headers(lang),
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 401:
                logger.error("LMIS API authentication failed - check API token")
                return None
            else:
                logger.warning(f"LMIS API returned status {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error calling LMIS API: {e}")
            return None
    
    # ==========================================================================
    # LABOR MARKET INDICATORS
    # ==========================================================================
    
    def get_qatar_main_indicators(self, lang: str = "en") -> pd.DataFrame:
        """
        Fetch main labor market indicators for Qatar.
        
        Includes: Population, GDP, unemployment, exports, imports, remittances,
        female labor participation, health coverage, internet usage, etc.
        
        Args:
            lang: Language ('en' or 'ar')
            
        Returns:
            DataFrame with main economic and labor indicators
        """
        endpoint = f"{self.powerbi_url}/escwa-api-qatar-indicators"
        data = self._make_request(endpoint, lang=lang)
        
        if data and isinstance(data, list) and len(data) > 0:
            df = pd.DataFrame(data)
            df["fetched_at"] = datetime.now()
            df["source"] = "LMIS_MOL"
            return df
        
        return pd.DataFrame()
    
    def get_sdg_indicators(self, lang: str = "en") -> pd.DataFrame:
        """
        Fetch Sustainable Development Goals (SDG) progress indicators.
        
        Args:
            lang: Language ('en' or 'ar')
            
        Returns:
            DataFrame with SDG indicators by country
        """
        endpoint = f"{self.powerbi_url}/escwa-api-sdgs"
        data = self._make_request(endpoint, lang=lang)
        
        if data and isinstance(data, list):
            # Flatten nested SDG data
            records = []
            for item in data:
                country = item.get("country")
                sdgs = item.get("sdgs", {})
                
                for sdg_code, value in sdgs.items():
                    records.append({
                        "country": country,
                        "sdg_code": sdg_code,
                        "value": value,
                        "timestamp": item.get("timestamp")
                    })
            
            df = pd.DataFrame(records)
            df["fetched_at"] = datetime.now()
            df["source"] = "LMIS_MOL"
            return df
        
        return pd.DataFrame()
    
    def get_job_seniority_distribution(self, lang: str = "en") -> pd.DataFrame:
        """
        Fetch workforce distribution by seniority level.
        
        Returns data for GCC countries with breakdown by:
        - Entry level
        - Junior
        - Mid-level
        - Senior
        
        Args:
            lang: Language ('en' or 'ar')
            
        Returns:
            DataFrame with seniority distribution by country
        """
        endpoint = f"{self.powerbi_url}/escwa-api-seniority"
        data = self._make_request(endpoint, lang=lang)
        
        if data and isinstance(data, list):
            df = pd.DataFrame(data)
            df["fetched_at"] = datetime.now()
            df["source"] = "LMIS_MOL"
            return df
        
        return pd.DataFrame()
    
    # ==========================================================================
    # ECONOMIC DIVERSIFICATION AND GROWTH
    # ==========================================================================
    
    def get_sector_growth(
        self,
        sector_type: SectorType = "NDS3",
        lang: str = "en"
    ) -> pd.DataFrame:
        """
        Fetch sector workforce growth data.
        
        Args:
            sector_type: 'NDS3' for strategic clusters or 'ISIC' for economic sectors
            lang: Language ('en' or 'ar')
            
        Returns:
            DataFrame with sector growth metrics
        """
        endpoint = f"{self.base_url}/sector-growth-new/{sector_type}"
        data = self._make_request(endpoint, lang=lang)
        
        if data:
            df = pd.DataFrame(data) if isinstance(data, list) else pd.DataFrame([data])
            df["sector_type"] = sector_type
            df["fetched_at"] = datetime.now()
            df["source"] = "LMIS_MOL"
            return df
        
        return pd.DataFrame()
    
    def get_top_skills_by_sector(
        self,
        sector_type: SectorType = "NDS3",
        lang: str = "en"
    ) -> pd.DataFrame:
        """
        Fetch top demanded skills by strategic cluster or economic sector.
        
        Args:
            sector_type: 'NDS3' for strategic clusters or 'ISIC' for economic sectors
            lang: Language ('en' or 'ar')
            
        Returns:
            DataFrame with top skills by sector
        """
        endpoint = f"{self.base_url}/top-skills-sector/{sector_type}"
        data = self._make_request(endpoint, lang=lang)
        
        if data:
            df = pd.DataFrame(data) if isinstance(data, list) else pd.DataFrame([data])
            df["sector_type"] = sector_type
            df["fetched_at"] = datetime.now()
            df["source"] = "LMIS_MOL"
            return df
        
        return pd.DataFrame()
    
    def get_attracted_expat_skills(self, lang: str = "en") -> pd.DataFrame:
        """
        Fetch skills analysis of attracted expatriate workforce.
        
        Args:
            lang: Language ('en' or 'ar')
            
        Returns:
            DataFrame with expat skills vs Qatari job seekers comparison
        """
        endpoint = f"{self.base_url}/demande-skills-mdm-vs-kawader"
        data = self._make_request(endpoint, lang=lang)
        
        if data:
            df = pd.DataFrame(data) if isinstance(data, list) else pd.DataFrame([data])
            df["fetched_at"] = datetime.now()
            df["source"] = "LMIS_MOL"
            return df
        
        return pd.DataFrame()
    
    def get_skills_diversification(self, lang: str = "en") -> pd.DataFrame:
        """
        Fetch skills diversification analysis by country.
        
        Args:
            lang: Language ('en' or 'ar')
            
        Returns:
            DataFrame with skills probability distribution
        """
        endpoint = f"{self.base_url}/skill-probability-country"
        data = self._make_request(endpoint, lang=lang)
        
        if data:
            df = pd.DataFrame(data) if isinstance(data, list) else pd.DataFrame([data])
            df["fetched_at"] = datetime.now()
            df["source"] = "LMIS_MOL"
            return df
        
        return pd.DataFrame()
    
    # ==========================================================================
    # HUMAN CAPITAL DEVELOPMENT
    # ==========================================================================
    
    def get_education_attainment_bachelors(self, lang: str = "en") -> pd.DataFrame:
        """
        Fetch bachelor's degree holders growth over time.
        
        Args:
            lang: Language ('en' or 'ar')
            
        Returns:
            DataFrame with education attainment trends
        """
        endpoint = f"{self.base_url}/edu-attainment-bachelors"
        data = self._make_request(endpoint, lang=lang)
        
        if data:
            df = pd.DataFrame(data) if isinstance(data, list) else pd.DataFrame([data])
            df["fetched_at"] = datetime.now()
            df["source"] = "LMIS_MOL"
            return df
        
        return pd.DataFrame()
    
    def get_emerging_decaying_skills(self, lang: str = "en") -> pd.DataFrame:
        """
        Fetch emerging and decaying skills analysis.
        
        Args:
            lang: Language ('en' or 'ar')
            
        Returns:
            DataFrame with emerging and declining skills
        """
        endpoint = f"{self.base_url}/emerging-decaying-skills"
        data = self._make_request(endpoint, lang=lang)
        
        if data:
            df = pd.DataFrame(data) if isinstance(data, list) else pd.DataFrame([data])
            df["fetched_at"] = datetime.now()
            df["source"] = "LMIS_MOL"
            return df
        
        return pd.DataFrame()
    
    def get_education_system_skills_gap(self, lang: str = "en") -> pd.DataFrame:
        """
        Fetch skills gap analysis between education system output and market demand.
        
        Args:
            lang: Language ('en' or 'ar')
            
        Returns:
            DataFrame with skills gap metrics
        """
        endpoint = f"{self.base_url}/demand-vps-supply-univ"
        data = self._make_request(endpoint, lang=lang)
        
        if data:
            df = pd.DataFrame(data) if isinstance(data, list) else pd.DataFrame([data])
            df["fetched_at"] = datetime.now()
            df["source"] = "LMIS_MOL"
            return df
        
        return pd.DataFrame()
    
    def get_best_paid_occupations(self, lang: str = "en") -> pd.DataFrame:
        """
        Fetch average salary by occupation/sector.
        
        Args:
            lang: Language ('en' or 'ar')
            
        Returns:
            DataFrame with occupation salary rankings
        """
        endpoint = f"{self.base_url}/avg-salary-no-sec"
        data = self._make_request(endpoint, lang=lang)
        
        if data:
            df = pd.DataFrame(data) if isinstance(data, list) else pd.DataFrame([data])
            df["fetched_at"] = datetime.now()
            df["source"] = "LMIS_MOL"
            return df
        
        return pd.DataFrame()
    
    # ==========================================================================
    # SKILLS-BASED FORECASTING AND NATIONALIZATION
    # ==========================================================================
    
    def get_qatari_jobseekers_skills_gap(self, lang: str = "en") -> pd.DataFrame:
        """
        Fetch skills gap for Qatari job seekers (Kawader system).
        
        Args:
            lang: Language ('en' or 'ar')
            
        Returns:
            DataFrame with Qatari job seeker skills vs market demand
        """
        endpoint = f"{self.base_url}/demande-skills-webscrap-vs-kawader"
        data = self._make_request(endpoint, lang=lang)
        
        if data:
            df = pd.DataFrame(data) if isinstance(data, list) else pd.DataFrame([data])
            df["fetched_at"] = datetime.now()
            df["source"] = "LMIS_MOL"
            return df
        
        return pd.DataFrame()
    
    # ==========================================================================
    # DYNAMIC LABOR MARKET MODELING
    # ==========================================================================
    
    def get_occupation_transitions(self, lang: str = "en") -> pd.DataFrame:
        """
        Fetch top pairs of occupation transitions (career mobility).
        
        Args:
            lang: Language ('en' or 'ar')
            
        Returns:
            DataFrame with occupation transition patterns
        """
        endpoint = f"{self.base_url}/job-source-destination"
        data = self._make_request(endpoint, lang=lang)
        
        if data:
            df = pd.DataFrame(data) if isinstance(data, list) else pd.DataFrame([data])
            df["fetched_at"] = datetime.now()
            df["source"] = "LMIS_MOL"
            return df
        
        return pd.DataFrame()
    
    def get_sector_mobility(self, lang: str = "en") -> pd.DataFrame:
        """
        Fetch mobility between sectors over time.
        
        Args:
            lang: Language ('en' or 'ar')
            
        Returns:
            DataFrame with inter-sector mobility patterns
        """
        endpoint = f"{self.base_url}/year-sector-source-dest"
        data = self._make_request(endpoint, lang=lang)
        
        if data:
            df = pd.DataFrame(data) if isinstance(data, list) else pd.DataFrame([data])
            df["fetched_at"] = datetime.now()
            df["source"] = "LMIS_MOL"
            return df
        
        return pd.DataFrame()
    
    # ==========================================================================
    # EXPAT LABOR DYNAMICS
    # ==========================================================================
    
    def get_expat_dominated_occupations(self, lang: str = "en") -> pd.DataFrame:
        """
        Fetch occupations with high reliance on expatriate labor.
        
        Args:
            lang: Language ('en' or 'ar')
            
        Returns:
            DataFrame with expat concentration by occupation
        """
        endpoint = f"{self.base_url}/job-monopoly"
        data = self._make_request(endpoint, lang=lang)
        
        if data:
            df = pd.DataFrame(data) if isinstance(data, list) else pd.DataFrame([data])
            df["fetched_at"] = datetime.now()
            df["source"] = "LMIS_MOL"
            return df
        
        return pd.DataFrame()
    
    def get_top_expat_skills(self, lang: str = "en") -> pd.DataFrame:
        """
        Fetch top skills among expatriate workforce.
        
        Args:
            lang: Language ('en' or 'ar')
            
        Returns:
            DataFrame with top expat skills
        """
        endpoint = f"{self.base_url}/top-skills"
        data = self._make_request(endpoint, lang=lang)
        
        if data:
            df = pd.DataFrame(data) if isinstance(data, list) else pd.DataFrame([data])
            df["fetched_at"] = datetime.now()
            df["source"] = "LMIS_MOL"
            return df
        
        return pd.DataFrame()
    
    # ==========================================================================
    # SMES AND LOCAL BUSINESSES
    # ==========================================================================
    
    def get_occupations_by_company_size(self, lang: str = "en") -> pd.DataFrame:
        """
        Fetch occupation distribution by company size.
        
        Args:
            lang: Language ('en' or 'ar')
            
        Returns:
            DataFrame with occupations grouped by firm size
        """
        endpoint = f"{self.powerbi_url}/grouped-firm-data"
        data = self._make_request(endpoint, lang=lang)
        
        if data:
            df = pd.DataFrame(data) if isinstance(data, list) else pd.DataFrame([data])
            df["fetched_at"] = datetime.now()
            df["source"] = "LMIS_MOL"
            return df
        
        return pd.DataFrame()
    
    def get_sme_growth(self, lang: str = "en") -> pd.DataFrame:
        """
        Fetch SME growth metrics over time.
        
        Args:
            lang: Language ('en' or 'ar')
            
        Returns:
            DataFrame with median growth by firm size and year
        """
        endpoint = f"{self.powerbi_url}/median-growth-size-year"
        data = self._make_request(endpoint, lang=lang)
        
        if data:
            df = pd.DataFrame(data) if isinstance(data, list) else pd.DataFrame([data])
            df["fetched_at"] = datetime.now()
            df["source"] = "LMIS_MOL"
            return df
        
        return pd.DataFrame()
    
    def get_firm_size_transitions(self, lang: str = "en") -> pd.DataFrame:
        """
        Fetch workforce dynamics by firm size (growth/contraction).
        
        Args:
            lang: Language ('en' or 'ar')
            
        Returns:
            DataFrame with firm size transition patterns
        """
        endpoint = f"{self.powerbi_url}/firm-size-transition"
        data = self._make_request(endpoint, lang=lang)
        
        if data:
            df = pd.DataFrame(data) if isinstance(data, list) else pd.DataFrame([data])
            df["fetched_at"] = datetime.now()
            df["source"] = "LMIS_MOL"
            return df
        
        return pd.DataFrame()


def fetch_all_lmis_data(api_token: str | None = None) -> dict[str, pd.DataFrame]:
    """
    Fetch all available LMIS data for database seeding.
    
    Args:
        api_token: LMIS API authentication token
        
    Returns:
        Dictionary mapping data category to DataFrames
    """
    client = LMISAPIClient(api_token=api_token)
    
    logger.info("Fetching comprehensive LMIS data from Ministry of Labour API...")
    
    results = {}
    
    # Labor Market Indicators
    try:
        results["main_indicators"] = client.get_qatar_main_indicators()
        results["sdg_indicators"] = client.get_sdg_indicators()
        results["job_seniority"] = client.get_job_seniority_distribution()
    except Exception as e:
        logger.error(f"Error fetching labor market indicators: {e}")
    
    # Economic Diversification
    try:
        results["sector_growth_nds3"] = client.get_sector_growth("NDS3")
        results["sector_growth_isic"] = client.get_sector_growth("ISIC")
        results["top_skills_nds3"] = client.get_top_skills_by_sector("NDS3")
        results["expat_skills"] = client.get_attracted_expat_skills()
    except Exception as e:
        logger.error(f"Error fetching economic diversification data: {e}")
    
    # Human Capital
    try:
        results["education_bachelors"] = client.get_education_attainment_bachelors()
        results["emerging_skills"] = client.get_emerging_decaying_skills()
        results["skills_gap_education"] = client.get_education_system_skills_gap()
        results["best_paid_occupations"] = client.get_best_paid_occupations()
    except Exception as e:
        logger.error(f"Error fetching human capital data: {e}")
    
    # Dynamic Modeling
    try:
        results["occupation_transitions"] = client.get_occupation_transitions()
        results["sector_mobility"] = client.get_sector_mobility()
    except Exception as e:
        logger.error(f"Error fetching dynamic modeling data: {e}")
    
    # Expat Dynamics
    try:
        results["expat_dominated_jobs"] = client.get_expat_dominated_occupations()
        results["top_expat_skills"] = client.get_top_expat_skills()
    except Exception as e:
        logger.error(f"Error fetching expat dynamics data: {e}")
    
    # SMEs
    try:
        results["occupations_by_company_size"] = client.get_occupations_by_company_size()
        results["sme_growth"] = client.get_sme_growth()
        results["firm_transitions"] = client.get_firm_size_transitions()
    except Exception as e:
        logger.error(f"Error fetching SME data: {e}")
    
    # Filter out empty DataFrames
    results = {k: v for k, v in results.items() if not v.empty}
    
    logger.info(f"Fetched {len(results)} LMIS datasets")
    return results
