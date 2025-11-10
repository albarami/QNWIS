"""
Generic webhook notification channel with HMAC signatures.

Supports custom endpoints with authentication via HMAC.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
from typing import TYPE_CHECKING, Any

import requests

if TYPE_CHECKING:
    from ..models import Notification

logger = logging.getLogger(__name__)


class WebhookChannel:
    """
    Generic webhook notification channel.

    Configuration via environment variables:
    - QNWIS_WEBHOOK_URL: Target webhook URL
    - QNWIS_WEBHOOK_SECRET: HMAC secret for signing
    """

    def __init__(self, dry_run: bool = True):
        """
        Initialize webhook channel.

        Args:
            dry_run: If True, log webhooks instead of POSTing
        """
        self.dry_run = dry_run
        self.webhook_url = os.getenv("QNWIS_WEBHOOK_URL", "")
        self.webhook_secret = os.getenv("QNWIS_WEBHOOK_SECRET", "")

    def send(self, notification: Notification) -> str:
        """
        Send notification to webhook endpoint.

        Args:
            notification: Notification to send

        Returns:
            Status string
        """
        if self.dry_run:
            logger.info(f"[DRY-RUN] Webhook POST: {notification.message}")
            return "dry_run_success"

        if not self.webhook_url:
            logger.error("Webhook URL not configured")
            return "error: webhook_url not configured"

        payload = notification.model_dump()
        headers = {"Content-Type": "application/json"}

        # Add HMAC signature if secret is configured
        if self.webhook_secret:
            signature = self._compute_signature(payload)
            headers["X-QNWIS-Signature"] = signature

        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers=headers,
                timeout=10,
            )
            response.raise_for_status()
            logger.info(f"Sent webhook notification {notification.notification_id}")
            return "success"
        except requests.RequestException as e:
            logger.error(f"Webhook send failed: {e}")
            return f"error: {e}"

    def _compute_signature(self, payload: dict[str, Any]) -> str:
        """
        Compute HMAC-SHA256 signature for payload.

        Args:
            payload: Payload dict

        Returns:
            Hex-encoded HMAC signature
        """
        import json

        payload_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
        secret_bytes = self.webhook_secret.encode("utf-8")
        signature = hmac.new(secret_bytes, payload_bytes, hashlib.sha256).hexdigest()
        return signature
