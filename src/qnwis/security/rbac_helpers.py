"""RBAC helpers for role-based access control."""

from __future__ import annotations

from typing import Iterable, Literal, Set

from fastapi import HTTPException, Request

from .security_settings import get_security_settings


def _extract_roles(request: Request) -> Set[str]:
    """
    Extract user roles from request.

    Args:
        request: Incoming request

    Returns:
        Set of role names (lowercase)
    """
    # Prefer roles set upstream (e.g., auth middleware)
    if getattr(request.state, "user", None) and getattr(
        request.state.user, "roles", None
    ):
        return set(map(str.lower, request.state.user.roles))
    # Fallback: header (useful in tests)
    roles_header = get_security_settings().roles_header
    hdr = request.headers.get(roles_header, "")
    return set(map(str.lower, [r.strip() for r in hdr.split(",") if r.strip()]))


def require_roles(
    allowed: Iterable[str], *, mode: Literal["any_of", "all_of"] = "any_of"
):
    """
    Create FastAPI dependency that requires specific roles.

    Args:
        allowed: Iterable of allowed role names
        mode: Matching mode. ``any_of`` requires at least one role,
            ``all_of`` requires every role to be present.

    Returns:
        FastAPI dependency function

    Raises:
        HTTPException: 403 if user lacks required role
    """
    allowed_lc = set(map(str.lower, allowed))
    if mode not in {"any_of", "all_of"}:
        raise ValueError("mode must be 'any_of' or 'all_of'")

    async def _dep(request: Request):
        roles = _extract_roles(request)
        if not allowed_lc:
            return
        if mode == "any_of":
            if roles & allowed_lc:
                return
        else:
            if allowed_lc.issubset(roles):
                return
        raise HTTPException(
            status_code=403, detail="Forbidden: missing required role"
        )

    return _dep
