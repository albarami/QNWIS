"""
FastAPI router for deterministic query endpoints.

Provides HTTP API access to the deterministic data layer with safe
parameter overrides and cache management.
"""

from __future__ import annotations

import json
import logging
import os
import time
from contextlib import suppress
from pathlib import Path
from typing import Any, AsyncGenerator

from fastapi import APIRouter, HTTPException, Query, Request, Response, status
from fastapi.responses import StreamingResponse

from ...data.deterministic.cache_access import execute_cached, invalidate_query
from ...data.deterministic.normalize import normalize_params, normalize_rows
from ...data.deterministic.registry import QueryRegistry
from ...ui.pagination import paginate
from ..models import (
    BatchQueryRequest,
    BatchQueryResponse,
    BatchQueryResult,
    PaginationMeta,
    QueryRunRequest,
    QueryRunResponse,
)
from ..streaming import add_timing_header, stream_json_array

router = APIRouter(tags=["queries"])
log = logging.getLogger(__name__)

MIN_TTL_S = 60
MAX_TTL_S = 86400
DEFAULT_TTL_S = 300
AUTO_PAGINATE_THRESHOLD = int(os.getenv("QNWIS_AUTO_PAGINATE_THRESHOLD", "2000"))
DEFAULT_PAGE_SIZE = int(os.getenv("QNWIS_DEFAULT_PAGE_SIZE", "500"))
MAX_PAGE_SIZE = int(os.getenv("QNWIS_MAX_PAGE_SIZE", "5000"))
STREAM_CHUNK_SIZE = int(os.getenv("QNWIS_STREAM_CHUNK_SIZE", "256"))


def _registry_from_env() -> QueryRegistry:
    """
    Load query registry from environment-configured directory.

    Attempts to locate the queries directory in the following order:
    1. QNWIS_QUERIES_DIR environment variable
    2. src/qnwis/data/queries
    3. data/queries

    Returns:
        QueryRegistry instance loaded with query definitions
    """
    # Support both src/qnwis/data/queries and data/queries
    roots: list[Path] = []
    env_root = os.getenv("QNWIS_QUERIES_DIR")
    if env_root:
        roots.append(Path(env_root))
    roots.extend(
        [
            Path("src") / "qnwis" / "data" / "queries",
            Path("data") / "queries",
        ]
    )
    for root in roots:
        if root.is_dir():
            reg = QueryRegistry(str(root))
            reg.load_all()
            return reg
    # Last resort: empty registry (handled in handlers)
    default_root = Path("src") / "qnwis" / "data" / "queries"
    reg = QueryRegistry(str(default_root))
    with suppress(Exception):
        reg.load_all()
    return reg


def _extract_overrides(payload: dict[str, Any]) -> dict[str, Any]:
    """Normalize and validate override params."""
    allowed_keys = {"year", "timeout_s", "max_rows", "to_percent"}
    overrides_raw = payload.get("override_params", {})
    if overrides_raw and not isinstance(overrides_raw, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="'override_params' must be an object mapping.",
        )
    if not overrides_raw:
        return {}
    filtered = {k: v for k, v in overrides_raw.items() if k in allowed_keys}
    return normalize_params(filtered)


def _resolve_spec_and_ttl(
    registry: QueryRegistry,
    query_id: str,
    payload: dict[str, Any],
    ttl_param: int | None,
) -> tuple[QuerySpec, int | None, bool]:
    """Resolve the QuerySpec to execute along with TTL policy."""
    try:
        base_spec = registry.get(query_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Unknown query_id") from None

    overrides = _extract_overrides(payload)
    merged_params = dict(base_spec.params or {})
    merged_params.update(overrides)
    spec_for_execution = base_spec.model_copy(deep=True)
    spec_for_execution.params = merged_params

    provided_ttl = ttl_param if ttl_param is not None else payload.get("ttl_s")
    coerced_ttl = _coerce_ttl(provided_ttl)
    ttl_for_execution = coerced_ttl if coerced_ttl is not None else DEFAULT_TTL_S
    adaptive = provided_ttl is None

    return spec_for_execution, ttl_for_execution, adaptive


def _paginate_rows(
    rows: list[dict[str, Any]],
    *,
    page: int,
    page_size: int | None,
) -> tuple[list[dict[str, Any]], PaginationMeta | None, bool]:
    """Return rows for the requested page along with metadata."""
    effective_page_size = page_size
    auto_paginated = False
    if effective_page_size is None and len(rows) > AUTO_PAGINATE_THRESHOLD:
        effective_page_size = DEFAULT_PAGE_SIZE
        auto_paginated = True

    if effective_page_size is None:
        return rows, None, auto_paginated

    clamped_size = max(1, min(effective_page_size, MAX_PAGE_SIZE))
    page_info = paginate(rows, page=page, page_size=clamped_size)
    items = page_info.pop("items")
    return items, PaginationMeta(**page_info), auto_paginated


async def _stream_rows_envelope(
    metadata: dict[str, Any],
    rows: list[dict[str, Any]],
) -> AsyncGenerator[str, None]:
    """Yield JSON fragments for streaming query results."""
    prefix = metadata.copy()
    prefix_json = json.dumps(prefix, separators=(",", ":"))
    # Drop the trailing '}' so we can append rows key.
    opening = prefix_json[:-1] + ',"rows":'
    yield opening
    async for chunk in stream_json_array(rows, chunk_size=STREAM_CHUNK_SIZE):
        yield chunk
    yield "}"


def _coerce_ttl(value: Any) -> int | None:
    """
    Coerce a user-provided TTL value into API bounds.

    Args:
        value: Raw TTL input (query param or JSON payload)

    Returns:
        Integer TTL within [MIN_TTL_S, MAX_TTL_S], or None if invalid/absent.
    """
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    try:
        ttl = int(float(str(value).strip()))
    except Exception:
        return None
    ttl = max(MIN_TTL_S, ttl)
    ttl = min(MAX_TTL_S, ttl)
    return ttl


def _request_id_from_request(req: Request) -> str | None:
    """Fetch request ID from headers or middleware-injected state."""
    header_val = req.headers.get("x-request-id")
    if header_val:
        return header_val
    return getattr(req.state, "request_id", None)


@router.get("/v1/queries")
def list_queries() -> dict[str, Any]:
    """
    List all available deterministic query identifiers.

    Returns:
        Dictionary with 'ids' key containing list of query IDs
    """
    reg = _registry_from_env()
    return {"ids": reg.all_ids()}


@router.get("/v1/queries/{query_id}")
def get_query(query_id: str) -> dict[str, Any]:
    """
    Retrieve the registered QuerySpec for a given identifier.

    Args:
        query_id: Query identifier from registry

    Returns:
        Dictionary containing the serialized QuerySpec

    Raises:
        HTTPException: 404 if the query is not registered
    """
    reg = _registry_from_env()
    try:
        spec = reg.get(query_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Unknown query_id") from None

    return {"query": spec.model_dump(exclude_none=True)}


@router.post("/v1/queries/{query_id}/run", response_model=QueryRunResponse)
def run_query(
    query_id: str,
    req: Request,
    response: Response,
    ttl_s: int | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int | None = Query(default=None, ge=1, le=MAX_PAGE_SIZE),
    body: QueryRunRequest | None = None,
) -> QueryRunResponse:
    """
    Execute a deterministic query through cached access.

    Allows safe parameter overrides from a whitelist:
    - year: int
    - timeout_s: int
    - max_rows: int
    - to_percent: list[str]

    Args:
        query_id: Query identifier from registry
        req: FastAPI request object
        ttl_s: Cache TTL override (seconds, bounded to 60-86400)
        body: Request body with override_params and ttl_s

    Returns:
        Query result with rows, provenance, freshness, and warnings

    Raises:
        HTTPException: 404 if query_id not found
    """
    reg = _registry_from_env()
    payload = body.model_dump(exclude_none=True) if body else {}
    spec_for_execution, ttl_for_execution, adaptive = _resolve_spec_and_ttl(
        reg, query_id, payload, ttl_s
    )

    try:
        res = execute_cached(
            query_id,
            reg,
            ttl_s=ttl_for_execution,
            spec_override=spec_for_execution,
            adaptive_ttl=adaptive,
        )
    except TimeoutError as exc:
        log.warning("Query %s timed out: %s", query_id, exc)
        raise HTTPException(status_code=504, detail="Query execution timed out.") from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Query source data not found.") from None
    except Exception:
        log.exception("Unexpected failure executing query %s", query_id)
        raise HTTPException(status_code=500, detail="Query execution failed.") from None

    normalized_rows = normalize_rows(res.rows)
    structured_rows = [entry["data"] for entry in normalized_rows]
    rows_out, pagination_meta, auto_paginated = _paginate_rows(
        structured_rows, page=page, page_size=page_size
    )
    request_id = _request_id_from_request(req)
    if request_id:
        response.headers["X-Request-ID"] = request_id
    response.headers["X-Total-Rows"] = str(len(structured_rows))

    output = QueryRunResponse(
        query_id=res.query_id,
        unit=res.unit,
        rows=rows_out,
        row_count=len(structured_rows),
        provenance=res.provenance.model_dump(),
        freshness=res.freshness.model_dump(),
        warnings=res.warnings,
        pagination=pagination_meta,
        auto_paginated=auto_paginated,
        request_id=request_id,
    )
    return output


@router.post(
    "/v1/queries/{query_id}/stream",
    response_class=StreamingResponse,
    summary="Stream deterministic query rows as JSON.",
)
async def stream_query(
    query_id: str,
    req: Request,
    ttl_s: int | None = Query(default=None),
    body: QueryRunRequest | None = None,
) -> StreamingResponse:
    """Stream deterministic query results as a JSON object with chunked rows."""
    reg = _registry_from_env()
    payload = body.model_dump(exclude_none=True) if body else {}
    spec_for_execution, ttl_for_execution, adaptive = _resolve_spec_and_ttl(
        reg, query_id, payload, ttl_s
    )

    started = time.perf_counter()
    try:
        res = execute_cached(
            query_id,
            reg,
            ttl_s=ttl_for_execution,
            spec_override=spec_for_execution,
            adaptive_ttl=adaptive,
        )
    except TimeoutError as exc:
        log.warning("Query %s timed out: %s", query_id, exc)
        raise HTTPException(status_code=504, detail="Query execution timed out.") from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Query source data not found.") from None
    except Exception:
        log.exception("Unexpected failure executing query %s", query_id)
        raise HTTPException(status_code=500, detail="Query execution failed.") from None

    duration_ms = (time.perf_counter() - started) * 1000
    normalized_rows = normalize_rows(res.rows)
    structured_rows = [entry["data"] for entry in normalized_rows]

    metadata = {
        "query_id": res.query_id,
        "unit": res.unit,
        "provenance": res.provenance.model_dump(),
        "freshness": res.freshness.model_dump(),
        "warnings": res.warnings,
        "row_count": len(structured_rows),
    }
    stream = _stream_rows_envelope(metadata, structured_rows)
    streaming_response = StreamingResponse(stream, media_type="application/json")
    streaming_response.headers["X-Query-ID"] = res.query_id
    request_id = _request_id_from_request(req)
    if request_id:
        streaming_response.headers["X-Request-ID"] = request_id
    add_timing_header(streaming_response, duration_ms)
    return streaming_response


@router.post("/v1/queries:batch", response_model=BatchQueryResponse)
def run_query_batch(
    req: Request,
    response: Response,
    batch: BatchQueryRequest,
) -> BatchQueryResponse:
    """Execute multiple deterministic queries in a single request."""
    reg = _registry_from_env()
    request_id = _request_id_from_request(req)
    if request_id:
        response.headers["X-Request-ID"] = request_id

    results: list[BatchQueryResult] = []
    for item in batch.queries:
        payload = (
            item.payload.model_dump(exclude_none=True) if item.payload else {}
        )
        try:
            spec_for_execution, ttl_for_execution, adaptive = _resolve_spec_and_ttl(
                reg, item.query_id, payload, ttl_param=None
            )
            res = execute_cached(
                item.query_id,
                reg,
                ttl_s=ttl_for_execution,
                spec_override=spec_for_execution,
                adaptive_ttl=adaptive,
            )
            normalized_rows = normalize_rows(res.rows)
            structured_rows = [entry["data"] for entry in normalized_rows]
            result_response = QueryRunResponse(
                query_id=res.query_id,
                unit=res.unit,
                rows=structured_rows,
                row_count=len(structured_rows),
                provenance=res.provenance.model_dump(),
                freshness=res.freshness.model_dump(),
                warnings=res.warnings,
                pagination=None,
                auto_paginated=False,
                request_id=request_id,
            )
            results.append(BatchQueryResult(query_id=item.query_id, ok=True, response=result_response))
        except HTTPException as exc:
            results.append(
                BatchQueryResult(
                    query_id=item.query_id,
                    ok=False,
                    error=exc.detail if isinstance(exc.detail, str) else str(exc.detail),
                )
            )
        except Exception as exc:
            log.exception("Batch query failed for %s", item.query_id)
            results.append(
                BatchQueryResult(
                    query_id=item.query_id,
                    ok=False,
                    error=str(exc),
                )
            )

    return BatchQueryResponse(results=results)


@router.post("/v1/queries/{query_id}/cache/invalidate")
def invalidate(query_id: str) -> dict[str, Any]:
    """
    Invalidate cached results for a specific query.

    Args:
        query_id: Query identifier to invalidate

    Returns:
        Status confirmation with invalidated query_id
    """
    reg = _registry_from_env()
    with suppress(Exception):
        invalidate_query(query_id, reg)
    return {"status": "ok", "invalidated": query_id}
