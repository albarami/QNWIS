"""
Unit tests for Server-Sent Events (SSE) module.

Tests event formatting, streaming, heartbeats, and event helpers.
"""

from __future__ import annotations

import asyncio

import pytest

from src.qnwis.ops_console.sse import (
    SSEEvent,
    SSEStream,
    create_alert_fired_event,
    create_incident_update_event,
)


class TestSSEEvent:
    """Test SSE event data class and formatting."""

    def test_event_immutable(self):
        """SSE events are immutable."""
        event = SSEEvent(event="test", data={"key": "value"})

        with pytest.raises(AttributeError):
            event.event = "new_event"  # type: ignore

    def test_format_simple_event(self):
        """Format simple event without id or retry."""
        event = SSEEvent(
            event="test_event",
            data={"message": "hello", "count": 42},
        )

        formatted = event.format()

        assert "event: test_event\n" in formatted
        assert "data: " in formatted
        assert '"message": "hello"' in formatted
        assert '"count": 42' in formatted
        assert formatted.endswith("\n\n")

    def test_format_with_id(self):
        """Format event with ID for reconnection."""
        event = SSEEvent(
            event="update",
            data={"status": "ok"},
            id="event_123",
        )

        formatted = event.format()

        assert "id: event_123\n" in formatted
        assert "event: update\n" in formatted

    def test_format_with_retry(self):
        """Format event with retry interval."""
        event = SSEEvent(
            event="error",
            data={"error": "temporary"},
            retry=5000,
        )

        formatted = event.format()

        assert "retry: 5000\n" in formatted
        assert "event: error\n" in formatted

    def test_format_with_all_fields(self):
        """Format event with all fields."""
        event = SSEEvent(
            event="full_event",
            data={"field": "value"},
            id="full_123",
            retry=3000,
        )

        formatted = event.format()

        assert "id: full_123\n" in formatted
        assert "retry: 3000\n" in formatted
        assert "event: full_event\n" in formatted
        assert "data: " in formatted

    def test_format_multiline_data(self):
        """Format event with multiline data."""
        event = SSEEvent(
            event="multiline",
            data={"text": "line1\nline2\nline3"},
        )

        formatted = event.format()

        # Each line should be prefixed with "data: "
        assert "data: " in formatted

    def test_format_unicode_data(self):
        """Format event with unicode characters."""
        event = SSEEvent(
            event="unicode",
            data={"message": "مرحبا", "emoji": "🚀"},
        )

        formatted = event.format()

        assert "مرحبا" in formatted
        assert "🚀" in formatted


class TestSSEStream:
    """Test SSE stream manager."""

    def test_initialization(self):
        """Can initialize SSE stream."""
        stream = SSEStream(heartbeat_interval=30)

        assert stream._heartbeat_interval == 30
        assert stream._closed is False

    @pytest.mark.asyncio
    async def test_send_event(self):
        """Can queue events for transmission."""
        stream = SSEStream()
        event = SSEEvent(event="test", data={"key": "value"})

        await stream.send_event(event)

        # Event should be in queue
        queued_event = await asyncio.wait_for(stream._event_queue.get(), timeout=1.0)
        assert queued_event == event

    @pytest.mark.asyncio
    async def test_close_stream(self):
        """Can close stream."""
        stream = SSEStream()

        await stream.close()

        assert stream._closed is True
        # None sentinel should be in queue
        sentinel = await asyncio.wait_for(stream._event_queue.get(), timeout=1.0)
        assert sentinel is None

    @pytest.mark.asyncio
    async def test_stream_events(self):
        """Stream yields formatted events."""
        stream = SSEStream(heartbeat_interval=100)  # Long interval to avoid heartbeat

        # Queue events
        event1 = SSEEvent(event="test1", data={"n": 1})
        event2 = SSEEvent(event="test2", data={"n": 2})

        # Send events before starting iteration
        await stream.send_event(event1)
        await stream.send_event(event2)

        # Start collection in background task
        output = []

        async def collect():
            async for chunk in stream.stream():
                output.append(chunk)

        # Start collection
        task = asyncio.create_task(collect())

        # Give it time to process queued events
        await asyncio.sleep(0.1)

        # Close stream
        await stream.close()

        # Wait for task to complete
        await asyncio.wait_for(task, timeout=2.0)

        assert len(output) == 2
        assert "test1" in output[0]
        assert "test2" in output[1]

    @pytest.mark.asyncio
    async def test_stream_heartbeat(self):
        """Stream sends heartbeat on timeout."""
        stream = SSEStream(heartbeat_interval=1)  # 1 second for test

        # Don't send any events, wait for heartbeat
        output = []

        async def collect_output():
            async for chunk in stream.stream():
                output.append(chunk)
                if len(output) >= 1:
                    await stream.close()
                    break

        # Run with timeout
        try:
            await asyncio.wait_for(collect_output(), timeout=3.0)
        except TimeoutError:
            pass

        # Should have at least one heartbeat
        assert len(output) >= 1
        assert any(": heartbeat" in chunk for chunk in output)

    @pytest.mark.asyncio
    async def test_stream_cancellation(self):
        """Stream handles cancellation gracefully."""
        stream = SSEStream(heartbeat_interval=100)

        async def run_stream():
            async for chunk in stream.stream():
                pass

        task = asyncio.create_task(run_stream())

        # Cancel after short delay
        await asyncio.sleep(0.1)
        task.cancel()

        # Should raise CancelledError
        with pytest.raises(asyncio.CancelledError):
            await task

    @pytest.mark.asyncio
    async def test_send_event_after_close(self):
        """Cannot send events after close."""
        stream = SSEStream()
        await stream.close()

        event = SSEEvent(event="test", data={})
        await stream.send_event(event)

        # Should not be queued (closed flag prevents it)
        # Queue should only have None sentinel
        sentinel = await asyncio.wait_for(stream._event_queue.get(), timeout=1.0)
        assert sentinel is None


class TestSSEEventHelpers:
    """Test helper functions for creating common events."""

    def test_create_incident_update_event(self):
        """Create incident update event."""
        event = create_incident_update_event(
            incident_id="inc_123",
            state="ACK",
            actor="user@example.com",
            timestamp="2024-01-01T12:00:00Z",
        )

        assert event.event == "incident_update"
        assert event.data["incident_id"] == "inc_123"
        assert event.data["state"] == "ACK"
        assert event.data["actor"] == "user@example.com"
        assert event.data["timestamp"] == "2024-01-01T12:00:00Z"
        assert event.id == "incident_inc_123_2024-01-01T12:00:00Z"

    def test_create_incident_update_event_no_actor(self):
        """Create incident update event without actor."""
        event = create_incident_update_event(
            incident_id="inc_456",
            state="RESOLVED",
            timestamp="2024-01-01T13:00:00Z",
        )

        assert event.data["actor"] is None

    def test_create_alert_fired_event(self):
        """Create alert fired event."""
        event = create_alert_fired_event(
            rule_id="rule_789",
            severity="CRITICAL",
            message="High CPU usage detected",
            timestamp="2024-01-01T14:00:00Z",
        )

        assert event.event == "alert_fired"
        assert event.data["rule_id"] == "rule_789"
        assert event.data["severity"] == "CRITICAL"
        assert event.data["message"] == "High CPU usage detected"
        assert event.data["timestamp"] == "2024-01-01T14:00:00Z"
        assert event.id == "alert_rule_789_2024-01-01T14:00:00Z"


@pytest.mark.asyncio
@pytest.mark.parametrize("heartbeat_interval", [1, 5, 30])
async def test_stream_with_different_intervals(heartbeat_interval: int):
    """Test stream with different heartbeat intervals."""
    stream = SSEStream(heartbeat_interval=heartbeat_interval)

    event = SSEEvent(event="test", data={"interval": heartbeat_interval})

    # Send event
    await stream.send_event(event)

    # Start collection task
    output = []

    async def collect():
        async for chunk in stream.stream():
            output.append(chunk)

    task = asyncio.create_task(collect())

    # Give time to process
    await asyncio.sleep(0.1)

    # Close stream
    await stream.close()

    # Wait for completion
    await asyncio.wait_for(task, timeout=2.0)

    assert len(output) >= 1
    assert f'"interval": {heartbeat_interval}' in output[0]
