"""
Lightweight timing and profiling utilities for QNWIS.

Provides context manager and decorator for measuring execution time
without heavy dependencies or overhead.
"""

from __future__ import annotations

import functools
import logging
import time
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


class Timer:
    """
    Context manager to measure wall time in seconds.
    
    Example:
        >>> def sink(name, duration, extra):
        ...     print(f"{name}: {duration:.3f}s")
        >>> with Timer(sink, "db_query", {"query_id": "salary_stats"}):
        ...     # expensive operation
        ...     pass
    """

    def __init__(
        self,
        sink: Callable[[str, float, Dict[str, Any]], None],
        name: str,
        extra: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize timer with callback sink.
        
        Args:
            sink: Callback function(name, duration_seconds, extra_dict)
            name: Operation name for logging
            extra: Additional context to pass to sink
        """
        self.sink = sink
        self.name = name
        self.extra = extra or {}
        self.start: float = 0.0
        self.duration: float = 0.0

    def __enter__(self) -> Timer:
        """Start timing."""
        self.start = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Stop timing and invoke sink."""
        self.duration = time.perf_counter() - self.start
        try:
            self.sink(self.name, self.duration, self.extra)
        except Exception as e:
            logger.warning(f"Timer sink failed for {self.name}: {e}")


def timeit(
    name: str, extra: Optional[Dict[str, Any]] = None
) -> Callable[[Callable], Callable]:
    """
    Decorator that records execution time via Timer sink.
    
    Uses default logging sink that writes to logger.info.
    
    Example:
        >>> @timeit("fetch_data", {"source": "csv"})
        ... def fetch():
        ...     return [1, 2, 3]
    
    Args:
        name: Operation name for logging
        extra: Additional context metadata
        
    Returns:
        Decorator function
    """

    def _default_sink(op_name: str, duration: float, ctx: Dict[str, Any]) -> None:
        """Default sink logs to INFO with context."""
        ctx_str = " ".join(f"{k}={v}" for k, v in ctx.items())
        logger.info(f"PERF {op_name} {duration:.3f}s {ctx_str}")

    def _wrap(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def _inner(*args, **kwargs):
            with Timer(_default_sink, name, extra):
                return fn(*args, **kwargs)

        return _inner

    return _wrap
