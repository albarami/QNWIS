"""
Role-based access controls backed by ``config/rbac.yml``.

Routes request the allowed role set from configuration and plug the resulting
list into the ``require_roles`` FastAPI dependency. This keeps policy changes
data-driven while keeping handler code simple.
"""

from __future__ import annotations

import functools
import logging
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from fastapi import Depends, HTTPException, Request, status

import yaml

from .auth import Principal

logger = logging.getLogger(__name__)
CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "rbac.yml"


@functools.lru_cache(maxsize=1)
def _load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():  # pragma: no cover - misconfiguration
        raise FileNotFoundError(f"RBAC configuration missing: {CONFIG_PATH}")
    data = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}
    return data


@functools.lru_cache(maxsize=32)
def allowed_roles(route_key: str) -> tuple[str, ...]:
    """Resolve allowed roles for a logical route."""
    config = _load_config()
    route_data = (config.get("routes") or {}).get(route_key, {})
    roles = tuple(role.lower() for role in route_data.get("allow", []))
    if not roles:  # fallback to analyst if unspecified
        roles = ("analyst",)
    return roles


def _principal_from_request(request: Request) -> Principal:
    principal = getattr(request.state, "principal", None)
    if principal is None or not isinstance(principal, Principal):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return principal


def require_roles(*roles: str | Iterable[str]):
    """
    FastAPI dependency enforcing that caller holds any of the provided roles.
    """

    normalized: set[str] = set()
    for role in roles:
        if not role:
            continue
        if isinstance(role, str):
            normalized.add(role.lower())
            continue
        if isinstance(role, Iterable):
            normalized.update(
                nested.lower() for nested in role if isinstance(nested, str)
            )

    def dependency(principal: Principal = Depends(_principal_from_request)) -> Principal:
        if not normalized:
            return principal
        if not any(role.lower() in normalized for role in principal.roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required roles: {', '.join(sorted(normalized))}",
            )
        return principal

    return dependency


__all__ = ["allowed_roles", "require_roles"]
