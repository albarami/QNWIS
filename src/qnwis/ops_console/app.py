"""
FastAPI application factory for ops console.

Creates server-rendered web UI with Jinja2 templates, HTMX, and SSE.
Mounts at /ops with RBAC, CSRF protection, and audit trail integration.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from pathlib import Path

from fastapi import APIRouter, FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from jinja2 import Environment, FileSystemLoader, TemplateNotFound

from ..utils.clock import Clock
from .csrf import CSRFProtection
from .sse import SSEStream
from .views import (
    alerts_list,
    incident_ack,
    incident_detail,
    incident_resolve,
    incident_silence,
    incidents_list,
    incidents_stream,
    ops_index,
)

logger = logging.getLogger(__name__)

# Template directory relative to this file
TEMPLATES_DIR = Path(__file__).parent / "templates"
ASSETS_DIR = Path(__file__).parent / "assets"


class SafeTemplateLoader(FileSystemLoader):
    """Prevent remote or absolute template includes."""

    def _validate_template_name(self, template: str) -> None:
        candidate = template.replace("\\", "/").strip()
        if "://" in candidate or candidate.startswith("file:"):
            raise TemplateNotFound(f"Remote includes blocked: {template}")
        if candidate.startswith("../") or "/../" in candidate or candidate.startswith("..\\"):
            raise TemplateNotFound(f"Path traversal blocked: {template}")
        if Path(candidate).is_absolute():
            raise TemplateNotFound(f"Absolute paths blocked: {template}")

    def get_source(
        self,
        environment: Environment,
        template: str,
    ) -> tuple[str, str, Callable[[], bool]]:
        self._validate_template_name(template)
        return super().get_source(environment, template)


def create_ops_app(
    clock: Clock | None = None,
    secret_key: str | None = None,
) -> FastAPI:
    """
    Create ops console FastAPI application.

    Args:
        clock: Optional clock for deterministic timestamps
        secret_key: Optional secret key for CSRF tokens

    Returns:
        FastAPI application configured with ops console routes
    """
    app = FastAPI(
        title="QNWIS Ops Console",
        description="Operations console for incident and alert management",
        version="1.0.0",
        docs_url=None,  # Disable Swagger UI for ops console
        redoc_url=None,
    )

    # Initialize app state
    app.state.clock = clock or Clock()
    app.state.csrf_protection = CSRFProtection(secret_key=secret_key)
    app.state.sse_stream = SSEStream()

    # Initialize Jinja2 templates
    if not TEMPLATES_DIR.exists():
        logger.warning("Templates directory not found: %s", TEMPLATES_DIR)
        TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)

    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
    templates.env.loader = SafeTemplateLoader(searchpath=[str(TEMPLATES_DIR)])

    # Add custom filters and globals
    templates.env.globals["csrf_field"] = lambda token: f'<input type="hidden" name="csrf_token" value="{token.token}">'

    app.state.ops_templates = templates

    # Mount static assets if directory exists
    if ASSETS_DIR.exists():
        app.mount("/assets", StaticFiles(directory=str(ASSETS_DIR)), name="assets")

    # Create router with routes
    router = APIRouter()

    # Index
    router.add_api_route(
        "/",
        ops_index,
        methods=["GET"],
        response_class=None,
        name="ops_index",
    )

    # Incidents
    router.add_api_route(
        "/incidents",
        incidents_list,
        methods=["GET"],
        response_class=None,
        name="incidents_list",
    )

    router.add_api_route(
        "/incidents/{incident_id}",
        incident_detail,
        methods=["GET"],
        response_class=None,
        name="incident_detail",
    )

    router.add_api_route(
        "/incidents/{incident_id}/ack",
        incident_ack,
        methods=["POST"],
        name="incident_ack",
    )

    router.add_api_route(
        "/incidents/{incident_id}/resolve",
        incident_resolve,
        methods=["POST"],
        name="incident_resolve",
    )

    router.add_api_route(
        "/incidents/{incident_id}/silence",
        incident_silence,
        methods=["POST"],
        name="incident_silence",
    )

    # Alerts
    router.add_api_route(
        "/alerts",
        alerts_list,
        methods=["GET"],
        response_class=None,
        name="alerts_list",
    )

    # SSE stream
    router.add_api_route(
        "/stream/incidents",
        incidents_stream,
        methods=["GET"],
        name="incidents_stream",
    )

    app.include_router(router)

    # Middleware for request ID and audit footer
    async def add_request_metadata(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Add request ID and timing metadata."""
        import hashlib

        # Generate request ID deterministically from timestamp and path
        timestamp = app.state.clock.now()
        seed = f"{timestamp}:{request.url.path}:{id(request)}"
        request_id = hashlib.sha256(seed.encode()).hexdigest()[:16]
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    app.middleware("http")(add_request_metadata)

    logger.info("Ops console app created with %d routes", len(router.routes))

    return app


def mount_ops_console(
    parent_app: FastAPI,
    mount_path: str = "/ops",
    clock: Clock | None = None,
    secret_key: str | None = None,
) -> None:
    """
    Mount ops console as sub-application on parent FastAPI app.

    Args:
        parent_app: Parent FastAPI application
        mount_path: Path to mount ops console (default /ops)
        clock: Optional clock for deterministic timestamps
        secret_key: Optional secret key for CSRF tokens
    """
    ops_app = create_ops_app(clock=clock, secret_key=secret_key)
    parent_app.mount(mount_path, ops_app)
    logger.info("Ops console mounted at %s", mount_path)


__all__ = ["create_ops_app", "mount_ops_console", "SafeTemplateLoader"]
