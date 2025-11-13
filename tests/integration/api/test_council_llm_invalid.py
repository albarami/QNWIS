"""
Negative-path integration tests for the LLM council API.

Ensures validation rejects malformed payloads before any workflow work begins.
"""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_run_llm_rejects_short_question(api_client: TestClient) -> None:
    response = api_client.post(
        "/api/v1/council/run-llm",
        json={"question": "Hi", "provider": "stub"},
    )
    assert response.status_code == 422
    detail = response.json()["detail"][0]
    assert detail["loc"][-1] == "question"


def test_run_llm_rejects_invalid_provider(api_client: TestClient) -> None:
    response = api_client.post(
        "/api/v1/council/run-llm",
        json={"question": "Valid question text", "provider": "azure"},
    )
    assert response.status_code == 422
    detail = response.json()["detail"][0]
    assert detail["loc"][-1] == "provider"


def test_run_llm_rejects_long_question(api_client: TestClient) -> None:
    response = api_client.post(
        "/api/v1/council/run-llm",
        json={"question": "X" * 6000, "provider": "stub"},
    )
    assert response.status_code == 422
    assert any(err["loc"][-1] == "question" for err in response.json()["detail"])
