"""Cached execution layer for deterministic queries with provenance enrichment."""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import time
import zlib
from collections.abc import Mapping, MutableMapping
from pathlib import Path
from typing import Any

from ..cache.backends import CacheBackend, get_cache_backend
from ..catalog.registry import DatasetCatalog
from ..freshness.verifier import verify_freshness
from .access import execute as execute_uncached
from .models import QueryResult, QuerySpec
from .registry import QueryRegistry
from .schema import QueryDefinition
from qnwis.perf.cache_tuning import should_cache, ttl_for

logger = logging.getLogger(__name__)

MAX_CACHE_TTL_S = 24 * 60 * 60  # 24 hours
COMPRESS_THRESHOLD_BYTES = 8 * 1024  # 8KB

COUNTERS: MutableMapping[str, int] = {"hits": 0, "misses": 0, "invalidations": 0}

_ADAPTIVE_CACHE_ENABLED = os.getenv("QNWIS_CACHE_TTL_MODE", "adaptive").lower() not in {
    "off",
    "legacy",
}
_SENSITIVE_HINTS = tuple(
    hint.strip().lower()
    for hint in os.getenv("QNWIS_SENSITIVE_QUERY_HINTS", "live,latest,hotlist,ewi").split(",")
    if hint.strip()
)
_SENSITIVE_MAX_TTL = int(os.getenv("QNWIS_SENSITIVE_MAX_TTL_S", "180"))
_DEFAULT_TTL_BASE = int(os.getenv("QNWIS_DEFAULT_TTL_BASE_S", "600"))


def _is_sensitive_query(query_id: str) -> bool:
    """Return True when query id hints that the data is highly volatile."""
    lowered = query_id.lower()
    return any(hint in lowered for hint in _SENSITIVE_HINTS)


def _compute_adaptive_ttl(
    query_id: str,
    requested_ttl: int | None,
    row_count: int,
    duration_ms: float,
) -> int | None:
    """
    Determine TTL after applying adaptive heuristics.

    Args:
        query_id: Deterministic query identifier
        requested_ttl: Explicit TTL request (seconds) or None
        row_count: Result row count
        duration_ms: Execution time in milliseconds

    Returns:
        TTL (seconds) or None for no expiration
    """
    if requested_ttl == 0:
        return 0

    base_ttl = requested_ttl if requested_ttl and requested_ttl > 0 else _DEFAULT_TTL_BASE
    adaptive_ttl = ttl_for(query_id, row_count, base=base_ttl)
    ttl_candidate = max(base_ttl, adaptive_ttl)

    if _is_sensitive_query(query_id):
        ttl_candidate = min(ttl_candidate, _SENSITIVE_MAX_TTL)

    # Fast queries with tiny payloads are cheap enough to skip caching altogether.
    if not should_cache(query_id, row_count, duration_ms):
        return 0

    return ttl_candidate


class CacheDecodingError(RuntimeError):
    """Raised when a cached payload cannot be decoded into a QueryResult."""


def _canonicalize_params(value: Any) -> Any:
    """Recursively canonicalize parameters for deterministic hashing."""
    if isinstance(value, Mapping):
        return {k: _canonicalize_params(value[k]) for k in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [_canonicalize_params(item) for item in value]
    if isinstance(value, set):
        normalized_items = [_canonicalize_params(item) for item in value]
        return sorted(
            normalized_items, key=lambda item: json.dumps(item, sort_keys=True, default=str)
        )
    return value


def _key_for(spec: QuerySpec | QueryDefinition) -> str:
    """Generate deterministic cache key from query spec or definition."""
    # Handle both QuerySpec and QueryDefinition types
    if isinstance(spec, QueryDefinition):
        # QueryDefinition from YAML
        query_id = spec.query_id
        params_dict = {p.name: p.default for p in spec.parameters} if spec.parameters else {}
        normalized_params = _canonicalize_params(params_dict)
        postprocess_data = []  # QueryDefinition doesn't have postprocess
        source = spec.dataset.lower()
    else:
        # QuerySpec (legacy)
        query_id = spec.id
        normalized_params = _canonicalize_params(spec.params or {})
        postprocess_data = [
            {"name": step.name, "params": _canonicalize_params(step.params)}
            for step in (spec.postprocess or [])
        ]
        source = spec.source

    payload = json.dumps(
        {
            "id": query_id,
            "source": source,
            "params": normalized_params,
            "postprocess": postprocess_data,
        },
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    h = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    return f"qnwis:ddl:v1:{query_id}:{h}"


def _enrich_provenance(res: QueryResult) -> None:
    """Enrich result provenance with license from catalog if available."""
    project_root = Path(__file__).resolve().parents[4]
    cat_path = project_root / "data" / "catalog" / "datasets.yaml"
    if cat_path.exists():
        try:
            cat = DatasetCatalog(cat_path)
            item = cat.match(res.provenance.locator)
            if not item:
                item = cat.match(res.provenance.dataset_id)
            if item:
                license_value = item.get("license")
                if license_value:
                    res.provenance.license = license_value
        except Exception as exc:
            logger.debug(
                "Failed to enrich provenance from catalog for %s: %s",
                res.provenance.locator,
                exc,
            )


def _normalize_ttl(ttl_s: int | None) -> int | None:
    """Validate and normalize TTL ensuring upper bound and explicit uncached behaviour."""
    if ttl_s is None:
        return None
    if ttl_s <= 0:
        return 0
    if ttl_s > MAX_CACHE_TTL_S:
        raise ValueError(f"Cache TTL cannot exceed {MAX_CACHE_TTL_S} seconds (24 hours).")
    return ttl_s


def _encode_for_cache(res: QueryResult) -> str:
    """Serialize QueryResult into a cache envelope with optional compression."""
    payload_dict = res.model_dump(mode="json")
    payload_json = json.dumps(payload_dict, separators=(",", ":"), sort_keys=True)
    payload_bytes = payload_json.encode("utf-8")

    if len(payload_bytes) >= COMPRESS_THRESHOLD_BYTES:
        compressed = zlib.compress(payload_bytes)
        envelope = {
            "_meta": {
                "content_encoding": "zlib",
                "compressed": True,
                "original_bytes": len(payload_bytes),
                "compressed_bytes": len(compressed),
            },
            "payload": base64.b64encode(compressed).decode("ascii"),
        }
    else:
        envelope = {
            "_meta": {
                "content_encoding": "identity",
                "compressed": False,
                "original_bytes": len(payload_bytes),
            },
            "payload": payload_json,
        }
    return json.dumps(envelope, separators=(",", ":"))


def _load_json(raw: str) -> Any:
    """Safely load JSON string, raising CacheDecodingError on failure."""
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise CacheDecodingError("Cached payload is not valid JSON.") from exc


def _extract_envelope(parsed: Any) -> tuple[Mapping[str, Any], Any]:
    """Extract metadata and payload from cache envelope."""
    if not isinstance(parsed, dict) or "_meta" not in parsed or "payload" not in parsed:
        raise CacheDecodingError("Cached payload missing metadata envelope.")
    meta = parsed["_meta"]
    if not isinstance(meta, Mapping):
        raise CacheDecodingError("Cache metadata is malformed.")
    return meta, parsed["payload"]


def _decode_envelope(meta: Mapping[str, Any], payload: Any) -> str:
    """Decode envelope payload according to encoding."""
    encoding = meta.get("content_encoding", "identity")
    if encoding == "zlib":
        if not isinstance(payload, str):
            raise CacheDecodingError("Compressed payload must be a base64 string.")
        try:
            compressed_bytes = base64.b64decode(payload)
            return zlib.decompress(compressed_bytes).decode("utf-8")
        except (ValueError, zlib.error) as exc:
            raise CacheDecodingError("Failed to decode cached payload.") from exc
    if encoding == "identity":
        return payload if isinstance(payload, str) else json.dumps(payload)
    raise CacheDecodingError(f"Unsupported cache encoding: {encoding}")


def _decode_cached_result(raw: str) -> QueryResult:
    """Decode cached payload back into a QueryResult."""
    parsed = _load_json(raw)

    if isinstance(parsed, dict) and "query_id" in parsed:
        return QueryResult.model_validate(parsed)

    meta, payload = _extract_envelope(parsed)
    decoded_json = _decode_envelope(meta, payload)
    payload_dict = _load_json(decoded_json)
    return QueryResult.model_validate(payload_dict)


def execute_cached(
    query_id: str,
    registry: QueryRegistry,
    ttl_s: int | None = 300,
    invalidate: bool = False,
    spec_override: QuerySpec | None = None,
    adaptive_ttl: bool = True,
) -> QueryResult:
    """
    Execute a deterministic query with caching and freshness verification.

    Args:
        query_id: Query identifier from registry
        registry: Query registry instance
        ttl_s: Cache TTL in seconds (default 300). Values <= 0 disable caching.
            Maximum supported TTL is 24 hours. None stores without expiration.
        invalidate: Force cache invalidation before execution
        spec_override: Optional QuerySpec to use for execution and cache key
            generation. Allows per-request parameter overrides without
            mutating the global registry state.
        adaptive_ttl: Enable adaptive TTL heuristics (default: True). Set to
            False to respect the requested TTL exactly.

    Returns:
        QueryResult with enriched provenance and freshness warnings
    """
    start_time = time.perf_counter()
    
    source_spec = spec_override or registry.get(query_id)
    spec = source_spec.model_copy(deep=True)
    # Handle both QuerySpec (id) and QueryDefinition (query_id)
    spec_id = spec.query_id if isinstance(spec, QueryDefinition) else spec.id
    if spec_id != query_id:
        raise ValueError(f"Spec ID mismatch: expected {query_id}, got {spec_id}")

    key = _key_for(spec)
    cache: CacheBackend = get_cache_backend()
    normalized_ttl = _normalize_ttl(ttl_s)

    if invalidate:
        cache.delete(key)
        COUNTERS["invalidations"] = COUNTERS.get("invalidations", 0) + 1

    cached = cache.get(key)
    if cached is not None:
        try:
            res = _decode_cached_result(cached)
        except CacheDecodingError:
            cache.delete(key)
        else:
            COUNTERS["hits"] = COUNTERS.get("hits", 0) + 1
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.debug(f"Cache HIT for {query_id} in {duration_ms:.2f}ms")
            _enrich_provenance(res)
            # Verify freshness only for QuerySpec (has constraints)
            if not isinstance(spec, QueryDefinition):
                res.warnings.extend(verify_freshness(spec, res))
            return res

    COUNTERS["misses"] = COUNTERS.get("misses", 0) + 1
    logger.debug(f"Cache MISS for {query_id}, executing query")

    exec_start = time.perf_counter()
    res = execute_uncached(query_id, registry, spec_override=spec)
    exec_duration_ms = (time.perf_counter() - exec_start) * 1000

    _enrich_provenance(res)
    # Verify freshness only for QuerySpec (has constraints)
    if not isinstance(spec, QueryDefinition):
        res.warnings.extend(verify_freshness(spec, res))

    cache_value = _encode_for_cache(res)
    ttl_for_storage = normalized_ttl

    if adaptive_ttl and _ADAPTIVE_CACHE_ENABLED and normalized_ttl is not None:
        spec_id = spec.query_id if isinstance(spec, QueryDefinition) else spec.id
        ttl_for_storage = _compute_adaptive_ttl(
            spec_id,
            normalized_ttl,
            len(res.rows),
            exec_duration_ms,
        )

    should_store = ttl_for_storage is None or (
        isinstance(ttl_for_storage, int) and ttl_for_storage > 0
    )
    if isinstance(ttl_for_storage, int) and ttl_for_storage <= 0:
        should_store = False

    if should_store:
        cache.set(key, cache_value, ttl_for_storage)
    else:
        cache.delete(key)
    
    total_duration_ms = (time.perf_counter() - start_time) * 1000
    logger.info(
        f"Query {query_id} executed in {exec_duration_ms:.2f}ms "
        f"(total: {total_duration_ms:.2f}ms, rows: {len(res.rows)})"
    )
    return res


def invalidate_query(query_id: str, registry: QueryRegistry) -> None:
    """Convenience helper to invalidate a cached deterministic query."""
    spec = registry.get(query_id).model_copy(deep=True)
    key = _key_for(spec)
    cache: CacheBackend = get_cache_backend()
    cache.delete(key)
    COUNTERS["invalidations"] = COUNTERS.get("invalidations", 0) + 1
