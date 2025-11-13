"""
Unit tests for SSE parsing and streaming client resilience.
"""

from __future__ import annotations

import json
from typing import Iterable, List

import pytest

from src.qnwis.ui.streaming_client import SSEClient, WorkflowEvent


class DummyResponse:
    """Minimal httpx.Response stand-in for SSE iteration tests."""

    def __init__(self, lines: Iterable[str]) -> None:
        self._lines = list(lines)

    def raise_for_status(self) -> None:
        return None

    def aiter_lines(self):
        async def _gen():
            for line in self._lines:
                yield line

        return _gen()


class DummyStreamContext:
    """Async context manager that yields the dummy response."""

    def __init__(self, response: DummyResponse) -> None:
        self._response = response

    async def __aenter__(self) -> DummyResponse:
        return self._response

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False


class DummyAsyncClient:
    """AsyncClient replacement that returns the dummy response."""

    def __init__(self, response: DummyResponse) -> None:
        self._response = response

    async def __aenter__(self) -> "DummyAsyncClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False

    def stream(self, *args, **kwargs) -> DummyStreamContext:
        return DummyStreamContext(self._response)


def _patch_async_client(monkeypatch, lines: List[str]) -> None:
    """Patch httpx.AsyncClient to yield the provided SSE lines."""

    response = DummyResponse(lines)

    def _factory(*_, **__):
        return DummyAsyncClient(response)

    monkeypatch.setattr("src.qnwis.ui.streaming_client.httpx.AsyncClient", _factory)


async def _collect_iterated_events(client: SSEClient, lines: List[str]) -> list[WorkflowEvent]:
    response = DummyResponse(lines)
    events: list[WorkflowEvent] = []
    async for event in client._iterate_sse(response, "rid-test"):  # type: ignore[attr-defined]
        events.append(event)
    return events


def test_workflow_event_creation():
    """Test WorkflowEvent dataclass creation and immutability."""

    event = WorkflowEvent(
        stage="classify",
        status="complete",
        payload={"classification": {"category": "employment"}},
        latency_ms=123.45,
        timestamp="2025-01-01T00:00:00Z",
        request_id="test-123",
    )

    assert event.stage == "classify"
    assert event.status == "complete"
    assert event.payload["classification"]["category"] == "employment"
    assert event.latency_ms == 123.45
    assert event.timestamp == "2025-01-01T00:00:00Z"
    assert event.request_id == "test-123"

    with pytest.raises(AttributeError):
        event.stage = "prefetch"  # type: ignore[attr-defined]


def test_sse_client_initialization():
    """Test SSE client initialization with various parameters."""

    client = SSEClient("http://localhost:8001")
    assert client.base_url == "http://localhost:8001"
    assert client.timeout == 120.0

    client2 = SSEClient("http://localhost:8001/", timeout=60.0)
    assert client2.base_url == "http://localhost:8001"
    assert client2.timeout == 60.0


def test_sse_invalid_base_url_rejected():
    """Ensure invalid base URLs raise immediately."""

    with pytest.raises(ValueError):
        SSEClient("localhost:8001")


@pytest.mark.asyncio
async def test_sse_stream_rejects_invalid_provider():
    """Providers outside allow-list should raise before network calls."""

    client = SSEClient("http://localhost:8001")
    with pytest.raises(ValueError):
        async for _ in client.stream(question="Valid question", provider="azure"):
            pass


@pytest.mark.asyncio
async def test_iterate_sse_parses_events_and_heartbeat():
    """_iterate_sse should parse events, ignore heartbeats, and keep request IDs."""

    client = SSEClient("http://localhost:8001")
    lines = [
        f"data: {json.dumps({'stage': 'classify', 'status': 'running', 'payload': {}, 'timestamp': '2025-01-01T00:00:00Z'})}",
        "",
        "event: heartbeat",
        "data: {}",
        "",
        f"data: {json.dumps({'stage': 'classify', 'status': 'complete', 'payload': {'classification': {'category': 'employment'}}, 'latency_ms': 120.0, 'timestamp': '2025-01-01T00:00:01Z'})}",
    ]
    events = await _collect_iterated_events(client, lines)

    assert [e.stage for e in events] == ["classify", "classify"]
    assert events[1].latency_ms == 120.0


@pytest.mark.asyncio
async def test_iterate_sse_returns_warning_on_malformed_json():
    """Malformed JSON should emit a client warning event instead of crashing."""

    client = SSEClient("http://localhost:8001")
    lines = [
        "data: {invalid json}",
        "",
    ]
    events = await _collect_iterated_events(client, lines)

    assert len(events) == 1
    assert events[0].status == "warning"
    assert events[0].payload["warning"]


@pytest.mark.asyncio
async def test_iterate_sse_validates_streaming_tokens():
    """Invalid streaming payloads should surface warning events."""

    client = SSEClient("http://localhost:8001")
    bad_payload = json.dumps(
        {"stage": "synthesize", "status": "streaming", "payload": {"token": 42}}
    )
    events = await _collect_iterated_events(client, [f"data: {bad_payload}", ""])

    assert events[0].status == "warning"
    assert "token" in events[0].payload["warning"].lower()


@pytest.mark.asyncio
async def test_stream_propagates_request_id(monkeypatch):
    """Stream should propagate provided request_id to every event."""

    lines = [
        f"data: {json.dumps({'stage': 'classify', 'status': 'complete', 'payload': {}, 'timestamp': '2025-01-01T00:00:00Z'})}",
    ]
    _patch_async_client(monkeypatch, lines)

    client = SSEClient("http://localhost:8001")
    events = []
    async for event in client.stream(
        question="Valid question",
        provider="stub",
        request_id="rid-custom",
    ):
        events.append(event)

    assert len(events) == 1
    assert events[0].request_id == "rid-custom"


@pytest.mark.asyncio
async def test_stream_handles_token_streaming(monkeypatch):
    """Tokens should propagate through streaming events."""

    payload_stream = json.dumps(
        {"stage": "synthesize", "status": "streaming", "payload": {"token": "Qa"}}
    )
    payload_complete = json.dumps(
        {"stage": "synthesize", "status": "complete", "payload": {"synthesis": "Qa"}}
    )
    lines = [
        f"data: {payload_stream}",
        "",
        f"data: {payload_complete}",
    ]
    _patch_async_client(monkeypatch, lines)

    client = SSEClient("http://localhost:8001")
    tokens: list[str] = []
    async for event in client.stream(question="Valid question", provider="stub"):
        if event.status == "streaming":
            tokens.append(event.payload.get("token"))

    assert tokens == ["Qa"]


@pytest.mark.asyncio
async def test_stream_handles_warning_events(monkeypatch):
    """Warning events should be yielded to the UI for display."""

    warning_payload = json.dumps(
        {"stage": "client", "status": "warning", "payload": {"warning": "schema"}}
    )
    _patch_async_client(monkeypatch, [f"data: {warning_payload}", ""])

    client = SSEClient("http://localhost:8001")
    events = []
    async for event in client.stream(question="Valid question", provider="stub"):
        events.append(event)

    assert events[0].status == "warning"
    assert "schema" in events[0].payload["warning"]


@pytest.mark.asyncio
async def test_validate_question_bounds():
    """Questions outside allowed bounds should raise ValueError."""

    client = SSEClient("http://localhost:8001")
    with pytest.raises(ValueError):
        async for _ in client.stream(question="yo", provider="stub"):
            pass

    long_question = "x" * 6001
    with pytest.raises(ValueError):
        async for _ in client.stream(question=long_question, provider="stub"):
            pass
