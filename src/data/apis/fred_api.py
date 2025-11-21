"""
FRED (Federal Reserve Economic Data) API Connector
API Docs: https://fred.stlouisfed.org/docs/api/fred/
Requires free API key from https://fred.stlouisfed.org/docs/api/api_key.html
"""

import httpx
import logging
import os
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class FREDConnector:
    """Connector for FRED API"""
    
    BASE_URL = "https://api.stlouisfed.org/fred"
    TIMEOUT = 30
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("FRED_API_KEY")
        if not self.api_key:
            logger.warning("FRED_API_KEY not set - API calls will fail")
        
        self.client = httpx.AsyncClient(timeout=self.TIMEOUT)
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
    
    async def get_series(
        self,
        series_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get FRED time series data
        
        Args:
            series_id: FRED series ID (e.g., "GDP", "UNRATE")
            start_date: Start date (YYYY-MM-DD format)
            end_date: End date (YYYY-MM-DD format)
        """
        if not self.api_key:
            raise ValueError("FRED API key required")
        
        params = {
            "series_id": series_id,
            "api_key": self.api_key,
            "file_type": "json"
        }
        
        if start_date:
            params["observation_start"] = start_date
        if end_date:
            params["observation_end"] = end_date
        
        url = f"{self.BASE_URL}/series/observations"
        
        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = await response.json()
            
            # Parse observations
            observations = {}
            for obs in data.get("observations", []):
                date = obs.get("date")
                value = obs.get("value")
                if value != ".":  # FRED uses "." for missing values
                    observations[date] = float(value)
            
            result = {
                "series_id": series_id,
                "values": observations,
                "source": "FRED",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Successfully fetched {len(observations)} observations from FRED")
            return result
            
        except httpx.HTTPError as e:
            logger.error(f"FRED API request failed: {e}")
            raise
    
    async def get_latest_value(self, series_id: str) -> Optional[float]:
        """Get most recent value for a series"""
        try:
            data = await self.get_series(series_id)
            values = data.get("values", {})
            
            if not values:
                return None
            
            latest_date = max(values.keys())
            return values[latest_date]
            
        except Exception as e:
            logger.error(f"Failed to get latest FRED value: {e}")
            return None
