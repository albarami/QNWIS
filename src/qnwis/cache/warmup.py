"""
Helpers for working with cache warmup packs.

Warmup packs are declarative YAML definitions of deterministic query calls
that should be prefetched after deployment to avoid cold starts.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

PACKS_PATH = Path(__file__).with_name("warmup_packs.yml")


class WarmupPackError(RuntimeError):
    """Raised when a warmup pack file is missing or malformed."""


def _load_all(path: Path = PACKS_PATH) -> dict[str, list[dict[str, Any]]]:
    """Load all warmup packs from YAML."""
    if not path.exists():
        raise WarmupPackError(f"Warmup pack file not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise WarmupPackError("Warmup pack YAML must be a mapping of pack names to specs.")

    packs: dict[str, list[dict[str, Any]]] = {}
    for name, specs in data.items():
        if not isinstance(specs, list):
            raise WarmupPackError(f"Warmup pack '{name}' must be a list of specs.")
        normalized: list[dict[str, Any]] = []
        for spec in specs:
            if not isinstance(spec, dict):
                raise WarmupPackError(f"Entries in pack '{name}' must be dictionaries.")
            if "fn" not in spec or "params" not in spec:
                raise WarmupPackError(
                    f"Warmup pack '{name}' entries must define 'fn' and 'params'."
                )
            params = spec["params"]
            if not isinstance(params, dict):
                raise WarmupPackError(
                    f"Warmup pack '{name}' params must be a mapping; got {type(params)!r}"
                )
            normalized.append({"fn": spec["fn"], "params": params})
        packs[name] = normalized
    return packs


def list_warmup_packs(path: Path = PACKS_PATH) -> list[str]:
    """Return the list of available warmup pack names."""
    return sorted(_load_all(path).keys())


def load_warmup_pack(name: str, path: Path = PACKS_PATH) -> list[dict[str, Any]]:
    """
    Load a single warmup pack by name.

    Args:
        name: Warmup pack identifier.
        path: Optional override path to warmup packs YAML.

    Returns:
        List of deterministic query specs (fn, params).

    Raises:
        WarmupPackError: If the pack cannot be found or is malformed.
    """
    packs = _load_all(path)
    try:
        return packs[name]
    except KeyError as exc:
        raise WarmupPackError(f"Unknown warmup pack: {name}") from exc
