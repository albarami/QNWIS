"""
Legacy application entrypoint for tests and local demos.

Wraps the main create_app factory (which includes auth, observability, and
all routers) but forces authentication bypass so unit/integration tests can
exercise the stack without API keys.
"""

from __future__ import annotations

import os

from fastapi.staticfiles import StaticFiles

# Tests expect to call endpoints without credentials and without /api prefix.
os.environ.setdefault("QNWIS_BYPASS_AUTH", "true")
os.environ.setdefault("QNWIS_API_PREFIX", "")

from .api.server import Settings, create_app

app = create_app(Settings())
app.state.auth_bypass = True

app.mount(
    "/dash",
    StaticFiles(directory="apps/dashboard/static", html=True),
    name="dashboard",
)

__all__ = ["app"]
