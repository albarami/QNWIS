"""Demo endpoints for security testing."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from src.qnwis.security.rbac_helpers import require_roles
from src.qnwis.security.sanitizer import sanitize_text

router = APIRouter()


@router.get("/ping")
async def ping():
    """
    Simple health check endpoint.

    Returns:
        JSON response with ok status
    """
    return {"ok": True}


@router.get("/form")
async def get_form():
    """
    GET endpoint that sets CSRF cookie.

    Returns:
        JSON response indicating CSRF cookie is set
    """
    # CSRF token is handled via middleware cookie
    return {"csrf": "cookie_set"}


@router.post("/form")
async def post_form(payload: dict):
    """
    POST endpoint that requires CSRF token.

    Args:
        payload: Request payload

    Returns:
        JSON response with sanitized message
    """
    # CSRF enforced by middleware; sanitize any echoed fields
    msg = sanitize_text(str(payload.get("message", "")))
    return JSONResponse({"message": msg})


@router.get("/secure/admin")
async def admin_only(_=Depends(require_roles({"admin"}))):
    """
    Admin-only endpoint requiring admin role.

    Args:
        _: RBAC dependency (auto-injected)

    Returns:
        JSON response with secret data
    """
    return {"secret": "admin-zone"}
