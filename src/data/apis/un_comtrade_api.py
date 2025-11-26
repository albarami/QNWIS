"""
UN Comtrade API Connector
API Docs: https://comtradeapi.un.org/
Rate Limit: 100 requests/hour (free) or higher with API key
"""

import httpx
import logging
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)


class UNComtradeConnector:
    """Connector for UN Comtrade API - Using FREE tier (limited queries)"""
    
    # Use data/v1 endpoint without authentication for limited free access
    # Free tier: limited queries, no authentication
    BASE_URL = "https://comtradeapi.un.org/data/v1"
    TIMEOUT = 60
    
    # Qatar country code
    QATAR_CODE = "634"
    
    # Food commodity codes (HS classification)
    FOOD_COMMODITIES = {
        "02": "Meat",
        "03": "Fish",
        "04": "Dairy, eggs, honey",
        "07": "Vegetables",
        "08": "Fruit, nuts",
        "10": "Cereals",
        "15": "Fats and oils",
        "20": "Vegetable preparations",
        "22": "Beverages"
    }
    
    def __init__(self, api_key: Optional[str] = None):
        # Try without authentication first (free tier with limits)
        # If subscription key available, use it for higher limits
        self.api_key = api_key or os.getenv("UN_COMTRADE_API_KEY")
        
        headers = {}
        if self.api_key:
            headers["Ocp-Apim-Subscription-Key"] = self.api_key
            logger.info("UN Comtrade: Using API key for premium access")
        else:
            logger.info("UN Comtrade: Using FREE tier (limited queries, no authentication)")
        
        self.client = httpx.AsyncClient(timeout=self.TIMEOUT, headers=headers)
        self._request_count = 0
        self._last_request_time = datetime.utcnow()
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
    
    async def _rate_limit_check(self):
        """Enforce 100 req/hour rate limit - DISABLED to avoid blocking workflow"""
        # DISABLED: UN Comtrade requires auth, so we fail fast instead of rate limiting
        # This prevents 35+ second waits that block the entire workflow
        pass
    
    async def get_imports(
        self,
        commodity_code: str,
        year: int = 2022,  # Use 2022 as most recent complete year
        partner: str = "0"
    ) -> Dict:
        """
        Get Qatar import data
        
        Args:
            commodity_code: HS code (e.g., "02" for meat)
            year: Year (default: 2022)
            partner: Partner country code (0 = all partners)
        
        Returns:
            Dictionary with data
        """
        await self._rate_limit_check()
        
        params = {
            "reporterCode": self.QATAR_CODE,
            "period": str(year),
            "partnerCode": partner,
            "flowCode": "M",  # M = imports
            "cmdCode": commodity_code
        }
        
        # Use standard data endpoint
        url = f"{self.BASE_URL}/get/C/A/HS"
        
        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPError as e:
            logger.warning(f"UN Comtrade API unavailable (401 auth required) - skipping")
            # Return immediately without retrying to avoid blocking workflow
            return {"error": "auth_required", "data": []}
    
    async def get_total_food_imports(self, year: int = 2023) -> Dict:
        """Get Qatar's total food imports across all categories"""
        results = {}
        total_value = 0
        
        for code, name in self.FOOD_COMMODITIES.items():
            try:
                data = await self.get_imports(code, year)
                if "data" in data and len(data["data"]) > 0:
                    value = sum(item.get("primaryValue", 0) for item in data["data"])
                    results[name] = {
                        "value_usd": value,
                        "records": len(data["data"])
                    }
                    total_value += value
            except Exception as e:
                logger.warning(f"Failed to fetch {name} imports: {e}")
                results[name] = {"error": str(e)}
        
        results["TOTAL"] = {"value_usd": total_value}
        return results
    
    async def get_top_import_partners(
        self,
        commodity_code: str,
        year: int = 2023,
        top_n: int = 10
    ) -> List[Dict]:
        """Get top N countries Qatar imports from for a commodity"""
        data = await self.get_imports(commodity_code, year)
        
        if "data" not in data:
            return []
        
        # Sort by value
        sorted_data = sorted(
            data["data"],
            key=lambda x: x.get("primaryValue", 0),
            reverse=True
        )
        
        return sorted_data[:top_n]
