"""
Main FastAPI application for QNWIS.

Provides HTTP API for accessing deterministic queries with caching,
provenance tracking, and freshness validation.
"""

from __future__ import annotations

import os

from fastapi import FastAPI
from starlette.staticfiles import StaticFiles

from .api.routers import briefing as briefing_router
from .api.routers import council as council_router
from .api.routers import export as export_router
from .api.routers import queries as queries_router
from .api.routers import ui as ui_router
from .api.routers import ui_dashboard as ui_dash_router
from .utils.health import healthcheck, readiness
from .utils.logger import get_logger
from .utils.rate_limit import RateLimitMiddleware
from .utils.request_id import RequestIDMiddleware

app = FastAPI(title="QNWIS", description="Qatar National Workforce Intelligence System")
log = get_logger("qnwis")

rate_limit_env: str | None = os.getenv("QNWIS_RATE_LIMIT_RPS")
if rate_limit_env:
    try:
        rate_limit_value = float(rate_limit_env)
    except ValueError:
        log.warning("Invalid QNWIS_RATE_LIMIT_RPS value '%s'; rate limiting disabled.", rate_limit_env)
    else:
        if rate_limit_value > 0:
            app.add_middleware(RateLimitMiddleware, rate=rate_limit_value)
        else:
            log.warning(
                "Non-positive QNWIS_RATE_LIMIT_RPS value '%s'; rate limiting disabled.",
                rate_limit_env,
            )

app.add_middleware(RequestIDMiddleware)
app.include_router(queries_router.router)
app.include_router(council_router.router)
app.include_router(briefing_router.router)
app.include_router(ui_router.router)
app.include_router(export_router.router)
app.include_router(ui_dash_router.router)


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return await healthcheck()


@app.get("/ready")
async def ready() -> dict[str, str]:
    """Readiness check endpoint."""
    return await readiness()


# Mount static dashboard (serves index.html at /dash)
app.mount(
    "/dash",
    StaticFiles(directory="apps/dashboard/static", html=True),
    name="dashboard",
)
