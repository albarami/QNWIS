"""
Timing instrumentation helpers for QNWIS.

Provides correct wall-clock timestamps (UTC) and performance counter durations.
Prevents epoch/timezone mistakes in audit trails.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from time import perf_counter


@dataclass
class Stopwatch:
    """
    Stopwatch for measuring elapsed time with correct timestamps.
    
    Uses:
    - datetime.now(timezone.utc) for wall-clock timestamps (audit trail)
    - perf_counter() for accurate duration measurement
    
    Example:
        >>> sw = Stopwatch.start()
        >>> # ... do work ...
        >>> elapsed_ms, finished_at = sw.stop_ms()
        >>> print(f"Took {elapsed_ms:.2f}ms, finished at {finished_at}")
    """
    started_at_utc: datetime
    _t0: float  # perf_counter() value at start

    @classmethod
    def start(cls) -> "Stopwatch":
        """
        Start a new stopwatch.
        
        Returns:
            Stopwatch instance with current UTC time and perf_counter
        """
        return cls(
            started_at_utc=datetime.now(timezone.utc),
            _t0=perf_counter()
        )

    def stop_ms(self) -> tuple[float, datetime]:
        """
        Stop the stopwatch and return elapsed time + finish timestamp.
        
        Returns:
            Tuple of (elapsed_milliseconds, finished_at_utc)
        """
        elapsed_ms = (perf_counter() - self._t0) * 1000.0
        finished_at_utc = datetime.now(timezone.utc)
        return elapsed_ms, finished_at_utc

    def elapsed_ms(self) -> float:
        """
        Get elapsed time without stopping the stopwatch.
        
        Returns:
            Elapsed milliseconds since start
        """
        return (perf_counter() - self._t0) * 1000.0

    def lap_ms(self) -> float:
        """
        Record a lap time and reset the internal counter.
        
        Returns:
            Elapsed milliseconds since last lap (or start)
        """
        now = perf_counter()
        elapsed = (now - self._t0) * 1000.0
        self._t0 = now
        return elapsed
