"""
Microsoft Teams notification channel via incoming webhooks.

Supports retry with exponential backoff and dry-run mode.
"""

from __future__ import annotations

import logging
import os
import time
from typing import TYPE_CHECKING, Any

import requests

if TYPE_CHECKING:
    from ..models import Notification

logger = logging.getLogger(__name__)


class TeamsChannel:
    """
    Microsoft Teams webhook notification channel.

    Configuration via environment variables:
    - QNWIS_TEAMS_WEBHOOK_URL: Incoming webhook URL
    """

    def __init__(self, dry_run: bool = True, max_retries: int = 3):
        """
        Initialize Teams channel.

        Args:
            dry_run: If True, log messages instead of sending
            max_retries: Maximum retry attempts
        """
        self.dry_run = dry_run
        self.max_retries = max_retries
        self.webhook_url = os.getenv("QNWIS_TEAMS_WEBHOOK_URL", "")

    def send(self, notification: Notification) -> str:
        """
        Send notification to Teams channel.

        Args:
            notification: Notification to send

        Returns:
            Status string
        """
        if self.dry_run:
            logger.info(f"[DRY-RUN] Teams notification: {notification.message}")
            return "dry_run_success"

        if not self.webhook_url:
            logger.error("Teams webhook URL not configured")
            return "error: webhook_url not configured"

        payload = self._build_payload(notification)

        # Retry with exponential backoff
        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    self.webhook_url,
                    json=payload,
                    timeout=10,
                    headers={"Content-Type": "application/json"},
                )
                response.raise_for_status()
                logger.info(f"Sent Teams notification {notification.notification_id}")
                return "success"
            except requests.RequestException as e:
                logger.warning(f"Teams send attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    backoff = 2**attempt  # 1s, 2s, 4s
                    time.sleep(backoff)
                else:
                    return f"error: {e}"

        return "error: max retries exceeded"

    def _build_payload(self, notification: Notification) -> dict[str, Any]:
        """
        Build Teams adaptive card payload.

        Args:
            notification: Notification content

        Returns:
            Adaptive card JSON
        """
        severity_color = {
            "info": "Accent",
            "warning": "Warning",
            "error": "Attention",
            "critical": "Attention",
        }.get(notification.severity.value, "Default")

        facts: list[dict[str, str]] = [
            {"name": "Rule ID", "value": notification.rule_id},
            {"name": "Severity", "value": notification.severity.value.upper()},
            {"name": "Time", "value": notification.timestamp},
            {"name": "Window", "value": f"{notification.window_start} to {notification.window_end}"},
        ]

        if notification.scope:
            facts.append({"name": "Scope", "value": str(notification.scope)})

        # Add evidence as facts
        for key, val in notification.evidence.items():
            facts.append({"name": key.replace("_", " ").title(), "value": str(val)})

        return {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": {
                        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                        "type": "AdaptiveCard",
                        "version": "1.2",
                        "body": [
                            {
                                "type": "TextBlock",
                                "text": f"QNWIS Alert: {notification.rule_id}",
                                "weight": "Bolder",
                                "size": "Large",
                                "color": severity_color,
                            },
                            {"type": "TextBlock", "text": notification.message, "wrap": True},
                            {"type": "FactSet", "facts": facts},
                        ],
                    },
                }
            ],
        }
