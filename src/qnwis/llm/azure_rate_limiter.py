"""
Azure OpenAI Rate Limiter with Monitoring.

Azure OpenAI has different rate limits than other providers:
- Tokens Per Minute (TPM) limits
- Requests Per Minute (RPM) limits
- Different limits per deployment/model

This module provides:
- Token and request tracking
- Exponential backoff for 429 errors
- Prometheus metrics for monitoring
- Automatic throttling to stay under limits
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


@dataclass
class AzureRateLimitConfig:
    """Configuration for Azure OpenAI rate limits."""
    
    # Default limits (adjust based on your Azure deployment)
    tokens_per_minute: int = 120000  # TPM limit
    requests_per_minute: int = 720   # RPM limit
    
    # Backoff configuration
    initial_backoff_seconds: float = 1.0
    max_backoff_seconds: float = 60.0
    backoff_multiplier: float = 2.0
    
    # Safety margin (use only X% of limit to avoid hitting it)
    safety_margin: float = 0.8


@dataclass
class RateLimitMetrics:
    """Metrics for rate limit monitoring."""
    
    total_requests: int = 0
    total_tokens: int = 0
    rate_limit_hits: int = 0
    throttled_requests: int = 0
    total_backoff_time: float = 0.0
    last_reset_time: float = field(default_factory=time.time)
    
    # Per-minute tracking
    requests_this_minute: int = 0
    tokens_this_minute: int = 0


class AzureRateLimiter:
    """
    Rate limiter specifically designed for Azure OpenAI API.
    
    Tracks tokens and requests per minute, implements exponential backoff,
    and provides Prometheus-compatible metrics.
    """
    
    def __init__(
        self,
        config: Optional[AzureRateLimitConfig] = None,
        deployment_name: Optional[str] = None
    ):
        """
        Initialize the rate limiter.
        
        Args:
            config: Rate limit configuration
            deployment_name: Azure deployment name for metrics tagging
        """
        self.config = config or AzureRateLimitConfig()
        self.deployment_name = deployment_name or "default"
        self.metrics = RateLimitMetrics()
        
        # Track requests in sliding window
        self._request_times: deque = deque()
        self._token_counts: deque = deque()
        
        # Backoff state
        self._current_backoff = 0.0
        self._consecutive_429s = 0
        
        # Lock for thread safety
        self._lock = asyncio.Lock()
        
        logger.info(
            "Azure rate limiter initialized (deployment=%s, TPM=%d, RPM=%d)",
            self.deployment_name,
            self.config.tokens_per_minute,
            self.config.requests_per_minute
        )
    
    async def acquire(self, estimated_tokens: int = 1000) -> None:
        """
        Acquire permission to make a request.
        
        Waits if necessary to stay under rate limits.
        
        Args:
            estimated_tokens: Estimated tokens for this request
        """
        async with self._lock:
            # Clean up old entries (older than 1 minute)
            self._cleanup_sliding_window()
            
            # Check if we need to wait
            wait_time = self._calculate_wait_time(estimated_tokens)
            
            if wait_time > 0:
                self.metrics.throttled_requests += 1
                logger.warning(
                    "Rate limit throttling: waiting %.2fs (deployment=%s, "
                    "requests_this_min=%d, tokens_this_min=%d)",
                    wait_time,
                    self.deployment_name,
                    len(self._request_times),
                    sum(self._token_counts)
                )
                await asyncio.sleep(wait_time)
            
            # Add backoff if we recently hit 429
            if self._current_backoff > 0:
                logger.info(
                    "Applying backoff: %.2fs (consecutive_429s=%d)",
                    self._current_backoff,
                    self._consecutive_429s
                )
                self.metrics.total_backoff_time += self._current_backoff
                await asyncio.sleep(self._current_backoff)
            
            # Record this request
            now = time.time()
            self._request_times.append(now)
            self._token_counts.append(estimated_tokens)
            
            self.metrics.total_requests += 1
            self.metrics.requests_this_minute = len(self._request_times)
            self.metrics.tokens_this_minute = sum(self._token_counts)
    
    def record_success(self, actual_tokens: int) -> None:
        """
        Record a successful request.
        
        Resets backoff and updates token count.
        
        Args:
            actual_tokens: Actual tokens used
        """
        self._consecutive_429s = 0
        self._current_backoff = 0.0
        self.metrics.total_tokens += actual_tokens
        
        # Update the last token count with actual value
        if self._token_counts:
            self._token_counts[-1] = actual_tokens
    
    def record_rate_limit_error(self, retry_after: Optional[float] = None) -> float:
        """
        Record a 429 rate limit error.
        
        Calculates and returns the backoff time.
        
        Args:
            retry_after: Retry-After header value from Azure (seconds)
            
        Returns:
            Backoff time in seconds
        """
        self._consecutive_429s += 1
        self.metrics.rate_limit_hits += 1
        
        # Use retry-after if provided, otherwise calculate exponential backoff
        if retry_after:
            self._current_backoff = retry_after
        else:
            self._current_backoff = min(
                self.config.initial_backoff_seconds * (
                    self.config.backoff_multiplier ** self._consecutive_429s
                ),
                self.config.max_backoff_seconds
            )
        
        logger.warning(
            "Rate limit hit (429): backoff=%.2fs, consecutive=%d, deployment=%s",
            self._current_backoff,
            self._consecutive_429s,
            self.deployment_name
        )
        
        return self._current_backoff
    
    def _cleanup_sliding_window(self) -> None:
        """Remove entries older than 1 minute from sliding window."""
        now = time.time()
        cutoff = now - 60.0
        
        while self._request_times and self._request_times[0] < cutoff:
            self._request_times.popleft()
            self._token_counts.popleft()
    
    def _calculate_wait_time(self, estimated_tokens: int) -> float:
        """
        Calculate how long to wait before making a request.
        
        Args:
            estimated_tokens: Estimated tokens for the request
            
        Returns:
            Wait time in seconds (0 if no wait needed)
        """
        # Check RPM limit
        effective_rpm = int(self.config.requests_per_minute * self.config.safety_margin)
        if len(self._request_times) >= effective_rpm:
            # Wait until oldest request falls out of window
            oldest = self._request_times[0]
            wait_for_rpm = (oldest + 60.0) - time.time()
            if wait_for_rpm > 0:
                return wait_for_rpm
        
        # Check TPM limit
        effective_tpm = int(self.config.tokens_per_minute * self.config.safety_margin)
        current_tokens = sum(self._token_counts)
        if current_tokens + estimated_tokens >= effective_tpm:
            # Wait until enough tokens fall out of window
            oldest = self._request_times[0] if self._request_times else time.time()
            wait_for_tpm = (oldest + 60.0) - time.time()
            if wait_for_tpm > 0:
                return wait_for_tpm
        
        return 0.0
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get current metrics for monitoring.
        
        Returns Prometheus-compatible metrics dictionary.
        """
        return {
            "deployment": self.deployment_name,
            "total_requests": self.metrics.total_requests,
            "total_tokens": self.metrics.total_tokens,
            "rate_limit_hits": self.metrics.rate_limit_hits,
            "throttled_requests": self.metrics.throttled_requests,
            "total_backoff_time_seconds": self.metrics.total_backoff_time,
            "requests_this_minute": len(self._request_times),
            "tokens_this_minute": sum(self._token_counts),
            "current_backoff_seconds": self._current_backoff,
            "consecutive_429s": self._consecutive_429s,
            "config": {
                "tpm_limit": self.config.tokens_per_minute,
                "rpm_limit": self.config.requests_per_minute,
                "safety_margin": self.config.safety_margin,
            }
        }
    
    def reset_metrics(self) -> None:
        """Reset all metrics (useful for testing or periodic resets)."""
        self.metrics = RateLimitMetrics()
        self._request_times.clear()
        self._token_counts.clear()
        self._current_backoff = 0.0
        self._consecutive_429s = 0
        logger.info("Rate limiter metrics reset (deployment=%s)", self.deployment_name)


# Global rate limiter instances per deployment
_rate_limiters: Dict[str, AzureRateLimiter] = {}


def get_azure_rate_limiter(
    deployment_name: str,
    config: Optional[AzureRateLimitConfig] = None
) -> AzureRateLimiter:
    """
    Get or create a rate limiter for an Azure deployment.
    
    Rate limiters are cached per deployment name.
    
    Args:
        deployment_name: Azure OpenAI deployment name
        config: Optional custom configuration
        
    Returns:
        AzureRateLimiter instance
    """
    if deployment_name not in _rate_limiters:
        _rate_limiters[deployment_name] = AzureRateLimiter(
            config=config,
            deployment_name=deployment_name
        )
    return _rate_limiters[deployment_name]


def get_all_rate_limiter_metrics() -> Dict[str, Dict[str, Any]]:
    """
    Get metrics from all active rate limiters.
    
    Returns:
        Dictionary mapping deployment names to their metrics
    """
    return {
        name: limiter.get_metrics()
        for name, limiter in _rate_limiters.items()
    }


__all__ = [
    "AzureRateLimitConfig",
    "AzureRateLimiter",
    "get_azure_rate_limiter",
    "get_all_rate_limiter_metrics",
]

