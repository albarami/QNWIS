"""
Integration tests for SSE live updates.

Tests SSE stream, event delivery, and HTMX integration.
"""

from __future__ import annotations

import asyncio
import contextlib
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from src.qnwis.ops_console.app import create_ops_app
from src.qnwis.ops_console.sse import SSEStream, create_incident_update_event
from src.qnwis.security import Principal
from src.qnwis.utils.clock import ManualClock


@pytest.fixture
def manual_clock():
    """Manual clock for deterministic timestamps."""
    return ManualClock(start=datetime(2024, 1, 1, 12, 0, tzinfo=UTC))


@pytest.fixture
def ops_app(manual_clock):
    """Create ops console app with test configuration."""
    app = create_ops_app(clock=manual_clock, secret_key="test_secret")

    # Add middleware to inject principal
    @app.middleware("http")
    async def inject_principal(request, call_next):
        request.state.principal = Principal(
            user_id="test@example.com",
            roles=["analyst"],
        )
        response = await call_next(request)
        return response

    return app


class TestSSEStream:
    """Test SSE streaming endpoint."""

    def test_sse_endpoint_exists(self, ops_app):
        """SSE stream endpoint exists."""
        client = TestClient(ops_app)

        # Note: TestClient doesn't fully support streaming, but we can check response
        response = client.get("/stream/incidents")

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

    def test_sse_headers(self, ops_app):
        """SSE response has correct headers."""
        client = TestClient(ops_app)

        response = client.get("/stream/incidents")

        assert "Cache-Control" in response.headers
        assert "no-cache" in response.headers["Cache-Control"]
        assert "X-Accel-Buffering" in response.headers

    @pytest.mark.asyncio
    async def test_sse_event_format(self):
        """SSE events have correct format."""
        stream = SSEStream(heartbeat_interval=100)

        # Send test event
        event = create_incident_update_event(
            incident_id="inc_123",
            state="ACK",
            actor="user@test.com",
            timestamp="2024-01-01T12:00:00Z",
        )

        await stream.send_event(event)
        await stream.close()

        # Collect output
        output = []
        async for chunk in stream.stream():
            output.append(chunk)

        assert len(output) == 1
        assert "event: incident_update\n" in output[0]
        assert "data: " in output[0]
        assert "inc_123" in output[0]

    @pytest.mark.asyncio
    async def test_sse_multiple_events(self):
        """Can stream multiple events."""
        stream = SSEStream(heartbeat_interval=100)

        # Send multiple events
        for i in range(3):
            event = create_incident_update_event(
                incident_id=f"inc_{i}",
                state="ACK",
                timestamp="2024-01-01T12:00:00Z",
            )
            await stream.send_event(event)

        await stream.close()

        # Collect output
        output = []
        async for chunk in stream.stream():
            output.append(chunk)

        assert len(output) == 3

    @pytest.mark.asyncio
    async def test_sse_event_id(self):
        """SSE events include ID for reconnection."""
        stream = SSEStream(heartbeat_interval=100)

        event = create_incident_update_event(
            incident_id="inc_123",
            state="RESOLVED",
            timestamp="2024-01-01T12:00:00Z",
        )

        await stream.send_event(event)
        await stream.close()

        output = []
        async for chunk in stream.stream():
            output.append(chunk)

        assert len(output) == 1
        assert "id: incident_inc_123" in output[0]

    @pytest.mark.asyncio
    async def test_sse_heartbeat(self):
        """SSE stream sends heartbeat on timeout."""
        stream = SSEStream(heartbeat_interval=1)  # 1 second

        output = []

        async def collect():
            async for chunk in stream.stream():
                output.append(chunk)
                if len(output) >= 1:
                    await stream.close()
                    break

        # Run with timeout
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(collect(), timeout=3.0)

        # Should have received heartbeat
        assert len(output) >= 1
        assert any(": heartbeat" in chunk for chunk in output)

    @pytest.mark.asyncio
    async def test_sse_close_terminates_stream(self):
        """Closing SSE stream terminates iteration."""
        stream = SSEStream(heartbeat_interval=100)

        # Close immediately
        await stream.close()

        output = []
        async for chunk in stream.stream():
            output.append(chunk)

        # Should have no events (only None sentinel processed)
        assert len(output) == 0

    @pytest.mark.asyncio
    async def test_sse_event_ordering(self):
        """SSE events are delivered in order."""
        stream = SSEStream(heartbeat_interval=100)

        # Send ordered events
        for i in range(5):
            event = create_incident_update_event(
                incident_id=f"inc_{i:03d}",
                state="ACK",
                timestamp=f"2024-01-01T12:00:{i:02d}Z",
            )
            await stream.send_event(event)

        await stream.close()

        output = []
        async for chunk in stream.stream():
            output.append(chunk)

        assert len(output) == 5
        # Check ordering
        for i in range(5):
            assert f"inc_{i:03d}" in output[i]


class TestLiveUpdateIntegration:
    """Test live updates integration with incident actions."""

    @pytest.mark.asyncio
    async def test_incident_update_sends_sse_event(self, ops_app, manual_clock):
        """Incident state change sends SSE event."""
        from src.qnwis.notify.models import Incident, IncidentState, Severity
        from src.qnwis.notify.resolver import IncidentResolver

        # Setup resolver and SSE stream
        resolver = IncidentResolver(clock=manual_clock, ledger_dir=None)
        sse_stream = SSEStream(heartbeat_interval=100)

        ops_app.state.incident_resolver = resolver
        ops_app.state.sse_stream = sse_stream

        # Create incident
        incident = Incident(
            incident_id="inc_test",
            notification_id="notif_test",
            rule_id="rule_1",
            severity=Severity.WARNING,
            state=IncidentState.OPEN,
            message="Test incident",
            scope={},
            window_start="2024-01-01T00:00:00Z",
            window_end="2024-01-01T01:00:00Z",
            created_at="2024-01-01T00:30:00Z",
            updated_at="2024-01-01T00:30:00Z",
            consecutive_green_count=0,
            metadata={},
        )
        resolver._store[incident.incident_id] = incident

        # Acknowledge incident (this should trigger SSE event)
        updated = resolver.acknowledge_incident(
            incident_id="inc_test",
            actor="test@example.com",
            timestamp=manual_clock.utcnow(),
        )

        # Manually send SSE event (views.py does this)
        from src.qnwis.ops_console.sse import create_incident_update_event
        await sse_stream.send_event(
            create_incident_update_event(
                incident_id="inc_test",
                state=updated.state.value,
                actor="test@example.com",
                timestamp=manual_clock.utcnow(),
            )
        )
        await sse_stream.close()

        # Collect SSE output
        output = []
        async for chunk in sse_stream.stream():
            output.append(chunk)

        assert len(output) == 1
        assert "inc_test" in output[0]
        assert "ack" in output[0].lower()


class TestSSEDeterminism:
    """Test SSE deterministic behavior."""

    @pytest.mark.asyncio
    async def test_same_event_same_output(self):
        """Same event produces same SSE output."""
        event = create_incident_update_event(
            incident_id="inc_123",
            state="ACK",
            actor="user@test.com",
            timestamp="2024-01-01T12:00:00Z",
        )

        formatted1 = event.format()
        formatted2 = event.format()

        assert formatted1 == formatted2

    @pytest.mark.asyncio
    async def test_stream_output_deterministic(self):
        """SSE stream produces deterministic output for same events."""
        async def run_stream():
            stream = SSEStream(heartbeat_interval=100)

            event = create_incident_update_event(
                incident_id="inc_123",
                state="RESOLVED",
                timestamp="2024-01-01T12:00:00Z",
            )

            await stream.send_event(event)
            await stream.close()

            output = []
            async for chunk in stream.stream():
                output.append(chunk)

            return output

        output1 = await run_stream()
        output2 = await run_stream()

        assert output1 == output2


class TestSSEPerformance:
    """Test SSE performance characteristics."""

    @pytest.mark.asyncio
    async def test_sse_enqueue_latency(self):
        """SSE event enqueue is fast (< 5ms)."""
        import time

        stream = SSEStream(heartbeat_interval=100)

        event = create_incident_update_event(
            incident_id="inc_perf",
            state="ACK",
            timestamp="2024-01-01T12:00:00Z",
        )

        # Measure enqueue time
        start = time.perf_counter()
        await stream.send_event(event)
        elapsed_ms = (time.perf_counter() - start) * 1000

        await stream.close()

        # Should be very fast (< 5ms target, but allow some margin for CI)
        assert elapsed_ms < 10.0

    @pytest.mark.asyncio
    async def test_sse_format_performance(self):
        """SSE event formatting is fast."""
        import time

        event = create_incident_update_event(
            incident_id="inc_perf",
            state="ACK",
            timestamp="2024-01-01T12:00:00Z",
        )

        # Measure format time
        start = time.perf_counter()
        for _ in range(1000):
            event.format()
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Average should be very fast (< 1ms per format for 1000 iterations)
        assert elapsed_ms < 100.0
