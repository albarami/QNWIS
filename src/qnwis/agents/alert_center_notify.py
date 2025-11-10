"""
Notification integration helpers for AlertCenterAgent.

Extracted to separate file to keep alert_center.py under 500 lines.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..alerts.engine import AlertDecision
    from ..alerts.rules import AlertRule
    from ..notify.dispatcher import NotificationDispatcher
    from ..notify.resolver import IncidentResolver
    from ..utils.clock import Clock

logger = logging.getLogger(__name__)


def emit_notifications(
    decisions: list[AlertDecision],
    rules: list[AlertRule],
    dispatcher: NotificationDispatcher,
    clock: Clock,
) -> None:
    """
    Emit notifications for triggered alerts.

    Args:
        decisions: List of alert decisions
        rules: List of evaluated rules
        dispatcher: Notification dispatcher
        clock: Clock for timestamps
    """
    from ..notify.models import Channel, Notification, Severity

    rules_dict = {r.rule_id: r for r in rules}
    triggered = [d for d in decisions if d.triggered]

    for decision in triggered:
        rule = rules_dict.get(decision.rule_id)
        if not rule:
            continue

        try:
            # Map alert severity to notification severity
            severity_map = {
                "info": Severity.INFO,
                "warning": Severity.WARNING,
                "error": Severity.ERROR,
                "critical": Severity.CRITICAL,
            }
            severity = severity_map.get(rule.severity.value, Severity.WARNING)

            # Compute idempotency key
            scope_dict = {"level": rule.scope.level, "code": rule.scope.code or ""}
            idempotency_key = dispatcher.compute_idempotency_key(
                rule_id=rule.rule_id,
                scope=scope_dict,
                window_start=decision.timestamp,
                window_end=decision.timestamp,
            )

            # Create notification
            notification = Notification(
                notification_id=idempotency_key,
                rule_id=rule.rule_id,
                severity=severity,
                message=decision.message,
                scope=scope_dict,
                window_start=decision.timestamp,
                window_end=decision.timestamp,
                channels=[Channel.EMAIL],  # Default to email
                evidence=decision.evidence,
                timestamp=clock.now_iso(),
            )

            # Dispatch
            result = dispatcher.dispatch(notification)
            logger.info(f"Dispatched notification {notification.notification_id}: {result}")

        except Exception as e:
            logger.error(f"Failed to emit notification for {decision.rule_id}: {e}")


def record_green_evaluations(
    decisions: list[AlertDecision],
    rules: list[AlertRule],
    resolver: IncidentResolver,
) -> None:
    """
    Record green (non-firing) evaluations for auto-resolution.

    Args:
        decisions: List of alert decisions
        rules: List of evaluated rules
        resolver: Incident resolver
    """
    rules_dict = {r.rule_id: r for r in rules}
    non_triggered = [d for d in decisions if not d.triggered]

    for decision in non_triggered:
        rule = rules_dict.get(decision.rule_id)
        if not rule:
            continue

        try:
            auto_resolved = resolver.record_green_evaluation(rule.rule_id)
            if auto_resolved:
                logger.info(f"Auto-resolved {len(auto_resolved)} incidents for rule {rule.rule_id}")
        except Exception as e:
            logger.error(f"Failed to record green evaluation for {decision.rule_id}: {e}")
