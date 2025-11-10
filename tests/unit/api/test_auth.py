import time
from datetime import UTC, datetime, timedelta

import jwt
import pytest

from qnwis.security.auth import (
    ApiKeyStore,
    AuthProvider,
    JWTConfig,
    Principal,
    TokenPayload,
    decode_jwt,
)
from qnwis.utils.clock import Clock


class FixedClock(Clock):
    def __init__(self):
        self.now_value = datetime(2024, 1, 1, tzinfo=UTC)
        self.perf_value = 0.0
        super().__init__(now=lambda: self.now_value, perf_counter=lambda: self.perf_value)


def test_decode_jwt_valid():
    config = JWTConfig(secret="secret")
    token = jwt.encode(
        {"sub": "user", "roles": ["analyst"], "iat": int(time.time()), "exp": int(time.time()) + 60},
        config.secret,
        algorithm=config.algorithm,
    )
    payload = decode_jwt(token, config.secret, algorithms=[config.algorithm])
    assert isinstance(payload, TokenPayload)
    assert payload.sub == "user"
    assert payload.roles == ["analyst"]


def test_decode_jwt_expired():
    config = JWTConfig(secret="secret")
    token = jwt.encode(
        {"sub": "user", "roles": [], "iat": 0, "exp": 1},
        config.secret,
        algorithm=config.algorithm,
    )
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_jwt(token, config.secret, algorithms=[config.algorithm])


def test_api_key_store_resolves_and_expires():
    clock = FixedClock()
    store = ApiKeyStore(salt="salt", clock=clock)
    principal = Principal(subject="svc", roles=("analyst",), ratelimit_id="svc")
    store.add_key(plaintext="plain", principal=principal, ttl_seconds=10)
    resolved = store.resolve("plain")
    assert resolved == principal
    clock.perf_value += 15
    clock.now_value += timedelta(seconds=15)
    with pytest.raises(ValueError):
        store.resolve("plain")


def test_auth_provider_issues_and_lists_keys(monkeypatch):
    monkeypatch.setenv("QNWIS_JWT_SECRET", "secret")
    provider = AuthProvider()
    key, record = provider.issue_api_key(subject="svc", roles=["analyst"])
    assert record.principal.subject == "svc"
    assert len(provider.list_api_keys()) >= 1
    principal = provider.authenticate_api_key(key)
    assert principal.subject == "svc"
    provider.revoke_api_key(record.key_id)
    with pytest.raises(ValueError):
        provider.authenticate_api_key(key)


def test_auth_provider_jwt(monkeypatch):
    monkeypatch.setenv("QNWIS_JWT_SECRET", "secret")
    provider = AuthProvider()
    token = provider.create_token("user-1", ["analyst"])
    principal = provider.authenticate_jwt(token)
    assert principal.subject == "user-1"
    assert "analyst" in principal.roles
