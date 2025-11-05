"""Cached execution layer for deterministic queries with provenance enrichment."""

from __future__ import annotations

import base64
import hashlib
import json
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

MAX_CACHE_TTL_S = 24 * 60 * 60  # 24 hours
COMPRESS_THRESHOLD_BYTES = 8 * 1024  # 8KB

COUNTERS: MutableMapping[str, int] = {"hits": 0, "misses": 0, "invalidations": 0}


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


def _key_for(spec: QuerySpec) -> str:
    """Generate deterministic cache key from query spec."""
    normalized_params = _canonicalize_params(spec.params or {})
    # Include postprocess in cache key to differentiate transform pipelines
    postprocess_data = [
        {"name": step.name, "params": _canonicalize_params(step.params)}
        for step in (spec.postprocess or [])
    ]
    payload = json.dumps(
        {
            "id": spec.id,
            "source": spec.source,
            "params": normalized_params,
            "postprocess": postprocess_data,
        },
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    h = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    return f"qnwis:ddl:v1:{spec.id}:{h}"


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
        except Exception:
            pass


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

    Returns:
        QueryResult with enriched provenance and freshness warnings
    """
    source_spec = spec_override or registry.get(query_id)
    spec = source_spec.model_copy(deep=True)
    if spec.id != query_id:
        raise ValueError(f"Spec ID mismatch: expected {query_id}, got {spec.id}")

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
            _enrich_provenance(res)
            res.warnings.extend(verify_freshness(spec, res))
            return res

    COUNTERS["misses"] = COUNTERS.get("misses", 0) + 1

    res = execute_uncached(query_id, registry, spec_override=spec)
    _enrich_provenance(res)
    res.warnings.extend(verify_freshness(spec, res))

    if normalized_ttl == 0:
        cache.delete(key)
    else:
        cache_value = _encode_for_cache(res)
        cache.set(key, cache_value, normalized_ttl)
    return res


def invalidate_query(query_id: str, registry: QueryRegistry) -> None:
    """Convenience helper to invalidate a cached deterministic query."""
    spec = registry.get(query_id).model_copy(deep=True)
    key = _key_for(spec)
    cache: CacheBackend = get_cache_backend()
    cache.delete(key)
    COUNTERS["invalidations"] = COUNTERS.get("invalidations", 0) + 1
