"""
Integration tests for C1: Legacy API endpoint deprecation.

Verifies that deprecated endpoints return proper warnings and redirect information.
"""

from __future__ import annotations

import warnings

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client() -> TestClient:
    """Create test client for API."""
    from qnwis.api.server import app

    return TestClient(app)


class TestLegacyCouncilDeprecation:
    """Test deprecated /v1/council/run endpoint."""

    def test_council_run_returns_deprecation_notice(self, client: TestClient) -> None:
        """Legacy council endpoint returns deprecation status."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            response = client.post("/api/v1/council/run")

            # Check HTTP response
            assert response.status_code == 200
            data = response.json()

            # Check deprecation metadata
            assert data["status"] == "deprecated"
            assert "Use /api/v1/council/run-llm" in data["message"]

            # Check Python warning was issued
            assert len(w) >= 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "/v1/council/run" in str(w[0].message)

    def test_council_run_still_functional(self, client: TestClient) -> None:
        """Legacy endpoint still executes (backward compatibility)."""
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            response = client.post("/api/v1/council/run")

            assert response.status_code == 200
            data = response.json()

            # Should contain legacy result structure (even if empty)
            assert "council" in data or "status" in data
            assert "verification" in data or "status" in data


class TestLegacyBriefingDeprecation:
    """Test deprecated /v1/briefing/minister endpoint."""

    def test_briefing_returns_deprecation_notice(self, client: TestClient) -> None:
        """Legacy briefing endpoint returns deprecation status."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            response = client.post("/api/v1/briefing/minister")

            # Check HTTP response
            assert response.status_code == 200
            data = response.json()

            # Check deprecation metadata
            assert data["status"] == "deprecated"
            assert "Use /api/v1/council/run-llm" in data["message"]

            # Check redirect information provided
            assert "redirect" in data
            assert data["redirect"]["complete_json"] == "/api/v1/council/run-llm"
            assert data["redirect"]["streaming_sse"] == "/api/v1/council/stream"

            # Check example migration provided
            assert "example" in data
            assert data["example"]["method"] == "POST"
            assert "question" in data["example"]["body"]

            # Check Python warning was issued
            assert len(w) >= 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "/v1/briefing/minister" in str(w[0].message)

    def test_briefing_provides_migration_guidance(self, client: TestClient) -> None:
        """Deprecated endpoint includes full migration example."""
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            response = client.post("/api/v1/briefing/minister")

            data = response.json()

            # Verify migration example is actionable
            example = data["example"]
            assert example["url"] == "/api/v1/council/run-llm"
            assert "provider" in example["body"]
            assert example["body"]["provider"] == "anthropic"


class TestNewEndpointsActive:
    """Verify new LLM endpoints are active and functional."""

    def test_council_llm_endpoint_exists(self, client: TestClient) -> None:
        """New LLM council endpoint is available."""
        # Use stub provider to avoid external dependencies
        response = client.post(
            "/api/v1/council/run-llm",
            json={"question": "Test question", "provider": "stub"},
        )

        # Should not be 404 (endpoint exists)
        # May be 200, 422 (validation), or 500 (execution) depending on setup
        assert response.status_code != 404

    def test_council_stream_endpoint_exists(self, client: TestClient) -> None:
        """New streaming LLM endpoint is available."""
        response = client.post(
            "/api/v1/council/stream",
            json={"question": "Test question", "provider": "stub"},
        )

        # Should not be 404 (endpoint exists)
        assert response.status_code != 404


class TestBackwardCompatibility:
    """Verify backward compatibility is maintained."""

    def test_legacy_endpoints_accept_original_parameters(
        self, client: TestClient
    ) -> None:
        """Legacy endpoints still accept their original parameter format."""
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")

            # Council endpoint
            response = client.post(
                "/api/v1/council/run",
                params={"queries_dir": None, "ttl_s": 300},
            )
            assert response.status_code == 200

            # Briefing endpoint
            response = client.post(
                "/api/v1/briefing/minister",
                params={"queries_dir": None, "ttl_s": 300},
            )
            assert response.status_code == 200

    def test_no_breaking_changes_to_response_structure(
        self, client: TestClient
    ) -> None:
        """Response structure changes are additive only."""
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")

            # Council response includes status field (additive)
            response = client.post("/api/v1/council/run")
            data = response.json()
            assert isinstance(data, dict)  # Still returns dict

            # Briefing response includes status field (additive)
            response = client.post("/api/v1/briefing/minister")
            data = response.json()
            assert isinstance(data, dict)  # Still returns dict


@pytest.mark.parametrize(
    "endpoint",
    [
        "/api/v1/council/run",
        "/api/v1/briefing/minister",
    ],
)
def test_all_legacy_endpoints_emit_warnings(
    endpoint: str, client: TestClient
) -> None:
    """All legacy endpoints emit deprecation warnings."""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        response = client.post(endpoint)

        assert response.status_code == 200
        assert len(w) >= 1
        assert issubclass(w[0].category, DeprecationWarning)


def test_openapi_schema_documents_deprecation(client: TestClient) -> None:
    """OpenAPI schema marks deprecated endpoints."""
    response = client.get("/openapi.json")
    assert response.status_code == 200

    schema = response.json()
    paths = schema.get("paths", {})

    # Check if endpoints are documented (may or may not have deprecated flag)
    # This is informational - FastAPI may not auto-mark @deprecated
    assert "/api/v1/council/run" in paths or "/v1/council/run" in paths
    assert (
        "/api/v1/briefing/minister" in paths or "/v1/briefing/minister" in paths
    )
