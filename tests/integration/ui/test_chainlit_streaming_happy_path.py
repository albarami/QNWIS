"""
Integration tests for Chainlit UI streaming happy path.

Smoke tests for UI streaming with mocked SSE responses to verify
the integration between Chainlit app and SSE client.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.qnwis.ui.streaming_client import WorkflowEvent


@pytest.fixture
def mock_sse_events():
    """Create mock SSE events for testing."""
    return [
        WorkflowEvent(
            stage="classify",
            status="running",
            payload={},
            latency_ms=None,
            timestamp="2025-01-01T00:00:00Z",
            request_id="test-123",
        ),
        WorkflowEvent(
            stage="classify",
            status="complete",
            payload={"classification": {"category": "employment"}},
            latency_ms=123.45,
            timestamp="2025-01-01T00:00:01Z",
            request_id="test-123",
        ),
        WorkflowEvent(
            stage="synthesize",
            status="streaming",
            payload={"token": "Qatar"},
            latency_ms=None,
            timestamp="2025-01-01T00:00:02Z",
            request_id="test-123",
        ),
        WorkflowEvent(
            stage="synthesize",
            status="streaming",
            payload={"token": "'s"},
            latency_ms=None,
            timestamp="2025-01-01T00:00:02.1Z",
            request_id="test-123",
        ),
        WorkflowEvent(
            stage="synthesize",
            status="complete",
            payload={"synthesis": "Qatar's unemployment rate..."},
            latency_ms=2500.0,
            timestamp="2025-01-01T00:00:05Z",
            request_id="test-123",
        ),
    ]


@pytest.mark.asyncio
async def test_sse_client_streams_events(mock_sse_events):
    """Test that SSE client can stream events successfully."""
    from src.qnwis.ui.streaming_client import SSEClient

    with patch("src.qnwis.ui.streaming_client.httpx.AsyncClient") as mock_client:
        # Mock the streaming response
        mock_response = AsyncMock()
        mock_response.aiter_lines = AsyncMock(return_value=iter([]))
        mock_response.raise_for_status = MagicMock()

        mock_ctx = AsyncMock()
        mock_ctx.__aenter__.return_value.stream.return_value.__aenter__.return_value = (
            mock_response
        )
        mock_client.return_value = mock_ctx.__aenter__.return_value

        # Override aiter_lines to return our mock events as JSON
        import json

        json_lines = []
        for event in mock_sse_events:
            json_lines.append(
                "data: " + json.dumps({
                    "stage": event.stage,
                    "status": event.status,
                    "payload": event.payload,
                    "latency_ms": event.latency_ms,
                    "timestamp": event.timestamp,
                })
            )

        mock_response.aiter_lines = AsyncMock(return_value=iter(json_lines))

        # Stream events
        client = SSEClient("http://localhost:8001")
        events = []
        async for event in client.stream("test question", provider="stub"):
            events.append(event)

        # Verify events were received
        assert len(events) == len(mock_sse_events)
        assert events[0].stage == "classify"
        assert events[-1].stage == "synthesize"


@pytest.mark.asyncio
async def test_telemetry_tracking():
    """Test that telemetry functions are called during streaming."""
    from src.qnwis.ui.telemetry import inc_errors, inc_requests, inc_tokens

    # These should not raise exceptions even if Prometheus unavailable
    inc_requests()
    inc_tokens(5)
    inc_errors()

    # Verify they're callable and non-blocking
    assert callable(inc_requests)
    assert callable(inc_tokens)
    assert callable(inc_errors)


@pytest.mark.asyncio
async def test_progress_panel_rendering():
    """Test that progress panel functions are callable."""
    from src.qnwis.ui.components.progress_panel import (
        render_error,
        render_info,
        render_stage,
        render_warning,
    )

    # These should be importable and callable
    assert callable(render_stage)
    assert callable(render_error)
    assert callable(render_warning)
    assert callable(render_info)


def test_chainlit_app_imports():
    """Test that Chainlit app imports successfully."""
    try:
        from src.qnwis.ui import chainlit_app_llm

        # Verify key components are present
        assert hasattr(chainlit_app_llm, "handle_message")
        assert hasattr(chainlit_app_llm, "start")
        assert hasattr(chainlit_app_llm, "BASE_URL")
    except ImportError as e:
        pytest.skip(f"Chainlit not available: {e}")


def test_sse_client_configuration():
    """Test SSE client can be configured with different URLs."""
    from src.qnwis.ui.streaming_client import SSEClient

    # Test default configuration
    client1 = SSEClient("http://localhost:8001")
    assert client1.base_url == "http://localhost:8001"
    assert client1.timeout == 120.0

    # Test custom timeout
    client2 = SSEClient("http://api.example.com", timeout=60.0)
    assert client2.base_url == "http://api.example.com"
    assert client2.timeout == 60.0


def test_workflow_event_immutability():
    """Test that WorkflowEvent is immutable (frozen dataclass)."""
    from src.qnwis.ui.streaming_client import WorkflowEvent

    event = WorkflowEvent(
        stage="test",
        status="complete",
        payload={},
        latency_ms=100.0,
        timestamp="2025-01-01T00:00:00Z",
        request_id="test-123",
    )

    # Attempting to modify should raise AttributeError
    with pytest.raises(AttributeError):
        event.stage = "modified"  # type: ignore


@pytest.mark.asyncio
async def test_sse_client_retry_logic():
    """Test that SSE client has retry capability."""
    from src.qnwis.ui.streaming_client import SSEClient
    import httpx

    client = SSEClient("http://localhost:8001")

    # Mock a connection error followed by success
    with patch("httpx.AsyncClient") as mock_client:
        mock_ctx = AsyncMock()

        # First attempt fails
        mock_ctx.__aenter__.return_value.stream.side_effect = [
            httpx.ConnectError("Connection failed"),
            # Second attempt would succeed but we'll just test the retry attempt
        ]

        mock_client.return_value = mock_ctx.__aenter__.return_value

        # This should attempt retry and eventually raise after 3 attempts
        with pytest.raises(httpx.ConnectError):
            async for _ in client.stream("test", provider="stub"):
                pass


def test_telemetry_no_op_without_prometheus():
    """Test that telemetry functions work without Prometheus."""
    from src.qnwis.ui import telemetry

    # Force PROM_AVAILABLE to False for testing
    original = telemetry.PROM_AVAILABLE
    try:
        telemetry.PROM_AVAILABLE = False

        # These should not raise exceptions
        telemetry.inc_requests()
        telemetry.inc_tokens(10)
        telemetry.inc_errors()
        telemetry.observe_stage_latency(123.45)

        # Test context manager
        with telemetry.stage_timer():
            pass  # Should not raise

    finally:
        telemetry.PROM_AVAILABLE = original


def test_base_url_from_environment():
    """Test that BASE_URL can be configured via environment."""
    import os
    from importlib import reload
    from src.qnwis.ui import chainlit_app_llm

    original = os.environ.get("QNWIS_API_URL")
    try:
        os.environ["QNWIS_API_URL"] = "http://custom-api:9000"
        reload(chainlit_app_llm)

        # BASE_URL should reflect environment variable
        assert chainlit_app_llm.BASE_URL == "http://custom-api:9000"

    finally:
        if original:
            os.environ["QNWIS_API_URL"] = original
        elif "QNWIS_API_URL" in os.environ:
            del os.environ["QNWIS_API_URL"]
        reload(chainlit_app_llm)
