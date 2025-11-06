"""
Lightweight observability primitives for the orchestration workflow.

The orchestration graph emits coarse-grained counters and timers through this
interface. Production deployments can supply a real observer that forwards the
signals to Prometheus, StatsD, etc. Tests and local runs use the no-op observer
defined here so instrumentation never becomes a hard dependency.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Protocol


class MetricsObserver(Protocol):
    """
    Minimal observer protocol used by orchestration nodes.

    Implementations must be side-effect free when metrics emission fails.
    """

    def increment(self, name: str, *, tags: Mapping[str, str] | None = None) -> None:
        """Increment a counter identified by ``name``."""

    def timing(
        self,
        name: str,
        value_ms: float,
        *,
        tags: Mapping[str, str] | None = None,
    ) -> None:
        """Record a timing sample in milliseconds."""


@dataclass(slots=True)
class NullMetricsObserver:
    """Default observer that quietly ignores all metric calls."""

    def increment(self, name: str, *, tags: Mapping[str, str] | None = None) -> None:
        """No-op counter increment."""

    def timing(
        self,
        name: str,
        value_ms: float,
        *,
        tags: Mapping[str, str] | None = None,
    ) -> None:
        """No-op timer sample."""


def ensure_observer(observer: MetricsObserver | None) -> MetricsObserver:
    """
    Return ``observer`` if provided, otherwise a :class:`NullMetricsObserver`.

    Args:
        observer: Optional custom observer.

    Returns:
        MetricsObserver guaranteed to be non-None.
    """
    return observer if observer is not None else NullMetricsObserver()
