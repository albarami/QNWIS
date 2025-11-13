"""Fixtures for API integration tests."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def api_client():
    """Create FastAPI test client with auth bypass for testing."""
    from src.qnwis.api.server import create_app

    app = create_app()
    # Bypass authentication for integration tests
    app.state.auth_bypass = True
    return TestClient(app)
