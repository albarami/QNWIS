from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status

from ...security import Principal
from ...security.rbac import require_roles
from ...slo.budget import WindowCounts, snapshot_budget
from ...slo.loader import load_directory
from ...utils.clock import Clock

router = APIRouter(prefix="/api/v1/slo", tags=["slo"])


def get_clock(request: Request) -> Clock:
    return getattr(request.app.state, "clock", Clock())


@router.get("/", response_model=dict)
async def list_slos(
    request: Request,
) -> dict:
    slos = load_directory("slo")
    items = [
        {
            "id": s.slo_id,
            "sli": s.target.sli.value,
            "objective": s.target.objective,
            "window_days": s.target.window_days,
            "windows": {"fast_minutes": s.windows.fast_minutes, "slow_minutes": s.windows.slow_minutes},
        }
        for s in slos
    ]
    return {"slos": items}


@router.get("/budget", response_model=dict)
async def get_budgets(
    request: Request,
) -> dict:
    # Expect windows JSON at default path
    import json
    from pathlib import Path

    slos = load_directory("slo")
    win_path = Path("docs/audit/rg6/sli_windows.json")
    if not win_path.exists():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing sli_windows.json")
    data = json.loads(win_path.read_text(encoding="utf-8"))
    items = data.get("sli_windows") if isinstance(data, dict) else []
    by_id = {str(it.get("id")): it for it in items}

    budgets = []
    for s in slos:
        it = by_id.get(s.slo_id, {})
        fast = it.get("fast", {"bad": 0, "total": 0})
        slow = it.get("slow", {"bad": 0, "total": 0})
        frac = float(it.get("window_error_fraction", 0.0))
        snap = snapshot_budget(
            target=s.target,
            fast_counts=WindowCounts(bad=int(fast.get("bad", 0)), total=int(fast.get("total", 0))),
            slow_counts=WindowCounts(bad=int(slow.get("bad", 0)), total=int(slow.get("total", 0))),
            window_error_fraction_so_far=frac,
        )
        budgets.append({
            "id": s.slo_id,
            "sli": s.target.sli.value,
            "objective": s.target.objective,
            "window_days": s.target.window_days,
            "remaining_pct": snap.remaining_pct,
            "minutes_left": snap.minutes_left,
            "burn_fast": snap.burn_fast,
            "burn_slow": snap.burn_slow,
        })

    budgets.sort(key=lambda x: x["id"])  # deterministic
    return {"budgets": budgets}


@router.post("/simulate", response_model=dict)
async def simulate(
    payload: dict[str, Any],
    _principal: Principal = Depends(require_roles("admin", "service")),
    clock: Clock = Depends(get_clock),
) -> dict:
    # Dry-run only; return computed budgets, do not persist
    slos = load_directory("slo")
    it = payload or {}
    fast = it.get("fast", {"bad": 0, "total": 0})
    slow = it.get("slow", {"bad": 0, "total": 0})
    frac = float(it.get("window_error_fraction", 0.0))

    budgets = []
    for s in slos:
        snap = snapshot_budget(
            target=s.target,
            fast_counts=WindowCounts(bad=int(fast.get("bad", 0)), total=int(fast.get("total", 0))),
            slow_counts=WindowCounts(bad=int(slow.get("bad", 0)), total=int(slow.get("total", 0))),
            window_error_fraction_so_far=frac,
        )
        budgets.append({
            "id": s.slo_id,
            "remaining_pct": snap.remaining_pct,
            "minutes_left": snap.minutes_left,
            "burn_fast": snap.burn_fast,
            "burn_slow": snap.burn_slow,
            "timestamp": clock.now_iso(),
        })

    budgets.sort(key=lambda x: x["id"])  # deterministic
    return {"budgets": budgets}
