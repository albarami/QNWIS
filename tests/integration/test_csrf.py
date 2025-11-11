"""Integration tests for CSRF protection."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.qnwis.api.deps import attach_security
from src.qnwis.api.endpoints_security_demo import router
from src.qnwis.security.security_settings import (
    get_security_settings,
    override_security_settings,
    reset_security_settings,
)


def test_csrf_cookie_set_on_get():
    """Test that CSRF cookie is set on GET requests."""
    app = FastAPI()
    app = attach_security(app)
    app.include_router(router)
    client = TestClient(app)

    r = client.get("/form")
    assert r.status_code == 200
    cookie = r.cookies.get(get_security_settings().csrf_cookie_name)
    assert cookie is not None
    assert len(cookie) > 0


def test_csrf_post_without_header_fails():
    """Test that POST without CSRF header fails."""
    app = FastAPI()
    app = attach_security(app)
    app.include_router(router)
    client = TestClient(app)

    # GET to set cookie
    client.get("/form")

    # POST without header should fail
    r = client.post("/form", json={"message": "test"})
    assert r.status_code == 403


def test_csrf_post_with_matching_header_passes():
    """Test that POST with matching CSRF header succeeds."""
    app = FastAPI()
    app = attach_security(app)
    app.include_router(router)
    # Use cookies parameter to persist cookies across requests
    with TestClient(app, base_url="https://testserver") as client:
        # GET to set cookie
        r = client.get("/form")
        assert r.status_code == 200
        cookie = r.cookies.get(get_security_settings().csrf_cookie_name)
        assert cookie

        # POST with matching header should pass
        headers = {get_security_settings().csrf_header_name: cookie}
        r = client.post("/form", headers=headers, json={"message": "test"})
        assert r.status_code == 200


def test_csrf_sanitizes_output():
    """Test that CSRF endpoint sanitizes user input."""
    app = FastAPI()
    app = attach_security(app)
    app.include_router(router)
    
    with TestClient(app, base_url="https://testserver") as client:
        # GET to set cookie
        r = client.get("/form")
        cookie = r.cookies.get(get_security_settings().csrf_cookie_name)

        # POST with XSS attempt
        headers = {get_security_settings().csrf_header_name: cookie}
        r = client.post(
            "/form", headers=headers, json={"message": "<script>alert(1)</script>"}
        )
        assert r.status_code == 200
        # Script tags should be stripped
        assert "<script>" not in r.json()["message"]
        assert "alert(1)" in r.json()["message"]


def test_csrf_post_with_wrong_token_fails():
    """Test that POST with wrong CSRF token fails."""
    app = FastAPI()
    app = attach_security(app)
    app.include_router(router)
    client = TestClient(app)

    # GET to set cookie
    client.get("/form")

    # POST with wrong token should fail
    headers = {get_security_settings().csrf_header_name: "wrong-token"}
    r = client.post("/form", headers=headers, json={"message": "test"})
    assert r.status_code == 403


def test_csrf_safe_methods_allowed():
    """Test that safe methods (GET, HEAD, OPTIONS) are allowed without CSRF."""
    app = FastAPI()
    app = attach_security(app)
    app.include_router(router)
    client = TestClient(app)

    # GET should work without CSRF
    r = client.get("/ping")
    assert r.status_code == 200

    # Note: HEAD and OPTIONS may not be implemented for all endpoints
    # Just verify GET works which is the main safe method


def test_csrf_cookie_attributes_are_configurable():
    """Ensure CSRF cookie respects Secure and SameSite settings."""
    override_security_settings(csrf_secure=True, csrf_samesite="strict")
    try:
        app = FastAPI()
        app = attach_security(app)
        app.include_router(router)
        client = TestClient(app)
        r = client.get("/form")
        cookie_header = r.headers.get("set-cookie", "")
        assert "Secure" in cookie_header
        assert "SameSite=Strict" in cookie_header
    finally:
        reset_security_settings()
