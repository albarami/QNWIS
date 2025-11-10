"""
Unit tests for alert engine evaluation logic.

Tests each trigger type with edge cases and guard conditions.
"""

import math

import pytest

from src.qnwis.alerts.engine import AlertEngine
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
def engine():
    """Create AlertEngine instance."""
    return AlertEngine()


class TestAlertEngine:
    """Tests for AlertEngine core functionality."""

    def test_empty_series(self, engine):
        """Test evaluation with empty series."""
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

        decision = engine.evaluate(rule, [], [])
        assert decision.triggered is False
        assert "Empty series" in decision.message

    def test_nan_in_series(self, engine):
        """Test that NaN in series is rejected."""
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

        decision = engine.evaluate(rule, [0.5, math.nan, 0.6], [])
        assert decision.triggered is False
        assert "NaN or Inf" in decision.message

    def test_inf_in_series(self, engine):
        """Test that Inf in series is rejected."""
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

        decision = engine.evaluate(rule, [0.5, math.inf, 0.6], [])
        assert decision.triggered is False
        assert "NaN or Inf" in decision.message

    def test_rate_clamping(self, engine):
        """Test that rate metrics are clamped to [0, 1]."""
        rule = AlertRule(
            rule_id="test",
            metric="retention_rate",
            scope=ScopeConfig(level="sector"),
            window=WindowConfig(months=3),
            trigger=TriggerConfig(
                type=TriggerType.THRESHOLD,
                op=TriggerOperator.GT,
                value=0.9,
            ),
            horizon=12,
            severity=Severity.LOW,
        )

        # Values outside [0, 1] should be clamped
        decision = engine.evaluate(rule, [-0.1, 1.5, 0.8], [])
        # Clamped: [0.0, 1.0, 0.8]
        # Most recent: 0.8, which is not > 0.9
        assert decision.triggered is False


class TestThresholdTrigger:
    """Tests for threshold-based triggers."""

    def test_lt_trigger_fires(self, engine):
        """Test less-than trigger fires when condition met."""
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

        decision = engine.evaluate(rule, [0.6, 0.5, 0.4], [])
        assert decision.triggered is True
        assert decision.evidence["current_value"] == 0.4

    def test_lt_trigger_not_fires(self, engine):
        """Test less-than trigger doesn't fire when condition not met."""
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

        decision = engine.evaluate(rule, [0.6, 0.5, 0.6], [])
        assert decision.triggered is False

    def test_lte_trigger(self, engine):
        """Test less-than-or-equal trigger."""
        rule = AlertRule(
            rule_id="test",
            metric="retention",
            scope=ScopeConfig(level="sector"),
            window=WindowConfig(months=3),
            trigger=TriggerConfig(
                type=TriggerType.THRESHOLD,
                op=TriggerOperator.LTE,
                value=0.5,
            ),
            horizon=12,
            severity=Severity.LOW,
        )

        # Equal: should trigger
        decision = engine.evaluate(rule, [0.6, 0.5, 0.5], [])
        assert decision.triggered is True

        # Less: should trigger
        decision = engine.evaluate(rule, [0.6, 0.5, 0.4], [])
        assert decision.triggered is True

        # Greater: should not trigger
        decision = engine.evaluate(rule, [0.6, 0.5, 0.6], [])
        assert decision.triggered is False

    def test_gt_trigger(self, engine):
        """Test greater-than trigger."""
        rule = AlertRule(
            rule_id="test",
            metric="salary",
            scope=ScopeConfig(level="sector"),
            window=WindowConfig(months=3),
            trigger=TriggerConfig(
                type=TriggerType.THRESHOLD,
                op=TriggerOperator.GT,
                value=10000.0,
            ),
            horizon=12,
            severity=Severity.LOW,
        )

        decision = engine.evaluate(rule, [9000.0, 10000.0, 11000.0], [])
        assert decision.triggered is True
        assert decision.evidence["current_value"] == 11000.0

    def test_gte_trigger(self, engine):
        """Test greater-than-or-equal trigger."""
        rule = AlertRule(
            rule_id="test",
            metric="salary",
            scope=ScopeConfig(level="sector"),
            window=WindowConfig(months=3),
            trigger=TriggerConfig(
                type=TriggerType.THRESHOLD,
                op=TriggerOperator.GTE,
                value=10000.0,
            ),
            horizon=12,
            severity=Severity.LOW,
        )

        # Equal: should trigger
        decision = engine.evaluate(rule, [9000.0, 10000.0, 10000.0], [])
        assert decision.triggered is True

    def test_eq_trigger(self, engine):
        """Test equality trigger."""
        rule = AlertRule(
            rule_id="test",
            metric="count",
            scope=ScopeConfig(level="sector"),
            window=WindowConfig(months=3),
            trigger=TriggerConfig(
                type=TriggerType.THRESHOLD,
                op=TriggerOperator.EQ,
                value=100.0,
            ),
            horizon=12,
            severity=Severity.LOW,
        )

        decision = engine.evaluate(rule, [99.0, 100.0, 100.0], [])
        assert decision.triggered is True


class TestYoYDeltaTrigger:
    """Tests for year-over-year delta percentage trigger."""

    def test_yoy_insufficient_data(self, engine):
        """Test YoY with insufficient data (< 13 points)."""
        rule = AlertRule(
            rule_id="test",
            metric="retention",
            scope=ScopeConfig(level="sector"),
            window=WindowConfig(months=6),
            trigger=TriggerConfig(
                type=TriggerType.YOY_DELTA_PCT,
                op=TriggerOperator.LTE,
                value=-5.0,
            ),
            horizon=12,
            severity=Severity.LOW,
        )

        decision = engine.evaluate(rule, [0.5] * 12, [])
        assert decision.triggered is False
        assert "Insufficient data for YoY" in decision.message

    def test_yoy_drop_triggers(self, engine):
        """Test YoY drop trigger fires on decline."""
        rule = AlertRule(
            rule_id="test",
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
        )

        # 13 months: steady at 0.5, then drop to 0.45 (10% drop)
        series = [0.5] * 12 + [0.45]
        decision = engine.evaluate(rule, series, [])
        assert decision.triggered is True
        assert decision.evidence["yoy_delta_pct"] <= -5.0

    def test_yoy_rise_not_triggers(self, engine):
        """Test YoY rise doesn't trigger drop alert."""
        rule = AlertRule(
            rule_id="test",
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
        )

        # 13 months: steady at 0.5, then rise to 0.55 (10% rise)
        series = [0.5] * 12 + [0.55]
        decision = engine.evaluate(rule, series, [])
        assert decision.triggered is False


class TestSlopeWindowTrigger:
    """Tests for slope-based triggers."""

    def test_slope_insufficient_data(self, engine):
        """Test slope with insufficient data."""
        rule = AlertRule(
            rule_id="test",
            metric="retention",
            scope=ScopeConfig(level="sector"),
            window=WindowConfig(months=6),
            trigger=TriggerConfig(
                type=TriggerType.SLOPE_WINDOW,
                op=TriggerOperator.LT,
                value=-0.01,
            ),
            horizon=12,
            severity=Severity.LOW,
        )

        decision = engine.evaluate(rule, [0.5, 0.48, 0.46], [])
        assert decision.triggered is False
        assert "Insufficient data for window" in decision.message

    def test_negative_slope_triggers(self, engine):
        """Test negative slope trigger fires on decline."""
        rule = AlertRule(
            rule_id="test",
            metric="retention",
            scope=ScopeConfig(level="sector"),
            window=WindowConfig(months=3),
            trigger=TriggerConfig(
                type=TriggerType.SLOPE_WINDOW,
                op=TriggerOperator.LT,
                value=-0.01,
            ),
            horizon=12,
            severity=Severity.MEDIUM,
        )

        # Declining series
        series = [0.5, 0.48, 0.46, 0.44, 0.42, 0.40]
        decision = engine.evaluate(rule, series, [])
        assert decision.triggered is True
        assert decision.evidence["slope"] < -0.01

    def test_positive_slope_not_triggers(self, engine):
        """Test positive slope doesn't trigger decline alert."""
        rule = AlertRule(
            rule_id="test",
            metric="retention",
            scope=ScopeConfig(level="sector"),
            window=WindowConfig(months=3),
            trigger=TriggerConfig(
                type=TriggerType.SLOPE_WINDOW,
                op=TriggerOperator.LT,
                value=-0.01,
            ),
            horizon=12,
            severity=Severity.MEDIUM,
        )

        # Rising series
        series = [0.40, 0.42, 0.44, 0.46, 0.48, 0.50]
        decision = engine.evaluate(rule, series, [])
        assert decision.triggered is False


class TestBreakEventTrigger:
    """Tests for structural break detection trigger."""

    def test_break_insufficient_data(self, engine):
        """Test break detection with insufficient data."""
        rule = AlertRule(
            rule_id="test",
            metric="retention",
            scope=ScopeConfig(level="sector"),
            window=WindowConfig(months=12),
            trigger=TriggerConfig(
                type=TriggerType.BREAK_EVENT,
                value=5.0,
            ),
            horizon=12,
            severity=Severity.CRITICAL,
        )

        decision = engine.evaluate(rule, [0.5] * 6, [])
        assert decision.triggered is False
        assert "Insufficient data for break" in decision.message

    def test_break_detected(self, engine):
        """Test structural break detection fires on level shift."""
        rule = AlertRule(
            rule_id="test",
            metric="retention",
            scope=ScopeConfig(level="sector"),
            window=WindowConfig(months=12),
            trigger=TriggerConfig(
                type=TriggerType.BREAK_EVENT,
                value=3.0,  # Lower threshold for easier detection
            ),
            horizon=12,
            severity=Severity.CRITICAL,
        )

        # Level shift: stable at 0.5, then jump to 0.7
        series = [0.5] * 6 + [0.7] * 6
        decision = engine.evaluate(rule, series, [])
        assert decision.triggered is True
        assert decision.evidence["break_count"] > 0

    def test_no_break_stable_series(self, engine):
        """Test no break detected in stable series."""
        rule = AlertRule(
            rule_id="test",
            metric="retention",
            scope=ScopeConfig(level="sector"),
            window=WindowConfig(months=12),
            trigger=TriggerConfig(
                type=TriggerType.BREAK_EVENT,
                value=5.0,
            ),
            horizon=12,
            severity=Severity.CRITICAL,
        )

        # Stable series with minor noise
        series = [0.5 + i * 0.001 for i in range(12)]
        decision = engine.evaluate(rule, series, [])
        assert decision.triggered is False


class TestBatchEvaluation:
    """Tests for batch evaluation."""

    def test_batch_evaluate_multiple_rules(self, engine):
        """Test batch evaluation of multiple rules."""
        rules = [
            AlertRule(
                rule_id="rule1",
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
                rule_id="rule2",
                metric="retention",
                scope=ScopeConfig(level="sector"),
                window=WindowConfig(months=3),
                trigger=TriggerConfig(
                    type=TriggerType.THRESHOLD,
                    op=TriggerOperator.GT,
                    value=0.8,
                ),
                horizon=12,
                severity=Severity.LOW,
            ),
        ]

        def data_provider(rule):
            if rule.rule_id == "rule1":
                return [0.6, 0.5, 0.4], []  # Triggers rule1
            else:
                return [0.7, 0.8, 0.85], []  # Triggers rule2

        decisions = engine.batch_evaluate(rules, data_provider)
        assert len(decisions) == 2
        assert decisions[0].rule_id == "rule1"
        assert decisions[0].triggered is True
        assert decisions[1].rule_id == "rule2"
        assert decisions[1].triggered is True

    def test_batch_disabled_rule_skipped(self, engine):
        """Test that disabled rules are skipped in batch."""
        rules = [
            AlertRule(
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
            ),
            AlertRule(
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
            ),
        ]

        def data_provider(rule):
            return [0.4], []

        decisions = engine.batch_evaluate(rules, data_provider)
        assert len(decisions) == 2
        assert decisions[1].triggered is False
        assert "disabled" in decisions[1].message
