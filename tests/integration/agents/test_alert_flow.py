"""
Integration tests for end-to-end alert flow.

Tests complete alert evaluation pipeline with real components.
"""

import json
import tempfile
from pathlib import Path

import pytest

import yaml
from src.qnwis.alerts.engine import AlertEngine
from src.qnwis.alerts.registry import AlertRegistry
from src.qnwis.alerts.report import AlertReportRenderer
from src.qnwis.monitoring.metrics import MetricsCollector, TimedEvaluation


@pytest.fixture
def sample_rules_file():
    """Create temporary rules file."""
    rules_data = {
        "rules": [
            {
                "rule_id": "integration_test_1",
                "metric": "retention",
                "scope": {"level": "sector", "code": "construction"},
                "window": {"months": 6},
                "trigger": {"type": "yoy_delta_pct", "op": "lte", "value": -5.0},
                "horizon": 12,
                "severity": "high",
                "enabled": True,
                "description": "Integration test rule 1",
            },
            {
                "rule_id": "integration_test_2",
                "metric": "salary",
                "scope": {"level": "sector"},
                "window": {"months": 3},
                "trigger": {"type": "threshold", "op": "lt", "value": 3000.0},
                "horizon": 6,
                "severity": "medium",
                "enabled": True,
            },
            {
                "rule_id": "integration_test_disabled",
                "metric": "retention",
                "scope": {"level": "sector"},
                "window": {"months": 3},
                "trigger": {"type": "threshold", "op": "lt", "value": 0.3},
                "horizon": 12,
                "severity": "low",
                "enabled": False,
            },
        ]
    }

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False, encoding="utf-8"
    ) as f:
        yaml.dump(rules_data, f)
        yield f.name

    # Cleanup
    Path(f.name).unlink(missing_ok=True)


class TestAlertFlowIntegration:
    """Integration tests for complete alert flow."""

    def test_load_and_validate_rules(self, sample_rules_file):
        """Test loading rules from file and validation."""
        registry = AlertRegistry()
        count = registry.load_file(sample_rules_file)

        assert count == 3
        assert len(registry) == 3

        is_valid, errors = registry.validate_all()
        assert is_valid is True
        assert len(errors) == 0

        # Check enabled/disabled
        all_rules = registry.get_all_rules()
        enabled_rules = registry.get_all_rules(enabled_only=True)
        assert len(all_rules) == 3
        assert len(enabled_rules) == 2

    def test_engine_batch_evaluation(self, sample_rules_file):
        """Test batch evaluation of loaded rules."""
        registry = AlertRegistry()
        registry.load_file(sample_rules_file)

        engine = AlertEngine()
        rules = registry.get_all_rules(enabled_only=True)

        def data_provider(rule):
            # Provide appropriate data based on trigger type
            if rule.trigger.type.value == "yoy_delta_pct":
                # Need 13+ points for YoY
                return [0.5] * 13, []
            else:
                return [0.6, 0.5, 0.4], []

        decisions = engine.batch_evaluate(rules, data_provider)

        assert len(decisions) == len(rules)
        for decision in decisions:
            assert decision.rule_id is not None
            assert isinstance(decision.triggered, bool)

    def test_report_generation_flow(self, sample_rules_file):
        """Test complete report generation flow."""
        registry = AlertRegistry()
        registry.load_file(sample_rules_file)

        engine = AlertEngine()
        renderer = AlertReportRenderer()

        rules = registry.get_all_rules(enabled_only=True)

        def data_provider(rule):
            if rule.trigger.type.value == "yoy_delta_pct":
                return [0.5] * 13, []
            else:
                return [0.6, 0.5, 0.4], []

        decisions = engine.batch_evaluate(rules, data_provider)
        rules_dict = {r.rule_id: r for r in rules}

        # Generate markdown report
        md_report = renderer.render_markdown(decisions, rules_dict)
        assert "# Alert Center Report" in md_report
        assert "Citations & Freshness" in md_report

        # Generate JSON report
        json_report = renderer.render_json(decisions, rules_dict)
        data = json.loads(json_report)
        assert "alerts" in data
        assert "summary" in data
        assert len(data["alerts"]) == len(decisions)

    def test_audit_pack_generation_flow(self, sample_rules_file):
        """Test audit pack generation flow."""
        registry = AlertRegistry()
        registry.load_file(sample_rules_file)

        engine = AlertEngine()
        renderer = AlertReportRenderer()

        rules = registry.get_all_rules(enabled_only=True)

        def data_provider(rule):
            if rule.trigger.type.value == "yoy_delta_pct":
                return [0.5] * 13, []
            else:
                return [0.6, 0.5, 0.4], []

        decisions = engine.batch_evaluate(rules, data_provider)
        rules_dict = {r.rule_id: r for r in rules}

        with tempfile.TemporaryDirectory() as tmpdir:
            artifacts = renderer.generate_audit_pack(decisions, rules_dict, tmpdir)

            # Verify artifacts
            assert "markdown" in artifacts
            assert "json" in artifacts
            assert "manifest" in artifacts

            # Verify files exist and have content
            for _key, path in artifacts.items():
                file_path = Path(path)
                assert file_path.exists()
                assert file_path.stat().st_size > 0

            # Verify manifest structure
            manifest_path = Path(artifacts["manifest"])
            with open(manifest_path, encoding="utf-8") as f:
                manifest = json.load(f)

            assert "timestamp" in manifest
            assert "files" in manifest
            assert "markdown" in manifest["files"]
            assert "json" in manifest["files"]

    def test_metrics_collection_flow(self, sample_rules_file):
        """Test metrics collection during evaluation."""
        registry = AlertRegistry()
        registry.load_file(sample_rules_file)

        engine = AlertEngine()
        collector = MetricsCollector()

        rules = registry.get_all_rules(enabled_only=True)

        def data_provider(rule):
            if rule.trigger.type.value == "yoy_delta_pct":
                return [0.5] * 13, []
            else:
                return [0.6, 0.5, 0.4], []

        # Evaluate with metrics collection
        for rule in rules:
            with TimedEvaluation(collector, rule.rule_id) as timer:
                series, timestamps = data_provider(rule)
                decision = engine.evaluate(rule, series, timestamps)
                timer.set_triggered(decision.triggered)

        metrics = collector.get_metrics()

        assert metrics["rules_evaluated_total"] == len(rules)
        assert metrics["eval_latency_ms_p50"] > 0
        assert metrics["eval_latency_ms_p95"] > 0

        # Export metrics
        with tempfile.TemporaryDirectory():
            collector.export_plain_text("test_metrics.txt")
            # Metrics file should be created in default dir
            # Just verify method runs without error

    def test_rule_query_methods(self, sample_rules_file):
        """Test rule query methods integration."""
        registry = AlertRegistry()
        registry.load_file(sample_rules_file)

        # Query by metric
        retention_rules = registry.get_rules_by_metric("retention")
        salary_rules = registry.get_rules_by_metric("salary")

        assert len(retention_rules) >= 1
        assert len(salary_rules) >= 1

        # Query by severity
        high_rules = registry.get_rules_by_severity("high")
        medium_rules = registry.get_rules_by_severity("medium")

        assert len(high_rules) >= 1
        assert len(medium_rules) >= 1

        # Verify filtering works correctly
        for rule in high_rules:
            assert rule.severity.value == "high"

    def test_deterministic_ordering(self, sample_rules_file):
        """Test that rule ordering is deterministic across loads."""
        # Load twice
        registry1 = AlertRegistry()
        registry1.load_file(sample_rules_file)

        registry2 = AlertRegistry()
        registry2.load_file(sample_rules_file)

        rules1 = registry1.get_all_rules()
        rules2 = registry2.get_all_rules()

        # Should have same order
        ids1 = [r.rule_id for r in rules1]
        ids2 = [r.rule_id for r in rules2]

        assert ids1 == ids2


class TestAlertFlowErrorHandling:
    """Integration tests for error handling."""

    def test_invalid_trigger_data(self):
        """Test handling of invalid trigger data."""
        engine = AlertEngine()

        from src.qnwis.alerts.rules import (
            AlertRule,
            ScopeConfig,
            Severity,
            TriggerConfig,
            TriggerOperator,
            TriggerType,
            WindowConfig,
        )

        rule = AlertRule(
            rule_id="test",
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

        # Empty series
        decision = engine.evaluate(rule, [], [])
        assert decision.triggered is False
        assert "Empty" in decision.message

    def test_batch_with_errors(self):
        """Test batch evaluation with some rules failing."""
        engine = AlertEngine()

        from src.qnwis.alerts.rules import (
            AlertRule,
            ScopeConfig,
            Severity,
            TriggerConfig,
            TriggerOperator,
            TriggerType,
            WindowConfig,
        )

        rules = [
            AlertRule(
                rule_id="valid",
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
            ),
            AlertRule(
                rule_id="yoy_insufficient",
                metric="retention",
                scope=ScopeConfig(level="sector"),
                window=WindowConfig(months=6),
                trigger=TriggerConfig(
                    type=TriggerType.YOY_DELTA_PCT,
                    op=TriggerOperator.LTE,
                    value=-5.0,
                ),
                horizon=12,
                severity=Severity.HIGH,
            ),
        ]

        def data_provider(rule):
            # Provide insufficient data for YoY
            return [0.5, 0.4, 0.3], []

        decisions = engine.batch_evaluate(rules, data_provider)

        # Both rules should return decisions (even if not triggered)
        assert len(decisions) == 2
        assert decisions[0].rule_id == "valid"
        assert decisions[1].rule_id == "yoy_insufficient"

        # YoY should not trigger due to insufficient data
        assert decisions[1].triggered is False

    def test_partial_rule_load_with_errors(self):
        """Test that valid rules load even with some invalid."""
        rules_data = {
            "rules": [
                {
                    "rule_id": "valid",
                    "metric": "retention",
                    "scope": {"level": "sector"},
                    "window": {"months": 6},
                    "trigger": {"type": "threshold", "op": "lt", "value": 0.5},
                    "horizon": 12,
                    "severity": "low",
                },
                {
                    "rule_id": "invalid_window",
                    "metric": "retention",
                    "scope": {"level": "sector"},
                    "window": {"months": 1},  # Below minimum
                    "trigger": {"type": "threshold", "op": "lt", "value": 0.5},
                    "horizon": 12,
                    "severity": "low",
                },
            ]
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            yaml.dump(rules_data, f)
            rules_file = f.name

        try:
            registry = AlertRegistry()
            count = registry.load_file(rules_file)

            # Only valid rule should load
            assert count == 1
            assert "valid" in registry
            assert "invalid_window" not in registry

        finally:
            Path(rules_file).unlink(missing_ok=True)
