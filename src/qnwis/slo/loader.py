from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .models import SLIKind, SLOTarget


@dataclass(frozen=True)
class BurnWindows:
    fast_minutes: int
    slow_minutes: int


@dataclass(frozen=True)
class SLODefinition:
    slo_id: str
    target: SLOTarget
    windows: BurnWindows


def _reject_nan_inf(value: float) -> float:
    import math

    if math.isnan(value) or math.isinf(value):
        raise ValueError("Value cannot be NaN or Inf")
    return float(value)


def _require_float(value: Any, field: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"SLO item '{field}' must be numeric") from exc


def _require_int(value: Any, field: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"SLO item '{field}' must be an integer") from exc


def _parse_item(item: dict[str, Any]) -> SLODefinition:
    slo_id = str(item.get("id") or item.get("slo_id"))
    if not slo_id or slo_id == "None":
        raise ValueError("SLO item missing 'id'")

    sli_raw = item.get("sli")
    if isinstance(sli_raw, str):
        sli = SLIKind(sli_raw)
    else:
        raise ValueError("SLO item 'sli' must be a string")

    objective = _reject_nan_inf(_require_float(item.get("objective"), "objective"))
    window_days = _require_int(item.get("window_days"), "window_days")
    target = SLOTarget(objective=objective, window_days=window_days, sli=sli)

    windows = item.get("windows", {}) or {}
    fast = _require_int(windows.get("fast_minutes", windows.get("fast", 5)), "windows.fast_minutes")
    slow = _require_int(windows.get("slow_minutes", windows.get("slow", 60)), "windows.slow_minutes")
    if fast <= 0 or slow <= 0:
        raise ValueError("Burn windows must be positive minutes")

    return SLODefinition(slo_id=slo_id, target=target, windows=BurnWindows(fast, slow))


def _load_from_dict(data: Any, source: str) -> list[SLODefinition]:
    if not isinstance(data, dict):
        raise ValueError(f"Expected dict at root in {source}")
    items = data.get("slos")
    if items is None:
        raise ValueError(f"Missing 'slos' list in {source}")
    if not isinstance(items, list):
        raise ValueError(f"'slos' must be a list in {source}")
    parsed = [_parse_item(it) for it in items]
    # Deterministic ordering by slo_id
    parsed.sort(key=lambda s: s.slo_id)
    return parsed


def load_file(path: str | Path) -> list[SLODefinition]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"SLO file not found: {path}")
    if p.suffix.lower() in {".yaml", ".yml"}:
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
        return _load_from_dict(data, str(path))
    if p.suffix.lower() == ".json":
        data = json.loads(p.read_text(encoding="utf-8"))
        return _load_from_dict(data, str(path))
    raise ValueError(f"Unsupported SLO file type: {p.suffix}")


def load_directory(directory: str | Path = "slo") -> list[SLODefinition]:
    d = Path(directory)
    if not d.exists():
        return []
    files = list(d.glob("*.yaml")) + list(d.glob("*.yml")) + list(d.glob("*.json"))
    results: list[SLODefinition] = []
    for fp in sorted(files, key=lambda p: p.name):
        results.extend(load_file(fp))
    # Deduplicate by slo_id keeping first occurrence deterministically
    by_id: dict[str, SLODefinition] = {}
    for s in results:
        if s.slo_id not in by_id:
            by_id[s.slo_id] = s
    return [by_id[k] for k in sorted(by_id.keys())]
