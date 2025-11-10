"""
Unit tests for alert rule DSL validation.

Tests Pydantic validation, guardrails, and edge cases.
"""

import math

import pytest
from pydantic import ValidationError

from src.qnwis.alerts.rules import (
    AlertRule,
    ScopeConfig,
    Severity,
    TriggerConfig,
    TriggerOperator,
    TriggerType,
    WindowConfig,
)


class TestScopeConfig:
    """Tests for ScopeConfig validation."""

    def test_valid_scope(self):
        """Test valid scope configuration."""
        scope = ScopeConfig(level="sector", code="construction")
        assert scope.level == "sector"
        assert scope.code == "construction"

    def test_scope_without_code(self):
        """Test scope without code filter."""
        scope = ScopeConfig(level="nationality")
        assert scope.level == "nationality"
        assert scope.code is None

    def test_empty_level_rejected(self):
        """Test that empty level is rejected."""
        with pytest.raises(ValidationError):
            ScopeConfig(level="", code="test")

    def test_whitespace_level_stripped(self):
        """Test that whitespace in level is stripped."""
        scope = ScopeConfig(level="  sector  ")
        assert scope.level == "sector"


class TestWindowConfig:
    """Tests for WindowConfig validation."""

    def test_valid_window(self):
        """Test valid window configuration."""
        window = WindowConfig(months=6)
        assert window.months == 6

    def test_minimum_window(self):
        """Test minimum 3-month window."""
        window = WindowConfig(months=3)
        assert window.months == 3

    def test_window_below_minimum_rejected(self):
        """Test that window below 3 months is rejected."""
        with pytest.raises(ValidationError):
            WindowConfig(months=2)

        with pytest.raises(ValidationError):
            WindowConfig(months=0)

        with pytest.raises(ValidationError):
            WindowConfig(months=-1)


class TestTriggerConfig:
    """Tests for TriggerConfig validation."""

    def test_threshold_trigger(self):
        """Test threshold trigger with operator."""
        trigger = TriggerConfig(
            type=TriggerType.THRESHOLD,
            op=TriggerOperator.LTE,
            value=0.5,
        )
        assert trigger.type == TriggerType.THRESHOLD
        assert trigger.op == TriggerOperator.LTE
        assert trigger.value == 0.5

    def test_yoy_delta_trigger(self):
        """Test YoY delta percentage trigger."""
        trigger = TriggerConfig(
            type=TriggerType.YOY_DELTA_PCT,
            op=TriggerOperator.LTE,
            value=-5.0,
        )
        assert trigger.type == TriggerType.YOY_DELTA_PCT
        assert trigger.value == -5.0

    def test_slope_trigger(self):
        """Test slope window trigger."""
        trigger = TriggerConfig(
            type=TriggerType.SLOPE_WINDOW,
            op=TriggerOperator.LT,
            value=-0.01,
        )
        assert trigger.type == TriggerType.SLOPE_WINDOW
        assert trigger.value == -0.01

    def test_break_event_trigger(self):
        """Test structural break trigger."""
        trigger = TriggerConfig(
            type=TriggerType.BREAK_EVENT,
            value=5.0,
        )
        assert trigger.type == TriggerType.BREAK_EVENT
        assert trigger.value == 5.0

    def test_nan_value_rejected(self):
        """Test that NaN values are rejected."""
        with pytest.raises(ValidationError):
            TriggerConfig(
                type=TriggerType.THRESHOLD,
                op=TriggerOperator.GT,
                value=math.nan,
            )

    def test_inf_value_rejected(self):
        """Test that Inf values are rejected."""
        with pytest.raises(ValidationError):
            TriggerConfig(
                type=TriggerType.THRESHOLD,
                op=TriggerOperator.GT,
                value=math.inf,
            )

        with pytest.raises(ValidationError):
            TriggerConfig(
                type=TriggerType.THRESHOLD,
                op=TriggerOperator.GT,
                value=-math.inf,
            )

    def test_threshold_requires_operator(self):
        """Test that threshold trigger requires operator."""
        with pytest.raises(ValidationError):
            TriggerConfig(
                type=TriggerType.THRESHOLD,
                value=0.5,
            )


class TestAlertRule:
    """Tests for AlertRule validation."""

    def test_valid_rule(self):
        """Test valid complete alert rule."""
        rule = AlertRule(
            rule_id="retention_drop_construction",
            metric="retention",
            scope=ScopeConfig(level="sector", code="construction"),
            window=WindowConfig(months=6),
            trigger=TriggerConfig(
                type=TriggerType.YOY_DELTA_PCT,
                op=TriggerOperator.LTE,
                value=-5.0,
            ),
            horizon=12,
            severity=Severity.HIGH,
            description="Alert on 5% YoY retention drop in construction sector",
        )
        assert rule.rule_id == "retention_drop_construction"
        assert rule.metric == "retention"
        assert rule.horizon == 12
        assert rule.severity == Severity.HIGH
        assert rule.enabled is True

    def test_disabled_rule(self):
        """Test disabled rule."""
        rule = AlertRule(
            rule_id="test_rule",
            metric="salary",
            scope=ScopeConfig(level="sector"),
            window=WindowConfig(months=3),
            trigger=TriggerConfig(
                type=TriggerType.THRESHOLD,
                op=TriggerOperator.LT,
                value=3000.0,
            ),
            horizon=6,
            severity=Severity.MEDIUM,
            enabled=False,
        )
        assert rule.enabled is False

    def test_empty_rule_id_rejected(self):
        """Test that empty rule_id is rejected."""
        with pytest.raises(ValidationError):
            AlertRule(
                rule_id="",
                metric="retention",
                scope=ScopeConfig(level="sector"),
                window=WindowConfig(months=6),
                trigger=TriggerConfig(
                    type=TriggerType.THRESHOLD,
                    op=TriggerOperator.LT,
                    value=0.5,
                ),
                horizon=12,
                severity=Severity.LOW,
            )

    def test_empty_metric_rejected(self):
        """Test that empty metric is rejected."""
        with pytest.raises(ValidationError):
            AlertRule(
                rule_id="test",
                metric="",
                scope=ScopeConfig(level="sector"),
                window=WindowConfig(months=6),
                trigger=TriggerConfig(
                    type=TriggerType.THRESHOLD,
                    op=TriggerOperator.LT,
                    value=0.5,
                ),
                horizon=12,
                severity=Severity.LOW,
            )

    def test_horizon_bounds(self):
        """Test horizon validation bounds."""
        # Valid: 1 month
        rule = AlertRule(
            rule_id="test_min",
            metric="retention",
            scope=ScopeConfig(level="sector"),
            window=WindowConfig(months=3),
            trigger=TriggerConfig(
                type=TriggerType.THRESHOLD,
                op=TriggerOperator.LT,
                value=0.5,
            ),
            horizon=1,
            severity=Severity.LOW,
        )
        assert rule.horizon == 1

        # Valid: 96 months
        rule = AlertRule(
            rule_id="test_max",
            metric="retention",
            scope=ScopeConfig(level="sector"),
            window=WindowConfig(months=3),
            trigger=TriggerConfig(
                type=TriggerType.THRESHOLD,
                op=TriggerOperator.LT,
                value=0.5,
            ),
            horizon=96,
            severity=Severity.LOW,
        )
        assert rule.horizon == 96

        # Invalid: 0 months
        with pytest.raises(ValidationError):
            AlertRule(
                rule_id="test_zero",
                metric="retention",
                scope=ScopeConfig(level="sector"),
                window=WindowConfig(months=3),
                trigger=TriggerConfig(
                    type=TriggerType.THRESHOLD,
                    op=TriggerOperator.LT,
                    value=0.5,
                ),
                horizon=0,
                severity=Severity.LOW,
            )

        # Invalid: 97 months
        with pytest.raises(ValidationError):
            AlertRule(
                rule_id="test_over",
                metric="retention",
                scope=ScopeConfig(level="sector"),
                window=WindowConfig(months=3),
                trigger=TriggerConfig(
                    type=TriggerType.THRESHOLD,
                    op=TriggerOperator.LT,
                    value=0.5,
                ),
                horizon=97,
                severity=Severity.LOW,
            )

    def test_clamp_rate(self):
        """Test rate clamping to [0, 1]."""
        rule = AlertRule(
            rule_id="test_rate",
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

        assert rule.clamp_rate(-0.1) == 0.0
        assert rule.clamp_rate(0.5) == 0.5
        assert rule.clamp_rate(1.0) == 1.0
        assert rule.clamp_rate(1.5) == 1.0

    def test_is_rate_metric(self):
        """Test rate metric detection."""
        # Rate metrics
        rate_rule = AlertRule(
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
        assert rate_rule.is_rate_metric() is True

        # Non-rate metric
        count_rule = AlertRule(
            rule_id="test",
            metric="employment_count",
            scope=ScopeConfig(level="sector"),
            window=WindowConfig(months=3),
            trigger=TriggerConfig(
                type=TriggerType.THRESHOLD,
                op=TriggerOperator.LT,
                value=1000.0,
            ),
            horizon=12,
            severity=Severity.LOW,
        )
        assert count_rule.is_rate_metric() is False

    def test_severity_levels(self):
        """Test all severity levels."""
        for severity in [Severity.LOW, Severity.MEDIUM, Severity.HIGH, Severity.CRITICAL]:
            rule = AlertRule(
                rule_id=f"test_{severity.value}",
                metric="retention",
                scope=ScopeConfig(level="sector"),
                window=WindowConfig(months=3),
                trigger=TriggerConfig(
                    type=TriggerType.THRESHOLD,
                    op=TriggerOperator.LT,
                    value=0.5,
                ),
                horizon=12,
                severity=severity,
            )
            assert rule.severity == severity
