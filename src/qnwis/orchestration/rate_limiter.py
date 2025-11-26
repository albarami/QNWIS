"""
Rate limiter for Claude API calls.

CRITICAL: This must wrap INDIVIDUAL LLM calls, not entire workflows.
Prevents 429 errors by enforcing API rate limits.
"""

import asyncio
import time
import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)


class RateLimitedExecutor:
    """
    Rate limiter for API calls.
    
    Enforces maximum requests per minute to prevent 429 errors from Claude API.
    Uses semaphore + time-based tracking for rate limiting.
    """
    
    def __init__(self, max_requests_per_minute: int = 50):
        """
        Initialize rate limiter.
        
        Args:
            max_requests_per_minute: Maximum API requests allowed per minute.
                                     Default 50 for standard Claude API tier.
        """
        self.max_requests_per_minute = max_requests_per_minute
        self.semaphore = asyncio.Semaphore(20)  # Conservative concurrent limit
        self.request_times = []
        logger.info(f"Rate limiter initialized: {max_requests_per_minute} req/min limit")
    
    async def execute_with_rate_limit(
        self, 
        func: Callable, 
        *args: Any, 
        **kwargs: Any
    ) -> Any:
        """
        Execute a function with rate limiting.
        
        This wraps individual LLM calls (llm.ainvoke), NOT entire workflows.
        
        Args:
            func: Async function to execute (e.g., llm.ainvoke)
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func
            
        Returns:
            Result from func execution
        """
        async with self.semaphore:
            await self._enforce_rate_limit()
            return await func(*args, **kwargs)
    
    async def _enforce_rate_limit(self):
        """
        Enforce rate limit by sleeping if necessary.
        
        Tracks request times in a sliding window and sleeps if we're
        about to exceed the rate limit.
        """
        now = time.time()
        
        # Remove requests older than 60 seconds (sliding window)
        self.request_times = [t for t in self.request_times if now - t < 60]
        
        # Check if we need to wait
        if len(self.request_times) >= self.max_requests_per_minute:
            # Calculate sleep time to stay under limit
            oldest_request = self.request_times[0]
            sleep_time = 60 - (now - oldest_request) + 0.1  # +0.1s buffer
            
            logger.info(
                f"Rate limit: {len(self.request_times)}/{self.max_requests_per_minute} "
                f"requests in last 60s. Sleeping {sleep_time:.2f}s..."
            )
            await asyncio.sleep(sleep_time)
        
        # Record this request
        self.request_times.append(time.time())


# Global singleton instance
_global_rate_limiter = None


def get_rate_limiter() -> RateLimitedExecutor:
    """
    Get singleton rate limiter instance.
    
    All LLM calls should use the same rate limiter instance to properly
    track total requests across all parallel scenarios.
    
    Returns:
        Shared RateLimitedExecutor instance
    """
    global _global_rate_limiter
    if _global_rate_limiter is None:
        _global_rate_limiter = RateLimitedExecutor(max_requests_per_minute=50)
    return _global_rate_limiter

