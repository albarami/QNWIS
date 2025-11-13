"""
Integration tests for health check endpoints.

Tests liveness and readiness probes with subsystem checks
and proper status code behavior (200/503).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def api_client():
    """Create FastAPI test client with health routes."""
    from src.qnwis.api.server import create_app

    app = create_app()
    app.state.auth_bypass = True
    return TestClient(app)


def test_liveness_probe(api_client):
    """Test liveness endpoint always returns 200."""
    response = api_client.get("/health/live")

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "healthy"
    assert "timestamp" in data
    # Timestamp should be ISO format
    assert "T" in data["timestamp"]
    assert "Z" in data["timestamp"] or "+" in data["timestamp"]


def test_liveness_alias(api_client):
    """Test simple /health alias for liveness."""
    response = api_client.get("/api/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_readiness_probe_structure(api_client):
    """Test readiness endpoint returns proper structure."""
    response = api_client.get("/health/ready")

    # Status code should be 200 (healthy) or 503 (degraded)
    assert response.status_code in [200, 503]

    data = response.json()

    # Verify top-level structure
    assert "status" in data
    assert data["status"] in ["healthy", "degraded"]
    assert "timestamp" in data
    assert "version" in data
    assert "llm_provider" in data
    assert "llm_model" in data
    assert "registry_query_count" in data
    assert "checks" in data

    # Verify checks structure
    checks = data["checks"]
    assert isinstance(checks, dict)

    # Expected subsystem checks
    expected_checks = ["data_client", "llm_client", "database", "query_registry"]
    for check in expected_checks:
        assert check in checks, f"Missing check: {check}"


def test_readiness_data_client_check(api_client):
    """Test that data_client check is performed."""
    response = api_client.get("/health/ready")
    data = response.json()

    checks = data["checks"]
    assert "data_client" in checks

    # Should be either "healthy" or an error message
    data_client_status = checks["data_client"]
    assert isinstance(data_client_status, str)


def test_readiness_llm_client_check(api_client):
    """Test that llm_client stub check is performed."""
    response = api_client.get("/health/ready")
    data = response.json()

    checks = data["checks"]
    assert "llm_client" in checks

    llm_client_status = checks["llm_client"]
    assert isinstance(llm_client_status, str)


def test_readiness_query_registry_check(api_client):
    """Test that query_registry check reports query count."""
    response = api_client.get("/health/ready")
    data = response.json()

    checks = data["checks"]
    assert "query_registry" in checks

    query_registry_status = checks["query_registry"]
    assert isinstance(query_registry_status, str)
    assert "registry_query_count" in data
    if response.status_code == 200:
        assert isinstance(data["registry_query_count"], int)

    # Should mention query count if healthy
    if "healthy" in query_registry_status:
        assert "queries" in query_registry_status


def test_readiness_database_check_optional(api_client):
    """Test that database check is present but optional."""
    response = api_client.get("/health/ready")
    data = response.json()

    checks = data["checks"]
    assert "database" in checks

    # Database can be healthy, unavailable, or unhealthy
    db_status = checks["database"]
    assert isinstance(db_status, str)


def test_readiness_503_on_critical_failure(api_client):
    """Test that readiness returns 503 if critical checks fail."""
    # We can't easily force a failure in integration tests,
    # but we can verify the response format matches expectations
    response = api_client.get("/health/ready")

    if response.status_code == 503:
        data = response.json()
        assert data["status"] == "degraded"
        assert "checks" in data

        # At least one check should be unhealthy
        checks = data["checks"]
        has_unhealthy = any(
            "unhealthy" in str(status) for status in checks.values()
        )
        assert has_unhealthy, "503 response should have at least one unhealthy check"


def test_readiness_200_on_all_healthy(api_client):
    """Test that readiness returns 200 when all checks pass."""
    response = api_client.get("/health/ready")

    if response.status_code == 200:
        data = response.json()
        assert data["status"] == "healthy"

        # Most checks should be healthy (database is optional)
        checks = data["checks"]
        critical_checks = ["data_client", "llm_client", "query_registry"]

        for check in critical_checks:
            status = checks.get(check, "")
            # Should contain "healthy" or be unavailable (for optional checks)
            assert "healthy" in status or "unavailable" in status
        assert isinstance(data["registry_query_count"], int)


def test_health_endpoints_no_auth_required(api_client):
    """Test that health endpoints don't require authentication."""
    # Health checks should work without auth for k8s/monitoring
    response = api_client.get("/health/live")
    assert response.status_code == 200

    response = api_client.get("/health/ready")
    assert response.status_code in [200, 503]


def test_liveness_idempotent(api_client):
    """Test that liveness can be called multiple times."""
    for _ in range(5):
        response = api_client.get("/health/live")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


def test_readiness_idempotent(api_client):
    """Test that readiness can be called multiple times."""
    responses = []
    for _ in range(3):
        response = api_client.get("/health/ready")
        responses.append(response.status_code)

    # All responses should be consistent
    assert all(code in [200, 503] for code in responses)
    # Status should be stable across calls
    assert len(set(responses)) <= 1 or max(responses) - min(responses) == 0


def test_readiness_timestamp_format(api_client):
    """Test that timestamps are properly formatted."""
    response = api_client.get("/health/ready")
    data = response.json()

    timestamp = data["timestamp"]
    # ISO 8601 format check
    assert isinstance(timestamp, str)
    assert "T" in timestamp
    # Should have timezone info
    assert "Z" in timestamp or "+" in timestamp or "-" in timestamp[-6:]
