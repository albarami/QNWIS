"""
CLI tool for QNWIS cache management.

Provides commands to:
- View cache statistics
- Warm cache with common queries
- Invalidate cache prefixes
- Inspect available warmup packs
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..cache.keys import make_cache_key
from ..cache.redis_cache import DeterministicRedisCache
from ..cache.warmup import (
    WarmupPackError,
    list_warmup_packs,
    load_warmup_pack,
)
from ..data.deterministic.registry import REGISTRY_VERSION

NEGATIVE_CACHE_TTL = 5 * 60  # Align with middleware default


def warmup(
    cache: DeterministicRedisCache,
    samples: List[Dict[str, Any]],
    client: Any,
    *,
    version: Optional[str] = None,
    negative_ttl: Optional[int] = NEGATIVE_CACHE_TTL,
) -> Dict[str, int]:
    """
    Run DataClient calls for commonly used queries to pre-populate cache.

    Args:
        cache: Redis cache instance
        samples: List of query specs with fn name and params
        client: DataClient instance to execute queries
        version: Cache version override (defaults to registry checksum)
        negative_ttl: Optional TTL for empty results (seconds)

    Returns:
        Dictionary with cache statistics (sets, hits)
    """
    hits = 0
    sets = 0
    version_tag = version or REGISTRY_VERSION
    for sample in samples:
        fn_name = sample["fn"]
        params = sample.get("params", {})
        fn = getattr(client, fn_name)
        qr = fn(**params)
        key, ttl = make_cache_key(fn_name, qr.query_id, params, version_tag)
        cached = cache.get(key)
        if cached:
            hits += 1
            continue
        ttl_to_use = ttl
        if negative_ttl is not None and not qr.rows:
            ttl_to_use = min(ttl, negative_ttl)
        cache.set(key, qr, ttl_to_use)
        sets += 1
    return {"sets": sets, "hits": hits}


def _print_json(payload: Dict[str, Any]) -> None:
    """Print a JSON object with stable formatting."""
    print(json.dumps(payload, separators=(",", ":"), sort_keys=True))


def main() -> None:
    """
    Main entry point for cache CLI.

    Supports:
    - info: Show Redis server info
    - warmup: Pre-populate cache (requires project bootstrap)
    - invalidate-prefix: Delete keys matching prefix
    - list-packs: List available warmup packs
    - show-pack: Show specs in a warmup pack
    """
    ap = argparse.ArgumentParser(
        prog="qnwis-cache",
        description="Manage QNWIS cache (Redis)",
    )
    ap.add_argument(
        "--action",
        choices=["info", "warmup", "invalidate-prefix", "list-packs", "show-pack"],
        required=True,
        help="Cache operation to perform",
    )
    ap.add_argument(
        "--prefix",
        default="",
        help="Key prefix for invalidate-prefix action",
    )
    ap.add_argument(
        "--pack",
        default="core_kpis",
        help="Warmup pack name for warmup/show-pack actions",
    )
    ap.add_argument(
        "--packs-path",
        default=str(Path(__file__).with_name("warmup_packs.yml")),
        help="Path to warmup packs YAML",
    )
    args = ap.parse_args()

    cache = DeterministicRedisCache()
    packs_path = Path(args.packs_path)

    if args.action == "info":
        payload = {
            "action": "info",
            "registry_version": REGISTRY_VERSION,
            "redis": cache.info(),
        }
        _print_json(payload)
    elif args.action == "invalidate-prefix":
        count = cache.delete_prefix(args.prefix)
        payload = {
            "action": "invalidate-prefix",
            "prefix": args.prefix,
            "deleted": count,
        }
        _print_json(payload)
    elif args.action == "list-packs":
        try:
            packs = list_warmup_packs(packs_path)
        except WarmupPackError as exc:
            payload = {
                "action": "list-packs",
                "error": str(exc),
            }
        else:
            payload = {
                "action": "list-packs",
                "packs": packs,
                "count": len(packs),
            }
        _print_json(payload)
    elif args.action == "show-pack":
        try:
            specs = load_warmup_pack(args.pack, packs_path)
        except WarmupPackError as exc:
            payload = {
                "action": "show-pack",
                "pack": args.pack,
                "error": str(exc),
            }
        else:
            payload = {
                "action": "show-pack",
                "pack": args.pack,
                "spec_count": len(specs),
                "specs": specs,
            }
        _print_json(payload)
    elif args.action == "warmup":
        payload = {
            "action": "warmup",
            "status": "requires-bootstrap",
            "message": (
                "Invoke warmup(cache, samples, client) from project bootstrap with "
                "an authenticated DataClient and warmup pack specs."
            ),
        }
        _print_json(payload)


if __name__ == "__main__":
    main()
