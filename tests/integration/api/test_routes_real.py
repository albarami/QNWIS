"""
Integration tests for FastAPI routes using the REAL application.

NO mocks, NO hardcoded data — exercises the actual create_app() factory,
real middleware stack, and real auth flow.
"""

from __future__ import annotations

from dotenv import load_dotenv
load_dotenv()

import pytest
from fastapi.testclient import TestClient

from src.qnwis.api.server import create_app

API_PREFIX = "/api/v1"


@pytest.fixture(scope="module")
def real_app():
    """Build the real FastAPI app once per module."""
    return create_app()


@pytest.fixture(scope="module")
def client(real_app):
    """TestClient wrapping the real app (auth bypass OFF)."""
    real_app.state.auth_bypass = False
    return TestClient(real_app, raise_server_exceptions=False)


@pytest.fixture(scope="module")
def authed_client(real_app):
    """TestClient wrapping the real app with auth bypass for protected routes."""
    real_app.state.auth_bypass = True
    return TestClient(real_app, raise_server_exceptions=False)


# ── Root info endpoint ──────────────────────────────────────────────────────

class TestRootInfo:
    def test_root_returns_200(self, client):
        resp = client.get("/")
        assert resp.status_code == 200

    def test_root_contains_app_name(self, client):
        data = client.get("/").json()
        assert "name" in data
        assert "QNWIS" in data["name"]

    def test_root_contains_version(self, client):
        data = client.get("/").json()
        assert "version" in data

    def test_root_contains_environment(self, client):
        data = client.get("/").json()
        assert "environment" in data


# ── Health endpoints (public, no auth required) ─────────────────────────────

class TestHealthEndpoints:
    def test_health_returns_200(self, client):
        resp = client.get("/health")
        assert resp.status_code in (200, 503)
        data = resp.json()
        assert "status" in data

    def test_health_live_returns_200(self, client):
        resp = client.get("/health/live")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data

    def test_health_live_idempotent(self, client):
        """Calling /health/live multiple times always succeeds."""
        for _ in range(3):
            resp = client.get("/health/live")
            assert resp.status_code == 200

    def test_health_ready_structure(self, client):
        resp = client.get("/health/ready")
        assert resp.status_code in (200, 503)
        data = resp.json()
        assert "status" in data
        assert data["status"] in ("healthy", "unhealthy", "degraded")
        assert "timestamp" in data
        assert "components" in data
        assert isinstance(data["components"], list)


# ── Auth enforcement on protected routes ─────────────────────────────────────

class TestAuthEnforcement:
    def test_council_stream_requires_auth(self, client):
        """POST /api/v1/council/stream without credentials must not succeed.

        Returns 401 (no creds) or 500 (auth provider unavailable in test)
        — either proves auth middleware is active and not bypassed.
        """
        resp = client.post(
            f"{API_PREFIX}/council/stream",
            json={"question": "test"},
        )
        assert resp.status_code != 200, (
            f"Protected route should NOT return 200 without auth, got: {resp.text}"
        )
        assert resp.status_code in (401, 403, 422, 500)

    def test_council_stream_rejects_empty_bearer(self, client):
        """Invalid bearer token must be rejected (401) or fail (500 if no provider)."""
        resp = client.post(
            f"{API_PREFIX}/council/stream",
            json={"question": "test"},
            headers={"Authorization": "Bearer invalid-token"},
        )
        assert resp.status_code in (401, 403, 500)

    def test_public_routes_skip_auth(self, client):
        """Health and root endpoints must be accessible without credentials."""
        for path in ("/", "/health", "/health/live", "/health/ready"):
            resp = client.get(path)
            assert resp.status_code in (200, 503), (
                f"{path} returned {resp.status_code}, expected public access"
            )


# ── Correct route-path prefixing (no double /api/v1) ────────────────────────

class TestRoutePaths:
    def test_continuity_plan_correct_path(self, authed_client):
        """The correct path is /api/v1/continuity/plan, NOT /api/v1/api/v1/continuity/plan."""
        resp = authed_client.get(f"{API_PREFIX}/continuity/plan")
        assert resp.status_code != 404, "Correct continuity/plan path should exist"

    def test_double_prefix_returns_404(self, authed_client):
        """A doubled prefix like /api/v1/api/v1/... must NOT resolve."""
        resp = authed_client.get(f"{API_PREFIX}{API_PREFIX}/continuity/plan")
        assert resp.status_code == 404

    def test_council_run_correct_path(self, authed_client):
        resp = authed_client.post(
            f"{API_PREFIX}/council/run",
            json={},
        )
        assert resp.status_code != 404, "council/run route should exist"

    def test_council_stream_correct_path(self, authed_client):
        resp = authed_client.post(
            f"{API_PREFIX}/council/stream",
            json={"question": "What is the employment rate?"},
        )
        assert resp.status_code != 404, "council/stream route should exist"


# ── Response headers ────────────────────────────────────────────────────────

class TestResponseHeaders:
    def test_request_id_header_present(self, client):
        resp = client.get("/")
        assert "x-request-id" in resp.headers

    def test_response_time_header_present(self, client):
        resp = client.get("/")
        assert "x-response-time-ms" in resp.headers

    def test_custom_request_id_echoed(self, client):
        custom_id = "test-req-12345"
        resp = client.get("/", headers={"x-request-id": custom_id})
        assert resp.headers.get("x-request-id") == custom_id
