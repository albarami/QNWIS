"""
FastAPI router for deterministic query endpoints.

Provides HTTP API access to the deterministic data layer with safe
parameter overrides and cache management.
"""

from __future__ import annotations

import logging
import os
from contextlib import suppress
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request, Response

from ...data.deterministic.cache_access import execute_cached, invalidate_query
from ...data.deterministic.normalize import normalize_params, normalize_rows
from ...data.deterministic.registry import QueryRegistry

router = APIRouter(tags=["queries"])
log = logging.getLogger(__name__)

MIN_TTL_S = 60
MAX_TTL_S = 86400
DEFAULT_TTL_S = 300


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


@router.post("/v1/queries/{query_id}/run", response_model=dict)
def run_query(
    query_id: str,
    req: Request,
    response: Response,
    ttl_s: int | None = Query(default=None),
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
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
    try:
        base_spec = reg.get(query_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Unknown query_id") from None
    # Apply whitelist overrides if provided
    allowed = {"year", "timeout_s", "max_rows", "to_percent"}
    payload: dict[str, Any] = body or {}
    overrides_raw = payload.get("override_params", {})
    if overrides_raw and not isinstance(overrides_raw, dict):
        raise HTTPException(
            status_code=400, detail="'override_params' must be an object mapping."
        )

    overrides = normalize_params({k: v for k, v in overrides_raw.items() if k in allowed})

    use_ttl_input = ttl_s if ttl_s is not None else payload.get("ttl_s")
    coerced_ttl = _coerce_ttl(use_ttl_input)
    ttl_for_execution = coerced_ttl if coerced_ttl is not None else DEFAULT_TTL_S

    # Merge params deterministically
    merged_params = dict(base_spec.params or {})
    merged_params.update(overrides)
    spec_for_execution = base_spec.model_copy(deep=True)
    spec_for_execution.params = merged_params

    try:
        res = execute_cached(
            query_id,
            reg,
            ttl_s=ttl_for_execution,
            spec_override=spec_for_execution,
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
    request_id = _request_id_from_request(req)
    if request_id:
        response.headers["X-Request-ID"] = request_id

    output = {
        "query_id": res.query_id,
        "unit": res.unit,
        "rows": [entry["data"] for entry in normalized_rows],
        "provenance": res.provenance.model_dump(),
        "freshness": res.freshness.model_dump(),
        "warnings": res.warnings,
        "request_id": request_id,
    }
    return output


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
