"""
Unit tests for alert rule registry.

Tests rule loading, validation, and deterministic ordering.
"""

import json
import tempfile
from pathlib import Path

import pytest

import yaml
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


@pytest.fixture
def registry():
    """Create empty AlertRegistry instance."""
    return AlertRegistry()


@pytest.fixture
def sample_rule_data():
    """Sample rule data as dict."""
    return {
        "rule_id": "test_rule",
        "metric": "retention",
        "scope": {"level": "sector", "code": "construction"},
        "window": {"months": 6},
        "trigger": {
            "type": "yoy_delta_pct",
            "op": "lte",
            "value": -5.0,
        },
        "horizon": 12,
        "severity": "high",
        "enabled": True,
        "description": "Test rule",
    }


class TestRegistryBasics:
    """Tests for basic registry operations."""

    def test_empty_registry(self, registry):
        """Test empty registry initialization."""
        assert len(registry) == 0
        assert registry.get_all_rules() == []

    def test_add_rule(self, registry):
        """Test adding a rule to registry."""
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

        registry.add_rule(rule)
        assert len(registry) == 1
        assert "test" in registry
        assert registry.get_rule("test") == rule

    def test_get_nonexistent_rule(self, registry):
        """Test retrieving non-existent rule returns None."""
        assert registry.get_rule("nonexistent") is None

    def test_overwrite_rule(self, registry):
        """Test that adding rule with same ID overwrites."""
        rule1 = AlertRule(
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

        rule2 = AlertRule(
            rule_id="test",
            metric="salary",
            scope=ScopeConfig(level="sector"),
            window=WindowConfig(months=6),
            trigger=TriggerConfig(
                type=TriggerType.THRESHOLD,
                op=TriggerOperator.GT,
                value=10000.0,
            ),
            horizon=12,
            severity=Severity.HIGH,
        )

        registry.add_rule(rule1)
        registry.add_rule(rule2)

        assert len(registry) == 1
        assert registry.get_rule("test").metric == "salary"

    def test_clear_registry(self, registry):
        """Test clearing all rules."""
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

        registry.add_rule(rule)
        assert len(registry) == 1

        registry.clear()
        assert len(registry) == 0
        assert registry.get_all_rules() == []


class TestYAMLLoading:
    """Tests for YAML rule loading."""

    def test_load_valid_yaml(self, registry, sample_rule_data):
        """Test loading valid YAML file."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            yaml.dump({"rules": [sample_rule_data]}, f)
            yaml_path = f.name

        try:
            count = registry.load_file(yaml_path)
            assert count == 1
            assert len(registry) == 1
            assert "test_rule" in registry
        finally:
            Path(yaml_path).unlink()

    def test_load_multiple_rules_yaml(self, registry, sample_rule_data):
        """Test loading multiple rules from YAML."""
        rule2 = sample_rule_data.copy()
        rule2["rule_id"] = "test_rule_2"

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            yaml.dump({"rules": [sample_rule_data, rule2]}, f)
            yaml_path = f.name

        try:
            count = registry.load_file(yaml_path)
            assert count == 2
            assert len(registry) == 2
        finally:
            Path(yaml_path).unlink()

    def test_load_yml_extension(self, registry, sample_rule_data):
        """Test loading .yml extension."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yml", delete=False, encoding="utf-8"
        ) as f:
            yaml.dump({"rules": [sample_rule_data]}, f)
            yml_path = f.name

        try:
            count = registry.load_file(yml_path)
            assert count == 1
        finally:
            Path(yml_path).unlink()

    def test_load_invalid_yaml(self, registry):
        """Test loading invalid YAML raises error."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            f.write("invalid: yaml: content: [")
            yaml_path = f.name

        try:
            with pytest.raises(ValueError, match="Invalid YAML"):
                registry.load_file(yaml_path)
        finally:
            Path(yaml_path).unlink()


class TestJSONLoading:
    """Tests for JSON rule loading."""

    def test_load_valid_json(self, registry, sample_rule_data):
        """Test loading valid JSON file."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump({"rules": [sample_rule_data]}, f)
            json_path = f.name

        try:
            count = registry.load_file(json_path)
            assert count == 1
            assert len(registry) == 1
        finally:
            Path(json_path).unlink()

    def test_load_invalid_json(self, registry):
        """Test loading invalid JSON raises error."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            f.write("{invalid json")
            json_path = f.name

        try:
            with pytest.raises(ValueError, match="Invalid JSON"):
                registry.load_file(json_path)
        finally:
            Path(json_path).unlink()


class TestFileHandling:
    """Tests for file handling edge cases."""

    def test_load_nonexistent_file(self, registry):
        """Test loading non-existent file raises error."""
        with pytest.raises(FileNotFoundError):
            registry.load_file("/nonexistent/path/rules.yaml")

    def test_load_unsupported_format(self, registry):
        """Test loading unsupported format raises error."""
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            txt_path = f.name

        try:
            with pytest.raises(ValueError, match="Unsupported file format"):
                registry.load_file(txt_path)
        finally:
            Path(txt_path).unlink()


class TestValidation:
    """Tests for rule validation."""

    def test_validate_all_success(self, registry):
        """Test validate_all with valid rules."""
        rule = AlertRule(
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
        )

        registry.add_rule(rule)
        is_valid, errors = registry.validate_all()
        assert is_valid is True
        assert len(errors) == 0

    def test_partial_load_with_validation_errors(self, registry):
        """Test that valid rules load even with some invalid."""
        valid_rule = {
            "rule_id": "valid",
            "metric": "retention",
            "scope": {"level": "sector"},
            "window": {"months": 6},
            "trigger": {"type": "threshold", "op": "lt", "value": 0.5},
            "horizon": 12,
            "severity": "low",
        }

        invalid_rule = {
            "rule_id": "invalid",
            "metric": "",  # Empty metric
            "scope": {"level": "sector"},
            "window": {"months": 1},  # Below minimum
            "trigger": {"type": "threshold", "op": "lt", "value": 0.5},
            "horizon": 12,
            "severity": "low",
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            yaml.dump({"rules": [valid_rule, invalid_rule]}, f)
            yaml_path = f.name

        try:
            count = registry.load_file(yaml_path)
            # Only valid rule should load
            assert count == 1
            assert "valid" in registry
            assert "invalid" not in registry
        finally:
            Path(yaml_path).unlink()


class TestDeterministicOrdering:
    """Tests for deterministic rule ordering."""

    def test_load_order_preserved(self, registry):
        """Test that load order is deterministic."""
        rules_data = [
            {"rule_id": f"rule_{i}", "metric": "retention", "scope": {"level": "sector"},
             "window": {"months": 3}, "trigger": {"type": "threshold", "op": "lt", "value": 0.5},
             "horizon": 12, "severity": "low"}
            for i in range(5)
        ]

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            yaml.dump({"rules": rules_data}, f)
            yaml_path = f.name

        try:
            registry.load_file(yaml_path)
            loaded_rules = registry.get_all_rules()
            loaded_ids = [r.rule_id for r in loaded_rules]
            expected_ids = [f"rule_{i}" for i in range(5)]
            assert loaded_ids == expected_ids
        finally:
            Path(yaml_path).unlink()


class TestQueryMethods:
    """Tests for rule query methods."""

    def test_get_rules_by_metric(self, registry):
        """Test filtering rules by metric."""
        rule1 = AlertRule(
            rule_id="ret1",
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

        rule2 = AlertRule(
            rule_id="sal1",
            metric="salary",
            scope=ScopeConfig(level="sector"),
            window=WindowConfig(months=3),
            trigger=TriggerConfig(
                type=TriggerType.THRESHOLD,
                op=TriggerOperator.LT,
                value=3000.0,
            ),
            horizon=12,
            severity=Severity.LOW,
        )

        registry.add_rule(rule1)
        registry.add_rule(rule2)

        retention_rules = registry.get_rules_by_metric("retention")
        assert len(retention_rules) == 1
        assert retention_rules[0].rule_id == "ret1"

    def test_get_rules_by_severity(self, registry):
        """Test filtering rules by severity."""
        rule1 = AlertRule(
            rule_id="low",
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

        rule2 = AlertRule(
            rule_id="high",
            metric="retention",
            scope=ScopeConfig(level="sector"),
            window=WindowConfig(months=3),
            trigger=TriggerConfig(
                type=TriggerType.THRESHOLD,
                op=TriggerOperator.LT,
                value=0.3,
            ),
            horizon=12,
            severity=Severity.HIGH,
        )

        registry.add_rule(rule1)
        registry.add_rule(rule2)

        high_rules = registry.get_rules_by_severity("high")
        assert len(high_rules) == 1
        assert high_rules[0].rule_id == "high"

    def test_get_all_enabled_only(self, registry):
        """Test filtering enabled rules."""
        rule1 = AlertRule(
            rule_id="enabled",
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
            enabled=True,
        )

        rule2 = AlertRule(
            rule_id="disabled",
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
            enabled=False,
        )

        registry.add_rule(rule1)
        registry.add_rule(rule2)

        all_rules = registry.get_all_rules()
        assert len(all_rules) == 2

        enabled_rules = registry.get_all_rules(enabled_only=True)
        assert len(enabled_rules) == 1
        assert enabled_rules[0].rule_id == "enabled"
