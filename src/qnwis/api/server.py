"""FastAPI application factory for the public API."""

from __future__ import annotations

import asyncio
import logging
import os
import uuid
from collections.abc import Callable
from contextlib import asynccontextmanager
from typing import Any

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

import jwt
from brotli_asgi import BrotliMiddleware
from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.exception_handlers import http_exception_handler
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from slowapi.errors import RateLimitExceeded

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
from .deps import attach_security
from ..perf.cache_warming import warm_queries
from .middleware.rate_limit import limiter, rate_limit_exceeded_handler

PUBLIC_EXACT = {"/", "/health", "/health/live", "/health/ready", "/metrics", "/openapi.json"}
PUBLIC_PREFIXES = ("/docs", "/redoc", "/api/v1/council/stream")
DEFAULT_WARM_QUERIES = tuple(
    qid.strip()
    for qid in os.getenv(
        "QNWIS_DEFAULT_WARM_QUERIES",
        "syn_employment_latest_total,syn_attrition_hotspots_latest,syn_qatarization_gap_latest",
    ).split(",")
    if qid.strip()
)
GZIP_MIN_BYTES = int(os.getenv("QNWIS_GZIP_MIN_BYTES", "1024"))
BROTLI_QUALITY = int(os.getenv("QNWIS_BROTLI_QUALITY", "5"))
BROTLI_MIN_BYTES = int(os.getenv("QNWIS_BROTLI_MIN_BYTES", "512"))
API_PREFIX = os.getenv("QNWIS_API_PREFIX", "/api/v1")
logger = logging.getLogger(__name__)


def _is_public(path: str) -> bool:
    if path in PUBLIC_EXACT:
        return True
    return any(path.startswith(prefix) for prefix in PUBLIC_PREFIXES)


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def _warm_targets() -> tuple[str, ...]:
    raw = os.getenv("QNWIS_WARM_QUERIES")
    if raw:
        return tuple(qid.strip() for qid in raw.split(",") if qid.strip())
    return DEFAULT_WARM_QUERIES


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

    # Pre-warm embedder model to avoid first-request delay
    if _env_flag("QNWIS_WARM_EMBEDDER", True):  # Default to True
        # TEMPORARILY DISABLED - Embedding warm-up causing meta tensor errors
        # Will load on-demand when first request arrives
        logger.info("RAG warm-up disabled (on-demand loading enabled)")
    
    # Pre-index documents for fact verification (Bug #3 FIX - CRITICAL)
    # This prevents 30-60 second delay on first query
    if _env_flag("QNWIS_ENABLE_FACT_VERIFICATION", True):
        try:
            logger.info("="*60)
            logger.info("Initializing GPU-accelerated fact verification system...")
            logger.info("="*60)
            
            from ..rag.gpu_verifier import GPUFactVerifier
            from ..rag.document_loader import load_source_documents
            from ..rag import initialize_fact_verifier
            
            # Initialize verifier on GPU 6 (shared with embeddings)
            verifier = GPUFactVerifier(gpu_id=6)
            
            # Load documents from configured sources
            logger.info("Loading documents for fact verification...")
            documents = load_source_documents()
            logger.info(f"Loaded {len(documents):,} documents")
            
            # Index documents (this is expensive, ~30-60s for 70K docs)
            logger.info(f"Indexing {len(documents):,} documents on GPU 6 (this may take 30-60s)...")
            verifier.index_documents(documents)
            
            # Store globally for access during queries
            initialize_fact_verifier(verifier)
            
            # Also store in app state for backward compatibility
            app.state.fact_verifier = verifier
            
            logger.info("="*60)
            logger.info("✅ Fact verification system ready - documents pre-indexed")
            logger.info("="*60)
            
        except Exception as e:
            logger.error("="*60)
            logger.error(f"⚠️ Fact verification initialization failed: {e}", exc_info=True)
            logger.error("="*60)
            logger.warning("Continuing without fact verification - queries will work but won't have verification")
            app.state.fact_verifier = None
            
            from ..rag import initialize_fact_verifier
            initialize_fact_verifier(None)
    else:
        logger.info("Fact verification disabled (set QNWIS_ENABLE_FACT_VERIFICATION=true to enable)")
        app.state.fact_verifier = None
    
    if _env_flag("QNWIS_WARM_CACHE", False):
        warm_ids = _warm_targets()
        if warm_ids:
            max_workers = int(os.getenv("QNWIS_WARM_MAX_WORKERS", "4"))
            loop = asyncio.get_running_loop()
            logger.info("Scheduling cache warming for %s", ", ".join(warm_ids))
            loop.run_in_executor(
                None,
                lambda: warm_queries(
                    factory=factory,
                    query_ids=warm_ids,
                    max_workers=max_workers,
                ),
            )

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
    
    # Add slowapi rate limiter
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
    logger.info("Rate limiter initialized (100/hour default)")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allow all origins for development
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=False,  # Must be False when allow_origins=["*"]
    )
    attach_security(app)
    app.add_middleware(GZipMiddleware, minimum_size=GZIP_MIN_BYTES)
    if _env_flag("QNWIS_ENABLE_BROTLI", True):
        app.add_middleware(
            BrotliMiddleware,
            quality=BROTLI_QUALITY,
            minimum_size=BROTLI_MIN_BYTES,
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
        """
        Enhanced health check with GPU and system status.
        
        Returns comprehensive system health including:
        - GPU count and status
        - Agent count
        - Fact verification status
        - Parallel scenarios status
        - Document indexing status
        """
        import torch
        from ..rag import get_fact_verifier
        
        # Get basic health
        health = check_health(readiness=True)
        health_dict = health.to_dict()
        
        # Add GPU information
        gpu_info = {
            "available": torch.cuda.is_available(),
            "count": torch.cuda.device_count() if torch.cuda.is_available() else 0
        }
        
        if torch.cuda.is_available():
            try:
                gpu_info["devices"] = [
                    {
                        "id": i,
                        "name": torch.cuda.get_device_name(i),
                        "memory_allocated_gb": round(torch.cuda.memory_allocated(i) / 1e9, 2),
                        "memory_total_gb": round(torch.cuda.get_device_properties(i).total_memory / 1e9, 1)
                    }
                    for i in range(min(8, torch.cuda.device_count()))
                ]
            except Exception as e:
                logger.warning(f"Could not get GPU details: {e}")
        
        # Add fact verification status
        verifier = get_fact_verifier()
        if verifier:
            fact_verification_status = {
                "ready": verifier.is_indexed,
                "documents_indexed": len(verifier.doc_texts) if verifier.is_indexed else 0,
                "gpu_id": verifier.gpu_id,
                "model": "all-mpnet-base-v2"
            }
        else:
            fact_verification_status = {
                "ready": False,
                "documents_indexed": 0
            }
        
        # Add parallel scenarios status
        parallel_scenarios_status = {
            "enabled": os.getenv("QNWIS_ENABLE_PARALLEL_SCENARIOS", "false").lower() == "true",
            "num_scenarios": 6,
            "gpus_allocated": [0, 1, 2, 3, 4, 5]
        }
        
        # Enhanced response
        enhanced_response = {
            **health_dict,
            "gpus": gpu_info["count"],
            "gpu_details": gpu_info,
            "agents": 12,  # 5 LLM + 7 deterministic
            "fact_verification": "ready" if fact_verification_status["ready"] else "not_ready",
            "fact_verification_details": fact_verification_status,
            "parallel_scenarios": "enabled" if parallel_scenarios_status["enabled"] else "disabled",
            "parallel_scenarios_details": parallel_scenarios_status,
            "documents_indexed": fact_verification_status["documents_indexed"],
            "workflow": os.getenv("QNWIS_WORKFLOW_IMPL", "langgraph")
        }
        
        status_code = status.HTTP_200_OK if health.status.value == "healthy" else status.HTTP_503_SERVICE_UNAVAILABLE
        return JSONResponse(content=enhanced_response, status_code=status_code)

    @app.get("/metrics", response_class=PlainTextResponse, tags=["observability"])
    async def metrics():
        """
        Prometheus metrics endpoint.
        
        Exposes application metrics in Prometheus text format including:
        - HTTP request/response metrics (qnwis_requests_total, qnwis_latency_seconds)
        - Database operation metrics (qnwis_db_latency_seconds)
        - Cache metrics (qnwis_cache_hits_total, qnwis_cache_misses_total)
        - Agent execution metrics (qnwis_agent_latency_seconds)
        
        Additional Prometheus metrics from perf module can be scraped here.
        """
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
        app.include_router(router, prefix=API_PREFIX)

    return app


app = create_app()
logger = logging.getLogger(__name__)
