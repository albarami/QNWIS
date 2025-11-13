"""
UI metrics and telemetry for QNWIS Chainlit application.

Provides Prometheus-backed metrics with safe no-op fallback when
prometheus_client is not installed. Tracks requests, tokens, stage
latencies, and errors for operational visibility.
"""

from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from typing import Iterator

logger = logging.getLogger(__name__)

# Try to import Prometheus client, fall back to no-op if unavailable
try:
    from prometheus_client import Counter, Histogram

    PROM_AVAILABLE = True
except ImportError:
    PROM_AVAILABLE = False
    logger.info("prometheus_client not available, metrics will be no-op")


# Initialize metrics if Prometheus is available
if PROM_AVAILABLE:
    REQUESTS_COUNTER = Counter(
        "qnwis_ui_requests_total",
        "Total number of questions processed by UI",
    )
    TOKENS_COUNTER = Counter(
        "qnwis_ui_tokens_streamed_total",
        "Total number of tokens streamed to UI",
    )
    STAGE_LATENCY_HISTOGRAM = Histogram(
        "qnwis_ui_stage_latency_ms",
        "Stage completion latency in milliseconds",
        buckets=[10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000],
    )
    ERRORS_COUNTER = Counter(
        "qnwis_ui_stream_errors_total",
        "Total number of streaming errors encountered",
    )
else:
    # No-op placeholders
    REQUESTS_COUNTER = None
    TOKENS_COUNTER = None
    STAGE_LATENCY_HISTOGRAM = None
    ERRORS_COUNTER = None


def inc_requests() -> None:
    """
    Increment request counter.

    Called when a new question is submitted to the UI.
    """
    if REQUESTS_COUNTER:
        REQUESTS_COUNTER.inc()


def inc_tokens(n: int = 1) -> None:
    """
    Increment token counter.

    Args:
        n: Number of tokens to add (default: 1)
    """
    if TOKENS_COUNTER:
        TOKENS_COUNTER.inc(n)


def inc_errors() -> None:
    """
    Increment error counter.

    Called when a streaming error occurs (network, parse, etc.).
    """
    if ERRORS_COUNTER:
        ERRORS_COUNTER.inc()


def observe_stage_latency(latency_ms: float) -> None:
    """
    Record stage latency observation.

    Args:
        latency_ms: Stage latency in milliseconds
    """
    if STAGE_LATENCY_HISTOGRAM:
        STAGE_LATENCY_HISTOGRAM.observe(latency_ms)


@contextmanager
def stage_timer() -> Iterator[None]:
    """
    Context manager for timing stage durations.

    Automatically observes latency when context exits.

    Example:
        ```python
        with stage_timer():
            # ... stage processing ...
            await render_stage("classify", 123.0)
        ```
    """
    start = time.perf_counter()
    try:
        yield
    finally:
        duration_ms = (time.perf_counter() - start) * 1000.0
        observe_stage_latency(duration_ms)


def get_metrics_available() -> bool:
    """
    Check if Prometheus metrics are available.

    Returns:
        True if prometheus_client is installed and metrics are active
    """
    return PROM_AVAILABLE
