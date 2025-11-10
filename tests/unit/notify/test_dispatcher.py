"""Unit tests for notification dispatcher."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from src.qnwis.notify.dispatcher import NotificationDispatcher
from src.qnwis.notify.models import Channel, Notification, Severity
from src.qnwis.utils.clock import Clock, ManualClock


@pytest.fixture
def fixed_clock() -> Clock:
    """Create a fixed clock for deterministic tests."""
    fixed_time = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)
    return Clock(now=lambda: fixed_time, perf_counter=lambda: 1000.0)


@pytest.fixture
def temp_ledger(tmp_path: Path) -> Path:
    """Create temporary ledger directory."""
    ledger_dir = tmp_path / "incidents"
    ledger_dir.mkdir()
    return ledger_dir


@pytest.fixture
def manual_clock() -> ManualClock:
    """Provide manually advanceable clock for rate limit tests."""
    start_time = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)
    return ManualClock(start=start_time)


class TestNotificationDispatcher:
    """Test NotificationDispatcher."""

    def test_compute_idempotency_key_deterministic(self, fixed_clock: Clock) -> None:
        """Test idempotency key is deterministic."""
        dispatcher = NotificationDispatcher(clock=fixed_clock, dry_run=True)

        key1 = dispatcher.compute_idempotency_key(
            rule_id="rule_001",
            scope={"level": "sector", "code": "010"},
            window_start="2024-01-01T00:00:00Z",
            window_end="2024-01-01T23:59:59Z",
        )

        key2 = dispatcher.compute_idempotency_key(
            rule_id="rule_001",
            scope={"level": "sector", "code": "010"},
            window_start="2024-01-01T00:00:00Z",
            window_end="2024-01-01T23:59:59Z",
        )

        assert key1 == key2
        assert len(key1) == 64  # SHA256 hex

    def test_compute_idempotency_key_different_params(self, fixed_clock: Clock) -> None:
        """Test different params produce different keys."""
        dispatcher = NotificationDispatcher(clock=fixed_clock, dry_run=True)

        key1 = dispatcher.compute_idempotency_key(
            rule_id="rule_001",
            scope={"level": "sector", "code": "010"},
            window_start="2024-01-01T00:00:00Z",
            window_end="2024-01-01T23:59:59Z",
        )

        key2 = dispatcher.compute_idempotency_key(
            rule_id="rule_002",  # Different rule
            scope={"level": "sector", "code": "010"},
            window_start="2024-01-01T00:00:00Z",
            window_end="2024-01-01T23:59:59Z",
        )

        assert key1 != key2

    def test_dispatch_dry_run(self, fixed_clock: Clock, temp_ledger: Path) -> None:
        """Test dispatch in dry-run mode."""
        dispatcher = NotificationDispatcher(clock=fixed_clock, ledger_dir=temp_ledger, dry_run=True)

        notification = Notification(
            notification_id="test_001",
            rule_id="rule_retention",
            severity=Severity.WARNING,
            message="Test notification",
            scope={},
            window_start="2024-01-01T00:00:00Z",
            window_end="2024-01-01T23:59:59Z",
            channels=[Channel.EMAIL],
            evidence={},
            timestamp="2024-01-15T12:00:00Z",
        )

        results = dispatcher.dispatch(notification)

        assert "email" in results
        assert results["email"] == "dry_run_success"

    def test_dispatch_deduplication(self, fixed_clock: Clock, temp_ledger: Path) -> None:
        """Test dispatch deduplicates identical notifications."""
        dispatcher = NotificationDispatcher(clock=fixed_clock, ledger_dir=temp_ledger, dry_run=True)

        notification = Notification(
            notification_id="test_dedupe",
            rule_id="rule_test",
            severity=Severity.INFO,
            message="Test",
            scope={},
            window_start="2024-01-01T00:00:00Z",
            window_end="2024-01-01T23:59:59Z",
            channels=[Channel.EMAIL],
            evidence={},
            timestamp="2024-01-15T12:00:00Z",
        )

        # First dispatch
        result1 = dispatcher.dispatch(notification)
        assert result1["email"] == "dry_run_success"

        # Second dispatch (duplicate)
        result2 = dispatcher.dispatch(notification)
        assert result2["status"] == "deduplicated"

    def test_dispatch_rate_limiting(self, fixed_clock: Clock, temp_ledger: Path) -> None:
        """Test dispatch respects rate limits."""
        dispatcher = NotificationDispatcher(
            clock=fixed_clock,
            ledger_dir=temp_ledger,
            rate_limit_per_rule=2,
            dry_run=True,
        )

        # Send notifications up to limit
        for i in range(2):
            notification = Notification(
                notification_id=f"test_rate_{i}",
                rule_id="rule_limited",
                severity=Severity.INFO,
                message=f"Test {i}",
                scope={},
                window_start="2024-01-01T00:00:00Z",
                window_end="2024-01-01T23:59:59Z",
                channels=[Channel.EMAIL],
                evidence={},
                timestamp="2024-01-15T12:00:00Z",
            )
            result = dispatcher.dispatch(notification)
            assert "email" in result

        # Exceed limit
        notification = Notification(
            notification_id="test_rate_exceed",
            rule_id="rule_limited",
            severity=Severity.INFO,
            message="Should be rate limited",
            scope={},
            window_start="2024-01-01T00:00:00Z",
            window_end="2024-01-01T23:59:59Z",
            channels=[Channel.EMAIL],
            evidence={},
            timestamp="2024-01-15T12:00:00Z",
        )
        result = dispatcher.dispatch(notification)
        assert result["status"] == "rate_limited"

    def test_rate_limit_window_resets_after_interval(self, manual_clock: ManualClock, temp_ledger: Path) -> None:
        """Rate limit permits dispatch once window fully elapses."""
        dispatcher = NotificationDispatcher(
            clock=manual_clock,
            ledger_dir=temp_ledger,
            rate_limit_per_rule=2,
            rate_limit_window_minutes=1,
            dry_run=True,
        )

        def _notification(idx: int) -> Notification:
            return Notification(
                notification_id=f"window_test_{idx}",
                rule_id="rule_window",
                severity=Severity.INFO,
                message=f"Window notification {idx}",
                scope={},
                window_start="2024-01-01T00:00:00Z",
                window_end="2024-01-01T23:59:59Z",
                channels=[Channel.EMAIL],
                evidence={},
                timestamp=manual_clock.now_iso(),
            )

        for i in range(2):
            result = dispatcher.dispatch(_notification(i))
            assert "email" in result

        blocked = dispatcher.dispatch(_notification(2))
        assert blocked["status"] == "rate_limited"

        manual_clock.advance(61)
        allowed = dispatcher.dispatch(_notification(3))
        assert "email" in allowed

    def test_dispatch_suppression(self, fixed_clock: Clock, temp_ledger: Path) -> None:
        """Test dispatch respects suppression windows."""
        dispatcher = NotificationDispatcher(clock=fixed_clock, ledger_dir=temp_ledger, dry_run=True)

        # Suppress rule
        dispatcher.suppress("rule_suppressed", duration_minutes=60)

        # Try to dispatch
        notification = Notification(
            notification_id="test_suppressed",
            rule_id="rule_suppressed",
            severity=Severity.WARNING,
            message="Should be suppressed",
            scope={},
            window_start="2024-01-01T00:00:00Z",
            window_end="2024-01-01T23:59:59Z",
            channels=[Channel.EMAIL],
            evidence={},
            timestamp="2024-01-15T12:00:00Z",
        )
        result = dispatcher.dispatch(notification)
        assert result["status"] == "suppressed"

    def test_suppress_and_clear(self, fixed_clock: Clock, temp_ledger: Path) -> None:
        """Test suppress and clear suppression."""
        dispatcher = NotificationDispatcher(clock=fixed_clock, ledger_dir=temp_ledger, dry_run=True)

        # Suppress
        success = dispatcher.suppress("rule_test", duration_minutes=30)
        assert success is True

        # Clear
        success = dispatcher.clear_suppression("rule_test")
        assert success is True

        # Clear non-existent
        success = dispatcher.clear_suppression("rule_nonexistent")
        assert success is False

    def test_persist_to_ledger(self, fixed_clock: Clock, temp_ledger: Path) -> None:
        """Test notification persistence to ledger."""
        dispatcher = NotificationDispatcher(clock=fixed_clock, ledger_dir=temp_ledger, dry_run=True)

        notification = Notification(
            notification_id="test_persist",
            rule_id="rule_persist",
            severity=Severity.ERROR,
            message="Test persistence",
            scope={"level": "national"},
            window_start="2024-01-01T00:00:00Z",
            window_end="2024-01-01T23:59:59Z",
            channels=[Channel.EMAIL, Channel.TEAMS],
            evidence={"test": "value"},
            timestamp="2024-01-15T12:00:00Z",
        )

        dispatcher.dispatch(notification)

        # Check ledger file
        ledger_file = temp_ledger / "incidents.jsonl"
        assert ledger_file.exists()

        # Check envelope
        envelope_file = temp_ledger / "test_persist.envelope.json"
        assert envelope_file.exists()

        # Verify envelope structure
        with open(envelope_file, encoding="utf-8") as f:
            envelope = json.load(f)

        assert envelope["incident_id"] == "test_persist"
        assert "payload" in envelope
        assert "signature" in envelope
        assert envelope["algorithm"] == "sha256"

        # Verify signature
        expected_sig = hashlib.sha256(envelope["payload"].encode("utf-8")).hexdigest()
        assert envelope["signature"] == expected_sig
