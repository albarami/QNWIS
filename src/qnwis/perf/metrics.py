"""
Prometheus metrics collection for QNWIS performance monitoring.

Exposes HTTP request/response metrics, database latency, cache hit ratios,
and custom operation timings via /metrics endpoint.
"""

from __future__ import annotations

from fastapi import APIRouter, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Histogram,
    generate_latest,
)

# HTTP request metrics
REQUESTS = Counter(
    "qnwis_requests_total",
    "Total HTTP requests",
    ["route", "method", "status"],
)

# HTTP latency distribution
LATENCY = Histogram(
    "qnwis_latency_seconds",
    "HTTP request latency in seconds",
    ["route", "method"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 90.0),
)

# Database operation latency
DB_LATENCY = Histogram(
    "qnwis_db_latency_seconds",
    "Database operation latency in seconds",
    ["operation"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)

# Cache hit/miss counters
CACHE_HIT = Counter(
    "qnwis_cache_hits_total",
    "Total cache hits",
    ["region"],
)

CACHE_MISS = Counter(
    "qnwis_cache_misses_total",
    "Total cache misses",
    ["region"],
)

# Agent execution metrics
AGENT_LATENCY = Histogram(
    "qnwis_agent_latency_seconds",
    "Agent execution latency in seconds",
    ["agent_name"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
)

# Orchestration stage metrics
STAGE_LATENCY = Histogram(
    "qnwis_stage_latency_seconds",
    "Orchestration stage latency in seconds",
    ["stage"],
    buckets=(0.01, 0.025, 0.04, 0.05, 0.06, 0.1, 0.25, 0.5, 1.0, 2.5),
)


def router() -> APIRouter:
    """
    Create FastAPI router with /metrics endpoint.
    
    Returns:
        APIRouter with Prometheus metrics endpoint
        
    Example:
        >>> from fastapi import FastAPI
        >>> app = FastAPI()
        >>> app.include_router(router())
    """
    r = APIRouter()

    @r.get("/metrics")
    def metrics() -> Response:
        """
        Expose Prometheus metrics in text format.
        
        Returns:
            Response with metrics in Prometheus exposition format
        """
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    return r
