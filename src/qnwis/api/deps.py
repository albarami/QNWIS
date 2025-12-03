"""FastAPI dependencies and security attachment."""

from __future__ import annotations

from fastapi import FastAPI

from src.qnwis.security.audit import RequestAuditMiddleware
from src.qnwis.security.csrf import CSRFMiddleware
from src.qnwis.security.headers import SecurityHeadersMiddleware
from src.qnwis.security.https import StrictTransportMiddleware
from src.qnwis.security.range_guard import RangeHeaderGuardMiddleware


def attach_security(app: FastAPI) -> FastAPI:
    """
    Attach security middlewares to FastAPI application.

    Middlewares are applied in reverse order (last added = first executed).
    Execution order (outermost -> innermost):
        RequestAudit -> StrictTransport -> RangeGuard -> CSRFMiddleware -> SecurityHeaders

    Args:
        app: FastAPI application instance

    Returns:
        FastAPI application with security middlewares attached
    """
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(CSRFMiddleware)
    app.add_middleware(RangeHeaderGuardMiddleware)
    #app.add_middleware(StrictTransportMiddleware) #REVERT
    app.add_middleware(RequestAuditMiddleware)
    return app
