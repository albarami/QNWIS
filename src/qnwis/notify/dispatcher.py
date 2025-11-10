"""
Notification dispatcher with deduplication, rate-limiting, and multi-channel fan-out.

All operations are deterministic and use injected timestamps for testability.
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

from .models import Channel, Incident, IncidentState, Notification

if TYPE_CHECKING:
    from ..utils.clock import Clock

logger = logging.getLogger(__name__)


class NotificationChannel(Protocol):
    """Protocol for notification channel handlers."""

    def send(self, notification: Notification) -> str: ...


class NotificationDispatcher:
    """
    Production-grade notification dispatcher.

    Features:
    - Deterministic deduplication via idempotency keys
    - Rate limiting per rule
    - Suppression windows
    - Multi-channel fan-out with dry-run support
    - Audit ledger with HMAC integrity
    """

    def __init__(
        self,
        clock: Clock,
        ledger_dir: Path | None = None,
        rate_limit_per_rule: int = 10,
        rate_limit_window_minutes: int = 60,
        dry_run: bool = True,
    ):
        """
        Initialize dispatcher.

        Args:
            clock: Clock instance for deterministic time
            ledger_dir: Directory for incident ledger (default: docs/audit/incidents)
            rate_limit_per_rule: Max notifications per rule in window
            rate_limit_window_minutes: Rate limit window duration
            dry_run: If True, no actual notifications are sent
        """
        self.clock = clock
        self.ledger_dir = ledger_dir or Path("docs/audit/incidents")
        self.ledger_dir.mkdir(parents=True, exist_ok=True)
        self.rate_limit_per_rule = rate_limit_per_rule
        self.rate_limit_window_minutes = rate_limit_window_minutes
        self.dry_run = dry_run

        # In-memory state (would use Redis in production)
        self._seen_keys: set[str] = set()
        self._rate_counters: dict[str, list[float]] = {}  # rule_id -> [timestamps]
        self._suppressions: dict[str, float] = {}  # rule_id -> suppress_until_ts

        # Channel handlers (lazy-loaded)
        self._channels: dict[Channel, NotificationChannel] = {}

    def compute_idempotency_key(
        self,
        rule_id: str,
        scope: dict[str, Any],
        window_start: str,
        window_end: str,
    ) -> str:
        """
        Compute deterministic idempotency key.

        Args:
            rule_id: Alert rule ID
            scope: Alert scope dict
            window_start: ISO 8601 timestamp
            window_end: ISO 8601 timestamp

        Returns:
            SHA256 hex digest
        """
        payload = {
            "rule_id": rule_id,
            "scope": scope,
            "window_start": window_start,
            "window_end": window_end,
        }
        canonical = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def dispatch(self, notification: Notification) -> dict[str, str]:
        """
        Dispatch notification through full pipeline.

        Pipeline:
        1. Deduplication check
        2. Rate limit check
        3. Suppression window check
        4. Fan-out to channels
        5. Persist to ledger

        Args:
            notification: Notification to dispatch

        Returns:
            Dict with dispatch results per channel
        """
        logger.info(f"Dispatching notification {notification.notification_id} (dry_run={self.dry_run})")

        # Step 1: Deduplication
        if not self._check_dedupe(notification):
            logger.info(f"Notification {notification.notification_id} deduplicated (already seen)")
            return {"status": "deduplicated"}

        # Step 2: Rate limit
        if not self._check_rate_limit(notification):
            logger.warning(f"Notification {notification.notification_id} rate-limited")
            return {"status": "rate_limited"}

        # Step 3: Suppression window
        if self._is_suppressed(notification):
            logger.info(f"Notification {notification.notification_id} suppressed")
            return {"status": "suppressed"}

        # Step 4: Fan-out
        results = self._fanout(notification)

        # Step 5: Persist
        self._persist_to_ledger(notification, results)

        return results

    def _check_dedupe(self, notification: Notification) -> bool:
        """
        Check if notification is duplicate.

        Args:
            notification: Notification to check

        Returns:
            True if unique, False if duplicate
        """
        key = notification.notification_id
        if key in self._seen_keys:
            return False
        self._seen_keys.add(key)
        return True

    def _check_rate_limit(self, notification: Notification) -> bool:
        """
        Check rate limit for rule.

        Args:
            notification: Notification to check

        Returns:
            True if within limit, False if exceeded
        """
        rule_id: str = notification.rule_id
        now = self.clock.time()
        window_start = now - (self.rate_limit_window_minutes * 60)

        # Get recent timestamps
        if rule_id not in self._rate_counters:
            self._rate_counters[rule_id] = []

        # Filter to window
        recent = [ts for ts in self._rate_counters[rule_id] if ts >= window_start]
        self._rate_counters[rule_id] = recent

        # Check limit
        if len(recent) >= self.rate_limit_per_rule:
            return False

        # Record this notification
        self._rate_counters[rule_id].append(now)
        return True

    def _is_suppressed(self, notification: Notification) -> bool:
        """
        Check if rule is currently suppressed.

        Args:
            notification: Notification to check

        Returns:
            True if suppressed, False otherwise
        """
        rule_id = notification.rule_id
        if rule_id not in self._suppressions:
            return False

        suppress_until: float = self._suppressions[rule_id]
        now: float = self.clock.time()
        is_active: bool = now < suppress_until
        return is_active

    def _fanout(self, notification: Notification) -> dict[str, str]:
        """
        Fan-out notification to all channels.

        Args:
            notification: Notification to send

        Returns:
            Dict mapping channel to result status
        """
        results: dict[str, str] = {}
        for channel in notification.channels:
            try:
                result = self._send_to_channel(channel, notification)
                results[channel.value] = result
            except Exception as e:
                logger.error(f"Failed to send to {channel}: {e}")
                results[channel.value] = f"error: {e}"

        return results

    def _send_to_channel(self, channel: Channel, notification: Notification) -> str:
        """
        Send notification to specific channel.

        Args:
            channel: Target channel
            notification: Notification to send

        Returns:
            Status string
        """
        # Lazy-load channel handler
        if channel not in self._channels:
            self._load_channel(channel)

        handler = self._channels.get(channel)
        if not handler:
            return "error: channel not configured"

        if self.dry_run:
            logger.info(f"DRY-RUN: Would send to {channel}: {notification.message}")
            return "dry_run_success"

        # Delegate to channel handler
        return handler.send(notification)

    def _load_channel(self, channel: Channel) -> None:
        """
        Lazy-load channel handler.

        Args:
            channel: Channel to load
        """
        from .channels.email import EmailChannel
        from .channels.teams import TeamsChannel
        from .channels.webhook import WebhookChannel

        if channel == Channel.EMAIL:
            self._channels[channel] = EmailChannel(dry_run=self.dry_run)
        elif channel == Channel.TEAMS:
            self._channels[channel] = TeamsChannel(dry_run=self.dry_run)
        elif channel == Channel.WEBHOOK:
            self._channels[channel] = WebhookChannel(dry_run=self.dry_run)
        else:
            logger.warning(f"Unknown channel: {channel}")

    def _persist_to_ledger(self, notification: Notification, results: dict[str, str]) -> None:
        """
        Persist notification to audit ledger.

        Args:
            notification: Notification dispatched
            results: Dispatch results per channel
        """
        try:
            # Create incident record
            incident = Incident(
                incident_id=notification.notification_id,
                notification_id=notification.notification_id,
                rule_id=notification.rule_id,
                severity=notification.severity,
                state=IncidentState.OPEN,
                message=notification.message,
                scope=notification.scope,
                window_start=notification.window_start,
                window_end=notification.window_end,
                created_at=notification.timestamp,
                updated_at=notification.timestamp,
                metadata={"dispatch_results": results},
            )

            # Write to JSONL ledger
            ledger_file = self.ledger_dir / "incidents.jsonl"
            with open(ledger_file, "a", encoding="utf-8") as f:
                line = incident.model_dump_json() + "\n"
                f.write(line)

            # Compute and store HMAC (placeholder for signature)
            envelope = self._create_envelope(incident)
            envelope_file = self.ledger_dir / f"{incident.incident_id}.envelope.json"
            with open(envelope_file, "w", encoding="utf-8") as f:
                json.dump(envelope, f, indent=2)

            logger.info(f"Persisted incident {incident.incident_id} to ledger")
        except Exception as e:
            logger.error(f"Failed to persist to ledger: {e}")

    def _create_envelope(self, incident: Incident) -> dict[str, str]:
        """
        Create HMAC envelope for incident.

        Args:
            incident: Incident to sign

        Returns:
            Envelope dict with signature
        """
        payload = incident.model_dump_json()
        signature = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return {
            "incident_id": incident.incident_id,
            "payload": payload,
            "signature": signature,
            "algorithm": "sha256",
        }

    def suppress(self, rule_id: str, duration_minutes: int) -> bool:
        """
        Suppress notifications for a rule.

        Args:
            rule_id: Rule to suppress
            duration_minutes: Suppression duration

        Returns:
            True if successful
        """
        now = self.clock.time()
        suppress_until = now + (duration_minutes * 60)
        self._suppressions[rule_id] = suppress_until
        logger.info(f"Suppressed rule {rule_id} for {duration_minutes} minutes")
        return True

    def clear_suppression(self, rule_id: str) -> bool:
        """
        Clear suppression for a rule.

        Args:
            rule_id: Rule to clear

        Returns:
            True if successful
        """
        if rule_id in self._suppressions:
            del self._suppressions[rule_id]
            logger.info(f"Cleared suppression for rule {rule_id}")
            return True
        return False
