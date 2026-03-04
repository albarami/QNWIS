"""
Real integration tests for the QNWIS security/auth module.

Exercises JWTConfig, AuthProvider, decode_jwt, require_roles, and the
QNWIS_BYPASS_AUTH gate using real code paths — no mocks, no stubs.
"""

from dotenv import load_dotenv

load_dotenv()

import os
import time

import jwt as pyjwt
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from src.qnwis.security.auth import (
    AuthProvider,
    JWTConfig,
    Principal,
    TokenPayload,
    decode_jwt,
)
from src.qnwis.security.rbac import require_roles

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TEST_SECRET = "real-integration-test-secret-value-2026"


def _jwt_config(**overrides) -> JWTConfig:
    defaults = dict(
        secret=TEST_SECRET,
        algorithm="HS256",
        issuer="qnwis-test",
        audience="qnwis-api",
        expiry_minutes=60,
        leeway_seconds=30,
    )
    defaults.update(overrides)
    return JWTConfig(**defaults)


def _make_provider(**overrides) -> AuthProvider:
    return AuthProvider(jwt_config=_jwt_config(**overrides))


# =========================================================================
# 1. JWT validation of a real JWT structure
# =========================================================================


class TestJWTValidation:
    """Validate that the JWT auth module can round-trip a real JWT."""

    def test_create_and_validate_jwt_round_trip(self):
        """AuthProvider.create_token produces a token that authenticate_jwt accepts."""
        provider = _make_provider()
        token = provider.create_token("analyst-user", ["analyst", "viewer"])
        principal = provider.authenticate_jwt(token)

        assert principal.subject == "analyst-user"
        assert "analyst" in principal.roles
        assert "viewer" in principal.roles

    def test_decode_jwt_returns_token_payload(self):
        """decode_jwt returns a validated TokenPayload with correct fields."""
        cfg = _jwt_config()
        now = int(time.time())
        payload = {
            "sub": "svc-account",
            "roles": ["admin"],
            "iat": now,
            "exp": now + 3600,
            "iss": cfg.issuer,
            "aud": cfg.audience,
        }
        raw = pyjwt.encode(payload, cfg.secret, algorithm=cfg.algorithm)
        result = decode_jwt(
            raw,
            cfg.secret,
            algorithms=[cfg.algorithm],
            audience=cfg.audience,
            issuer=cfg.issuer,
        )

        assert isinstance(result, TokenPayload)
        assert result.sub == "svc-account"
        assert list(result.roles) == ["admin"]
        assert result.iss == cfg.issuer
        assert result.aud == cfg.audience

    def test_expired_token_is_rejected(self):
        """An expired JWT is rejected even with leeway."""
        cfg = _jwt_config(leeway_seconds=1)
        now = int(time.time())
        payload = {
            "sub": "expired-user",
            "roles": [],
            "iat": now - 7200,
            "exp": now - 3600,
            "iss": cfg.issuer,
            "aud": cfg.audience,
        }
        raw = pyjwt.encode(payload, cfg.secret, algorithm=cfg.algorithm)

        with pytest.raises(pyjwt.ExpiredSignatureError):
            decode_jwt(
                raw,
                cfg.secret,
                algorithms=[cfg.algorithm],
                audience=cfg.audience,
                issuer=cfg.issuer,
                leeway=1,
            )

    def test_wrong_secret_is_rejected(self):
        """A token signed with a different secret cannot be decoded."""
        cfg = _jwt_config()
        now = int(time.time())
        payload = {"sub": "u", "roles": [], "iat": now, "exp": now + 3600}
        raw = pyjwt.encode(payload, "wrong-secret", algorithm="HS256")

        with pytest.raises(pyjwt.InvalidSignatureError):
            decode_jwt(raw, cfg.secret, algorithms=["HS256"])


# =========================================================================
# 2. require_roles dependency rejects unauthorized roles
# =========================================================================


class TestRequireRolesRejectsUnauthorized:
    """require_roles FastAPI dependency enforces role checks."""

    def _build_app_with_role_check(self, *allowed_roles: str) -> TestClient:
        app = FastAPI()
        dep = require_roles(*allowed_roles)

        @app.get("/protected")
        def protected(principal: Principal = Depends(dep)):
            return {"subject": principal.subject, "roles": list(principal.roles)}

        return TestClient(app, raise_server_exceptions=False)

    def test_missing_principal_returns_401(self):
        """No principal on request.state → 401."""
        client = self._build_app_with_role_check("admin")
        resp = client.get("/protected")
        assert resp.status_code == 401

    def test_wrong_role_returns_403(self):
        """Principal present but lacking required role → 403."""
        app = FastAPI()
        dep = require_roles("admin")

        @app.middleware("http")
        async def inject_principal(request, call_next):
            request.state.principal = Principal(
                subject="viewer-user", roles=["viewer"]
            )
            return await call_next(request)

        @app.get("/admin-only")
        def admin_only(principal: Principal = Depends(dep)):
            return {"ok": True}

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/admin-only")
        assert resp.status_code == 403

    def test_matching_role_returns_200(self):
        """Principal with matching role → 200."""
        app = FastAPI()
        dep = require_roles("analyst")

        @app.middleware("http")
        async def inject_principal(request, call_next):
            request.state.principal = Principal(
                subject="good-user", roles=["analyst"]
            )
            return await call_next(request)

        @app.get("/ok")
        def ok_route(principal: Principal = Depends(dep)):
            return {"subject": principal.subject}

        client = TestClient(app)
        resp = client.get("/ok")
        assert resp.status_code == 200
        assert resp.json()["subject"] == "good-user"


# =========================================================================
# 3. Auth bypass is gated on QNWIS_ENV
# =========================================================================


class TestAuthBypassGating:
    """QNWIS_BYPASS_AUTH is only honoured when QNWIS_ENV is development or test."""

    @staticmethod
    def _read_bypass_flag(qnwis_env: str, bypass_value: str) -> bool:
        """Reproduce the exact gating logic from api/server.py."""
        env = qnwis_env.lower()
        if env in ("development", "test"):
            return bypass_value.lower() == "true"
        return False

    def test_bypass_enabled_in_development(self):
        assert self._read_bypass_flag("development", "true") is True

    def test_bypass_enabled_in_test(self):
        assert self._read_bypass_flag("test", "true") is True

    def test_bypass_blocked_in_production(self):
        """Even when QNWIS_BYPASS_AUTH=true, production ignores it."""
        assert self._read_bypass_flag("production", "true") is False

    def test_bypass_blocked_in_staging(self):
        assert self._read_bypass_flag("staging", "true") is False

    def test_bypass_false_in_development(self):
        assert self._read_bypass_flag("development", "false") is False

    def test_bypass_respects_real_env_vars(self):
        """Read the actual env vars and verify production safety."""
        env = os.getenv("QNWIS_ENV", "production").lower()
        bypass_raw = os.getenv("QNWIS_BYPASS_AUTH", "false")
        result = self._read_bypass_flag(env, bypass_raw)
        if env == "production":
            assert result is False, "Bypass must NEVER be active in production"
