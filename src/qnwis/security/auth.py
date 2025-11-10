"""
Authentication primitives for the QNWIS API.

Supports JWT bearer tokens and salted API keys that can be stored in Redis or an
in-memory fallback. All helpers avoid embedding secrets in logs and expose a
`Principal` dataclass for downstream RBAC/rate limiting layers.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import secrets
import time
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from pydantic import BaseModel, Field

from ..utils.clock import Clock

try:  # pragma: no cover - optional dependency
    import redis  # type: ignore
except Exception:  # pragma: no cover
    redis = None

logger = logging.getLogger(__name__)


class TokenPayload(BaseModel):
    """Validated JWT payload."""

    sub: str = Field(..., description="Subject / principal identifier")
    roles: Sequence[str] = Field(default_factory=list, description="Granted roles")
    exp: int = Field(..., description="Expiry timestamp (seconds since epoch)")
    iat: int = Field(..., description="Issued-at timestamp (seconds since epoch)")
    iss: str | None = Field(None, description="Issuer")
    aud: str | None = Field(None, description="Audience")
    ratelimit_id: str | None = Field(None, description="Rate-limit partition")
    jti: str | None = Field(None, description="Token identifier")


@dataclass(frozen=True)
class Principal:
    """Authenticated principal enriched with RBAC metadata."""

    subject: str
    roles: tuple[str, ...]
    ratelimit_id: str


@dataclass
class JWTConfig:
    """Runtime JWT configuration derived from environment variables."""

    secret: str
    algorithm: str = "HS256"
    issuer: str | None = None
    audience: str | None = None
    expiry_minutes: int = 60
    leeway_seconds: int = 30

    @classmethod
    def from_env(cls) -> JWTConfig:
        """Load configuration from environment variables."""
        secret = os.getenv("QNWIS_JWT_SECRET")
        if not secret:
            raise ValueError("QNWIS_JWT_SECRET must be configured for JWT authentication.")

        algorithm = os.getenv("QNWIS_JWT_ALGORITHM", "HS256").upper()
        if algorithm not in {"HS256", "RS256"}:
            raise ValueError(f"Unsupported JWT algorithm: {algorithm}")

        issuer = os.getenv("QNWIS_JWT_ISSUER")
        audience = os.getenv("QNWIS_JWT_AUDIENCE")
        expiry_minutes = int(os.getenv("QNWIS_JWT_EXPIRY_MINUTES", "60"))
        leeway_seconds = int(os.getenv("QNWIS_JWT_LEEWAY_SECONDS", "30"))
        return cls(
            secret=secret,
            algorithm=algorithm,
            issuer=issuer,
            audience=audience,
            expiry_minutes=expiry_minutes,
            leeway_seconds=leeway_seconds,
        )


def _load_redis_client(redis_url: str | None) -> Any | None:
    """Create Redis client if dependency/URL available."""
    if not redis_url or redis is None:  # type: ignore[truthy-function]
        return None
    try:  # pragma: no cover - network handshake
        client = redis.from_url(redis_url, decode_responses=True, socket_connect_timeout=1)
        client.ping()
        return client
    except Exception as exc:  # pragma: no cover - fallback path
        logger.warning("Redis unavailable for ApiKeyStore: %s", exc)
        return None


def decode_jwt(
    token: str,
    jwk_or_secret: str | dict[str, Any],
    *,
    algorithms: Iterable[str] | None = None,
    audience: str | None = None,
    issuer: str | None = None,
    leeway: int = 30,
) -> TokenPayload:
    """
    Decode and validate JWT tokens with configurable leeway.
    """
    payload = jwt.decode(
        token,
        jwk_or_secret,
        algorithms=list(algorithms) if algorithms else None,
        audience=audience,
        issuer=issuer,
        leeway=leeway,
    )
    return TokenPayload(**payload)


def generate_api_key(length_bytes: int = 32) -> str:
    """Generate a new hex-encoded API key."""
    return secrets.token_hex(length_bytes)


def _hash_key(key: str, salt: str) -> str:
    digest = hashlib.sha256()
    digest.update(salt.encode("utf-8"))
    digest.update(key.encode("utf-8"))
    return digest.hexdigest()


@dataclass
class ApiKeyRecord:
    """Persisted metadata for hashed API keys."""

    key_hash: str
    principal: Principal
    expires_at: float | None
    created_at: float = field(default_factory=lambda: time.time())

    @property
    def key_id(self) -> str:
        """Short identifier safe to expose in logs/CLI."""
        return self.key_hash[:12]


class ApiKeyStore:
    """
    API key registry backed by Redis when available, or in-memory dict fallback.
    """

    def __init__(
        self,
        *,
        salt: str,
        redis_url: str | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._salt = salt
        self._clock = clock or Clock()
        self._redis = _load_redis_client(redis_url)
        self._records: dict[str, ApiKeyRecord] = {}

    def _serialize(self, record: ApiKeyRecord) -> str:
        data = {
            "hash": record.key_hash,
            "subject": record.principal.subject,
            "roles": list(record.principal.roles),
            "ratelimit_id": record.principal.ratelimit_id,
            "expires_at": record.expires_at,
            "created_at": record.created_at,
        }
        return json.dumps(data)

    @staticmethod
    def _deserialize(blob: str) -> ApiKeyRecord:
        data = json.loads(blob)
        principal = Principal(
            subject=data["subject"],
            roles=tuple(data["roles"]),
            ratelimit_id=data["ratelimit_id"],
        )
        return ApiKeyRecord(
            key_hash=data["hash"],
            principal=principal,
            expires_at=data["expires_at"],
            created_at=data["created_at"],
        )

    def _now(self) -> float:
        return self._clock.time()

    def _expiry_ts(self, ttl_seconds: int | None) -> float | None:
        if ttl_seconds is None:
            return None
        return self._now() + ttl_seconds

    def _store(self, record: ApiKeyRecord, ttl_seconds: int | None) -> None:
        if self._redis:
            key = f"qnwis:api_keys:{record.key_hash}"
            self._redis.set(key, self._serialize(record))
            if ttl_seconds:
                self._redis.expire(key, int(ttl_seconds))
        self._records[record.key_hash] = record

    def add_key(
        self,
        *,
        plaintext: str,
        principal: Principal,
        ttl_seconds: int | None = None,
    ) -> ApiKeyRecord:
        """Store a new API key (hashed)."""
        key_hash = _hash_key(plaintext, self._salt)
        record = ApiKeyRecord(
            key_hash=key_hash,
            principal=principal,
            expires_at=self._expiry_ts(ttl_seconds),
        )
        self._store(record, ttl_seconds)
        return record

    def resolve(self, candidate: str) -> Principal:
        """Validate plaintext key and return associated principal."""
        key_hash = _hash_key(candidate, self._salt)
        record = self._records.get(key_hash)

        if not record and self._redis:
            blob = self._redis.get(f"qnwis:api_keys:{key_hash}")
            if blob:
                record = self._deserialize(blob)
                self._records[key_hash] = record

        if not record or not hmac.compare_digest(record.key_hash, key_hash):
            raise ValueError("Invalid API key")

        if record.expires_at and self._now() > record.expires_at:
            self._records.pop(key_hash, None)
            if self._redis:
                self._redis.delete(f"qnwis:api_keys:{key_hash}")
            raise ValueError("API key expired")

        return record.principal

    def list_records(self) -> list[ApiKeyRecord]:
        """Return cached records (without exposing plaintext)."""
        if self._redis:
            for raw_key in self._redis.scan_iter(match="qnwis:api_keys:*"):  # pragma: no cover - redis path
                blob = self._redis.get(raw_key)
                if blob:
                    record = self._deserialize(blob)
                    self._records[record.key_hash] = record
        return sorted(self._records.values(), key=lambda r: r.created_at)

    def revoke(self, key_id: str) -> bool:
        """Remove key matching short identifier or full hash."""
        target = None
        if key_id in self._records:
            target = key_id
        else:
            for key_hash in list(self._records.keys()):
                if self._records[key_hash].key_id == key_id:
                    target = key_hash
                    break
        if not target:
            return False

        self._records.pop(target, None)
        if self._redis:
            self._redis.delete(f"qnwis:api_keys:{target}")
        return True


class AuthProvider:
    """High-level façade for JWT and API key authentication."""

    def __init__(
        self,
        jwt_config: JWTConfig | None = None,
        *,
        salt: str | None = None,
        redis_url: str | None = None,
        clock: Clock | None = None,
        env: Mapping[str, str] | None = None,
    ) -> None:
        self.jwt_config = jwt_config or JWTConfig.from_env()
        salt_value = salt or os.getenv("QNWIS_API_KEY_SALT") or self.jwt_config.secret
        self._clock = clock or Clock()
        self._key_store = ApiKeyStore(salt=salt_value, redis_url=redis_url or os.getenv("QNWIS_REDIS_URL"), clock=self._clock)
        self._load_env_keys(env or os.environ)

    def _load_env_keys(self, env: Mapping[str, str]) -> None:
        for key, value in env.items():
            if not key.startswith("QNWIS_API_KEY_"):
                continue
            label = key.replace("QNWIS_API_KEY_", "").lower()
            try:
                parts = value.split(":")
                if len(parts) < 2:
                    raise ValueError("Expected <key>:<roles>[:ratelimit]")
                plaintext = parts[0]
                roles = tuple(r.strip() for r in parts[1].split(",") if r.strip())
                ratelimit_id = parts[2] if len(parts) >= 3 and parts[2] else label
                if not roles:
                    roles = ("analyst",)
                principal = Principal(subject=label, roles=roles, ratelimit_id=ratelimit_id)
                self._key_store.add_key(plaintext=plaintext, principal=principal)
            except Exception as exc:
                logger.warning("Failed to load API key '%s': %s", label, exc)

    def create_token(self, subject: str, roles: Sequence[str], *, ratelimit_id: str | None = None, ttl_minutes: int | None = None) -> str:
        """Create signed JWT for service accounts and tests."""
        now = datetime.now(UTC)
        expiry_minutes = ttl_minutes or self.jwt_config.expiry_minutes
        payload = {
            "sub": subject,
            "roles": list(roles),
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=expiry_minutes)).timestamp()),
        }
        if self.jwt_config.issuer:
            payload["iss"] = self.jwt_config.issuer
        if self.jwt_config.audience:
            payload["aud"] = self.jwt_config.audience
        if ratelimit_id:
            payload["ratelimit_id"] = ratelimit_id
        return jwt.encode(payload, self.jwt_config.secret, algorithm=self.jwt_config.algorithm)

    def authenticate_jwt(self, token: str) -> Principal:
        """Validate JWT and return principal."""
        payload = decode_jwt(
            token,
            self.jwt_config.secret,
            algorithms=[self.jwt_config.algorithm],
            audience=self.jwt_config.audience,
            issuer=self.jwt_config.issuer,
            leeway=self.jwt_config.leeway_seconds,
        )
        roles = tuple(payload.roles) if payload.roles else ("analyst",)
        ratelimit_id = payload.ratelimit_id or payload.sub
        return Principal(subject=payload.sub, roles=roles, ratelimit_id=ratelimit_id)

    def authenticate_api_key(self, key: str) -> Principal:
        """Validate API key via store backend."""
        return self._key_store.resolve(key)

    def issue_api_key(
        self,
        *,
        subject: str,
        roles: Sequence[str],
        ttl_seconds: int | None = None,
        ratelimit_id: str | None = None,
    ) -> tuple[str, ApiKeyRecord]:
        """Programmatically mint a new API key."""
        plaintext = generate_api_key()
        principal = Principal(subject=subject, roles=tuple(roles), ratelimit_id=ratelimit_id or subject)
        record = self._key_store.add_key(plaintext=plaintext, principal=principal, ttl_seconds=ttl_seconds)
        return plaintext, record

    def list_api_keys(self) -> list[ApiKeyRecord]:
        """Return stored API key metadata."""
        return self._key_store.list_records()

    def revoke_api_key(self, key_id: str) -> bool:
        """Remove key by ID."""
        return self._key_store.revoke(key_id)


def create_jwt_token(subject: str, role: str, jwt_config: JWTConfig | None = None) -> str:
    """Compatibility helper for legacy tests."""
    provider = AuthProvider(jwt_config=jwt_config)
    return provider.create_token(subject, [role])


def verify_jwt_token(token: str, jwt_config: JWTConfig | None = None) -> TokenPayload:
    """Decode JWT using configured settings."""
    config = jwt_config or JWTConfig.from_env()
    return decode_jwt(
        token,
        config.secret,
        algorithms=[config.algorithm],
        audience=config.audience,
        issuer=config.issuer,
        leeway=config.leeway_seconds,
    )


__all__ = [
    "ApiKeyRecord",
    "ApiKeyStore",
    "AuthProvider",
    "JWTConfig",
    "Principal",
    "TokenPayload",
    "create_jwt_token",
    "decode_jwt",
    "generate_api_key",
    "verify_jwt_token",
]
