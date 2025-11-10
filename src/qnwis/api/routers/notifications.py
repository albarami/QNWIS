"""
Notification and incident management API endpoints.

POST /api/v1/notify/send - Send notification (admin/service only)
POST /api/v1/incidents/{id}/ack - Acknowledge incident
POST /api/v1/incidents/{id}/resolve - Resolve incident
POST /api/v1/incidents/{id}/silence - Silence incident
GET /api/v1/incidents - List incidents with filters
GET /api/v1/incidents/{id} - Get incident details
"""

from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from ...notify.dispatcher import NotificationDispatcher
from ...notify.models import Channel, IncidentState, Notification, Severity
from ...notify.resolver import IncidentResolver
from ...security import Principal, require_roles
from ...utils.clock import Clock

logger = logging.getLogger(__name__)

router = APIRouter(tags=["notifications"])


# Request/Response Models
class SendNotificationRequest(BaseModel):
    """Request to send a notification."""

    rule_id: str = Field(..., description="Alert rule ID")
    severity: Severity = Field(..., description="Alert severity")
    message: str = Field(..., description="Notification message")
    scope: dict[str, Any] = Field(default_factory=dict, description="Alert scope")
    window_start: str = Field(..., description="Alert window start (ISO 8601)")
    window_end: str = Field(..., description="Alert window end (ISO 8601)")
    channels: list[Channel] = Field(default_factory=lambda: [Channel.EMAIL], description="Target channels")
    evidence: dict[str, Any] = Field(default_factory=dict, description="Supporting evidence")


class NotificationResponse(BaseModel):
    """Response after sending notification."""

    notification_id: str
    status: str
    results: dict[str, str]


class IncidentResponse(BaseModel):
    """Incident response model."""

    incident_id: str
    notification_id: str
    rule_id: str
    severity: str
    state: str
    message: str
    scope: dict[str, Any]
    window_start: str
    window_end: str
    created_at: str
    updated_at: str
    ack_at: str | None = None
    resolved_at: str | None = None
    consecutive_green_count: int
    metadata: dict[str, Any]


class IncidentListResponse(BaseModel):
    """List of incidents with metadata."""

    incidents: list[IncidentResponse]
    total: int
    filters: dict[str, Any]


class IncidentStatsResponse(BaseModel):
    """Incident statistics."""

    total: int
    by_state: dict[str, int]
    by_severity: dict[str, int]
    by_rule: dict[str, int]


def get_clock(request: Request) -> Clock:
    """Get clock from app state."""
    return getattr(request.app.state, "clock", Clock())


def get_dispatcher(request: Request) -> NotificationDispatcher:
    """Get or create notification dispatcher."""
    if not hasattr(request.app.state, "notification_dispatcher"):
        clock = get_clock(request)
        request.app.state.notification_dispatcher = NotificationDispatcher(clock=clock, dry_run=False)
    return request.app.state.notification_dispatcher


def get_resolver(request: Request) -> IncidentResolver:
    """Get or create incident resolver."""
    if not hasattr(request.app.state, "incident_resolver"):
        clock = get_clock(request)
        request.app.state.incident_resolver = IncidentResolver(clock=clock)
    return request.app.state.incident_resolver


@router.post("/notify/send", response_model=NotificationResponse)
async def send_notification(
    req: SendNotificationRequest,
    _request: Request,
    principal: Annotated[Principal, Depends(require_roles("admin", "service"))],
    dispatcher: Annotated[NotificationDispatcher, Depends(get_dispatcher)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> NotificationResponse:
    """
    Send a notification (admin/service only).

    Requires admin or service role.
    """
    try:
        # Compute idempotency key
        idempotency_key = dispatcher.compute_idempotency_key(
            rule_id=req.rule_id,
            scope=req.scope,
            window_start=req.window_start,
            window_end=req.window_end,
        )

        # Create notification
        notification = Notification(
            notification_id=idempotency_key,
            rule_id=req.rule_id,
            severity=req.severity,
            message=req.message,
            scope=req.scope,
            window_start=req.window_start,
            window_end=req.window_end,
            channels=req.channels,
            evidence=req.evidence,
            timestamp=clock.now_iso(),
        )

        # Dispatch
        results = dispatcher.dispatch(notification)
        logger.info(f"Sent notification {idempotency_key} via API (user: {principal.subject})")

        return NotificationResponse(
            notification_id=idempotency_key,
            status="dispatched",
            results=results,
        )

    except Exception as e:
        logger.error(f"Failed to send notification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send notification: {e}",
        ) from e


@router.get("/incidents", response_model=IncidentListResponse)
async def list_incidents(
    _request: Request,
    _principal: Annotated[Principal, Depends(require_roles("admin", "analyst", "service"))],
    resolver: Annotated[IncidentResolver, Depends(get_resolver)],
    state: Annotated[str | None, Query(description="Filter by state")] = None,
    severity: Annotated[str | None, Query(description="Filter by severity")] = None,
    rule_id: Annotated[str | None, Query(description="Filter by rule ID")] = None,
    limit: Annotated[int, Query(ge=1, le=100, description="Maximum results")] = 20,
) -> IncidentListResponse:
    """
    List incidents with optional filters.

    Supports filtering by state, severity, rule_id.
    """
    try:
        # Parse state filter
        state_filter = IncidentState(state) if state else None

        # Get incidents
        incidents = resolver.list_incidents(state=state_filter, rule_id=rule_id, limit=limit)

        # Filter by severity if specified
        if severity:
            incidents = [i for i in incidents if i.severity.value == severity]

        # Convert to response
        incident_responses = [
            IncidentResponse(
                incident_id=i.incident_id,
                notification_id=i.notification_id,
                rule_id=i.rule_id,
                severity=i.severity.value,
                state=i.state.value,
                message=i.message,
                scope=i.scope,
                window_start=i.window_start,
                window_end=i.window_end,
                created_at=i.created_at,
                updated_at=i.updated_at,
                ack_at=i.ack_at,
                resolved_at=i.resolved_at,
                consecutive_green_count=i.consecutive_green_count,
                metadata=i.metadata,
            )
            for i in incidents
        ]

        return IncidentListResponse(
            incidents=incident_responses,
            total=len(incident_responses),
            filters={"state": state, "severity": severity, "rule_id": rule_id},
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid filter value: {e}",
        ) from e
    except Exception as e:
        logger.error(f"Failed to list incidents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list incidents: {e}",
        ) from e


@router.get("/incidents/stats", response_model=IncidentStatsResponse)
async def get_incident_stats(
    _request: Request,
    _principal: Annotated[Principal, Depends(require_roles("admin", "analyst", "service"))],
    resolver: Annotated[IncidentResolver, Depends(get_resolver)],
) -> IncidentStatsResponse:
    """Get incident statistics."""
    try:
        stats = resolver.get_stats()
        return IncidentStatsResponse(**stats)
    except Exception as e:
        logger.error(f"Failed to get incident stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get stats: {e}",
        ) from e


@router.get("/incidents/{incident_id}", response_model=IncidentResponse)
async def get_incident(
    incident_id: str,
    _request: Request,
    _principal: Annotated[Principal, Depends(require_roles("admin", "analyst", "service"))],
    resolver: Annotated[IncidentResolver, Depends(get_resolver)],
) -> IncidentResponse:
    """Get incident details by ID."""
    incident = resolver.get_incident(incident_id)
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident {incident_id} not found",
        )

    return IncidentResponse(
        incident_id=incident.incident_id,
        notification_id=incident.notification_id,
        rule_id=incident.rule_id,
        severity=incident.severity.value,
        state=incident.state.value,
        message=incident.message,
        scope=incident.scope,
        window_start=incident.window_start,
        window_end=incident.window_end,
        created_at=incident.created_at,
        updated_at=incident.updated_at,
        ack_at=incident.ack_at,
        resolved_at=incident.resolved_at,
        consecutive_green_count=incident.consecutive_green_count,
        metadata=incident.metadata,
    )


@router.post("/incidents/{incident_id}/ack", response_model=IncidentResponse)
async def acknowledge_incident(
    incident_id: str,
    _request: Request,
    principal: Annotated[Principal, Depends(require_roles("admin", "analyst"))],
    resolver: Annotated[IncidentResolver, Depends(get_resolver)],
) -> IncidentResponse:
    """Acknowledge an incident (OPEN → ACK)."""
    incident = resolver.acknowledge(incident_id)
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident {incident_id} not found",
        )

    logger.info(f"Acknowledged incident {incident_id} by {principal.subject}")

    return IncidentResponse(
        incident_id=incident.incident_id,
        notification_id=incident.notification_id,
        rule_id=incident.rule_id,
        severity=incident.severity.value,
        state=incident.state.value,
        message=incident.message,
        scope=incident.scope,
        window_start=incident.window_start,
        window_end=incident.window_end,
        created_at=incident.created_at,
        updated_at=incident.updated_at,
        ack_at=incident.ack_at,
        resolved_at=incident.resolved_at,
        consecutive_green_count=incident.consecutive_green_count,
        metadata=incident.metadata,
    )


@router.post("/incidents/{incident_id}/resolve", response_model=IncidentResponse)
async def resolve_incident(
    incident_id: str,
    _request: Request,
    principal: Annotated[Principal, Depends(require_roles("admin", "analyst"))],
    resolver: Annotated[IncidentResolver, Depends(get_resolver)],
) -> IncidentResponse:
    """Resolve an incident (any state → RESOLVED)."""
    incident = resolver.resolve(incident_id)
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident {incident_id} not found",
        )

    logger.info(f"Resolved incident {incident_id} by {principal.subject}")

    return IncidentResponse(
        incident_id=incident.incident_id,
        notification_id=incident.notification_id,
        rule_id=incident.rule_id,
        severity=incident.severity.value,
        state=incident.state.value,
        message=incident.message,
        scope=incident.scope,
        window_start=incident.window_start,
        window_end=incident.window_end,
        created_at=incident.created_at,
        updated_at=incident.updated_at,
        ack_at=incident.ack_at,
        resolved_at=incident.resolved_at,
        consecutive_green_count=incident.consecutive_green_count,
        metadata=incident.metadata,
    )


@router.post("/incidents/{incident_id}/silence", response_model=IncidentResponse)
async def silence_incident(
    incident_id: str,
    _request: Request,
    principal: Annotated[Principal, Depends(require_roles("admin"))],
    resolver: Annotated[IncidentResolver, Depends(get_resolver)],
) -> IncidentResponse:
    """Silence an incident (OPEN|ACK → SILENCED). Admin only."""
    incident = resolver.silence(incident_id)
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident {incident_id} not found",
        )

    logger.info(f"Silenced incident {incident_id} by {principal.subject}")

    return IncidentResponse(
        incident_id=incident.incident_id,
        notification_id=incident.notification_id,
        rule_id=incident.rule_id,
        severity=incident.severity.value,
        state=incident.state.value,
        message=incident.message,
        scope=incident.scope,
        window_start=incident.window_start,
        window_end=incident.window_end,
        created_at=incident.created_at,
        updated_at=incident.updated_at,
        ack_at=incident.ack_at,
        resolved_at=incident.resolved_at,
        consecutive_green_count=incident.consecutive_green_count,
        metadata=incident.metadata,
    )
