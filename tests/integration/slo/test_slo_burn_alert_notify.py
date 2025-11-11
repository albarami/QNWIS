from __future__ import annotations

from pathlib import Path

from src.qnwis.agents.alert_center_notify import emit_notifications
from src.qnwis.alerts.engine import AlertEngine
from src.qnwis.alerts.rules import (
    AlertRule,
    ScopeConfig,
    Severity,
    TriggerConfig,
    TriggerType,
    WindowConfig,
)
from src.qnwis.notify.dispatcher import NotificationDispatcher
from src.qnwis.utils.clock import ManualClock


def test_burnrate_alert_triggers_notification(tmp_path: Path, monkeypatch):
    # Use a temporary ledger directory to avoid polluting repo
    ledger_dir = tmp_path / "incidents"
    clock = ManualClock()
    dispatcher = NotificationDispatcher(clock=clock, ledger_dir=ledger_dir, dry_run=True)

    # Burn-rate rule: CRITICAL tier thresholds
    rule = AlertRule(
        rule_id="slo_burn_critial_test",
        metric="availability",
        scope=ScopeConfig(level="global", code=None),
        window=WindowConfig(months=3),
        trigger=TriggerConfig(type=TriggerType.BURN_RATE, fast_threshold=2.0, slow_threshold=1.0, value=0.0),
        horizon=12,
        severity=Severity.HIGH,
    )

    engine = AlertEngine()
    decision = engine.evaluate(rule, [2.1, 1.1])
    assert decision.triggered, "Expected burn-rate rule to trigger"
    decision.timestamp = "2025-01-01T00:00:00Z"

    # Emit notification via helper
    emit_notifications([decision], [rule], dispatcher, clock)

    # Verify ledger entry written
    ledger_file = ledger_dir / "incidents.jsonl"
    assert ledger_file.exists(), "Expected ledger to be created"
    contents = ledger_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(contents) >= 1, "Expected at least one incident logged"
