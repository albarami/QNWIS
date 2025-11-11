"""
RG-6 Resilience Gate for SLO/SLI & Error Budgets.

Deterministic checks:
- slo_presence
- sli_accuracy (optional golden)
- budget_correctness
- burnrate_alerts
- resilience_perf (p95 < 50 ms for 100 SLOs)

Artifacts:
- docs/audit/rg6/rg6_report.json
- docs/audit/rg6/SLO_SUMMARY.md
- docs/audit/badges/rg6_pass.svg
"""

from __future__ import annotations

import json
import sys
import time
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _ensure_repo_root() -> None:
    repo_root = Path(__file__).resolve().parents[4]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))


def _write_json(path: Path, payload: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True, separators=(",", ":")), encoding="utf-8")
    return str(path)


def _write_md(path: Path, lines: list[str]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(path)


def _write_badge(path: Path, label: str, status: str, color: str) -> str:
    svg = f"""
<svg xmlns='http://www.w3.org/2000/svg' width='190' height='20' role='img' aria-label='{label}: {status}'>
  <linearGradient id='s' x2='0' y2='100%'>
    <stop offset='0' stop-color='#bbb' stop-opacity='.1'/>
    <stop offset='1' stop-opacity='.1'/>
  </linearGradient>
  <rect rx='3' width='190' height='20' fill='#555'/>
  <rect rx='3' x='85' width='105' height='20' fill='{color}'/>
  <path fill='{color}' d='M85 0h4v20h-4z'/>
  <rect rx='3' width='190' height='20' fill='url(#s)'/>
  <g fill='#fff' text-anchor='middle' font-family='DejaVu Sans,Verdana,Geneva,sans-serif' font-size='11'>
    <text x='43' y='15' fill='#010101' fill-opacity='.3'>{label}</text>
    <text x='43' y='14'>{label}</text>
    <text x='137' y='15' fill='#010101' fill-opacity='.3'>{status}</text>
    <text x='137' y='14'>{status}</text>
  </g>
</svg>
""".strip()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(svg, encoding="utf-8")
    return str(path)


def _compare_golden(actual: dict[str, Any], golden_path: Path) -> tuple[bool, dict[str, Any]]:
    if not golden_path.exists():
        return True, {"status": "skipped", "reason": "golden_missing"}
    expected = json.loads(golden_path.read_text(encoding="utf-8"))
    return actual == expected, {"expected": expected, "actual": actual}


def _percentile(values: Sequence[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = max(0, min(len(ordered) - 1, int(round(percentile * (len(ordered) - 1)))))
    return float(ordered[idx])


def _summarize_budgets(budgets: Sequence[dict[str, float]]) -> dict[str, float]:
    if not budgets:
        return {}
    remaining = [float(item.get("remaining_pct", 0.0)) for item in budgets]
    minutes = [float(item.get("minutes_left", 0.0)) for item in budgets]
    return {
        "samples": len(budgets),
        "avg_remaining_pct": round(sum(remaining) / len(remaining), 4),
        "min_remaining_pct": round(min(remaining), 4),
        "avg_minutes_left": round(sum(minutes) / len(minutes), 4),
        "min_minutes_left": round(min(minutes), 4),
    }


def _summarize_burn(budgets: Sequence[dict[str, float]]) -> dict[str, float]:
    if not budgets:
        return {}
    fast = [float(item.get("burn_fast", 0.0)) for item in budgets]
    slow = [float(item.get("burn_slow", 0.0)) for item in budgets]
    return {
        "p95_fast": round(_percentile(fast, 0.95), 4),
        "p95_slow": round(_percentile(slow, 0.95), 4),
        "max_fast": round(max(fast), 4) if fast else 0.0,
        "max_slow": round(max(slow), 4) if slow else 0.0,
    }


def _objective_rows(slos: Sequence[Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for slo_def in slos:
        rows.append(
            {
                "id": slo_def.slo_id,
                "sli": slo_def.target.sli.value,
                "objective": float(slo_def.target.objective),
                "window_days": int(slo_def.target.window_days),
                "fast_minutes": getattr(slo_def.windows, "fast_minutes", None),
                "slow_minutes": getattr(slo_def.windows, "slow_minutes", None),
            }
        )
    return rows


def run_gate() -> int:
    _ensure_repo_root()
    from src.qnwis.alerts.engine import AlertEngine
    from src.qnwis.alerts.rules import (
        AlertRule,
        ScopeConfig,
        Severity,
        TriggerConfig,
        TriggerType,
        WindowConfig,
    )
    from src.qnwis.observability.metrics import compute_sli_snapshot, write_sli_snapshot_json
    from src.qnwis.slo.budget import WindowCounts, snapshot_budget
    from src.qnwis.slo.loader import load_directory
    from src.qnwis.slo.models import SLIKind, SLOTarget
    from src.qnwis.utils.clock import ManualClock

    out_dir = Path("docs/audit/rg6")
    badge_dir = Path("docs/audit/badges")

    clock = ManualClock(start=datetime(2024, 1, 1, tzinfo=UTC))

    results: dict[str, Any] = {"checks": {}, "metrics": {}}

    # 1) SLO presence
    slos = load_directory("slo")
    results["checks"]["slo_presence"] = {"count": len(slos), "pass": len(slos) > 0}
    results["metrics"]["slo_count"] = len(slos)
    results["metrics"]["slos"] = _objective_rows(slos)

    # 2) SLI accuracy (compute + optional golden compare)
    sli_snapshot = compute_sli_snapshot()
    write_sli_snapshot_json(str(out_dir / "sli_snapshot.json"), clock=clock)
    golden_ok, golden_info = _compare_golden({"sli": sli_snapshot}, out_dir / "sli_golden.json")
    results["checks"]["sli_accuracy"] = {"pass": golden_ok, **golden_info}

    # 3) Budget correctness (basic invariants + optional golden budgets file)
    windows_path = out_dir / "sli_windows.json"
    budgets: list[dict[str, Any]] = []
    budget_pass = True
    budget_source = "observed"
    if windows_path.exists() and slos:
        data = json.loads(windows_path.read_text(encoding="utf-8"))
        raw_items = data.get("sli_windows") if isinstance(data, dict) else []
        items = raw_items if isinstance(raw_items, list) else []
        by_id = {str(it.get("id")): it for it in items}
        for slo_def in slos:
            sample = by_id.get(slo_def.slo_id, {})
            fast = sample.get("fast", {"bad": 0, "total": 0})
            slow = sample.get("slow", {"bad": 0, "total": 0})
            frac = float(sample.get("window_error_fraction", 0.0))
            snap = snapshot_budget(
                target=slo_def.target,
                fast_counts=WindowCounts(bad=int(fast.get("bad", 0)), total=int(fast.get("total", 0))),
                slow_counts=WindowCounts(bad=int(slow.get("bad", 0)), total=int(slow.get("total", 0))),
                window_error_fraction_so_far=frac,
            )
            budgets.append(
                {
                    "id": slo_def.slo_id,
                    "remaining_pct": snap.remaining_pct,
                    "minutes_left": snap.minutes_left,
                    "burn_fast": snap.burn_fast,
                    "burn_slow": snap.burn_slow,
                }
            )
            if not (0.0 <= snap.remaining_pct <= 100.0):
                budget_pass = False
            if snap.minutes_left < 0.0:
                budget_pass = False
            if snap.burn_fast < 0.0 or snap.burn_slow < 0.0:
                budget_pass = False
    elif slos:
        budget_source = "synthetic_zero_load"
        for slo_def in slos:
            fast_total = max(1, int(getattr(slo_def.windows, "fast_minutes", 5)))
            slow_total = max(1, int(getattr(slo_def.windows, "slow_minutes", 60)))
            snap = snapshot_budget(
                target=slo_def.target,
                fast_counts=WindowCounts(bad=0, total=fast_total),
                slow_counts=WindowCounts(bad=0, total=slow_total),
                window_error_fraction_so_far=0.0,
            )
            budgets.append(
                {
                    "id": slo_def.slo_id,
                    "remaining_pct": snap.remaining_pct,
                    "minutes_left": snap.minutes_left,
                    "burn_fast": snap.burn_fast,
                    "burn_slow": snap.burn_slow,
                }
            )
    else:
        budget_source = "no_slos"

    results["checks"]["budget_correctness"] = {"pass": budget_pass, "samples": len(budgets)}
    results["metrics"]["budget_source"] = budget_source
    results["metrics"]["budget_summary"] = _summarize_budgets(budgets)
    results["metrics"]["burn_summary"] = _summarize_burn(budgets)

    # 4) Burn-rate alerts (trip fast/slow)
    engine = AlertEngine()
    rule = AlertRule(
        rule_id="rg6_burnrate_test",
        metric="availability",
        scope=ScopeConfig(level="global", code=None),
        window=WindowConfig(months=3),
        trigger=TriggerConfig(type=TriggerType.BURN_RATE, fast_threshold=2.0, slow_threshold=1.0, value=0.0),
        horizon=12,
        severity=Severity.HIGH,
    )
    dec1 = engine.evaluate(rule, [2.1, 1.0])
    dec2 = engine.evaluate(rule, [1.5, 0.9])
    burnrate_ok = dec1.triggered and (not dec2.triggered)
    results["checks"]["burnrate_alerts"] = {"pass": burnrate_ok, "evidence": [dec1.evidence, dec2.evidence]}

    # 5) Resilience perf (100 SLOs p95 < 50 ms)
    perf_times: list[float] = []
    for _ in range(100):
        t = SLOTarget(objective=99.9, window_days=14, sli=SLIKind.AVAILABILITY_PCT)
        fast = WindowCounts(bad=1, total=1000)
        slow = WindowCounts(bad=10, total=10000)
        start = time.perf_counter()
        snapshot_budget(t, fast, slow, 0.0001)
        perf_times.append((time.perf_counter() - start) * 1000.0)
    p95_ms = round(_percentile(perf_times, 0.95), 3)
    perf_ok = p95_ms < 50.0
    results["checks"]["resilience_perf"] = {"pass": perf_ok, "p95_ms": p95_ms}

    passes = [v.get("pass", False) for v in results["checks"].values()]
    all_pass = all(passes)

    out_dir.mkdir(parents=True, exist_ok=True)
    _write_json(out_dir / "rg6_report.json", results)

    lines = [
        "# RG-6 Resilience Gate Report",
        "",
        f"- **slo_presence**: {'PASS' if results['checks']['slo_presence']['pass'] else 'FAIL'} (count={results['checks']['slo_presence']['count']})",
        f"- **sli_accuracy**: {'PASS' if results['checks']['sli_accuracy']['pass'] else 'FAIL'}",
        f"- **budget_correctness**: {'PASS' if results['checks']['budget_correctness']['pass'] else 'FAIL'} (samples={results['checks']['budget_correctness']['samples']})",
        f"- **burnrate_alerts**: {'PASS' if results['checks']['burnrate_alerts']['pass'] else 'FAIL'}",
        f"- **resilience_perf**: {'PASS' if results['checks']['resilience_perf']['pass'] else 'FAIL'} (p95_ms={results['checks']['resilience_perf']['p95_ms']})",
        "",
    ]
    if slos:
        lines.append("## SLOs")
        for slo_def in slos:
            lines.append(
                f"- `{slo_def.slo_id}`: {slo_def.target.sli.value} objective={slo_def.target.objective} window_days={slo_def.target.window_days}"
            )
    summary = results["metrics"].get("budget_summary") or {}
    burn_summary = results["metrics"].get("burn_summary") or {}
    lines.extend(
        [
            "",
            "## Budget Snapshot",
            "",
        ]
    )
    if budgets:
        lines.extend(
            [
                f"- Samples: {summary.get('samples', 0)} (source={results['metrics'].get('budget_source')})",
                f"- Avg Remaining %: {summary.get('avg_remaining_pct', 0.0)} / Min Remaining %: {summary.get('min_remaining_pct', 0.0)}",
                f"- Avg Minutes Left: {summary.get('avg_minutes_left', 0.0)} / Min Minutes Left: {summary.get('min_minutes_left', 0.0)}",
                f"- Burn p95 (fast/slow): {burn_summary.get('p95_fast', 0.0)} / {burn_summary.get('p95_slow', 0.0)}",
                f"- Burn max (fast/slow): {burn_summary.get('max_fast', 0.0)} / {burn_summary.get('max_slow', 0.0)}",
                "",
                "| SLO | Remaining % | Minutes Left | Burn Rate (fast/slow) |",
                "| --- | --- | --- | --- |",
            ]
        )
        for sample in budgets:
            lines.append(
                f"| {sample['id']} | {sample['remaining_pct']:.3f} | {sample['minutes_left']:.3f} | "
                f"{sample['burn_fast']:.3f} / {sample['burn_slow']:.3f} |"
            )
    else:
        lines.append("- No budget samples available.")
    _write_md(out_dir / "SLO_SUMMARY.md", lines)

    _write_badge(
        badge_dir / "rg6_pass.svg",
        label="RG-6",
        status="pass" if all_pass else "fail",
        color="#4c1" if all_pass else "#e05d44",
    )

    print(
        f"STEP 31 COMPLETE -- RG-6 {'PASS' if all_pass else 'FAIL'} -- Artifacts published"
        f" (slo={len(slos)}, p95_ms={results['checks']['resilience_perf']['p95_ms']})"
    )

    return 0 if all_pass else 2


if __name__ == "__main__":
    sys.exit(run_gate())
