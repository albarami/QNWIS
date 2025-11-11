"""
CLI interface for SLO/SLI and Error Budgets (RG-6).

Deterministic operations: validate, snapshot, budget, simulate, drill.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from src.qnwis.observability.metrics import write_sli_snapshot_json
from src.qnwis.slo.budget import WindowCounts, snapshot_budget
from src.qnwis.slo.loader import SLODefinition, load_directory, load_file


def _read_sli_windows(path: str | Path) -> dict[str, dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"SLI windows file not found: {path}")
    data = json.loads(p.read_text(encoding="utf-8"))
    items = data.get("sli_windows") if isinstance(data, dict) else data
    if not isinstance(items, list):
        raise ValueError("'sli_windows' must be a list")
    out: dict[str, dict[str, Any]] = {}
    for it in items:
        slo_id = str(it.get("id"))
        out[slo_id] = {
            "fast": it.get("fast", {"bad": 0, "total": 0}),
            "slow": it.get("slow", {"bad": 0, "total": 0}),
            "window_error_fraction": float(it.get("window_error_fraction", 0.0)),
        }
    return out


def _write_budgets_json(path: str | Path, budgets: list[dict[str, Any]]) -> str:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"budgets": budgets}, sort_keys=True, separators=(",", ":")), encoding="utf-8")
    return str(p)


def cmd_validate(args: argparse.Namespace) -> int:
    try:
        slos = load_file(args.file) if args.file else load_directory(args.dir)
        print(f"✅ Validation PASSED: {len(slos)} SLOs parsed")
        return 0
    except Exception as e:
        print(f"❌ Validation FAILED: {e}", file=sys.stderr)
        return 1


def cmd_snapshot(args: argparse.Namespace) -> int:
    try:
        out = write_sli_snapshot_json(args.out)
        print(f"SLI snapshot written: {out}")
        return 0
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


def _load_slos(args: argparse.Namespace) -> list[SLODefinition]:
    if args.file:
        return load_file(args.file)
    return load_directory(args.dir)


def _compute_budgets(
    slos: list[SLODefinition],
    sli_windows: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    budgets: list[dict[str, Any]] = []
    for slo in slos:
        win = sli_windows.get(slo.slo_id, {"fast": {"bad": 0, "total": 0}, "slow": {"bad": 0, "total": 0}, "window_error_fraction": 0.0})
        fast = win.get("fast", {})
        slow = win.get("slow", {})
        eb = snapshot_budget(
            target=slo.target,
            fast_counts=WindowCounts(bad=int(fast.get("bad", 0)), total=int(fast.get("total", 0))),
            slow_counts=WindowCounts(bad=int(slow.get("bad", 0)), total=int(slow.get("total", 0))),
            window_error_fraction_so_far=float(win.get("window_error_fraction", 0.0)),
        )
        item = {
            "id": slo.slo_id,
            "sli": slo.target.sli.value,
            "objective": slo.target.objective,
            "window_days": slo.target.window_days,
            "remaining_pct": eb.remaining_pct,
            "minutes_left": eb.minutes_left,
            "burn_fast": eb.burn_fast,
            "burn_slow": eb.burn_slow,
        }
        budgets.append(item)
    # Deterministic ordering
    budgets.sort(key=lambda x: x["id"])
    return budgets


def cmd_budget(args: argparse.Namespace) -> int:
    try:
        slos = _load_slos(args)
        windows = _read_sli_windows(args.sli_windows)
        budgets = _compute_budgets(slos, windows)
        if args.out:
            out = _write_budgets_json(args.out, budgets)
            print(f"Budgets written: {out}")
        else:
            print(json.dumps({"budgets": budgets}, indent=2))
        return 0
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


def cmd_simulate(args: argparse.Namespace) -> int:
    try:
        # Load SLOs to enumerate ids
        slos = _load_slos(args)
        sli_windows = []
        for slo in slos:
            sli_windows.append(
                {
                    "id": slo.slo_id,
                    "fast": {"bad": args.fast_bad, "total": args.fast_total},
                    "slow": {"bad": args.slow_bad, "total": args.slow_total},
                    "window_error_fraction": args.window_error_fraction,
                }
            )
        p = Path(args.out)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"sli_windows": sli_windows}, sort_keys=True, separators=(",", ":")), encoding="utf-8")
        print(f"Simulation windows written: {p}")
        return 0
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


def cmd_drill(args: argparse.Namespace) -> int:
    try:
        slos = _load_slos(args)
        windows = _read_sli_windows(args.sli_windows)
        budgets = _compute_budgets(slos, windows)
        # Simple tabular print
        print("id,sli,objective,window_days,remaining_pct,minutes_left,burn_fast,burn_slow")
        for b in budgets:
            print(
                f"{b['id']},{b['sli']},{b['objective']},{b['window_days']},{b['remaining_pct']},"
                f"{b['minutes_left']},{b['burn_fast']},{b['burn_slow']}"
            )
        return 0
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="QNWIS SLO CLI",
    )
    sub = parser.add_subparsers(dest="command")

    p_validate = sub.add_parser("validate", help="Validate SLO definitions")
    p_validate.add_argument("--dir", default="slo", help="Directory with SLO YAML/JSON")
    p_validate.add_argument("--file", default=None, help="Specific SLO file")

    p_snapshot = sub.add_parser("snapshot", help="Write SLI snapshot JSON from metrics")
    p_snapshot.add_argument("--out", default="docs/audit/rg6/sli_snapshot.json")

    p_budget = sub.add_parser("budget", help="Compute error budgets for SLOs")
    p_budget.add_argument("--dir", default="slo", help="Directory with SLO YAML/JSON")
    p_budget.add_argument("--file", default=None, help="Specific SLO file")
    p_budget.add_argument("--sli-windows", dest="sli_windows", default="docs/audit/rg6/sli_windows.json")
    p_budget.add_argument("--out", default=None, help="Output file for budgets JSON")

    p_sim = sub.add_parser("simulate", help="Generate SLI windows with error bursts")
    p_sim.add_argument("--dir", default="slo", help="Directory with SLO YAML/JSON")
    p_sim.add_argument("--file", default=None, help="Specific SLO file")
    p_sim.add_argument("--fast-bad", type=int, default=10)
    p_sim.add_argument("--fast-total", type=int, default=1000)
    p_sim.add_argument("--slow-bad", type=int, default=100)
    p_sim.add_argument("--slow-total", type=int, default=10000)
    p_sim.add_argument("--window-error-fraction", type=float, default=0.0001)
    p_sim.add_argument("--out", default="docs/audit/rg6/sli_windows.json")

    p_drill = sub.add_parser("drill", help="Print tabular budget breakdown")
    p_drill.add_argument("--dir", default="slo", help="Directory with SLO YAML/JSON")
    p_drill.add_argument("--file", default=None, help="Specific SLO file")
    p_drill.add_argument("--sli-windows", dest="sli_windows", default="docs/audit/rg6/sli_windows.json")

    return parser


def main() -> int:
    parser = create_parser()
    args = parser.parse_args()
    if args.command == "validate":
        return cmd_validate(args)
    if args.command == "snapshot":
        return cmd_snapshot(args)
    if args.command == "budget":
        return cmd_budget(args)
    if args.command == "simulate":
        return cmd_simulate(args)
    if args.command == "drill":
        return cmd_drill(args)
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
