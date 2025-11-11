"""Unit tests for RBAC helpers."""

from __future__ import annotations

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from src.qnwis.security.rbac_helpers import require_roles


def test_rbac_denies_without_role():
    """Test that RBAC denies access without required role."""
    app = FastAPI()

    @app.get("/adm", dependencies=[Depends(require_roles({"admin"}))])
    def _adm():
        return {"ok": True}

    client = TestClient(app)
    r = client.get("/adm")
    assert r.status_code == 403


def test_rbac_allows_with_role_header():
    """Test that RBAC allows access with role in header."""
    app = FastAPI()

    @app.get("/adm", dependencies=[Depends(require_roles({"admin"}))])
    def _adm():
        return {"ok": True}

    client = TestClient(app)
    r = client.get("/adm", headers={"X-User-Roles": "Admin"})
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_rbac_case_insensitive():
    """Test that RBAC role matching is case-insensitive."""
    app = FastAPI()

    @app.get("/adm", dependencies=[Depends(require_roles({"admin"}))])
    def _adm():
        return {"ok": True}

    client = TestClient(app)
    # Test various case combinations
    assert client.get("/adm", headers={"X-User-Roles": "ADMIN"}).status_code == 200
    assert client.get("/adm", headers={"X-User-Roles": "admin"}).status_code == 200
    assert client.get("/adm", headers={"X-User-Roles": "Admin"}).status_code == 200


def test_rbac_multiple_roles():
    """Test that RBAC works with multiple roles."""
    app = FastAPI()

    @app.get("/adm", dependencies=[Depends(require_roles({"admin", "superuser"}))])
    def _adm():
        return {"ok": True}

    client = TestClient(app)
    # Should allow with admin role
    assert (
        client.get("/adm", headers={"X-User-Roles": "admin"}).status_code == 200
    )
    # Should allow with superuser role
    assert (
        client.get("/adm", headers={"X-User-Roles": "superuser"}).status_code == 200
    )
    # Should deny with other role
    assert client.get("/adm", headers={"X-User-Roles": "user"}).status_code == 403


def test_rbac_comma_separated_roles():
    """Test that RBAC handles comma-separated roles in header."""
    app = FastAPI()

    @app.get("/adm", dependencies=[Depends(require_roles({"admin"}))])
    def _adm():
        return {"ok": True}

    client = TestClient(app)
    r = client.get("/adm", headers={"X-User-Roles": "user,admin,editor"})
    assert r.status_code == 200


def test_rbac_empty_roles():
    """Test that RBAC denies access with empty roles."""
    app = FastAPI()

    @app.get("/adm", dependencies=[Depends(require_roles({"admin"}))])
    def _adm():
        return {"ok": True}

    client = TestClient(app)
    assert client.get("/adm", headers={"X-User-Roles": ""}).status_code == 403
    assert client.get("/adm").status_code == 403


def test_rbac_whitespace_handling():
    """Test that RBAC handles whitespace in roles correctly."""
    app = FastAPI()

    @app.get("/adm", dependencies=[Depends(require_roles({"admin"}))])
    def _adm():
        return {"ok": True}

    client = TestClient(app)
    # Should handle whitespace around commas
    r = client.get("/adm", headers={"X-User-Roles": " admin , user "})
    assert r.status_code == 200


def test_rbac_different_endpoints_different_roles():
    """Test that different endpoints can require different roles."""
    app = FastAPI()

    @app.get("/admin", dependencies=[Depends(require_roles({"admin"}))])
    def _admin():
        return {"area": "admin"}

    @app.get("/editor", dependencies=[Depends(require_roles({"editor"}))])
    def _editor():
        return {"area": "editor"}

    client = TestClient(app)
    # Admin role should access admin endpoint but not editor
    assert (
        client.get("/admin", headers={"X-User-Roles": "admin"}).status_code == 200
    )
    assert (
        client.get("/editor", headers={"X-User-Roles": "admin"}).status_code == 403
    )
    # Editor role should access editor endpoint but not admin
    assert (
        client.get("/admin", headers={"X-User-Roles": "editor"}).status_code == 403
    )
    assert (
        client.get("/editor", headers={"X-User-Roles": "editor"}).status_code == 200
    )


def test_rbac_all_of_mode_requires_every_role():
    """Test that all_of mode enforces every listed role."""
    app = FastAPI()

    @app.get("/combo", dependencies=[Depends(require_roles({"admin", "auditor"}, mode="all_of"))])
    def _combo():
        return {"ok": True}

    client = TestClient(app)
    assert client.get("/combo", headers={"X-User-Roles": "admin"}).status_code == 403
    assert client.get("/combo", headers={"X-User-Roles": "auditor"}).status_code == 403
    assert client.get("/combo", headers={"X-User-Roles": "admin,auditor"}).status_code == 200


def test_rbac_multi_role_header_case_insensitive_any_mode():
    """Test that multiple roles in a header are matched case-insensitively."""
    app = FastAPI()

    @app.get("/combo", dependencies=[Depends(require_roles({"admin", "auditor"}, mode="all_of"))])
    def _combo():
        return {"ok": True}

    client = TestClient(app)
    assert (
        client.get("/combo", headers={"X-User-Roles": "ADMIN,Auditor"}).status_code == 200
    )
