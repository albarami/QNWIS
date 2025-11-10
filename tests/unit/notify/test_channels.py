"""Unit tests for notification channels."""

from __future__ import annotations

import pytest

from src.qnwis.notify.channels.email import EmailChannel
from src.qnwis.notify.channels.teams import TeamsChannel
from src.qnwis.notify.channels.webhook import WebhookChannel
from src.qnwis.notify.models import Channel, Notification, Severity


@pytest.fixture
def sample_notification() -> Notification:
    """Create a sample notification for testing."""
    return Notification(
        notification_id="test_001",
        rule_id="rule_test",
        severity=Severity.WARNING,
        message="Test notification message",
        scope={"level": "sector", "code": "010"},
        window_start="2024-01-01T00:00:00Z",
        window_end="2024-01-01T23:59:59Z",
        channels=[Channel.EMAIL],
        evidence={"metric": 0.65, "threshold": 0.70},
        timestamp="2024-01-15T12:00:00Z",
    )


class TestEmailChannel:
    """Test EmailChannel."""

    def test_dry_run_mode(self, sample_notification: Notification) -> None:
        """Test email channel in dry-run mode."""
        channel = EmailChannel(dry_run=True)
        result = channel.send(sample_notification)
        assert result == "dry_run_success"

    def test_format_text(self, sample_notification: Notification) -> None:
        """Test plain text formatting."""
        channel = EmailChannel(dry_run=True)
        text = channel._format_text(sample_notification)

        assert "QNWIS Alert: rule_test" in text
        assert "Severity: WARNING" in text
        assert "Test notification message" in text
        assert "Window: 2024-01-01T00:00:00Z to 2024-01-01T23:59:59Z" in text
        assert "metric: 0.65" in text
        assert "threshold: 0.7" in text

    def test_format_html(self, sample_notification: Notification) -> None:
        """Test HTML formatting."""
        channel = EmailChannel(dry_run=True)
        html = channel._format_html(sample_notification)

        assert "QNWIS Alert: rule_test" in html
        assert "WARNING" in html
        assert "Test notification message" in html
        assert "<html>" in html
        assert "</html>" in html
        assert "Evidence" in html

    def test_severity_colors(self) -> None:
        """Test different severity colors in HTML."""
        channel = EmailChannel(dry_run=True)

        for severity in [Severity.INFO, Severity.WARNING, Severity.ERROR, Severity.CRITICAL]:
            notification = Notification(
                notification_id="test",
                rule_id="rule",
                severity=severity,
                message="Test",
                scope={},
                window_start="2024-01-01T00:00:00Z",
                window_end="2024-01-01T23:59:59Z",
                timestamp="2024-01-15T12:00:00Z",
            )
            html = channel._format_html(notification)
            assert severity.value.upper() in html


class TestTeamsChannel:
    """Test TeamsChannel."""

    def test_dry_run_mode(self, sample_notification: Notification) -> None:
        """Test Teams channel in dry-run mode."""
        channel = TeamsChannel(dry_run=True)
        result = channel.send(sample_notification)
        assert result == "dry_run_success"

    def test_build_payload_structure(self, sample_notification: Notification) -> None:
        """Test Teams adaptive card payload structure."""
        channel = TeamsChannel(dry_run=True)
        payload = channel._build_payload(sample_notification)

        assert payload["type"] == "message"
        assert "attachments" in payload
        assert len(payload["attachments"]) == 1

        card = payload["attachments"][0]["content"]
        assert card["type"] == "AdaptiveCard"
        assert card["version"] == "1.2"
        assert "body" in card

    def test_build_payload_facts(self, sample_notification: Notification) -> None:
        """Test Teams payload includes all facts."""
        channel = TeamsChannel(dry_run=True)
        payload = channel._build_payload(sample_notification)

        card = payload["attachments"][0]["content"]
        fact_set = next((item for item in card["body"] if item["type"] == "FactSet"), None)

        assert fact_set is not None
        facts = fact_set["facts"]

        fact_names = [f["name"] for f in facts]
        assert "Rule ID" in fact_names
        assert "Severity" in fact_names
        assert "Time" in fact_names
        assert "Window" in fact_names
        assert "Metric" in fact_names  # From evidence


class TestWebhookChannel:
    """Test WebhookChannel."""

    def test_dry_run_mode(self, sample_notification: Notification) -> None:
        """Test webhook channel in dry-run mode."""
        channel = WebhookChannel(dry_run=True)
        result = channel.send(sample_notification)
        assert result == "dry_run_success"

    def test_compute_signature(self, sample_notification: Notification) -> None:
        """Test HMAC signature computation."""
        channel = WebhookChannel(dry_run=True)
        channel.webhook_secret = "test_secret"

        payload = sample_notification.model_dump()
        signature = channel._compute_signature(payload)

        # Signature should be hex string
        assert isinstance(signature, str)
        assert len(signature) == 64  # SHA256 hex digest

        # Same payload should produce same signature
        signature2 = channel._compute_signature(payload)
        assert signature == signature2

    def test_signature_deterministic(self) -> None:
        """Test signature is deterministic for same input."""
        channel = WebhookChannel(dry_run=True)
        channel.webhook_secret = "test_secret"

        payload1 = {"rule_id": "rule_001", "message": "Test"}
        payload2 = {"rule_id": "rule_001", "message": "Test"}

        sig1 = channel._compute_signature(payload1)
        sig2 = channel._compute_signature(payload2)

        assert sig1 == sig2

    def test_signature_different_for_different_payload(self) -> None:
        """Test signature differs for different payloads."""
        channel = WebhookChannel(dry_run=True)
        channel.webhook_secret = "test_secret"

        payload1 = {"rule_id": "rule_001", "message": "Test1"}
        payload2 = {"rule_id": "rule_001", "message": "Test2"}

        sig1 = channel._compute_signature(payload1)
        sig2 = channel._compute_signature(payload2)

        assert sig1 != sig2
