"""
Microbenchmark tests for alert evaluation performance.

Validates p95 latency < 150ms for 200 rules.
"""

import time

import pytest

from src.qnwis.alerts.engine import AlertEngine
from src.qnwis.alerts.registry import AlertRegistry
from src.qnwis.alerts.rules import (
    AlertRule,
    ScopeConfig,
    Severity,
    TriggerConfig,
    TriggerOperator,
    TriggerType,
    WindowConfig,
)


def generate_test_rules(count: int) -> list[AlertRule]:
    """
    Generate test alert rules for benchmarking.

    Args:
        count: Number of rules to generate

    Returns:
        List of AlertRule instances
    """
    rules = []
    severities = [Severity.LOW, Severity.MEDIUM, Severity.HIGH, Severity.CRITICAL]
    trigger_types = [
        TriggerType.THRESHOLD,
        TriggerType.YOY_DELTA_PCT,
        TriggerType.SLOPE_WINDOW,
        TriggerType.BREAK_EVENT,
    ]

    for i in range(count):
        severity = severities[i % len(severities)]
        trigger_type = trigger_types[i % len(trigger_types)]

        # Generate appropriate trigger config
        if trigger_type == TriggerType.THRESHOLD:
            trigger = TriggerConfig(
                type=trigger_type,
                op=TriggerOperator.LT,
                value=0.5 + (i % 10) * 0.05,
            )
        elif trigger_type == TriggerType.YOY_DELTA_PCT:
            trigger = TriggerConfig(
                type=trigger_type,
                op=TriggerOperator.LTE,
                value=-5.0 - (i % 10),
            )
        elif trigger_type == TriggerType.SLOPE_WINDOW:
            trigger = TriggerConfig(
                type=trigger_type,
                op=TriggerOperator.LT,
                value=-0.01 - (i % 10) * 0.001,
            )
        else:  # BREAK_EVENT
            trigger = TriggerConfig(
                type=trigger_type,
                value=3.0 + (i % 5),
            )

        rule = AlertRule(
            rule_id=f"bench_rule_{i:04d}",
            metric="retention",
            scope=ScopeConfig(level="sector", code=f"sector_{i % 10}"),
            window=WindowConfig(months=3 + (i % 9)),
            trigger=trigger,
            horizon=12 + (i % 84),
            severity=severity,
            enabled=True,
        )
        rules.append(rule)

    return rules


def generate_test_series(trigger_type: TriggerType) -> list[float]:
    """
    Generate appropriate test series for trigger type.

    Args:
        trigger_type: Type of trigger

    Returns:
        List of float values
    """
    if trigger_type == TriggerType.YOY_DELTA_PCT:
        # Need 13+ points for YoY
        return [0.5 + i * 0.01 for i in range(24)]
    elif trigger_type == TriggerType.BREAK_EVENT:
        # Stable series for break detection
        return [0.5] * 12
    else:
        # Generic series
        return [0.5 + i * 0.01 for i in range(12)]


class TestMicrobenchmark:
    """Microbenchmark tests for alert evaluation performance."""

    def test_single_rule_latency(self):
        """Test single rule evaluation latency."""
        engine = AlertEngine()
        rule = AlertRule(
            rule_id="single",
            metric="retention",
            scope=ScopeConfig(level="sector"),
            window=WindowConfig(months=3),
            trigger=TriggerConfig(
                type=TriggerType.THRESHOLD,
                op=TriggerOperator.LT,
                value=0.5,
            ),
            horizon=12,
            severity=Severity.LOW,
        )

        series = [0.6, 0.5, 0.4]

        # Warm-up
        for _ in range(10):
            engine.evaluate(rule, series)

        # Benchmark
        start = time.perf_counter()
        iterations = 1000
        for _ in range(iterations):
            engine.evaluate(rule, series)
        elapsed = time.perf_counter() - start

        avg_latency_ms = (elapsed / iterations) * 1000
        print(f"\nSingle rule avg latency: {avg_latency_ms:.3f} ms")

        # Should be well under 1ms per rule
        assert avg_latency_ms < 1.0

    @pytest.mark.slow
    def test_200_rules_p95_latency(self):
        """
        Test p95 latency for 200 rule evaluations.

        Requirements: p95 < 150ms
        """
        engine = AlertEngine()
        rules = generate_test_rules(200)

        def data_provider(rule):
            series = generate_test_series(rule.trigger.type)
            return series, []

        # Warm-up: evaluate all rules once
        engine.batch_evaluate(rules, data_provider)

        # Benchmark: run 10 iterations
        latencies = []
        for _ in range(10):
            start = time.perf_counter()
            decisions = engine.batch_evaluate(rules, data_provider)
            elapsed = time.perf_counter() - start

            latency_ms = elapsed * 1000
            latencies.append(latency_ms)

            assert len(decisions) == 200

        # Compute percentiles
        latencies.sort()
        p50 = latencies[len(latencies) // 2]
        p95 = latencies[int(len(latencies) * 0.95)]
        p99 = latencies[int(len(latencies) * 0.99)]
        mean = sum(latencies) / len(latencies)

        print("\n200 rules - Latency distribution:")
        print(f"  Mean: {mean:.2f} ms")
        print(f"  p50:  {p50:.2f} ms")
        print(f"  p95:  {p95:.2f} ms")
        print(f"  p99:  {p99:.2f} ms")

        # Performance requirement
        assert p95 < 150.0, f"p95 latency {p95:.2f}ms exceeds 150ms requirement"

    def test_registry_load_performance(self):
        """Test registry loading performance."""
        import tempfile

        import yaml

        rules = generate_test_rules(200)
        rules_data = [
            {
                "rule_id": r.rule_id,
                "metric": r.metric,
                "scope": {"level": r.scope.level, "code": r.scope.code},
                "window": {"months": r.window.months},
                "trigger": {
                    "type": r.trigger.type.value,
                    "op": r.trigger.op.value if r.trigger.op else None,
                    "value": r.trigger.value,
                },
                "horizon": r.horizon,
                "severity": r.severity.value,
                "enabled": r.enabled,
            }
            for r in rules
        ]

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            yaml.dump({"rules": rules_data}, f)
            yaml_path = f.name

        try:
            registry = AlertRegistry()

            start = time.perf_counter()
            count = registry.load_file(yaml_path)
            elapsed = time.perf_counter() - start

            load_time_ms = elapsed * 1000
            print(f"\nRegistry load time for 200 rules: {load_time_ms:.2f} ms")

            assert count == 200
            # Loading should be fast
            assert load_time_ms < 500.0

        finally:
            from pathlib import Path
            Path(yaml_path).unlink()

    def test_batch_vs_sequential_performance(self):
        """Compare batch vs sequential evaluation performance."""
        engine = AlertEngine()
        rules = generate_test_rules(50)

        def data_provider(rule):
            series = generate_test_series(rule.trigger.type)
            return series, []

        # Sequential evaluation
        start = time.perf_counter()
        sequential_decisions = []
        for rule in rules:
            series, timestamps = data_provider(rule)
            decision = engine.evaluate(rule, series, timestamps)
            sequential_decisions.append(decision)
        sequential_time = time.perf_counter() - start

        # Batch evaluation
        start = time.perf_counter()
        batch_decisions = engine.batch_evaluate(rules, data_provider)
        batch_time = time.perf_counter() - start

        print("\n50 rules:")
        print(f"  Sequential: {sequential_time * 1000:.2f} ms")
        print(f"  Batch:      {batch_time * 1000:.2f} ms")

        assert len(sequential_decisions) == 50
        assert len(batch_decisions) == 50

        # Batch should be comparable or faster
        # (No significant overhead from batch wrapper)
        assert batch_time <= sequential_time * 1.2
