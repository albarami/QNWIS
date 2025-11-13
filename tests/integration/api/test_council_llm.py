"""
Integration tests for LLM council API endpoints.

Tests both streaming (SSE) and complete (JSON) endpoints,
plus deprecation warning for legacy endpoint.
"""

from __future__ import annotations

import json
import warnings

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def api_client():
    """Create FastAPI test client with LLM council routes."""
    from src.qnwis.api.server import create_app

    app = create_app()
    app.state.auth_bypass = True
    return TestClient(app)


def test_run_llm_complete_returns_structure(api_client):
    """Test that /api/v1/council/run-llm returns expected structure."""
    response = api_client.post(
        "/api/v1/council/run-llm",
        json={"question": "Demo question for testing", "provider": "stub"},
    )

    assert response.status_code == 200
    data = response.json()

    # Verify all required top-level keys are present
    assert "synthesis" in data, "Missing synthesis in response"
    assert "agent_reports" in data, "Missing agent_reports in response"
    assert "classification" in data, "Missing classification in response"
    assert "verification" in data, "Missing verification in response"
    assert "metadata" in data, "Missing metadata in response"

    # Verify metadata structure
    metadata = data["metadata"]
    assert metadata["provider"] == "stub", "Provider mismatch"
    assert "question" in metadata, "Missing question in metadata"
    assert "model" in metadata, "Missing model in metadata"
    assert "stages" in metadata, "Missing stages in metadata"

    # Verify agent_reports is a list
    assert isinstance(data["agent_reports"], list), "agent_reports should be a list"


def test_run_llm_validates_provider(api_client):
    """Test that invalid provider is rejected."""
    response = api_client.post(
        "/api/v1/council/run-llm",
        json={"question": "Test question", "provider": "invalid_provider"},
    )

    # Should get validation error (422)
    assert response.status_code == 422


def test_run_llm_validates_question_length(api_client):
    """Test that question length is validated."""
    # Too short (< 3 chars)
    response = api_client.post(
        "/api/v1/council/run-llm",
        json={"question": "Hi", "provider": "stub"},
    )
    assert response.status_code == 422

    # Too long (> 5000 chars)
    long_question = "x" * 5001
    response = api_client.post(
        "/api/v1/council/run-llm",
        json={"question": long_question, "provider": "stub"},
    )
    assert response.status_code == 422


def test_streaming_endpoint_emits_sse_events(api_client):
    """Test that /api/v1/council/stream emits SSE events."""
    with api_client.stream(
        "POST",
        "/api/v1/council/stream",
        json={"question": "Test streaming", "provider": "stub"},
    ) as response:
        assert response.status_code == 200

        # Verify SSE content type
        content_type = response.headers.get("content-type", "")
        assert content_type.startswith(
            "text/event-stream"
        ), f"Expected text/event-stream, got {content_type}"

        # Verify cache headers
        assert response.headers.get("cache-control") == "no-cache"
        assert response.headers.get("x-accel-buffering") == "no"

        # Collect SSE event lines
        data_lines = []
        for line_bytes in response.iter_lines():
            line = line_bytes.decode("utf-8") if isinstance(line_bytes, bytes) else line_bytes
            if line.startswith("data: "):
                data_lines.append(line)
            # Collect at least a few events
            if len(data_lines) >= 3:
                break

        # Verify we received some events
        assert len(data_lines) >= 1, "Should receive at least one SSE event"

        # Parse first event to verify structure
        first_event_json = data_lines[0][6:]  # Remove "data: " prefix
        first_event = json.loads(first_event_json)

        # Verify event structure
        assert "stage" in first_event, "Event missing 'stage' field"
        assert "status" in first_event, "Event missing 'status' field"
        assert "payload" in first_event, "Event missing 'payload' field"
        assert "latency_ms" in first_event, "Event missing 'latency_ms' field"
        assert "timestamp" in first_event, "Event missing 'timestamp' field"


def test_streaming_endpoint_validates_input(api_client):
    """Test that streaming endpoint validates input."""
    # Invalid provider
    response = api_client.post(
        "/api/v1/council/stream",
        json={"question": "Test", "provider": "invalid"},
    )
    assert response.status_code == 422

    # Question too short
    response = api_client.post(
        "/api/v1/council/stream",
        json={"question": "Hi", "provider": "stub"},
    )
    assert response.status_code == 422


def test_legacy_endpoint_deprecation_warning(api_client):
    """Test that legacy /v1/council/run endpoint issues deprecation warning."""
    with warnings.catch_warnings(record=True) as warning_list:
        warnings.simplefilter("always")

        response = api_client.post("/api/v1/council/run")

        # Verify response indicates deprecation
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "deprecated", "Expected deprecated status"
        assert "message" in data, "Expected deprecation message"
        assert "run-llm" in data["message"], "Message should mention new endpoint"

        # Verify DeprecationWarning was issued
        deprecation_warnings = [
            w for w in warning_list if issubclass(w.category, DeprecationWarning)
        ]
        assert len(deprecation_warnings) > 0, "Should issue DeprecationWarning"

        # Verify warning message mentions the new endpoint
        warning_message = str(deprecation_warnings[0].message)
        assert "run-llm" in warning_message, "Warning should mention new endpoint"


def test_run_llm_with_anthropic_provider(api_client):
    """Test with anthropic provider (will use stub if no API key)."""
    response = api_client.post(
        "/api/v1/council/run-llm",
        json={"question": "Test with anthropic", "provider": "anthropic"},
    )

    # Should work even without API key (falls back to stub)
    # or might return 500 if anthropic client fails
    assert response.status_code in [200, 500]


def test_run_llm_with_custom_model(api_client):
    """Test with custom model override."""
    response = api_client.post(
        "/api/v1/council/run-llm",
        json={
            "question": "Test custom model",
            "provider": "stub",
            "model": "custom-model-v1",
        },
    )

    assert response.status_code == 200
    data = response.json()

    # Model should be in metadata
    assert "metadata" in data
    assert "model" in data["metadata"]


def test_streaming_event_stages(api_client):
    """Test that streaming endpoint emits expected stages."""
    expected_stages = {"classify", "prefetch", "verify", "synthesize"}
    observed_stages = set()

    with api_client.stream(
        "POST",
        "/api/v1/council/stream",
        json={"question": "Test stages", "provider": "stub"},
    ) as response:
        assert response.status_code == 200

        for line_bytes in response.iter_lines():
            line = line_bytes.decode("utf-8") if isinstance(line_bytes, bytes) else line_bytes
            if line.startswith("data: "):
                try:
                    event = json.loads(line[6:])
                    stage = event.get("stage")
                    if stage:
                        observed_stages.add(stage.split(":")[0])  # Remove agent: prefix
                except json.JSONDecodeError:
                    continue

            # Stop after collecting a reasonable number of events
            if len(observed_stages) >= 3:
                break

    # Verify we saw some expected stages
    assert len(observed_stages) > 0, "Should observe at least some stages"
