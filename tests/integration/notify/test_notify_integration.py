"""Integration tests for notification system."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from src.qnwis.notify.dispatcher import NotificationDispatcher
from src.qnwis.notify.models import Channel, Notification, Severity
from src.qnwis.notify.resolver import IncidentResolver
from src.qnwis.utils.clock import Clock


@pytest.fixture
def fixed_clock() -> Clock:
    """Fixed clock for testing."""
    return Clock(now=lambda: datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC), perf_counter=lambda: 1000.0)


@pytest.fixture
def temp_ledger(tmp_path: Path) -> Path:
    """Temporary ledger directory."""
    ledger_dir = tmp_path / "incidents"
    ledger_dir.mkdir()
    return ledger_dir


def test_alert_to_incident_flow(fixed_clock: Clock, temp_ledger: Path) -> None:
    """Test full flow: alert → notification → incident."""
    dispatcher = NotificationDispatcher(clock=fixed_clock, ledger_dir=temp_ledger, dry_run=True)
    resolver = IncidentResolver(clock=fixed_clock, ledger_dir=temp_ledger)

    # Create notification
    notification = Notification(
        notification_id="flow_test_001",
        rule_id="rule_flow",
        severity=Severity.WARNING,
        message="Integration test alert",
        scope={"level": "sector", "code": "010"},
        window_start="2024-01-01T00:00:00Z",
        window_end="2024-01-01T23:59:59Z",
        channels=[Channel.EMAIL, Channel.TEAMS],
        evidence={"test": "value"},
        timestamp=fixed_clock.now_iso(),
    )

    # Dispatch
    results = dispatcher.dispatch(notification)
    assert results["email"] == "dry_run_success"
    assert results["teams"] == "dry_run_success"

    # Check incident created
    incident = resolver.get_incident("flow_test_001")
    assert incident is not None
    assert incident.rule_id == "rule_flow"
    assert incident.severity == Severity.WARNING

    # Acknowledge
    ack_incident = resolver.acknowledge("flow_test_001")
    assert ack_incident.state.value == "ack"

    # Resolve
    resolved_incident = resolver.resolve("flow_test_001")
    assert resolved_incident.state.value == "resolved"


def test_auto_resolution_flow(fixed_clock: Clock, temp_ledger: Path) -> None:
    """Test auto-resolution after consecutive green evaluations."""
    resolver = IncidentResolver(clock=fixed_clock, ledger_dir=temp_ledger, auto_resolve_threshold=3)

    # Create incident via dispatcher
    from src.qnwis.notify.models import Incident, IncidentState

    incident = Incident(
        incident_id="auto_res_001",
        notification_id="auto_res_001",
        rule_id="rule_auto",
        severity=Severity.WARNING,
        state=IncidentState.OPEN,
        message="Test",
        scope={},
        window_start="2024-01-01T00:00:00Z",
        window_end="2024-01-01T23:59:59Z",
        created_at=fixed_clock.now_iso(),
        updated_at=fixed_clock.now_iso(),
    )
    resolver._incidents[incident.incident_id] = incident

    # Record 3 green evaluations
    for _ in range(3):
        resolved = resolver.record_green_evaluation("rule_auto")

    assert len(resolved) == 1
    assert resolved[0].state == IncidentState.RESOLVED
    assert resolved[0].metadata.get("auto_resolved") is True
