"""
Integration tests for static dashboard.

Tests that the dashboard is served correctly and contains expected content.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from src.qnwis.app import app


def test_static_dashboard_served() -> None:
    """Test that static dashboard is accessible at /dash."""
    client = TestClient(app)
    response = client.get("/dash")
    assert response.status_code == 200
    assert "<title>QNWIS Synthetic Dashboard</title>" in response.text


def test_dashboard_has_expected_structure() -> None:
    """Test that dashboard HTML has expected sections."""
    client = TestClient(app)
    response = client.get("/dash")
    assert response.status_code == 200
    html = response.text
    # Check for main sections
    assert "<h1>QNWIS - Synthetic Dashboard</h1>" in html
    assert 'id="cards"' in html
    assert 'id="sector-employment"' in html
    assert 'id="salary"' in html


def test_dashboard_has_export_links() -> None:
    """Test that dashboard includes CSV and SVG export links."""
    client = TestClient(app)
    response = client.get("/dash")
    assert response.status_code == 200
    html = response.text
    # Check for export links
    assert "/v1/ui/export/csv?resource=sector-employment" in html
    assert "/v1/ui/export/svg?chart=sector-employment" in html


def test_dashboard_has_inline_css() -> None:
    """Test that dashboard embeds CSS inline and has no external stylesheet."""
    client = TestClient(app)
    response = client.get("/dash")
    assert response.status_code == 200
    html = response.text
    assert "<style>" in html
    assert "body {" in html
    assert 'href="styles.css"' not in html


def test_dashboard_has_js() -> None:
    """Test that dashboard links to JavaScript file."""
    client = TestClient(app)
    response = client.get("/dash")
    assert response.status_code == 200
    assert 'src="app.js"' in response.text


def test_static_css_missing() -> None:
    """Test that no standalone CSS file is served."""
    client = TestClient(app)
    response = client.get("/dash/styles.css")
    assert response.status_code == 404


def test_static_js_served() -> None:
    """Test that JavaScript file is served correctly."""
    client = TestClient(app)
    response = client.get("/dash/app.js")
    assert response.status_code == 200
    assert "fetchJSON" in response.text
    assert "/v1/ui/cards/top-sectors" in response.text
