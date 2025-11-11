"""Unit tests for burn-rate alert trigger integration."""
from __future__ import annotations

from src.qnwis.alerts.engine import AlertEngine
from src.qnwis.alerts.rules import (
    AlertRule,
    ScopeConfig,
    Severity,
    TriggerConfig,
    TriggerType,
    WindowConfig,
)


def test_burn_rate_trigger_fires_on_threshold():
    """Burn-rate trigger fires when fast>=fast_th AND slow>=slow_th."""
    engine = AlertEngine()
    rule = AlertRule(
        rule_id="test_burn",
        metric="availability",
        scope=ScopeConfig(level="global", code=None),
        window=WindowConfig(months=3),
        trigger=TriggerConfig(type=TriggerType.BURN_RATE, fast_threshold=2.0, slow_threshold=1.0, value=0.0),
        horizon=12,
        severity=Severity.HIGH,
    )

    # Both exceed thresholds
    dec1 = engine.evaluate(rule, [2.1, 1.1])
    assert dec1.triggered
    assert dec1.evidence["tier"] == "critical"

    # Fast exceeds, slow does not
    dec2 = engine.evaluate(rule, [2.5, 0.9])
    assert not dec2.triggered

    # Slow exceeds, fast does not
    dec3 = engine.evaluate(rule, [1.5, 1.2])
    assert not dec3.triggered

    # Neither exceeds
    dec4 = engine.evaluate(rule, [0.5, 0.5])
    assert not dec4.triggered


def test_burn_rate_tier_classification():
    """Burn-rate evidence includes tier classification."""
    engine = AlertEngine()
    rule = AlertRule(
        rule_id="test_tier",
        metric="availability",
        scope=ScopeConfig(level="global", code=None),
        window=WindowConfig(months=3),
        trigger=TriggerConfig(type=TriggerType.BURN_RATE, fast_threshold=0.5, slow_threshold=0.5, value=0.0),
        horizon=12,
        severity=Severity.HIGH,
    )

    # CRITICAL: fast>=2.0 AND slow>=1.0
    dec_crit = engine.evaluate(rule, [2.0, 1.0])
    assert dec_crit.evidence["tier"] == "critical"

    # HIGH: fast>=1.0 AND slow>=1.0
    dec_high = engine.evaluate(rule, [1.0, 1.0])
    assert dec_high.evidence["tier"] == "high"

    # MEDIUM: fast>=1.0
    dec_med = engine.evaluate(rule, [1.0, 0.5])
    assert dec_med.evidence["tier"] == "medium"

    # LOW: slow>=1.0
    dec_low = engine.evaluate(rule, [0.5, 1.0])
    assert dec_low.evidence["tier"] == "low"

    # NONE: neither
    dec_none = engine.evaluate(rule, [0.5, 0.5])
    assert dec_none.evidence["tier"] == "none"


def test_burn_rate_single_value_fallback():
    """Single value in series is interpreted as slow burn."""
    engine = AlertEngine()
    rule = AlertRule(
        rule_id="test_single",
        metric="availability",
        scope=ScopeConfig(level="global", code=None),
        window=WindowConfig(months=3),
        trigger=TriggerConfig(type=TriggerType.BURN_RATE, fast_threshold=1.0, slow_threshold=1.0, value=0.0),
        horizon=12,
        severity=Severity.HIGH,
    )

    dec = engine.evaluate(rule, [1.5])
    assert dec.triggered
    assert dec.evidence["fast_burn"] == 1.5
    assert dec.evidence["slow_burn"] == 1.5


def test_burn_rate_rejects_nan_inf():
    """Burn-rate trigger rejects NaN/Inf values."""
    engine = AlertEngine()
    rule = AlertRule(
        rule_id="test_nan",
        metric="availability",
        scope=ScopeConfig(level="global", code=None),
        window=WindowConfig(months=3),
        trigger=TriggerConfig(type=TriggerType.BURN_RATE, fast_threshold=1.0, slow_threshold=1.0, value=0.0),
        horizon=12,
        severity=Severity.HIGH,
    )

    dec = engine.evaluate(rule, [float('nan'), 1.0])
    assert not dec.triggered
    assert "NaN or Inf" in dec.message
