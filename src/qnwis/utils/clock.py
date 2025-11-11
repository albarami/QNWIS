"""
Deterministic clock utilities for FastAPI handlers.

Provides pluggable time sources so tests can inject fixed timestamps
while production defaults to UTC now + ``time.perf_counter``.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

NowCallable = Callable[[], datetime]
PerfCallable = Callable[[], float]


class Clock:
    """Lightweight clock abstraction with injectable sources."""

    def __init__(
        self,
        now: NowCallable | None = None,
        perf_counter: PerfCallable | None = None,
    ) -> None:
        self._now = now or (lambda: datetime.now(UTC))
        self._perf_counter = perf_counter or time.perf_counter

    def now(self) -> datetime:
        """Return current UTC timestamp."""
        return self._now()

    def iso(self) -> str:
        """Return ISO 8601 timestamp."""
        return self.now().isoformat()

    def utcnow(self) -> str:
        """Return ISO 8601 timestamp with UTC suffix."""
        iso_value = self.iso()
        if iso_value.endswith("+00:00"):
            return iso_value[:-6] + "Z"
        return iso_value

    def now_iso(self) -> str:
        """Return ISO 8601 timestamp (alias for iso)."""
        return self.iso()

    def time(self) -> float:
        """Return monotonic time seconds precision."""
        return self._perf_counter()

    def ms(self) -> int:
        """Return monotonic time in milliseconds (rounded down)."""
        return int(self.time() * 1000)


class ManualClock(Clock):
    """Test clock with manual time advancement."""

    def __init__(
        self,
        start: datetime | None = None,
    ) -> None:
        self._current = start or datetime.now(UTC)
        self._perf_value = 0.0
        super().__init__(now=lambda: self._current, perf_counter=lambda: self._perf_value)

    def advance(self, seconds: float = 1.0) -> None:
        """Advance clock time by given seconds."""
        self._current = self._current + timedelta(seconds=seconds)
        self._perf_value += seconds


__all__ = ["Clock", "ManualClock"]
