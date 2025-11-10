"""
Plain-text metrics collection for alert center monitoring.

Tracks evaluation counts, alert firing rates, and latency percentiles.
"""

from __future__ import annotations

import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Literal


class MetricsCollector:
    """
    Collects and exports plain-text metrics for monitoring.

    Tracks:
    - rules_evaluated_total: Counter of rule evaluations
    - alerts_fired_total: Counter of triggered alerts
    - eval_latency_ms: Latency distribution (p50, p95, p99)
    """

    def __init__(self, output_dir: str = "docs/audit/metrics") -> None:
        """
        Initialize metrics collector.

        Args:
            output_dir: Directory for metrics output
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Counters
        self._rules_evaluated = 0
        self._alerts_fired = 0

        # Latency tracking
        self._latencies: list[float] = []

        # Per-rule counters
        self._rule_counters: dict[str, int] = defaultdict(int)
        self._rule_triggers: dict[str, int] = defaultdict(int)

    def record_evaluation(
        self,
        rule_id: str,
        triggered: bool,
        latency_ms: float,
    ) -> None:
        """
        Record a single rule evaluation.

        Args:
            rule_id: Rule identifier
            triggered: Whether alert was triggered
            latency_ms: Evaluation latency in milliseconds
        """
        self._rules_evaluated += 1
        self._rule_counters[rule_id] += 1

        if triggered:
            self._alerts_fired += 1
            self._rule_triggers[rule_id] += 1

        self._latencies.append(latency_ms)

    def record_batch_evaluation(
        self,
        results: list[tuple[str, bool, float]],
    ) -> None:
        """
        Record multiple evaluations in batch.

        Args:
            results: List of (rule_id, triggered, latency_ms) tuples
        """
        for rule_id, triggered, latency_ms in results:
            self.record_evaluation(rule_id, triggered, latency_ms)

    def get_metrics(self) -> dict[str, Any]:
        """
        Get current metrics snapshot.

        Returns:
            Dictionary of metric names to values
        """
        metrics: dict[str, Any] = {
            "rules_evaluated_total": self._rules_evaluated,
            "alerts_fired_total": self._alerts_fired,
        }

        # Compute latency percentiles
        if self._latencies:
            sorted_latencies = sorted(self._latencies)
            n = len(sorted_latencies)

            p50_idx = int(n * 0.50)
            p95_idx = int(n * 0.95)
            p99_idx = int(n * 0.99)

            metrics["eval_latency_ms_p50"] = sorted_latencies[min(p50_idx, n - 1)]
            metrics["eval_latency_ms_p95"] = sorted_latencies[min(p95_idx, n - 1)]
            metrics["eval_latency_ms_p99"] = sorted_latencies[min(p99_idx, n - 1)]
            metrics["eval_latency_ms_mean"] = sum(self._latencies) / len(self._latencies)
            metrics["eval_latency_ms_max"] = max(self._latencies)
        else:
            metrics["eval_latency_ms_p50"] = 0.0
            metrics["eval_latency_ms_p95"] = 0.0
            metrics["eval_latency_ms_p99"] = 0.0
            metrics["eval_latency_ms_mean"] = 0.0
            metrics["eval_latency_ms_max"] = 0.0

        return metrics

    def export_plain_text(self, filename: str = "metrics.txt") -> str:
        """
        Export metrics as plain text snapshot.

        Args:
            filename: Output filename

        Returns:
            Path to written file
        """
        metrics = self.get_metrics()
        timestamp = datetime.utcnow().isoformat() + "Z"

        lines = [
            "# QNWIS Alert Center Metrics",
            f"# Generated: {timestamp}",
            "",
            "## Counters",
            f"rules_evaluated_total {metrics['rules_evaluated_total']}",
            f"alerts_fired_total {metrics['alerts_fired_total']}",
            "",
            "## Latency (milliseconds)",
            f"eval_latency_ms_p50 {metrics['eval_latency_ms_p50']:.2f}",
            f"eval_latency_ms_p95 {metrics['eval_latency_ms_p95']:.2f}",
            f"eval_latency_ms_p99 {metrics['eval_latency_ms_p99']:.2f}",
            f"eval_latency_ms_mean {metrics['eval_latency_ms_mean']:.2f}",
            f"eval_latency_ms_max {metrics['eval_latency_ms_max']:.2f}",
            "",
        ]

        # Per-rule statistics
        if self._rule_counters:
            lines.append("## Per-Rule Statistics")
            for rule_id in sorted(self._rule_counters.keys()):
                eval_count = self._rule_counters[rule_id]
                trigger_count = self._rule_triggers.get(rule_id, 0)
                trigger_rate = (trigger_count / eval_count * 100) if eval_count > 0 else 0
                lines.append(
                    f"{rule_id}: evaluated={eval_count}, "
                    f"triggered={trigger_count}, "
                    f"rate={trigger_rate:.1f}%"
                )
            lines.append("")

        output_path = self.output_dir / filename
        output_path.write_text("\n".join(lines), encoding="utf-8")

        return str(output_path)

    def reset(self) -> None:
        """Reset all metrics to zero."""
        self._rules_evaluated = 0
        self._alerts_fired = 0
        self._latencies.clear()
        self._rule_counters.clear()
        self._rule_triggers.clear()


class TimedEvaluation:
    """
    Context manager for timing alert evaluations.

    Usage:
        collector = MetricsCollector()
        with TimedEvaluation(collector, "my_rule") as timer:
            # Evaluate rule
            triggered = evaluate_rule(...)
            timer.set_triggered(triggered)
    """

    def __init__(self, collector: MetricsCollector, rule_id: str):
        """
        Initialize timed evaluation.

        Args:
            collector: MetricsCollector instance
            rule_id: Rule identifier
        """
        self.collector = collector
        self.rule_id = rule_id
        self.triggered = False
        self.start_time = 0.0

    def __enter__(self) -> TimedEvaluation:
        """Start timing."""
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> Literal[False]:
        """Stop timing and record metrics."""
        elapsed_ms = (time.perf_counter() - self.start_time) * 1000.0
        self.collector.record_evaluation(self.rule_id, self.triggered, elapsed_ms)
        return False

    def set_triggered(self, triggered: bool) -> None:
        """
        Set whether alert was triggered.

        Args:
            triggered: True if alert fired
        """
        self.triggered = triggered
