"""
Arab Development Portal (ADP) Universal Connector.

Provides access to 179,000+ datasets across all domains:
- Labor & Employment: 13,178 datasets
- Trade: 16,721 datasets
- Macroeconomy: 12,688 datasets
- Health, Education, Energy, Tourism, etc.

API Documentation: https://data.arabdevelopmentportal.org/api

Features:
- Domain-agnostic: Works with any theme/category
- Rate limiting: Respects API limits
- Checkpointing: Resumable bulk ingestion
- ODATA v2.1 compliant
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


class ArabDevPortalClient:
    """
    Universal connector for Arab Development Portal ODATA API.
    
    Supports all domains: Labor, Trade, Economy, Health, Education, Energy, Tourism
    """
    
    BASE_URL = "https://data.arabdevelopmentportal.org/api/explore/v2.1"
    
    # Domain themes mapping
    DOMAIN_THEMES = {
        "Labor": "labor-and-employment",
        "Trade": "trade",
        "Economy": "macroeconomy",
        "Health": "health",
        "Education": "education",
        "Energy": "energy",
        "Tourism": "tourism",
        "Youth": "youth",
        "Gender": "gender",
        "Environment": "environment",
        "Finance": "banking-and-finance",
        "Infrastructure": "infrastructure",
        "Governance": "governance",
        "Digital": "digital-and-ict",
    }
    
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
        "IRQ": "Iraq",
    }
    
    def __init__(
        self,
        timeout: int = 60,
        rate_limiter: Optional[RateLimiter] = None,
        checkpoint_manager: Optional[CheckpointManager] = None,
    ):
        """
        Initialize ADP client.
        
        Args:
            timeout: Request timeout in seconds
            rate_limiter: Optional custom rate limiter
            checkpoint_manager: Optional custom checkpoint manager
        """
        self.client = httpx.AsyncClient(timeout=timeout)
        self.rate_limiter = rate_limiter or get_rate_limiter(
            requests_per_minute=60,
            requests_per_day=5000
        )
        self.checkpoint_manager = checkpoint_manager or get_checkpoint_manager()
        self.backoff = ExponentialBackoff(max_retries=5)
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
    
    async def search_datasets(
        self,
        theme: Optional[str] = None,
        country: str = "QAT",
        search_query: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Search ADP catalog for datasets.
        
        Args:
            theme: Domain theme (e.g., "Labor", "Health")
            country: Country code (default: QAT)
            search_query: Free text search query
            limit: Max results per request
            offset: Pagination offset
            
        Returns:
            List of dataset metadata dicts
        """
        await self.rate_limiter.wait_if_needed()
        
        url = f"{self.BASE_URL}/catalog/datasets"
        
        params = {
            "limit": limit,
            "offset": offset,
        }
        
        # Build where clause
        where_clauses = []
        if theme:
            theme_code = self.DOMAIN_THEMES.get(theme, theme)
            where_clauses.append(f"theme='{theme_code}'")
        
        if where_clauses:
            params["where"] = " AND ".join(where_clauses)
        
        # Add country refinement
        if country:
            params["refine"] = f"country:{country}"
        
        # Add search query
        if search_query:
            params["q"] = search_query
        
        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            results = data.get("results", [])
            logger.info(f"Found {len(results)} datasets for theme={theme}, country={country}")
            return results
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise RateLimitExceeded(
                    "ADP rate limit exceeded",
                    retry_after=float(e.response.headers.get("Retry-After", 60))
                )
            elif e.response.status_code == 404:
                # API endpoint may have changed or dataset doesn't exist
                logger.warning(f"ADP returned 404 for theme={theme}, country={country} - endpoint may have changed")
                return []  # Return empty instead of crashing
            logger.error(f"ADP search failed: {e}")
            return []  # Graceful degradation - return empty instead of raising
    
    async def get_dataset_records(
        self,
        dataset_id: str,
        limit: int = 10000,
        offset: int = 0,
        select: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """
        Fetch all records from a specific dataset.
        
        Args:
            dataset_id: ADP dataset identifier
            limit: Max records per request
            offset: Pagination offset
            select: Optional list of fields to retrieve
            
        Returns:
            DataFrame with dataset records
        """
        await self.rate_limiter.wait_if_needed()
        
        url = f"{self.BASE_URL}/catalog/datasets/{dataset_id}/records"
        
        params = {
            "limit": limit,
            "offset": offset,
        }
        
        if select:
            params["select"] = ",".join(select)
        
        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            records = data.get("results", [])
            
            if not records:
                return pd.DataFrame()
            
            # Flatten nested record structure
            flat_records = []
            for record in records:
                flat = record.get("record", {}).get("fields", record)
                flat_records.append(flat)
            
            df = pd.DataFrame(flat_records)
            logger.debug(f"Fetched {len(df)} records from {dataset_id}")
            return df
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise RateLimitExceeded("ADP rate limit exceeded")
            elif e.response.status_code == 404:
                logger.warning(f"ADP dataset {dataset_id} not found (404)")
                return pd.DataFrame()  # Return empty DataFrame
            logger.error(f"ADP fetch failed for {dataset_id}: {e}")
            return pd.DataFrame()  # Graceful degradation
    
    async def get_country_indicators(
        self,
        country: str = "QAT",
    ) -> Dict[str, Any]:
        """
        Get key indicators for a country (GDP, HDI, Population, etc.).
        
        Args:
            country: Country code
            
        Returns:
            Dict with key indicators
        """
        await self.rate_limiter.wait_if_needed()
        
        url = f"{self.BASE_URL}/catalog/datasets/country-key-indicators/records"
        
        params = {
            "limit": 100,
            "refine": f"country_code:{country}",
        }
        
        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            records = data.get("results", [])
            
            indicators = {}
            for record in records:
                fields = record.get("record", {}).get("fields", record)
                indicator_name = fields.get("indicator_name", "Unknown")
                indicators[indicator_name] = {
                    "value": fields.get("value"),
                    "year": fields.get("year"),
                    "unit": fields.get("unit"),
                    "source": "Arab Development Portal",
                }
            
            return indicators
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to get country indicators: {e}")
            return {}
    
    async def get_domain_data(
        self,
        domain: str,
        country: str = "QAT",
        max_datasets: int = 50,
    ) -> pd.DataFrame:
        """
        Get all data for a domain (e.g., "Labor", "Health").
        
        Args:
            domain: Domain name
            country: Country code
            max_datasets: Maximum datasets to fetch
            
        Returns:
            Combined DataFrame from all datasets
        """
        # Check for existing checkpoint
        start_idx = self.checkpoint_manager.get_resume_index(domain, "adp")
        
        if start_idx > 0:
            logger.info(f"Resuming {domain} ingestion from index {start_idx}")
        
        # Get datasets for domain
        datasets = await self.search_datasets(
            theme=domain,
            country=country,
            limit=max_datasets,
        )
        
        if not datasets:
            logger.warning(f"No datasets found for domain: {domain}")
            return pd.DataFrame()
        
        all_data = []
        
        for idx, ds in enumerate(datasets[start_idx:], start=start_idx):
            dataset_id = ds.get("dataset_id", ds.get("datasetid"))
            
            if not dataset_id:
                continue
            
            try:
                df = await self.get_dataset_records(dataset_id)
                
                if not df.empty:
                    df["source_dataset"] = dataset_id
                    df["domain"] = domain
                    df["source"] = "ADP"
                    all_data.append(df)
                
                # Save checkpoint every 10 datasets
                if idx % 10 == 0 and idx > start_idx:
                    self.checkpoint_manager.save_checkpoint(
                        domain=domain,
                        current_index=idx,
                        total_items=len(datasets),
                        source="adp",
                        metadata={"country": country, "last_dataset": dataset_id}
                    )
                
            except RateLimitExceeded:
                # Save checkpoint and wait
                self.checkpoint_manager.save_checkpoint(
                    domain=domain,
                    current_index=idx,
                    total_items=len(datasets),
                    source="adp",
                )
                logger.warning(f"Rate limit hit at dataset {idx}. Checkpoint saved.")
                await asyncio.sleep(60)
                continue
                
            except Exception as e:
                logger.error(f"Failed to fetch {dataset_id}: {e}")
                continue
        
        # Clear checkpoint on success
        self.checkpoint_manager.clear_checkpoint(domain, "adp")
        
        if all_data:
            result = pd.concat(all_data, ignore_index=True)
            logger.info(f"Collected {len(result)} total records for {domain}")
            return result
        
        return pd.DataFrame()
    
    async def get_qatar_labor_data(self) -> pd.DataFrame:
        """Convenience method to get Qatar labor market data."""
        return await self.get_domain_data("Labor", "QAT")
    
    async def get_qatar_health_data(self) -> pd.DataFrame:
        """Convenience method to get Qatar health data."""
        return await self.get_domain_data("Health", "QAT")
    
    async def get_qatar_trade_data(self) -> pd.DataFrame:
        """Convenience method to get Qatar trade data."""
        return await self.get_domain_data("Trade", "QAT")
    
    async def get_qatar_education_data(self) -> pd.DataFrame:
        """Convenience method to get Qatar education data."""
        return await self.get_domain_data("Education", "QAT")
    
    async def get_qatar_energy_data(self) -> pd.DataFrame:
        """Convenience method to get Qatar energy data."""
        return await self.get_domain_data("Energy", "QAT")
    
    def get_available_domains(self) -> List[str]:
        """Get list of available domains."""
        return list(self.DOMAIN_THEMES.keys())
    
    def get_supported_countries(self) -> Dict[str, str]:
        """Get dict of supported country codes and names."""
        return self.COUNTRIES.copy()


# Singleton instance
_client: Optional[ArabDevPortalClient] = None


def get_adp_client() -> ArabDevPortalClient:
    """Get or create shared ADP client instance."""
    global _client
    if _client is None:
        _client = ArabDevPortalClient()
    return _client


async def close_adp_client():
    """Close the shared ADP client."""
    global _client
    if _client:
        await _client.close()
        _client = None

