"""Unit tests for notification models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.qnwis.notify.models import (
    Channel,
    EscalationPolicy,
    Incident,
    IncidentState,
    Notification,
    Severity,
    SuppressionWindow,
)


class TestSeverity:
    """Test Severity enum."""

    def test_severity_values(self) -> None:
        """Test all severity values."""
        assert Severity.INFO.value == "info"
        assert Severity.WARNING.value == "warning"
        assert Severity.ERROR.value == "error"
        assert Severity.CRITICAL.value == "critical"


class TestChannel:
    """Test Channel enum."""

    def test_channel_values(self) -> None:
        """Test all channel values."""
        assert Channel.EMAIL.value == "email"
        assert Channel.TEAMS.value == "teams"
        assert Channel.WEBHOOK.value == "webhook"


class TestIncidentState:
    """Test IncidentState enum."""

    def test_state_values(self) -> None:
        """Test all state values."""
        assert IncidentState.OPEN.value == "open"
        assert IncidentState.ACK.value == "ack"
        assert IncidentState.SILENCED.value == "silenced"
        assert IncidentState.RESOLVED.value == "resolved"


class TestSuppressionWindow:
    """Test SuppressionWindow model."""

    def test_valid_window(self) -> None:
        """Test valid suppression window."""
        window = SuppressionWindow(
            start_time="2024-01-01T00:00:00Z",
            end_time="2024-01-01T01:00:00Z",
        )
        assert window.start_time == "2024-01-01T00:00:00Z"
        assert window.end_time == "2024-01-01T01:00:00Z"

    def test_immutable(self) -> None:
        """Test window is frozen/immutable."""
        window = SuppressionWindow(
            start_time="2024-01-01T00:00:00Z",
            end_time="2024-01-01T01:00:00Z",
        )
        with pytest.raises(ValidationError):
            window.start_time = "2024-01-02T00:00:00Z"  # type: ignore


class TestEscalationPolicy:
    """Test EscalationPolicy model."""

    def test_default_policy(self) -> None:
        """Test policy with defaults."""
        policy = EscalationPolicy(name="default")
        assert policy.name == "default"
        assert policy.channels == []
        assert policy.escalate_after_minutes == 15
        assert policy.max_retries == 3

    def test_custom_policy(self) -> None:
        """Test custom escalation policy."""
        policy = EscalationPolicy(
            name="critical",
            channels=[Channel.EMAIL, Channel.TEAMS, Channel.WEBHOOK],
            escalate_after_minutes=5,
            max_retries=5,
        )
        assert policy.name == "critical"
        assert len(policy.channels) == 3
        assert policy.escalate_after_minutes == 5
        assert policy.max_retries == 5


class TestNotification:
    """Test Notification model."""

    def test_valid_notification(self) -> None:
        """Test valid notification creation."""
        notification = Notification(
            notification_id="test_001",
            rule_id="rule_retention_low",
            severity=Severity.WARNING,
            message="Retention below threshold",
            scope={"level": "sector", "code": "010"},
            window_start="2024-01-01T00:00:00Z",
            window_end="2024-01-01T23:59:59Z",
            channels=[Channel.EMAIL],
            evidence={"retention_rate": 0.65},
            timestamp="2024-01-02T00:00:00Z",
        )

        assert notification.notification_id == "test_001"
        assert notification.rule_id == "rule_retention_low"
        assert notification.severity == Severity.WARNING
        assert notification.message == "Retention below threshold"
        assert notification.scope["level"] == "sector"
        assert notification.channels == [Channel.EMAIL]
        assert notification.evidence["retention_rate"] == 0.65

    def test_notification_defaults(self) -> None:
        """Test notification with defaults."""
        notification = Notification(
            notification_id="test_002",
            rule_id="test_rule",
            severity=Severity.INFO,
            message="Test message",
            window_start="2024-01-01T00:00:00Z",
            window_end="2024-01-01T23:59:59Z",
            timestamp="2024-01-02T00:00:00Z",
        )

        assert notification.scope == {}
        assert notification.channels == [Channel.EMAIL]
        assert notification.evidence == {}

    def test_notification_immutable(self) -> None:
        """Test notification is frozen."""
        notification = Notification(
            notification_id="test_003",
            rule_id="test_rule",
            severity=Severity.INFO,
            message="Test",
            window_start="2024-01-01T00:00:00Z",
            window_end="2024-01-01T23:59:59Z",
            timestamp="2024-01-02T00:00:00Z",
        )

        with pytest.raises(ValidationError):
            notification.message = "Changed"  # type: ignore


class TestIncident:
    """Test Incident model."""

    def test_valid_incident(self) -> None:
        """Test valid incident creation."""
        incident = Incident(
            incident_id="inc_001",
            notification_id="notif_001",
            rule_id="rule_001",
            severity=Severity.ERROR,
            state=IncidentState.OPEN,
            message="Test incident",
            scope={"level": "national"},
            window_start="2024-01-01T00:00:00Z",
            window_end="2024-01-01T23:59:59Z",
            created_at="2024-01-02T00:00:00Z",
            updated_at="2024-01-02T00:00:00Z",
        )

        assert incident.incident_id == "inc_001"
        assert incident.notification_id == "notif_001"
        assert incident.state == IncidentState.OPEN
        assert incident.consecutive_green_count == 0
        assert incident.ack_at is None
        assert incident.resolved_at is None

    def test_incident_with_resolution(self) -> None:
        """Test incident with ack and resolution timestamps."""
        incident = Incident(
            incident_id="inc_002",
            notification_id="notif_002",
            rule_id="rule_002",
            severity=Severity.WARNING,
            state=IncidentState.RESOLVED,
            message="Test",
            scope={},
            window_start="2024-01-01T00:00:00Z",
            window_end="2024-01-01T23:59:59Z",
            created_at="2024-01-02T00:00:00Z",
            updated_at="2024-01-02T01:00:00Z",
            ack_at="2024-01-02T00:30:00Z",
            resolved_at="2024-01-02T01:00:00Z",
            consecutive_green_count=5,
        )

        assert incident.state == IncidentState.RESOLVED
        assert incident.ack_at == "2024-01-02T00:30:00Z"
        assert incident.resolved_at == "2024-01-02T01:00:00Z"
        assert incident.consecutive_green_count == 5

    def test_incident_metadata(self) -> None:
        """Test incident with metadata."""
        incident = Incident(
            incident_id="inc_003",
            notification_id="notif_003",
            rule_id="rule_003",
            severity=Severity.INFO,
            message="Test",
            scope={},
            window_start="2024-01-01T00:00:00Z",
            window_end="2024-01-01T23:59:59Z",
            created_at="2024-01-02T00:00:00Z",
            updated_at="2024-01-02T00:00:00Z",
            metadata={"dispatch_results": {"email": "success"}},
        )

        assert "dispatch_results" in incident.metadata
        assert incident.metadata["dispatch_results"]["email"] == "success"
