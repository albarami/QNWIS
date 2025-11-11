"""Integration tests for security headers."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from src.qnwis.api.deps import attach_security
from src.qnwis.api.endpoints_security_demo import router
from src.qnwis.security.csp import get_csp_nonce


def test_security_headers_present():
    """Test that all required security headers are present in responses."""
    app = FastAPI()
    app = attach_security(app)
    app.include_router(router)
    client = TestClient(app)
    r = client.get("/ping")
    assert r.status_code == 200
    h = r.headers
    assert "Strict-Transport-Security" in h
    assert "Content-Security-Policy" in h
    assert h["X-Content-Type-Options"] == "nosniff"
    assert h["X-Frame-Options"] == "DENY"
    assert h["Referrer-Policy"] == "no-referrer"


def test_hsts_header_format():
    """Test HSTS header has correct format."""
    app = FastAPI()
    app = attach_security(app)
    app.include_router(router)
    client = TestClient(app)
    r = client.get("/ping")
    hsts = r.headers.get("Strict-Transport-Security", "")
    assert "max-age=" in hsts
    assert "includeSubDomains" in hsts
    assert "preload" in hsts


def test_csp_header_format():
    """Test CSP header has correct directives."""
    app = FastAPI()
    app = attach_security(app)
    app.include_router(router)
    client = TestClient(app)
    r = client.get("/ping")
    csp = r.headers.get("Content-Security-Policy", "")
    assert "default-src" in csp
    assert "script-src" in csp
    assert "style-src" in csp
    assert "frame-ancestors" in csp
    assert "nonce-" in csp


def test_additional_security_headers():
    """Test additional security headers are present."""
    app = FastAPI()
    app = attach_security(app)
    app.include_router(router)
    client = TestClient(app)
    r = client.get("/ping")
    h = r.headers
    assert "Permissions-Policy" in h
    assert "Cross-Origin-Opener-Policy" in h
    assert "Cross-Origin-Resource-Policy" in h


def test_https_enforcement_blocks_plain_http_remote_host():
    """Ensure StrictTransportMiddleware rejects http requests for non-local hosts."""
    app = FastAPI()
    app = attach_security(app)
    app.include_router(router)
    client = TestClient(app, base_url="http://evil.example.com")
    r = client.get("/ping")
    assert r.status_code == 400


def test_https_enforcement_allows_https_requests():
    """Ensure HTTPS requests succeed when strict transport is enabled."""
    app = FastAPI()
    app = attach_security(app)
    app.include_router(router)
    client = TestClient(app, base_url="https://secure.example.com")
    r = client.get("/ping")
    assert r.status_code == 200


def test_csp_nonce_helper_matches_header_value():
    """Ensure helper exposes the same nonce that is added to CSP header."""
    app = FastAPI()
    app = attach_security(app)

    @app.get("/nonce")
    async def nonce_endpoint(request: Request):
        return {"nonce": get_csp_nonce(request)}

    client = TestClient(app)
    rsp = client.get("/nonce")
    assert rsp.status_code == 200
    nonce = rsp.json()["nonce"]
    assert nonce
    assert f"nonce-{nonce}" in rsp.headers["Content-Security-Policy"]


def test_range_guard_rejects_excessive_ranges():
    """Ensure multiple comma-separated ranges are clamped."""
    app = FastAPI()
    app = attach_security(app)
    app.include_router(router)
    client = TestClient(app)
    header = "bytes=" + ",".join(["0-1"] * 10)
    r = client.get("/ping", headers={"Range": header})
    assert r.status_code == 416


def test_range_guard_allows_small_header():
    """Ensure valid Range headers continue to work."""
    app = FastAPI()
    app = attach_security(app)
    app.include_router(router)
    client = TestClient(app)
    r = client.get("/ping", headers={"Range": "bytes=0-100"})
    assert r.status_code == 200
