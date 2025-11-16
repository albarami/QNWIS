"""Observability infrastructure (health, metrics, logging) for QNWIS API."""

from .health import HealthCheck, HealthStatus, check_health
from .logging import configure_logging, get_logger, mask_sensitive_data
from .metrics import (
    MetricsCollector,
    get_metrics_collector,
    record_agent_execution,
    record_auth_attempt,
    record_cache_hit,
    record_llm_call,
    record_query_execution,
    record_rate_limit_event,
    record_request,
)

__all__ = [
    "HealthCheck",
    "HealthStatus",
    "check_health",
    "configure_logging",
    "get_logger",
    "mask_sensitive_data",
    "MetricsCollector",
    "get_metrics_collector",
    "record_request",
    "record_agent_execution",
    "record_cache_hit",
    "record_auth_attempt",
    "record_rate_limit_event",
    "record_llm_call",
    "record_query_execution",
]
