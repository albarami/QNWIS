"""
CLI commands for notification and incident operations.

Commands: send, silence, ack, resolve, status, replay
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from ..notify.dispatcher import NotificationDispatcher
from ..notify.models import Channel, Incident, IncidentState, Notification, Severity
from ..notify.resolver import IncidentResolver
from ..utils.clock import Clock


@click.group()
def notify() -> None:
    """Notification and incident management commands."""
    # Click group - subcommands defined below
    ...


@notify.command()
@click.option("--rule-id", required=True, help="Alert rule ID")
@click.option("--severity", type=click.Choice(["info", "warning", "error", "critical"]), default="warning")
@click.option("--message", required=True, help="Notification message")
@click.option("--scope", default="{}", help="JSON scope dict")
@click.option("--channel", type=click.Choice(["email", "teams", "webhook"]), multiple=True, default=["email"])
@click.option("--dry-run/--no-dry-run", default=True, help="Dry-run mode (default: true)")
def send(rule_id: str, severity: str, message: str, scope: str, channel: tuple[str, ...], dry_run: bool) -> None:
    """Send a notification manually."""
    try:
        scope_dict = json.loads(scope)
    except json.JSONDecodeError:
        click.echo("Error: Invalid JSON in --scope", err=True)
        sys.exit(1)

    clock = Clock()
    dispatcher = NotificationDispatcher(clock=clock, dry_run=dry_run)

    # Parse channels
    channels = [Channel(ch) for ch in channel]

    # Compute idempotency key
    window_time = clock.now_iso()
    idempotency_key = dispatcher.compute_idempotency_key(
        rule_id=rule_id,
        scope=scope_dict,
        window_start=window_time,
        window_end=window_time,
    )

    # Create notification
    notification = Notification(
        notification_id=idempotency_key,
        rule_id=rule_id,
        severity=Severity(severity),
        message=message,
        scope=scope_dict,
        window_start=window_time,
        window_end=window_time,
        channels=channels,
        evidence={},
        timestamp=window_time,
    )

    # Dispatch
    result = dispatcher.dispatch(notification)
    click.echo(f"Notification {idempotency_key}: {result}")


@notify.command()
@click.option("--rule-id", required=True, help="Rule ID to silence")
@click.option("--duration", type=int, default=60, help="Suppression duration in minutes")
def silence(rule_id: str, duration: int) -> None:
    """Silence notifications for a rule."""
    clock = Clock()
    dispatcher = NotificationDispatcher(clock=clock)
    success = dispatcher.suppress(rule_id, duration)

    if success:
        click.echo(f"Silenced rule {rule_id} for {duration} minutes")
    else:
        click.echo(f"Failed to silence rule {rule_id}", err=True)
        sys.exit(1)


@notify.command()
@click.argument("incident_id")
def ack(incident_id: str) -> None:
    """Acknowledge an incident."""
    clock = Clock()
    resolver = IncidentResolver(clock=clock)
    incident = resolver.acknowledge(incident_id)

    if incident:
        click.echo(f"Acknowledged incident {incident_id}")
        click.echo(f"State: {incident.state.value}")
    else:
        click.echo(f"Incident {incident_id} not found", err=True)
        sys.exit(1)


@notify.command()
@click.argument("incident_id")
def resolve(incident_id: str) -> None:
    """Resolve an incident."""
    clock = Clock()
    resolver = IncidentResolver(clock=clock)
    incident = resolver.resolve(incident_id)

    if incident:
        click.echo(f"Resolved incident {incident_id}")
        click.echo(f"Resolved at: {incident.resolved_at}")
    else:
        click.echo(f"Incident {incident_id} not found", err=True)
        sys.exit(1)


@notify.command()
@click.option("--state", type=click.Choice(["open", "ack", "silenced", "resolved"]), help="Filter by state")
@click.option("--rule-id", help="Filter by rule ID")
@click.option("--limit", type=int, default=20, help="Maximum results")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
def status(state: str | None, rule_id: str | None, limit: int, output_format: str) -> None:
    """Show incident status."""
    clock = Clock()
    resolver = IncidentResolver(clock=clock)

    # Apply filters
    state_filter = IncidentState(state) if state else None
    incidents = resolver.list_incidents(state=state_filter, rule_id=rule_id, limit=limit)

    if output_format == "json":
        output = [i.model_dump() for i in incidents]
        click.echo(json.dumps(output, indent=2))
    else:
        # Table format
        if not incidents:
            click.echo("No incidents found")
            return

        click.echo(f"{'Incident ID':<40} {'Rule ID':<30} {'State':<10} {'Severity':<10} {'Created':<20}")
        click.echo("-" * 120)
        for incident in incidents:
            click.echo(
                f"{incident.incident_id[:38]:<40} "
                f"{incident.rule_id[:28]:<30} "
                f"{incident.state.value:<10} "
                f"{incident.severity.value:<10} "
                f"{incident.created_at[:19]:<20}"
            )

        # Show stats
        click.echo()
        stats = resolver.get_stats()
        click.echo(f"Total incidents: {stats['total']}")
        click.echo(f"By state: {stats['by_state']}")


@notify.command()
@click.option("--since", help="Replay since timestamp (ISO 8601)")
@click.option("--rule-id", help="Replay for specific rule")
@click.option("--dry-run/--no-dry-run", default=True, help="Dry-run mode")
def replay(since: str | None, rule_id: str | None, dry_run: bool) -> None:
    """Replay notifications from audit ledger."""
    ledger_file = Path("docs/audit/incidents/incidents.jsonl")
    if not ledger_file.exists():
        click.echo("No incident ledger found", err=True)
        sys.exit(1)

    clock = Clock()
    dispatcher = NotificationDispatcher(clock=clock, dry_run=dry_run)

    replayed = 0
    with open(ledger_file, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue

            try:
                data = json.loads(line)
                incident = Incident(**data)

                # Apply filters
                if since and incident.created_at < since:
                    continue
                if rule_id and incident.rule_id != rule_id:
                    continue

                # Create notification from incident
                notification = Notification(
                    notification_id=incident.notification_id,
                    rule_id=incident.rule_id,
                    severity=incident.severity,
                    message=incident.message,
                    scope=incident.scope,
                    window_start=incident.window_start,
                    window_end=incident.window_end,
                    channels=[Channel.EMAIL],
                    evidence=incident.metadata.get("evidence", {}),
                    timestamp=incident.created_at,
                )

                # Replay dispatch
                result = dispatcher.dispatch(notification)
                click.echo(f"Replayed {notification.notification_id}: {result}")
                replayed += 1

            except Exception as e:
                click.echo(f"Error replaying incident: {e}", err=True)

    click.echo(f"\nReplayed {replayed} notifications")


if __name__ == "__main__":
    notify()
