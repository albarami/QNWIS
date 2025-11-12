"""Pen-test harness sending common XSS payloads to /form endpoint."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.qnwis.api.deps import attach_security
from src.qnwis.api.endpoints_security_demo import router
from src.qnwis.security.security_settings import get_security_settings


@pytest.mark.parametrize(
    "payload",
    [
        '<img src="x" onerror="alert(1)">',
        '"><svg onload=alert(1)>',
        '<a href="javascript:alert(1)">boom</a>',
        '<div style="background:url(data:text/html;base64,PHNjcmlwdA==)">boom</div>',
    ],
)
def test_pen_test_payloads_are_neutralized(payload: str):
    """Ensure common XSS payloads are sanitized on /form echo endpoint."""
    app = FastAPI()
    app = attach_security(app)
    app.include_router(router)
    cfg = get_security_settings()
    with TestClient(app, base_url="https://testserver") as client:
        token = client.get("/form").cookies.get(cfg.csrf_cookie_name)
        assert token
        headers = {cfg.csrf_header_name: token}
        rsp = client.post("/form", headers=headers, json={"message": payload})
        assert rsp.status_code == 200
        body = rsp.json()["message"]
        assert "<" not in body
        assert "javascript:" not in body
        assert "data:text" not in body
