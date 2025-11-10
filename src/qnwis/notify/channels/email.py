"""
Email notification channel with SMTP support.

Uses environment variables for configuration and supports dry-run mode.
"""

from __future__ import annotations

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..models import Notification

logger = logging.getLogger(__name__)


class EmailChannel:
    """
    SMTP email notification channel.

    Configuration via environment variables:
    - QNWIS_SMTP_HOST: SMTP server hostname
    - QNWIS_SMTP_PORT: SMTP server port (default 587)
    - QNWIS_SMTP_USER: SMTP username
    - QNWIS_SMTP_PASS: SMTP password
    - QNWIS_SMTP_FROM: From email address
    - QNWIS_SMTP_TO: Comma-separated recipient emails
    - QNWIS_SMTP_USE_TLS: Use TLS (default true)
    """

    def __init__(self, dry_run: bool = True):
        """
        Initialize email channel.

        Args:
            dry_run: If True, log emails instead of sending
        """
        self.dry_run = dry_run
        self.smtp_host = os.getenv("QNWIS_SMTP_HOST", "localhost")
        self.smtp_port = int(os.getenv("QNWIS_SMTP_PORT", "587"))
        self.smtp_user = os.getenv("QNWIS_SMTP_USER", "")
        self.smtp_pass = os.getenv("QNWIS_SMTP_PASS", "")
        self.smtp_from = os.getenv("QNWIS_SMTP_FROM", "qnwis@example.com")
        self.smtp_to = os.getenv("QNWIS_SMTP_TO", "alerts@example.com")
        self.use_tls = os.getenv("QNWIS_SMTP_USE_TLS", "true").lower() == "true"

    def send(self, notification: Notification) -> str:
        """
        Send notification via email.

        Args:
            notification: Notification to send

        Returns:
            Status string
        """
        if self.dry_run:
            logger.info(f"[DRY-RUN] Email to {self.smtp_to}: {notification.message}")
            return "dry_run_success"

        try:
            msg = self._build_message(notification)
            recipients = [addr.strip() for addr in self.smtp_to.split(",")]

            # Connect and send
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                if self.smtp_user and self.smtp_pass:
                    server.login(self.smtp_user, self.smtp_pass)
                server.sendmail(self.smtp_from, recipients, msg.as_string())

            logger.info(f"Sent email notification {notification.notification_id}")
            return "success"
        except Exception as e:
            logger.error(f"Email send failed: {e}")
            return f"error: {e}"

    def _build_message(self, notification: Notification) -> MIMEMultipart:
        """
        Build MIME message from notification.

        Args:
            notification: Notification content

        Returns:
            MIME message
        """
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"[{notification.severity.value.upper()}] QNWIS Alert: {notification.rule_id}"
        msg["From"] = self.smtp_from
        msg["To"] = self.smtp_to

        # Plain text body
        text_body = self._format_text(notification)
        msg.attach(MIMEText(text_body, "plain"))

        # HTML body
        html_body = self._format_html(notification)
        msg.attach(MIMEText(html_body, "html"))

        return msg

    def _format_text(self, notification: Notification) -> str:
        """Format notification as plain text."""
        lines = [
            f"QNWIS Alert: {notification.rule_id}",
            f"Severity: {notification.severity.value.upper()}",
            f"Time: {notification.timestamp}",
            "",
            notification.message,
            "",
            f"Window: {notification.window_start} to {notification.window_end}",
        ]
        if notification.scope:
            lines.append(f"Scope: {notification.scope}")
        if notification.evidence:
            lines.append("")
            lines.append("Evidence:")
            for key, val in notification.evidence.items():
                lines.append(f"  {key}: {val}")
        return "\n".join(lines)

    def _format_html(self, notification: Notification) -> str:
        """Format notification as HTML."""
        severity_color = {
            "info": "#0066cc",
            "warning": "#ff9900",
            "error": "#cc0000",
            "critical": "#990000",
        }.get(notification.severity.value, "#333333")

        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <div style="border-left: 4px solid {severity_color}; padding-left: 16px;">
                <h2 style="color: {severity_color};">QNWIS Alert: {notification.rule_id}</h2>
                <p><strong>Severity:</strong> {notification.severity.value.upper()}</p>
                <p><strong>Time:</strong> {notification.timestamp}</p>
                <hr/>
                <p>{notification.message}</p>
                <p><strong>Window:</strong> {notification.window_start} to {notification.window_end}</p>
        """

        if notification.scope:
            html += f"<p><strong>Scope:</strong> {notification.scope}</p>"

        if notification.evidence:
            html += "<h3>Evidence</h3><ul>"
            for key, val in notification.evidence.items():
                html += f"<li><strong>{key}:</strong> {val}</li>"
            html += "</ul>"

        html += """
            </div>
        </body>
        </html>
        """
        return html
