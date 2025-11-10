"""FastAPI application factory for the public API."""

from __future__ import annotations

import logging
import os
import uuid
from collections.abc import Callable
from contextlib import asynccontextmanager
from typing import Any

import jwt
from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.exception_handlers import http_exception_handler
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse

from ..agents.base import DataClient
from ..config.settings import Settings
from ..observability import (
    check_health,
    configure_logging,
    get_metrics_collector,
    record_auth_attempt,
    record_rate_limit_event,
    record_request,
)
from ..security import AuthProvider, Principal, RateLimiter
from ..utils.clock import Clock
from .routers import ROUTERS

PUBLIC_EXACT = {"/", "/health", "/health/live", "/health/ready", "/metrics", "/openapi.json"}
PUBLIC_PREFIXES = ("/docs", "/redoc")
logger = logging.getLogger(__name__)


def _is_public(path: str) -> bool:
    if path in PUBLIC_EXACT:
        return True
    return any(path.startswith(prefix) for prefix in PUBLIC_PREFIXES)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings: Settings = app.state.settings
    configure_logging(level=settings.log_level, json_format=True, enable_redaction=True)
    app.state.clock = Clock()
    app.state.auth_provider = AuthProvider(clock=app.state.clock, redis_url=settings.redis_url)
    app.state.rate_limiter = RateLimiter(redis_url=settings.redis_url, clock=app.state.clock)

    def factory() -> DataClient:
        return DataClient(queries_dir=settings.queries_dir, ttl_s=settings.default_cache_ttl_s)

    app.state.data_client_factory = factory
    yield


def _request_id(request: Request) -> str:
    return request.headers.get("x-request-id", str(uuid.uuid4()))


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()

    enable_docs = os.getenv("QNWIS_ENABLE_DOCS", "false").lower() == "true"
    docs_url = "/docs" if enable_docs else None
    redoc_url = "/redoc" if enable_docs else None
    openapi_url = "/openapi.json" if enable_docs else None

    app = FastAPI(
        title="QNWIS Agent API",
        version=os.getenv("QNWIS_VERSION", "dev"),
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_url=openapi_url,
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.auth_bypass = os.getenv("QNWIS_BYPASS_AUTH", "false").lower() == "true"
    logger.info("Auth bypass enabled: %s", app.state.auth_bypass)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.api_cors_origins or ["*"],
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True,
    )

    @app.middleware("http")
    async def context_middleware(request: Request, call_next: Callable[[Request], Any]):
        clock: Clock = getattr(app.state, "clock", Clock())
        metrics = get_metrics_collector()
        request_id = _request_id(request)
        request.state.request_id = request_id
        metrics.increment_gauge("qnwis_active_requests", 1)
        started = clock.time()
        try:
            response = await call_next(request)
        except HTTPException as exc:
            metrics.increment_gauge("qnwis_active_requests", -1)
            record_request(request.method, request.url.path, exc.status_code, clock.time() - started)
            raise
        except Exception:
            metrics.increment_gauge("qnwis_active_requests", -1)
            record_request(request.method, request.url.path, 500, clock.time() - started)
            raise
        duration = clock.time() - started
        metrics.increment_gauge("qnwis_active_requests", -1)
        record_request(request.method, request.url.path, response.status_code, duration)
        response.headers["x-request-id"] = request_id
        response.headers["x-response-time-ms"] = str(int(duration * 1000))
        return response

    @app.middleware("http")
    async def auth_middleware(request: Request, call_next: Callable[[Request], Any]):
        if _is_public(request.url.path):
            return await call_next(request)

        if getattr(request.app.state, "auth_bypass", False):
            request.state.principal = Principal(subject="test-bypass", roles=("admin",), ratelimit_id="test-bypass")
            return await call_next(request)

        auth_provider: AuthProvider | None = getattr(request.app.state, "auth_provider", None)
        rate_limiter: RateLimiter | None = getattr(request.app.state, "rate_limiter", None)
        if auth_provider is None:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Authentication provider unavailable"},
            )

        header = request.headers.get("authorization")
        api_key = request.headers.get("x-api-key")
        principal: Principal | None = None
        auth_method = "unknown"

        if header and header.lower().startswith("bearer "):
            token = header.split(" ", 1)[1].strip()
            auth_method = "jwt"
        elif api_key:
            auth_method = "api_key"
        else:
            record_auth_attempt("none", "failure")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Authentication required"},
                headers={"WWW-Authenticate": "Bearer"},
            )

        try:
            if auth_method == "jwt" and header:
                token = header.split(" ", 1)[1].strip()
                principal = auth_provider.authenticate_jwt(token)
            elif auth_method == "api_key" and api_key:
                principal = auth_provider.authenticate_api_key(api_key)
            else:  # pragma: no cover - defensive
                raise ValueError("Unsupported authentication method")
            record_auth_attempt(auth_method, "success")
        except (jwt.PyJWTError, ValueError):
            record_auth_attempt(auth_method, "failure")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid authentication credentials"},
                headers={"WWW-Authenticate": "Bearer"},
            )

        request.state.principal = principal
        rate_result = None
        if rate_limiter is not None and principal is not None:
            rate_result = rate_limiter.consume(principal)
            if not rate_result.allowed:
                record_rate_limit_event(principal.subject, rate_result.reason or "limit_exceeded")
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={"detail": "Rate limit exceeded", "reason": rate_result.reason},
                )

        response: Response = await call_next(request)
        if principal is not None:
            response.headers["X-Principal-Subject"] = principal.subject
        if rate_result is not None:
            response.headers["X-RateLimit-Remaining"] = str(rate_result.remaining)
            response.headers["X-RateLimit-Reset"] = str(int(rate_result.reset_after))
            if rate_result.daily_remaining is not None:
                response.headers["X-RateLimit-DailyRemaining"] = str(rate_result.daily_remaining)
        return response

    @app.get("/", tags=["info"])
    async def info() -> dict[str, Any]:
        return {
            "name": "QNWIS Agent API",
            "version": app.version,
            "environment": settings.environment,
            "docs_enabled": enable_docs,
        }

    @app.get("/health/live", response_class=JSONResponse, tags=["observability"])
    async def health_live():
        health = check_health(readiness=False)
        return health.to_dict()

    @app.get("/health/ready", response_class=JSONResponse, tags=["observability"])
    async def health_ready():
        health = check_health(readiness=True)
        status_code = status.HTTP_200_OK if health.status.value == "healthy" else status.HTTP_503_SERVICE_UNAVAILABLE
        return JSONResponse(content=health.to_dict(), status_code=status_code)

    @app.get("/health", response_class=JSONResponse, tags=["observability"])
    async def health_alias():
        return await health_ready()

    @app.get("/metrics", response_class=PlainTextResponse, tags=["observability"])
    async def metrics():
        collector = get_metrics_collector()
        return collector.export_prometheus_text()

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        if exc.status_code >= status.HTTP_500_INTERNAL_SERVER_ERROR:
            error_id = str(uuid.uuid4())
            logger.exception(
                "Unhandled HTTPException %s", error_id, extra={"request_id": getattr(request.state, "request_id", None)}
            )
            return JSONResponse(
                status_code=exc.status_code,
                content={"detail": exc.detail, "error_id": error_id},
            )
        return await http_exception_handler(request, exc)

    @app.exception_handler(Exception)
    async def unhandled_error(request: Request, exc: Exception):
        error_id = str(uuid.uuid4())
        logger.exception(
            "Unhandled error %s", error_id, exc_info=exc, extra={"request_id": getattr(request.state, "request_id", None)}
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal Server Error", "error_id": error_id},
        )

    @app.get("/openapi.json", include_in_schema=False)
    async def openapi():
        return app.openapi()

    for router in ROUTERS:
        app.include_router(router, prefix="/api/v1")

    return app


app = create_app()
logger = logging.getLogger(__name__)
