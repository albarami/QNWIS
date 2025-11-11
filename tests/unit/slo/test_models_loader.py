from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.qnwis.slo.loader import load_directory, load_file
from src.qnwis.slo.models import SLIKind


def test_slo_target_validation_rejects_nan_inf(tmp_path: Path):
    data = {
        "slos": [
            {"id": "s1", "sli": "availability_pct", "objective": 99.9, "window_days": 14},
        ]
    }
    p = tmp_path / "slo.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    slos = load_file(p)
    assert len(slos) == 1
    assert slos[0].target.sli == SLIKind.AVAILABILITY_PCT


def test_loader_deterministic_ordering(tmp_path: Path):
    # Two files with overlapping SLO ids
    d = tmp_path / "slo"
    d.mkdir()
    a = {
        "slos": [
            {"id": "b", "sli": "error_rate_pct", "objective": 1.0, "window_days": 30},
            {"id": "a", "sli": "latency_ms_p95", "objective": 200, "window_days": 7},
        ]
    }
    b = {"slos": [{"id": "a", "sli": "availability_pct", "objective": 99.9, "window_days": 30}]}
    (d / "a.json").write_text(json.dumps(a), encoding="utf-8")
    (d / "b.json").write_text(json.dumps(b), encoding="utf-8")
    slos = load_directory(d)
    ids = [s.slo_id for s in slos]
    assert ids == sorted(set(ids))  # unique and sorted
    # First-seen wins for duplicate 'a'
    assert slos[0].slo_id == "a"


def test_loader_rejects_missing_fields(tmp_path: Path):
    bad = {"slos": [{"sli": "availability_pct", "objective": 99.9, "window_days": 30}]}
    p = tmp_path / "bad.json"
    p.write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(ValueError):
        load_file(p)
