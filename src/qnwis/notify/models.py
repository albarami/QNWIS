"""
Pydantic models for notification and incident management.

All models are deterministic, immutable, and support full JSON serialization.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Severity(str, Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class Channel(str, Enum):
    """Notification channels."""

    EMAIL = "email"
    TEAMS = "teams"
    WEBHOOK = "webhook"


class IncidentState(str, Enum):
    """Incident lifecycle states."""

    OPEN = "open"
    ACK = "ack"
    SILENCED = "silenced"
    RESOLVED = "resolved"


class SuppressionWindow(BaseModel):
    """
    Time window for suppressing duplicate notifications.

    Attributes:
        start_time: ISO 8601 timestamp (UTC)
        end_time: ISO 8601 timestamp (UTC)
    """

    start_time: str = Field(..., description="ISO 8601 start timestamp (UTC)")
    end_time: str = Field(..., description="ISO 8601 end timestamp (UTC)")

    class Config:
        frozen = True


class EscalationPolicy(BaseModel):
    """
    Escalation policy for notifications.

    Attributes:
        name: Policy identifier
        channels: Ordered list of channels to try
        escalate_after_minutes: Minutes before escalating to next channel
        max_retries: Maximum retries per channel
    """

    name: str = Field(..., description="Policy name")
    channels: list[Channel] = Field(default_factory=list, description="Ordered channel list")
    escalate_after_minutes: int = Field(default=15, ge=1, description="Minutes before escalation")
    max_retries: int = Field(default=3, ge=0, description="Max retries per channel")

    class Config:
        frozen = True


class Notification(BaseModel):
    """
    Notification message to be dispatched.

    Attributes:
        notification_id: Unique identifier (idempotency key)
        rule_id: Alert rule ID that triggered this notification
        severity: Alert severity
        message: Human-readable message
        scope: Alert scope (e.g., {"level": "sector", "code": "010"})
        window_start: Alert window start (ISO 8601)
        window_end: Alert window end (ISO 8601)
        channels: Target channels for dispatch
        evidence: Supporting evidence/metrics
        timestamp: Creation timestamp (ISO 8601 UTC)
    """

    notification_id: str = Field(..., description="Unique notification ID (idempotency key)")
    rule_id: str = Field(..., description="Alert rule ID")
    severity: Severity = Field(..., description="Alert severity")
    message: str = Field(..., description="Human-readable message")
    scope: dict[str, Any] = Field(default_factory=dict, description="Alert scope")
    window_start: str = Field(..., description="Alert window start (ISO 8601)")
    window_end: str = Field(..., description="Alert window end (ISO 8601)")
    channels: list[Channel] = Field(default_factory=lambda: [Channel.EMAIL], description="Target channels")
    evidence: dict[str, Any] = Field(default_factory=dict, description="Supporting evidence")
    timestamp: str = Field(..., description="Creation timestamp (ISO 8601 UTC)")

    class Config:
        frozen = True


class Incident(BaseModel):
    """
    Incident record tracking notification lifecycle.

    Attributes:
        incident_id: Unique identifier
        notification_id: Associated notification ID
        rule_id: Alert rule ID
        severity: Alert severity
        state: Current incident state
        message: Alert message
        scope: Alert scope
        window_start: Alert window start (ISO 8601)
        window_end: Alert window end (ISO 8601)
        created_at: Incident creation time (ISO 8601 UTC)
        updated_at: Last update time (ISO 8601 UTC)
        ack_at: Acknowledgment time (ISO 8601 UTC, optional)
        resolved_at: Resolution time (ISO 8601 UTC, optional)
        consecutive_green_count: Count of consecutive green evaluations
        metadata: Additional metadata
    """

    incident_id: str = Field(..., description="Unique incident ID")
    notification_id: str = Field(..., description="Associated notification ID")
    rule_id: str = Field(..., description="Alert rule ID")
    severity: Severity = Field(..., description="Alert severity")
    state: IncidentState = Field(default=IncidentState.OPEN, description="Current state")
    message: str = Field(..., description="Alert message")
    scope: dict[str, Any] = Field(default_factory=dict, description="Alert scope")
    window_start: str = Field(..., description="Alert window start (ISO 8601)")
    window_end: str = Field(..., description="Alert window end (ISO 8601)")
    created_at: str = Field(..., description="Creation timestamp (ISO 8601 UTC)")
    updated_at: str = Field(..., description="Last update timestamp (ISO 8601 UTC)")
    ack_at: str | None = Field(default=None, description="Acknowledgment timestamp (ISO 8601 UTC)")
    resolved_at: str | None = Field(default=None, description="Resolution timestamp (ISO 8601 UTC)")
    consecutive_green_count: int = Field(default=0, ge=0, description="Consecutive green evaluations")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    class Config:
        frozen = True
