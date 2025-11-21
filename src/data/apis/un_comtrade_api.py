"""
UN Comtrade API Connector
API Docs: https://comtradeapi.un.org/
Rate Limit: 100 requests/hour (free)
"""

import httpx
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)


class UNComtradeConnector:
    """Connector for UN Comtrade API"""
    
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
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=self.TIMEOUT)
        self._request_count = 0
        self._last_request_time = datetime.utcnow()
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
    
    async def _rate_limit_check(self):
        """Enforce 100 req/hour rate limit"""
        self._request_count += 1
        
        # Simple rate limiting: max 1 req/36 seconds = 100/hour
        if self._request_count > 1:
            time_since_last = (datetime.utcnow() - self._last_request_time).total_seconds()
            if time_since_last < 36:
                wait_time = 36 - time_since_last
                logger.info(f"Rate limiting: waiting {wait_time:.1f}s")
                await asyncio.sleep(wait_time)
        
        self._last_request_time = datetime.utcnow()
    
    async def get_imports(
        self,
        commodity_code: str,
        year: int = 2023,
        partner: str = "0"
    ) -> Dict:
        """
        Get Qatar import data
        
        Args:
            commodity_code: HS code (e.g., "02" for meat)
            year: Year (default: 2023)
            partner: Partner country code (0 = all partners)
        """
        await self._rate_limit_check()
        
        params = {
            "reporterCode": self.QATAR_CODE,
            "period": year,
            "partnerCode": partner,
            "flowCode": "M",  # M = imports
            "cmdCode": commodity_code
        }
        
        url = f"{self.BASE_URL}/get/C/A/HS"
        
        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            return await response.json()
            
        except httpx.HTTPError as e:
            logger.error(f"UN Comtrade API request failed: {e}")
            raise
    
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
