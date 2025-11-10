"""
Notification & Incident Management Layer.

Production-grade notification handling with deduplication, rate-limiting,
escalation policies, and multi-channel dispatch (email, Teams, webhooks).
"""

from .dispatcher import NotificationDispatcher
from .models import (
    Channel,
    EscalationPolicy,
    Incident,
    IncidentState,
    Notification,
    Severity,
    SuppressionWindow,
)
from .resolver import IncidentResolver

__all__ = [
    "Channel",
    "EscalationPolicy",
    "Incident",
    "IncidentResolver",
    "IncidentState",
    "Notification",
    "NotificationDispatcher",
    "Severity",
    "SuppressionWindow",
]
