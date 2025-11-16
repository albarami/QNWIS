"""
Prometheus metrics collection for QNWIS API.

Tracks:
- Request counts by endpoint, status, method
- Request latency histograms
- Agent execution metrics
- Cache hit/miss rates
- Authentication metrics
- Rate limit events
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from typing import Any

logger = logging.getLogger(__name__)


class MetricsCollector:
    """
    In-memory metrics collector compatible with Prometheus exposition format.

    Maintains counters, gauges, and histograms for API operations.
    Can be exposed via /metrics endpoint in Prometheus text format.
    """

    def __init__(self) -> None:
        """Initialize metrics collector."""
        # Counters
        self.request_total = defaultdict(int)  # {(method, endpoint, status): count}
        self.agent_execution_total = defaultdict(int)  # {(agent, status): count}
        self.cache_operations_total = defaultdict(int)  # {(operation, result): count}
        self.auth_attempts_total = defaultdict(int)  # {(method, result): count}
        self.rate_limit_events_total = defaultdict(int)  # {(principal, reason): count}

        # DR/Backup counters
        self.dr_backup_total = defaultdict(int)  # {(tag, status): count}
        self.dr_restore_total = defaultdict(int)  # {(status): count}
        self.dr_verify_failures_total = defaultdict(int)  # {(snapshot_id): count}

        # Continuity/Failover counters
        self.failover_executions_total = defaultdict(int)  # {(cluster, status): count}
        self.failover_success_total = defaultdict(int)  # {(cluster): count}
        self.failover_failures_total = defaultdict(int)  # {(cluster, reason): count}
        
        # LLM usage counters (Phase 2)
        self.llm_calls_total = defaultdict(int)  # {(model, agent, purpose): count}
        self.llm_tokens_total = defaultdict(int)  # {(model, token_type): count}
        self.llm_cost_usd_total = defaultdict(float)  # {(model): cost}
        
        # Query-level counters (Phase 2)
        self.query_executions_total = defaultdict(int)  # {(complexity, status): count}
        self.citation_violations_total = defaultdict(int)  # {(): count}

        # Histograms (simplified - store all observations for percentile calculation)
        self.request_duration_seconds: list[tuple[dict[str, str], float]] = []
        self.agent_execution_duration_seconds: list[tuple[dict[str, str], float]] = []
        self.cache_latency_seconds: list[tuple[dict[str, str], float]] = []
        self.dr_backup_duration_seconds: list[tuple[dict[str, str], float]] = []
        self.dr_restore_duration_seconds: list[tuple[dict[str, str], float]] = []
        self.failover_execution_ms: list[tuple[dict[str, str], float]] = []
        self.failover_validation_ms: list[tuple[dict[str, str], float]] = []
        
        # LLM and Query histograms (Phase 2)
        self.llm_call_latency_ms: list[tuple[dict[str, str], float]] = []
        self.query_latency_ms: list[tuple[dict[str, str], float]] = []

        # Gauges
        self.active_requests = 0
        self.agent_queue_depth = 0
        self.dr_snapshots_total = 0
        self.dr_retained_total = 0
        self.dr_backup_bytes = 0
        self.continuity_nodes_healthy = 0
        self.continuity_quorum_reached = 0

        # Metadata
        self.start_time = time.time()

    def increment_counter(self, metric: str, labels: dict[str, str], value: int = 1) -> None:
        """
        Increment a counter metric.

        Args:
            metric: Metric name
            labels: Label dictionary
            value: Increment value (default: 1)
        """
        key = tuple(sorted(labels.items()))
        if metric == "qnwis_http_requests_total":
            self.request_total[key] += value
        elif metric == "qnwis_agent_executions_total":
            self.agent_execution_total[key] += value
        elif metric == "qnwis_cache_operations_total":
            self.cache_operations_total[key] += value
        elif metric == "qnwis_auth_attempts_total":
            self.auth_attempts_total[key] += value
        elif metric == "qnwis_rate_limit_events_total":
            self.rate_limit_events_total[key] += value
        elif metric == "qnwis_dr_backup_total":
            self.dr_backup_total[key] += value
        elif metric == "qnwis_dr_restore_total":
            self.dr_restore_total[key] += value
        elif metric == "qnwis_dr_verify_failures_total":
            self.dr_verify_failures_total[key] += value
        elif metric == "qnwis_failover_executions_total":
            self.failover_executions_total[key] += value
        elif metric == "qnwis_failover_success_total":
            self.failover_success_total[key] += value
        elif metric == "qnwis_failover_failures_total":
            self.failover_failures_total[key] += value

    def observe_histogram(
        self, metric: str, labels: dict[str, str], value: float
    ) -> None:
        """
        Record a histogram observation.

        Args:
            metric: Metric name
            labels: Label dictionary
            value: Observed value
        """
        if metric == "qnwis_http_request_duration_seconds":
            self.request_duration_seconds.append((labels, value))
        elif metric == "qnwis_agent_execution_duration_seconds":
            self.agent_execution_duration_seconds.append((labels, value))
        elif metric == "qnwis_cache_latency_seconds":
            self.cache_latency_seconds.append((labels, value))
        elif metric == "qnwis_dr_backup_duration_seconds":
            self.dr_backup_duration_seconds.append((labels, value))
        elif metric == "qnwis_dr_restore_duration_seconds":
            self.dr_restore_duration_seconds.append((labels, value))
        elif metric == "qnwis_failover_execution_ms":
            self.failover_execution_ms.append((labels, value))
        elif metric == "qnwis_failover_validation_ms":
            self.failover_validation_ms.append((labels, value))

    def set_gauge(self, metric: str, value: int) -> None:
        """
        Set a gauge metric value.

        Args:
            metric: Metric name
            value: Gauge value
        """
        if metric == "qnwis_active_requests":
            self.active_requests = value
        elif metric == "qnwis_agent_queue_depth":
            self.agent_queue_depth = value
        elif metric == "qnwis_dr_snapshots_total":
            self.dr_snapshots_total = value
        elif metric == "qnwis_dr_retained_total":
            self.dr_retained_total = value
        elif metric == "qnwis_dr_backup_bytes":
            self.dr_backup_bytes = value
        elif metric == "qnwis_continuity_nodes_healthy":
            self.continuity_nodes_healthy = value
        elif metric == "qnwis_continuity_quorum_reached":
            self.continuity_quorum_reached = value

    def increment_gauge(self, metric: str, delta: int = 1) -> None:
        """
        Increment a gauge metric.

        Args:
            metric: Metric name
            delta: Increment value (default: 1)
        """
        if metric == "qnwis_active_requests":
            self.active_requests += delta
        elif metric == "qnwis_agent_queue_depth":
            self.agent_queue_depth += delta

    def _format_labels(self, labels: dict[str, str]) -> str:
        """Format labels for Prometheus text format."""
        if not labels:
            return ""
        items = [f'{k}="{v}"' for k, v in sorted(labels.items())]
        return "{" + ",".join(items) + "}"

    def _calculate_histogram_buckets(
        self, observations: list[float], buckets: list[float]
    ) -> dict[str, int]:
        """Calculate histogram bucket counts."""
        bucket_counts = {str(b): 0 for b in buckets}
        bucket_counts["+Inf"] = 0

        for value in observations:
            for bucket in buckets:
                if value <= bucket:
                    bucket_counts[str(bucket)] += 1
            bucket_counts["+Inf"] += 1

        return bucket_counts

    def export_prometheus_text(self) -> str:
        """
        Export metrics in Prometheus text exposition format.

        Returns:
            Metrics in Prometheus text format
        """
        lines = []

        # Process uptime
        uptime = time.time() - self.start_time
        lines.append("# HELP qnwis_process_uptime_seconds Process uptime in seconds")
        lines.append("# TYPE qnwis_process_uptime_seconds gauge")
        lines.append(f"qnwis_process_uptime_seconds {uptime}")
        lines.append("")

        # HTTP request counter
        lines.append("# HELP qnwis_http_requests_total Total HTTP requests")
        lines.append("# TYPE qnwis_http_requests_total counter")
        for labels, count in self.request_total.items():
            label_dict = dict(labels)
            label_str = self._format_labels(label_dict)
            lines.append(f"qnwis_http_requests_total{label_str} {count}")
        lines.append("")

        # Agent execution counter
        lines.append("# HELP qnwis_agent_executions_total Total agent executions")
        lines.append("# TYPE qnwis_agent_executions_total counter")
        for labels, count in self.agent_execution_total.items():
            label_dict = dict(labels)
            label_str = self._format_labels(label_dict)
            lines.append(f"qnwis_agent_executions_total{label_str} {count}")
        lines.append("")

        # Cache operations counter
        lines.append("# HELP qnwis_cache_operations_total Total cache operations")
        lines.append("# TYPE qnwis_cache_operations_total counter")
        for labels, count in self.cache_operations_total.items():
            label_dict = dict(labels)
            label_str = self._format_labels(label_dict)
            lines.append(f"qnwis_cache_operations_total{label_str} {count}")
        lines.append("")

        # Active requests gauge
        lines.append("# HELP qnwis_active_requests Number of active HTTP requests")
        lines.append("# TYPE qnwis_active_requests gauge")
        lines.append(f"qnwis_active_requests {self.active_requests}")
        lines.append("")

        # DR backup counter
        lines.append("# HELP qnwis_dr_backup_total Total DR backup operations")
        lines.append("# TYPE qnwis_dr_backup_total counter")
        for labels, count in self.dr_backup_total.items():
            label_dict = dict(labels)
            label_str = self._format_labels(label_dict)
            lines.append(f"qnwis_dr_backup_total{label_str} {count}")
        lines.append("")

        # DR restore counter
        lines.append("# HELP qnwis_dr_restore_total Total DR restore operations")
        lines.append("# TYPE qnwis_dr_restore_total counter")
        for labels, count in self.dr_restore_total.items():
            label_dict = dict(labels)
            label_str = self._format_labels(label_dict)
            lines.append(f"qnwis_dr_restore_total{label_str} {count}")
        lines.append("")

        # DR verify failures counter
        lines.append("# HELP qnwis_dr_verify_failures_total Total DR verification failures")
        lines.append("# TYPE qnwis_dr_verify_failures_total counter")
        for labels, count in self.dr_verify_failures_total.items():
            label_dict = dict(labels)
            label_str = self._format_labels(label_dict)
            lines.append(f"qnwis_dr_verify_failures_total{label_str} {count}")
        lines.append("")

        # DR gauges
        lines.append("# HELP qnwis_dr_snapshots_total Total number of DR snapshots")
        lines.append("# TYPE qnwis_dr_snapshots_total gauge")
        lines.append(f"qnwis_dr_snapshots_total {self.dr_snapshots_total}")
        lines.append("")

        lines.append("# HELP qnwis_dr_retained_total Number of retained DR snapshots")
        lines.append("# TYPE qnwis_dr_retained_total gauge")
        lines.append(f"qnwis_dr_retained_total {self.dr_retained_total}")
        lines.append("")

        lines.append("# HELP qnwis_dr_backup_bytes Total bytes in DR backups")
        lines.append("# TYPE qnwis_dr_backup_bytes gauge")
        lines.append(f"qnwis_dr_backup_bytes {self.dr_backup_bytes}")
        lines.append("")

        # HTTP request duration histogram
        lines.append(
            "# HELP qnwis_http_request_duration_seconds HTTP request latency"
        )
        lines.append("# TYPE qnwis_http_request_duration_seconds histogram")
        # Group by labels
        duration_by_labels: dict[tuple, list[float]] = defaultdict(list)
        for labels, value in self.request_duration_seconds:
            key = tuple(sorted(labels.items()))
            duration_by_labels[key].append(value)

        buckets = [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
        for label_key, observations in duration_by_labels.items():
            label_dict = dict(label_key)
            bucket_counts = self._calculate_histogram_buckets(observations, buckets)

            for bucket, count in bucket_counts.items():
                label_str = self._format_labels({**label_dict, "le": bucket})
                lines.append(
                    f"qnwis_http_request_duration_seconds_bucket{label_str} {count}"
                )

            label_str = self._format_labels(label_dict)
            lines.append(
                f"qnwis_http_request_duration_seconds_sum{label_str} {sum(observations)}"
            )
            lines.append(
                f"qnwis_http_request_duration_seconds_count{label_str} {len(observations)}"
            )
        lines.append("")

        # DR backup duration histogram
        lines.append("# HELP qnwis_dr_backup_duration_seconds DR backup operation duration")
        lines.append("# TYPE qnwis_dr_backup_duration_seconds histogram")
        backup_duration_by_labels: dict[tuple, list[float]] = defaultdict(list)
        for labels, value in self.dr_backup_duration_seconds:
            key = tuple(sorted(labels.items()))
            backup_duration_by_labels[key].append(value)

        for label_key, observations in backup_duration_by_labels.items():
            label_dict = dict(label_key)
            bucket_counts = self._calculate_histogram_buckets(observations, buckets)

            for bucket, count in bucket_counts.items():
                label_str = self._format_labels({**label_dict, "le": bucket})
                lines.append(
                    f"qnwis_dr_backup_duration_seconds_bucket{label_str} {count}"
                )

            label_str = self._format_labels(label_dict)
            lines.append(
                f"qnwis_dr_backup_duration_seconds_sum{label_str} {sum(observations)}"
            )
            lines.append(
                f"qnwis_dr_backup_duration_seconds_count{label_str} {len(observations)}"
            )
        lines.append("")

        # DR restore duration histogram
        lines.append("# HELP qnwis_dr_restore_duration_seconds DR restore operation duration")
        lines.append("# TYPE qnwis_dr_restore_duration_seconds histogram")
        restore_duration_by_labels: dict[tuple, list[float]] = defaultdict(list)
        for labels, value in self.dr_restore_duration_seconds:
            key = tuple(sorted(labels.items()))
            restore_duration_by_labels[key].append(value)

        for label_key, observations in restore_duration_by_labels.items():
            label_dict = dict(label_key)
            bucket_counts = self._calculate_histogram_buckets(observations, buckets)

            for bucket, count in bucket_counts.items():
                label_str = self._format_labels({**label_dict, "le": bucket})
                lines.append(
                    f"qnwis_dr_restore_duration_seconds_bucket{label_str} {count}"
                )

            label_str = self._format_labels(label_dict)
            lines.append(
                f"qnwis_dr_restore_duration_seconds_sum{label_str} {sum(observations)}"
            )
            lines.append(
                f"qnwis_dr_restore_duration_seconds_count{label_str} {len(observations)}"
            )
        lines.append("")

        return "\n".join(lines)

    def get_summary(self) -> dict[str, Any]:
        """
        Get metrics summary as dictionary.

        Returns:
            Dictionary with metrics summary
        """
        return {
            "uptime_seconds": time.time() - self.start_time,
            "counters": {
                "http_requests": dict(self.request_total),
                "agent_executions": dict(self.agent_execution_total),
                "cache_operations": dict(self.cache_operations_total),
                "auth_attempts": dict(self.auth_attempts_total),
                "rate_limit_events": dict(self.rate_limit_events_total),
            },
            "gauges": {
                "active_requests": self.active_requests,
                "agent_queue_depth": self.agent_queue_depth,
            },
            "histograms": {
                "request_duration_count": len(self.request_duration_seconds),
                "agent_execution_count": len(self.agent_execution_duration_seconds),
                "cache_latency_count": len(self.cache_latency_seconds),
            },
        }


def _percentile(values: list[float], p: float) -> float:
    """Compute percentile p in [0,100] deterministically.

    Uses nearest-rank on sorted values. Returns 0.0 if empty.
    """
    if not values:
        return 0.0
    if p <= 0:
        return float(sorted(values)[0])
    if p >= 100:
        return float(sorted(values)[-1])
    ordered = sorted(values)
    rank = int(round((p / 100.0) * (len(ordered) - 1)))
    return float(ordered[rank])


def compute_sli_snapshot() -> dict[str, float]:
    """Compute process-level SLI snapshot from MetricsCollector.

    - latency_ms_p95: p95 of HTTP request durations (seconds * 1000)
    - availability_pct: 1 - (5xx / total) expressed in percent [0,100]
    - error_rate_pct: 5xx / total expressed in percent [0,100]
    """
    mc = get_metrics_collector()

    # Gather HTTP durations
    durations_s = [v for _, v in mc.request_duration_seconds]
    p95_ms = _percentile(durations_s, 95.0) * 1000.0

    # Gather HTTP status counts
    total = 0
    err5xx = 0
    for labels, count in mc.request_total.items():
        label_dict = dict(labels)
        try:
            status = int(label_dict.get("status", "0"))
        except ValueError:
            status = 0
        total += count
        if status >= 500:
            err5xx += count

    if total <= 0:
        availability_pct = 100.0
        error_rate_pct = 0.0
    else:
        error_rate = err5xx / float(total)
        error_rate_pct = max(0.0, min(100.0, 100.0 * error_rate))
        availability_pct = max(0.0, min(100.0, 100.0 * (1.0 - error_rate)))

    return {
        "latency_ms_p95": round(float(p95_ms), 6),
        "availability_pct": round(float(availability_pct), 6),
        "error_rate_pct": round(float(error_rate_pct), 6),
    }


def write_sli_snapshot_json(path: str = "docs/audit/rg6/sli_snapshot.json", *, clock=None) -> str:
    """Write deterministic SLI snapshot JSON to path and return path.

    Args:
        path: Output file path
        clock: Optional Clock with now_iso(); if None, avoids timestamp.

    Returns:
        The output path as a string
    """
    import json
    from pathlib import Path

    payload: dict[str, Any] = {
        "sli": compute_sli_snapshot(),
    }
    if clock is not None and hasattr(clock, "now_iso"):
        payload["timestamp"] = clock.now_iso()

    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # Deterministic key ordering
    out_path.write_text(json.dumps(payload, sort_keys=True, separators=(",", ":")), encoding="utf-8")
    return str(out_path)


# Global metrics collector
_metrics_collector: MetricsCollector | None = None


def get_metrics_collector() -> MetricsCollector:
    """Get or create global metrics collector."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


def record_request(
    method: str, endpoint: str, status_code: int, duration_seconds: float
) -> None:
    """
    Record HTTP request metrics.

    Args:
        method: HTTP method
        endpoint: Endpoint path
        status_code: HTTP status code
        duration_seconds: Request duration in seconds
    """
    collector = get_metrics_collector()
    labels = {
        "method": method,
        "endpoint": endpoint,
        "status": str(status_code),
    }
    collector.increment_counter("qnwis_http_requests_total", labels)
    collector.observe_histogram(
        "qnwis_http_request_duration_seconds", labels, duration_seconds
    )


def record_agent_execution(
    agent: str, status: str, duration_seconds: float
) -> None:
    """
    Record agent execution metrics.

    Args:
        agent: Agent name
        status: Execution status (success, error)
        duration_seconds: Execution duration in seconds
    """
    collector = get_metrics_collector()
    labels = {"agent": agent, "status": status}
    collector.increment_counter("qnwis_agent_executions_total", labels)
    collector.observe_histogram(
        "qnwis_agent_execution_duration_seconds", labels, duration_seconds
    )


def record_cache_hit(operation: str, result: str) -> None:
    """
    Record cache operation.

    Args:
        operation: Operation type (get, set, delete)
        result: Result (hit, miss, error)
    """
    collector = get_metrics_collector()
    labels = {"operation": operation, "result": result}
    collector.increment_counter("qnwis_cache_operations_total", labels)


def record_auth_attempt(method: str, result: str) -> None:
    """
    Record authentication attempt.

    Args:
        method: Auth method (jwt, api_key)
        result: Result (success, failure)
    """
    collector = get_metrics_collector()
    labels = {"method": method, "result": result}
    collector.increment_counter("qnwis_auth_attempts_total", labels)


def record_rate_limit_event(principal: str, reason: str) -> None:
    """
    Record rate limit event.

    Args:
        principal: User or API key identifier
        reason: Rate limit reason (rps_exceeded, daily_exceeded)
    """
    collector = get_metrics_collector()
    labels = {"principal": principal, "reason": reason}
    collector.increment_counter("qnwis_rate_limit_events_total", labels)


def record_failover_execution(
    cluster_id: str, status: str, duration_ms: float
) -> None:
    """
    Record failover execution metrics.

    Args:
        cluster_id: Cluster identifier
        status: Execution status (success, failure)
        duration_ms: Execution duration in milliseconds
    """
    collector = get_metrics_collector()
    labels = {"cluster": cluster_id, "status": status}
    collector.increment_counter("qnwis_failover_executions_total", labels)
    
    if status == "success":
        collector.increment_counter("qnwis_failover_success_total", {"cluster": cluster_id})
    else:
        collector.increment_counter("qnwis_failover_failures_total", {"cluster": cluster_id, "reason": "execution_failed"})
    
    collector.observe_histogram("qnwis_failover_execution_ms", labels, duration_ms)


def record_failover_validation(cluster_id: str, duration_ms: float) -> None:
    """
    Record failover validation metrics.

    Args:
        cluster_id: Cluster identifier
        duration_ms: Validation duration in milliseconds
    """
    collector = get_metrics_collector()
    labels = {"cluster": cluster_id}
    collector.observe_histogram("qnwis_failover_validation_ms", labels, duration_ms)


def update_continuity_status(healthy_nodes: int, has_quorum: bool) -> None:
    """
    Update continuity status gauges.

    Args:
        healthy_nodes: Number of healthy nodes
        has_quorum: Whether quorum is achieved
    """
    collector = get_metrics_collector()
    collector.set_gauge("qnwis_continuity_nodes_healthy", healthy_nodes)
    collector.set_gauge("qnwis_continuity_quorum_reached", 1 if has_quorum else 0)


def record_llm_call(
    model: str,
    input_tokens: int,
    output_tokens: int,
    latency_ms: float,
    agent_name: str | None = None,
    purpose: str | None = None
) -> None:
    """
    Record LLM API call metrics.

    Args:
        model: Model name (e.g., claude-3-5-sonnet-20241022)
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        latency_ms: API call latency in milliseconds
        agent_name: Name of agent making the call (if applicable)
        purpose: Purpose of the call (e.g., analysis, synthesis, debate)
    """
    collector = get_metrics_collector()
    
    # Record call count
    labels = {
        "model": model,
        "agent": agent_name or "unknown",
        "purpose": purpose or "unknown"
    }
    key = tuple(sorted(labels.items()))
    collector.llm_calls_total[key] += 1
    
    # Record tokens
    token_labels_input = ("model", model), ("token_type", "input")
    token_labels_output = ("model", model), ("token_type", "output")
    collector.llm_tokens_total[token_labels_input] += input_tokens
    collector.llm_tokens_total[token_labels_output] += output_tokens
    
    # Record cost (Anthropic Claude pricing as of Nov 2024)
    # claude-3-5-sonnet-20241022: $3/M input, $15/M output
    cost_input = (input_tokens / 1_000_000) * 3.0
    cost_output = (output_tokens / 1_000_000) * 15.0
    total_cost = cost_input + cost_output
    
    cost_key = (("model", model),)
    collector.llm_cost_usd_total[cost_key] += total_cost
    
    # Record latency
    collector.llm_call_latency_ms.append((labels, latency_ms))
    
    logger.debug(
        f"LLM call: model={model}, agent={agent_name}, "
        f"tokens={input_tokens}+{output_tokens}, "
        f"latency={latency_ms:.1f}ms, cost=${total_cost:.6f}"
    )


def record_query_execution(
    complexity: str,
    status: str,
    total_latency_ms: float,
    agents_invoked: list[str],
    confidence: float,
    citation_violations: int,
    facts_extracted: int
) -> None:
    """
    Record workflow query execution metrics.

    Args:
        complexity: Query complexity (simple, medium, complex)
        status: Execution status (success, error)
        total_latency_ms: Total query latency in milliseconds
        agents_invoked: List of agents invoked
        confidence: Final confidence score (0.0-1.0)
        citation_violations: Number of citation violations
        facts_extracted: Number of facts extracted
    """
    collector = get_metrics_collector()
    
    # Record query execution count
    query_labels = {
        "complexity": complexity,
        "status": status
    }
    key = tuple(sorted(query_labels.items()))
    collector.query_executions_total[key] += 1
    
    # Record citation violations
    if citation_violations > 0:
        violation_key = ()
        collector.citation_violations_total[violation_key] += citation_violations
    
    # Record query latency
    latency_labels = {
        "complexity": complexity,
        "agent_count": str(len(agents_invoked)),
        "status": status
    }
    collector.query_latency_ms.append((latency_labels, total_latency_ms))
    
    logger.info(
        f"Query execution: complexity={complexity}, status={status}, "
        f"latency={total_latency_ms:.1f}ms, agents={len(agents_invoked)}, "
        f"confidence={confidence:.2f}, violations={citation_violations}, "
        f"facts={facts_extracted}"
    )
