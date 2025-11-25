"""
Rate Limiter and Checkpoint Manager for Bulk Data Ingestion.

Provides:
- Rate limiting for API calls (requests per minute/day)
- Checkpoint management for resumable ingestion
- Exponential backoff for retries

Used by ADP, ESCWA, and other connectors with large datasets.
"""

import asyncio
import json
import time
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Rate limiter for API requests.
    
    Supports:
    - Requests per minute (RPM) limiting
    - Requests per day (RPD) limiting
    - Automatic waiting when limits are approached
    """
    
    def __init__(
        self,
        requests_per_minute: int = 60,
        requests_per_day: int = 10000,
        burst_size: int = 10
    ):
        """
        Initialize rate limiter.
        
        Args:
            requests_per_minute: Max requests per minute
            requests_per_day: Max requests per day
            burst_size: Max requests in quick succession
        """
        self.rpm = requests_per_minute
        self.rpd = requests_per_day
        self.burst_size = burst_size
        
        self.minute_window: list[float] = []
        self.day_count = 0
        self.day_start = time.time()
        self._lock = asyncio.Lock()
    
    async def wait_if_needed(self) -> float:
        """
        Wait if rate limit is being approached.
        
        Returns:
            Seconds waited (0 if no wait needed)
        """
        async with self._lock:
            now = time.time()
            
            # Reset daily counter if new day
            if now - self.day_start > 86400:  # 24 hours
                self.day_count = 0
                self.day_start = now
            
            # Check daily limit
            if self.day_count >= self.rpd:
                wait_time = 86400 - (now - self.day_start) + 1
                logger.warning(f"Daily rate limit reached. Waiting {wait_time:.0f}s until reset.")
                await asyncio.sleep(wait_time)
                self.day_count = 0
                self.day_start = time.time()
                return wait_time
            
            # Clean old entries from minute window
            self.minute_window = [t for t in self.minute_window if now - t < 60]
            
            # Check minute limit
            if len(self.minute_window) >= self.rpm:
                oldest = min(self.minute_window)
                wait_time = 60 - (now - oldest) + 0.1
                if wait_time > 0:
                    logger.debug(f"Minute rate limit approached. Waiting {wait_time:.1f}s")
                    await asyncio.sleep(wait_time)
                    self.minute_window = [t for t in self.minute_window if time.time() - t < 60]
                    return wait_time
            
            # Record this request
            self.minute_window.append(time.time())
            self.day_count += 1
            
            return 0.0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current rate limiter statistics."""
        now = time.time()
        return {
            "requests_last_minute": len([t for t in self.minute_window if now - t < 60]),
            "requests_today": self.day_count,
            "rpm_limit": self.rpm,
            "rpd_limit": self.rpd,
            "seconds_until_day_reset": max(0, 86400 - (now - self.day_start))
        }


class ExponentialBackoff:
    """
    Exponential backoff retry strategy for failed requests.
    """
    
    def __init__(
        self,
        max_retries: int = 5,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0
    ):
        """
        Initialize backoff strategy.
        
        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Initial delay in seconds
            max_delay: Maximum delay between retries
            exponential_base: Base for exponential growth
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
    
    def get_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt number."""
        delay = self.base_delay * (self.exponential_base ** attempt)
        return min(delay, self.max_delay)
    
    async def wait(self, attempt: int) -> float:
        """Wait for the backoff delay."""
        delay = self.get_delay(attempt)
        logger.debug(f"Backoff attempt {attempt + 1}/{self.max_retries}, waiting {delay:.1f}s")
        await asyncio.sleep(delay)
        return delay


class CheckpointManager:
    """
    Checkpoint manager for resumable data ingestion.
    
    Saves progress to disk so ingestion can resume after failures.
    """
    
    def __init__(self, checkpoint_dir: str = "data/checkpoints"):
        """
        Initialize checkpoint manager.
        
        Args:
            checkpoint_dir: Directory to store checkpoint files
        """
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_checkpoint_path(self, domain: str, source: str = "adp") -> Path:
        """Get path for checkpoint file."""
        safe_domain = domain.lower().replace(" ", "_").replace("/", "_")
        return self.checkpoint_dir / f"{source}_{safe_domain}_checkpoint.json"
    
    def save_checkpoint(
        self,
        domain: str,
        current_index: int,
        total_items: int,
        source: str = "adp",
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Save checkpoint to disk.
        
        Args:
            domain: Domain being ingested (e.g., "Labor", "Health")
            current_index: Current item index (0-based)
            total_items: Total number of items to process
            source: Data source name
            metadata: Additional metadata to save
        """
        checkpoint = {
            "domain": domain,
            "source": source,
            "current_index": current_index,
            "total_items": total_items,
            "progress_percent": round((current_index / max(total_items, 1)) * 100, 2),
            "last_updated": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        }
        
        path = self._get_checkpoint_path(domain, source)
        with open(path, 'w') as f:
            json.dump(checkpoint, f, indent=2)
        
        logger.debug(f"Checkpoint saved: {domain} at index {current_index}/{total_items}")
    
    def load_checkpoint(self, domain: str, source: str = "adp") -> Optional[Dict[str, Any]]:
        """
        Load checkpoint from disk.
        
        Args:
            domain: Domain to load checkpoint for
            source: Data source name
            
        Returns:
            Checkpoint dict if exists, None otherwise
        """
        path = self._get_checkpoint_path(domain, source)
        
        if not path.exists():
            return None
        
        try:
            with open(path, 'r') as f:
                checkpoint = json.load(f)
            
            logger.info(f"Loaded checkpoint: {domain} at index {checkpoint['current_index']}")
            return checkpoint
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to load checkpoint for {domain}: {e}")
            return None
    
    def get_resume_index(self, domain: str, source: str = "adp") -> int:
        """
        Get the index to resume from.
        
        Args:
            domain: Domain being ingested
            source: Data source name
            
        Returns:
            Index to resume from (0 if no checkpoint)
        """
        checkpoint = self.load_checkpoint(domain, source)
        if checkpoint:
            return checkpoint["current_index"]
        return 0
    
    def clear_checkpoint(self, domain: str, source: str = "adp") -> bool:
        """
        Clear checkpoint after successful completion.
        
        Args:
            domain: Domain to clear checkpoint for
            source: Data source name
            
        Returns:
            True if cleared, False if not found
        """
        path = self._get_checkpoint_path(domain, source)
        
        if path.exists():
            path.unlink()
            logger.info(f"Checkpoint cleared: {domain}")
            return True
        return False
    
    def list_checkpoints(self) -> list[Dict[str, Any]]:
        """List all saved checkpoints."""
        checkpoints = []
        
        for path in self.checkpoint_dir.glob("*_checkpoint.json"):
            try:
                with open(path, 'r') as f:
                    checkpoint = json.load(f)
                checkpoints.append(checkpoint)
            except (json.JSONDecodeError, KeyError):
                continue
        
        return checkpoints


class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded and cannot wait."""
    
    def __init__(self, message: str, retry_after: Optional[float] = None):
        super().__init__(message)
        self.retry_after = retry_after


# Singleton instances for shared use
_rate_limiter: Optional[RateLimiter] = None
_checkpoint_manager: Optional[CheckpointManager] = None


def get_rate_limiter(
    requests_per_minute: int = 60,
    requests_per_day: int = 10000
) -> RateLimiter:
    """Get or create shared rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter(requests_per_minute, requests_per_day)
    return _rate_limiter


def get_checkpoint_manager(checkpoint_dir: str = "data/checkpoints") -> CheckpointManager:
    """Get or create shared checkpoint manager instance."""
    global _checkpoint_manager
    if _checkpoint_manager is None:
        _checkpoint_manager = CheckpointManager(checkpoint_dir)
    return _checkpoint_manager

