"""
Rate limiting middleware for QNWIS API.

Protects against abuse and helps control costs by limiting the number of
requests per user/IP address.

Features:
- In-memory rate limiting for single-instance deployments
- Redis-backed rate limiting for multi-instance deployments
- Configurable limits per endpoint
- Rate limit headers in responses
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from typing import Callable, Optional

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)


def get_rate_limit_key(request: Request) -> str:
    """
    Get rate limit key from request.
    
    Uses IP address by default, but can be extended to use:
    - API key
    - User ID
    - Session token
    
    Args:
        request: FastAPI request object
        
    Returns:
        Rate limit key string
    """
    # Try to get API key from header
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return f"api_key:{api_key}"
    
    # Try to get user ID from auth (if available)
    user_id = getattr(request.state, "user_id", None)
    if user_id:
        return f"user:{user_id}"
    
    # Fall back to IP address
    return f"ip:{get_remote_address(request)}"


# Initialize limiter with custom key function
limiter = Limiter(
    key_func=get_rate_limit_key,
    default_limits=["100/hour"],  # Default: 100 requests per hour
    storage_uri="memory://",  # Use in-memory storage (can be changed to Redis)
)


class RedisRateLimiter:
    """
    Redis-backed rate limiter for distributed deployments.
    
    Use this when running multiple QNWIS instances behind a load balancer.
    Provides centralized rate limiting across all instances.
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        """
        Initialize Redis rate limiter.
        
        Args:
            redis_url: Redis connection URL
        """
        try:
            import redis
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            self.enabled = True
            logger.info(f"Redis rate limiter initialized: {redis_url}")
        except ImportError:
            logger.warning(
                "redis package not installed. "
                "Install with: pip install redis"
            )
            self.enabled = False
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.enabled = False
    
    async def check_limit(
        self,
        key: str,
        limit: int,
        window_seconds: int
    ) -> tuple[bool, int, int]:
        """
        Check if request is within rate limit.
        
        Args:
            key: Rate limit key (user ID, IP, etc.)
            limit: Maximum requests allowed in window
            window_seconds: Time window in seconds
            
        Returns:
            Tuple of (is_allowed, current_count, retry_after_seconds)
        """
        if not self.enabled:
            return True, 0, 0
        
        try:
            # Use Redis key with window timestamp
            window_key = f"rate_limit:{key}:{int(time.time() // window_seconds)}"
            
            # Get current count
            current = self.redis_client.get(window_key)
            
            if current is None:
                # First request in window
                pipe = self.redis_client.pipeline()
                pipe.set(window_key, 1)
                pipe.expire(window_key, window_seconds)
                pipe.execute()
                return True, 1, 0
            
            current_count = int(current)
            
            if current_count >= limit:
                # Rate limit exceeded
                ttl = self.redis_client.ttl(window_key)
                retry_after = max(ttl, 0)
                return False, current_count, retry_after
            
            # Increment counter
            new_count = self.redis_client.incr(window_key)
            return True, new_count, 0
            
        except Exception as e:
            logger.error(f"Redis rate limit check failed: {e}")
            # Fail open: allow request if Redis is down
            return True, 0, 0
    
    async def reset_limit(self, key: str) -> None:
        """
        Reset rate limit for a specific key.
        
        Args:
            key: Rate limit key to reset
        """
        if not self.enabled:
            return
        
        try:
            # Delete all keys matching pattern
            pattern = f"rate_limit:{key}:*"
            keys = self.redis_client.keys(pattern)
            if keys:
                self.redis_client.delete(*keys)
                logger.info(f"Reset rate limit for key: {key}")
        except Exception as e:
            logger.error(f"Failed to reset rate limit: {e}")


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """
    Custom handler for rate limit exceeded errors.
    
    Returns a JSON response with rate limit information.
    
    Args:
        request: FastAPI request
        exc: RateLimitExceeded exception
        
    Returns:
        JSON response with 429 status code
    """
    logger.warning(
        f"Rate limit exceeded for {get_rate_limit_key(request)}: {exc.detail}"
    )
    
    return JSONResponse(
        status_code=429,
        content={
            "error": "rate_limit_exceeded",
            "message": "Too many requests. Please try again later.",
            "detail": str(exc.detail),
            "retry_after": getattr(exc, "retry_after", 60),
        },
        headers={
            "Retry-After": str(getattr(exc, "retry_after", 60)),
            "X-RateLimit-Limit": str(getattr(exc, "limit", "unknown")),
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": str(int(time.time()) + getattr(exc, "retry_after", 60)),
        },
    )


def add_rate_limit_headers(
    response: Response,
    limit: int,
    remaining: int,
    reset_time: int
) -> Response:
    """
    Add rate limit headers to response.
    
    Args:
        response: FastAPI response object
        limit: Rate limit (max requests)
        remaining: Remaining requests in window
        reset_time: Unix timestamp when limit resets
        
    Returns:
        Response with added headers
    """
    response.headers["X-RateLimit-Limit"] = str(limit)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    response.headers["X-RateLimit-Reset"] = str(reset_time)
    return response


# Global Redis rate limiter instance (optional)
redis_limiter: Optional[RedisRateLimiter] = None


def init_redis_rate_limiter(redis_url: str) -> RedisRateLimiter:
    """
    Initialize global Redis rate limiter.
    
    Args:
        redis_url: Redis connection URL
        
    Returns:
        RedisRateLimiter instance
    """
    global redis_limiter
    redis_limiter = RedisRateLimiter(redis_url)
    return redis_limiter


def get_redis_limiter() -> Optional[RedisRateLimiter]:
    """
    Get global Redis rate limiter instance.
    
    Returns:
        RedisRateLimiter instance or None if not initialized
    """
    return redis_limiter
