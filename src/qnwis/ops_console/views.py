"""
Page handlers for ops console views.

Implements incident list, detail, and actions (ack, resolve, silence).
All views use server-side rendering with Jinja2 and HTMX for interactivity.
"""

from __future__ import annotations

import logging
from typing import Any, cast

from fastapi import Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, Response, StreamingResponse
from fastapi.templating import Jinja2Templates

from ..notify.models import IncidentState, Severity
from ..notify.resolver import IncidentResolver
from ..security import Principal, require_roles
from ..utils.clock import Clock
from .csrf import get_csrf_protection, verify_csrf_token
from .sse import SSEStream, create_incident_update_event

logger = logging.getLogger(__name__)


def get_templates(request: Request) -> Jinja2Templates:
    """Get Jinja2 templates from app state."""
    return request.app.state.ops_templates


def get_clock(request: Request) -> Clock:
    """Get clock from app state."""
    return getattr(request.app.state, "clock", Clock())


def get_incident_resolver(request: Request) -> IncidentResolver:
    """Get or create incident resolver."""
    if not hasattr(request.app.state, "incident_resolver"):
        clock = get_clock(request)
        request.app.state.incident_resolver = IncidentResolver(clock=clock, ledger_dir=None)
    return cast(IncidentResolver, request.app.state.incident_resolver)


def get_sse_stream(request: Request) -> SSEStream:
    """Get or create SSE stream for live updates."""
    if not hasattr(request.app.state, "sse_stream"):
        request.app.state.sse_stream = SSEStream()
    return cast(SSEStream, request.app.state.sse_stream)


async def ops_index(
    request: Request,
    principal: Principal = Depends(require_roles("analyst", "admin", "auditor")),
) -> HTMLResponse:
    """
    Ops console home page.

    Shows dashboard overview with incident counts and recent activity.
    """
    templates = get_templates(request)
    clock = get_clock(request)
    resolver = get_incident_resolver(request)
    csrf = get_csrf_protection(request)

    # Get incident statistics
    all_incidents = resolver.list_incidents()
    stats: dict[str, Any] = {
        "total": len(all_incidents),
        "by_state": {},
        "by_severity": {},
    }
    by_state = cast(dict[str, int], stats["by_state"])
    by_severity = cast(dict[str, int], stats["by_severity"])

    for inc in all_incidents:
        by_state[inc.state.value] = by_state.get(inc.state.value, 0) + 1
        by_severity[inc.severity.value] = by_severity.get(inc.severity.value, 0) + 1

    # Generate CSRF token
    csrf_token = csrf.generate_token(clock.utcnow())

    # Render template
    context = {
        "request": request,
        "principal": principal,
        "stats": stats,
        "csrf_token": csrf_token,
        "request_id": getattr(request.state, "request_id", "unknown"),
        "render_start": clock.utcnow(),
    }

    return templates.TemplateResponse("ops_index.html", context)


async def incidents_list(
    request: Request,
    state: str | None = None,
    severity: str | None = None,
    rule_id: str | None = None,
    limit: int = 100,
    principal: Principal = Depends(require_roles("analyst", "admin", "auditor")),
) -> HTMLResponse:
    """
    List incidents with optional filters.

    Query params:
        state: Filter by state (OPEN, ACK, SILENCED, RESOLVED)
        severity: Filter by severity (INFO, WARNING, ERROR, CRITICAL)
        rule_id: Filter by rule ID
        limit: Max results (default 100)
    """
    templates = get_templates(request)
    clock = get_clock(request)
    resolver = get_incident_resolver(request)
    csrf = get_csrf_protection(request)

    # Apply filters
    incidents = resolver.list_incidents()

    if state:
        try:
            state_enum = IncidentState(state.lower())
            incidents = [inc for inc in incidents if inc.state == state_enum]
        except ValueError:
            # Invalid state filter - ignore and return all states
            ...

    if severity:
        try:
            severity_enum = Severity(severity.lower())
            incidents = [inc for inc in incidents if inc.severity == severity_enum]
        except ValueError:
            # Invalid severity filter - ignore and return all severities
            ...

    if rule_id:
        incidents = [inc for inc in incidents if inc.rule_id == rule_id]

    # Sort by created_at descending and limit
    incidents.sort(key=lambda x: x.created_at, reverse=True)
    incidents = incidents[:limit]

    # Generate CSRF token
    csrf_token = csrf.generate_token(clock.utcnow())

    context = {
        "request": request,
        "principal": principal,
        "incidents": incidents,
        "filters": {"state": state, "severity": severity, "rule_id": rule_id},
        "csrf_token": csrf_token,
        "request_id": getattr(request.state, "request_id", "unknown"),
        "render_start": clock.utcnow(),
    }

    return templates.TemplateResponse("incidents_list.html", context)


async def incident_detail(
    request: Request,
    incident_id: str,
    principal: Principal = Depends(require_roles("analyst", "admin", "auditor")),
) -> HTMLResponse:
    """
    Show incident detail page with timeline.

    Path params:
        incident_id: Incident identifier
    """
    templates = get_templates(request)
    clock = get_clock(request)
    resolver = get_incident_resolver(request)
    csrf = get_csrf_protection(request)

    # Get incident
    incident = resolver.get_incident(incident_id)
    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident {incident_id} not found",
        )

    # Build timeline
    timeline = [
        {"event": "CREATED", "timestamp": incident.created_at, "actor": "system"},
    ]
    if incident.ack_at:
        timeline.append({"event": "ACK", "timestamp": incident.ack_at, "actor": incident.metadata.get("ack_actor", "unknown")})
    if incident.resolved_at:
        timeline.append({"event": "RESOLVED", "timestamp": incident.resolved_at, "actor": incident.metadata.get("resolve_actor", "unknown")})
    if incident.state == IncidentState.SILENCED:
        timeline.append({
            "event": "SILENCED",
            "timestamp": incident.metadata.get("silence_at", incident.updated_at),
            "actor": incident.metadata.get("silence_actor", "unknown"),
        })

    # Generate CSRF token
    csrf_token = csrf.generate_token(clock.utcnow())

    # Check for audit pack link
    audit_pack_path = None
    if "audit_pack_id" in incident.metadata:
        audit_pack_path = f"/audit_packs/{incident.metadata['audit_pack_id']}"

    context = {
        "request": request,
        "principal": principal,
        "incident": incident,
        "timeline": timeline,
        "audit_pack_path": audit_pack_path,
        "csrf_token": csrf_token,
        "request_id": getattr(request.state, "request_id", "unknown"),
        "render_start": clock.utcnow(),
    }

    return templates.TemplateResponse("incident_detail.html", context)


async def incident_ack(
    request: Request,
    incident_id: str,
    csrf_token: str = Form(...),
    principal: Principal = Depends(require_roles("analyst", "admin")),
    _csrf_check: None = Depends(verify_csrf_token),
) -> Response:
    _ = csrf_token
    """
    Acknowledge an incident (POST).

    Form params:
        csrf_token: CSRF protection token
    """
    clock = get_clock(request)
    resolver = get_incident_resolver(request)
    sse_stream = get_sse_stream(request)

    # Get incident
    incident = resolver.get_incident(incident_id)
    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident {incident_id} not found",
        )

    # Acknowledge
    updated = resolver.acknowledge_incident(
        incident_id=incident_id,
        actor=principal.user_id,
        timestamp=clock.utcnow(),
    )

    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to acknowledge incident",
        )

    # Send SSE update
    await sse_stream.send_event(
        create_incident_update_event(
            incident_id=incident_id,
            state=updated.state.value,
            actor=principal.user_id,
            timestamp=clock.utcnow(),
        )
    )

    logger.info(
        "Incident %s acknowledged by %s",
        incident_id,
        principal.user_id,
        extra={"request_id": getattr(request.state, "request_id", "unknown")},
    )

    # HTMX redirect to detail page
    return Response(
        status_code=status.HTTP_303_SEE_OTHER,
        headers={"HX-Redirect": f"/ops/incidents/{incident_id}"},
    )


async def incident_resolve(
    request: Request,
    incident_id: str,
    csrf_token: str = Form(...),
    note: str = Form(""),
    principal: Principal = Depends(require_roles("analyst", "admin")),
    _csrf_check: None = Depends(verify_csrf_token),
) -> Response:
    _ = csrf_token
    """
    Resolve an incident (POST).

    Form params:
        csrf_token: CSRF protection token
        note: Optional resolution note
    """
    clock = get_clock(request)
    resolver = get_incident_resolver(request)
    sse_stream = get_sse_stream(request)

    # Get incident
    incident = resolver.get_incident(incident_id)
    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident {incident_id} not found",
        )

    # Resolve
    updated = resolver.resolve_incident(
        incident_id=incident_id,
        actor=principal.user_id,
        timestamp=clock.utcnow(),
        note=note or None,
    )

    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to resolve incident",
        )

    # Send SSE update
    await sse_stream.send_event(
        create_incident_update_event(
            incident_id=incident_id,
            state=updated.state.value,
            actor=principal.user_id,
            timestamp=clock.utcnow(),
        )
    )

    logger.info(
        "Incident %s resolved by %s: %s",
        incident_id,
        principal.user_id,
        note or "(no note)",
        extra={"request_id": getattr(request.state, "request_id", "unknown")},
    )

    # HTMX redirect to detail page
    return Response(
        status_code=status.HTTP_303_SEE_OTHER,
        headers={"HX-Redirect": f"/ops/incidents/{incident_id}"},
    )


async def incident_silence(
    request: Request,
    incident_id: str,
    csrf_token: str = Form(...),
    until: str = Form(...),
    reason: str = Form(""),
    principal: Principal = Depends(require_roles("analyst", "admin")),
    _csrf_check: None = Depends(verify_csrf_token),
) -> Response:
    _ = csrf_token
    """
    Silence an incident (POST).

    Form params:
        csrf_token: CSRF protection token
        until: ISO 8601 timestamp for silence expiration
        reason: Optional reason for silencing
    """
    clock = get_clock(request)
    resolver = get_incident_resolver(request)
    sse_stream = get_sse_stream(request)

    # Get incident
    incident = resolver.get_incident(incident_id)
    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident {incident_id} not found",
        )

    # Silence (update metadata)
    metadata = dict(incident.metadata)
    metadata["silence_until"] = until
    metadata["silence_reason"] = reason
    metadata["silence_actor"] = principal.user_id
    metadata["silence_at"] = clock.utcnow()

    from ..notify.models import Incident
    updated = Incident(
        incident_id=incident.incident_id,
        notification_id=incident.notification_id,
        rule_id=incident.rule_id,
        severity=incident.severity,
        state=IncidentState.SILENCED,
        message=incident.message,
        scope=incident.scope,
        window_start=incident.window_start,
        window_end=incident.window_end,
        created_at=incident.created_at,
        updated_at=clock.utcnow(),
        ack_at=incident.ack_at,
        resolved_at=incident.resolved_at,
        consecutive_green_count=incident.consecutive_green_count,
        metadata=metadata,
    )

    resolver._store[incident_id] = updated

    # Send SSE update
    await sse_stream.send_event(
        create_incident_update_event(
            incident_id=incident_id,
            state=updated.state.value,
            actor=principal.user_id,
            timestamp=clock.utcnow(),
        )
    )

    logger.info(
        "Incident %s silenced by %s until %s: %s",
        incident_id,
        principal.user_id,
        until,
        reason or "(no reason)",
        extra={"request_id": getattr(request.state, "request_id", "unknown")},
    )

    # HTMX redirect to detail page
    return Response(
        status_code=status.HTTP_303_SEE_OTHER,
        headers={"HX-Redirect": f"/ops/incidents/{incident_id}"},
    )


async def alerts_list(
    request: Request,
    principal: Principal = Depends(require_roles("analyst", "admin", "auditor")),
) -> HTMLResponse:
    """
    List recent alert evaluations.

    Note: This is a placeholder for future alert history feature.
    """
    templates = get_templates(request)
    clock = get_clock(request)
    csrf = get_csrf_protection(request)

    # Generate CSRF token
    csrf_token = csrf.generate_token(clock.utcnow())

    context = {
        "request": request,
        "principal": principal,
        "alerts": [],  # Placeholder
        "csrf_token": csrf_token,
        "request_id": getattr(request.state, "request_id", "unknown"),
        "render_start": clock.utcnow(),
    }

    return templates.TemplateResponse("alerts_list.html", context)


async def incidents_stream(
    request: Request,
    _principal: Principal = Depends(require_roles("analyst", "admin", "auditor")),
) -> StreamingResponse:
    """
    SSE stream for live incident updates.

    Sends server-sent events when incidents change state.
    """
    sse_stream = get_sse_stream(request)

    return StreamingResponse(
        sse_stream.stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


__all__ = [
    "ops_index",
    "incidents_list",
    "incident_detail",
    "incident_ack",
    "incident_resolve",
    "incident_silence",
    "alerts_list",
    "incidents_stream",
]
