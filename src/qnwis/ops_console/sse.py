"""
Server-Sent Events (SSE) for real-time incident and alert updates.

Provides a dry-run SSE stream with heartbeats and event formatting.
No external message queue dependency - events are generated deterministically.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

# Heartbeat interval in seconds
HEARTBEAT_INTERVAL = 30


@dataclass(frozen=True)
class SSEEvent:
    """
    Server-Sent Event message.

    Attributes:
        event: Event type (e.g., "incident_update", "alert_fired")
        data: JSON-serializable event data
        id: Optional event ID for reconnection
        retry: Optional retry interval in milliseconds
    """

    event: str
    data: dict[str, Any]
    id: str | None = None
    retry: int | None = None

    def format(self) -> str:
        """
        Format event as SSE protocol string.

        Returns:
            Formatted SSE message with event, data, optional id/retry
        """
        lines = []

        if self.id:
            lines.append(f"id: {self.id}")

        if self.retry:
            lines.append(f"retry: {self.retry}")

        lines.append(f"event: {self.event}")

        # JSON encode data and split into lines (for multiline support)
        data_json = json.dumps(self.data, ensure_ascii=False)
        for line in data_json.split("\n"):
            lines.append(f"data: {line}")

        # Terminate with double newline
        return "\n".join(lines) + "\n\n"


class SSEStream:
    """
    Server-Sent Events stream manager.

    Provides async iterator for SSE events with heartbeat support.
    Deterministic dry-run mode for testing without external dependencies.
    """

    def __init__(self, heartbeat_interval: int = HEARTBEAT_INTERVAL) -> None:
        """
        Initialize SSE stream.

        Args:
            heartbeat_interval: Seconds between heartbeat events
        """
        self._heartbeat_interval = heartbeat_interval
        self._event_queue: asyncio.Queue[SSEEvent | None] = asyncio.Queue()
        self._closed = False

    async def send_event(self, event: SSEEvent) -> None:
        """
        Queue an event for transmission.

        Args:
            event: SSE event to send
        """
        if not self._closed:
            await self._event_queue.put(event)

    async def close(self) -> None:
        """Close the stream and stop sending events."""
        self._closed = True
        await self._event_queue.put(None)

    async def stream(self) -> AsyncIterator[str]:
        """
        Generate SSE event stream with heartbeats.

        Yields:
            Formatted SSE event strings
        """
        event_count = 0

        try:
            while not self._closed:
                try:
                    # Wait for event with timeout for heartbeat
                    event = await asyncio.wait_for(
                        self._event_queue.get(),
                        timeout=self._heartbeat_interval,
                    )

                    if event is None:
                        # Close signal received
                        break

                    event_count += 1
                    yield event.format()

                except TimeoutError:
                    # Send heartbeat comment
                    yield ": heartbeat\n\n"

        except asyncio.CancelledError:
            logger.info("SSE stream cancelled after %d events", event_count)
            raise

        finally:
            self._closed = True


def create_incident_update_event(
    incident_id: str,
    state: str,
    actor: str | None = None,
    timestamp: str = "",
) -> SSEEvent:
    """
    Create an incident state update event.

    Args:
        incident_id: Incident identifier
        state: New state (OPEN, ACK, SILENCED, RESOLVED)
        actor: Optional actor who triggered the update
        timestamp: ISO 8601 timestamp

    Returns:
        SSEEvent for incident update
    """
    return SSEEvent(
        event="incident_update",
        data={
            "incident_id": incident_id,
            "state": state,
            "actor": actor,
            "timestamp": timestamp,
        },
        id=f"incident_{incident_id}_{timestamp}",
    )


def create_alert_fired_event(
    rule_id: str,
    severity: str,
    message: str,
    timestamp: str = "",
) -> SSEEvent:
    """
    Create an alert fired event.

    Args:
        rule_id: Alert rule identifier
        severity: Alert severity (INFO, WARNING, ERROR, CRITICAL)
        message: Alert message
        timestamp: ISO 8601 timestamp

    Returns:
        SSEEvent for alert fired
    """
    return SSEEvent(
        event="alert_fired",
        data={
            "rule_id": rule_id,
            "severity": severity,
            "message": message,
            "timestamp": timestamp,
        },
        id=f"alert_{rule_id}_{timestamp}",
    )


__all__ = [
    "SSEEvent",
    "SSEStream",
    "create_incident_update_event",
    "create_alert_fired_event",
]
