"""
Utilities to benchmark ops console performance for RG-5.

Provides helpers shared by tests and QA gates to measure render latency,
SSE enqueue throughput, and CSRF verification timing, persisting metrics
for downstream readiness review.
"""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import Request, Response
from fastapi.testclient import TestClient

from ..notify.models import Incident, IncidentState, Severity
from ..notify.resolver import IncidentResolver
from ..security import Principal
from ..utils.clock import ManualClock
from .app import create_ops_app
from .csrf import CSRFProtection
from .sse import SSEStream, create_incident_update_event

SRC_ROOT = Path(__file__).resolve().parents[2]
AUDIT_OPS_DIR = SRC_ROOT / "qnwis" / "docs" / "audit" / "ops"
DEFAULT_METRICS_PATH = AUDIT_OPS_DIR / "ui_metrics.json"

DEFAULT_START = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)


def _build_sample_incident(idx: int) -> Incident:
    """Create deterministic incident payload used across benchmarks."""
    severity = Severity.CRITICAL if idx % 3 == 0 else Severity.WARNING
    state = IncidentState.OPEN if idx % 4 == 0 else IncidentState.RESOLVED
    return Incident(
        incident_id=f"inc_{idx:03d}",
        notification_id=f"notif_{idx:03d}",
        rule_id=f"rule_{idx % 10}",
        severity=severity,
        state=state,
        message=f"Test incident {idx} with synthetic payload",
        scope={"level": "sector", "code": f"{idx:03d}"},
        window_start=f"2024-01-01T{idx % 24:02d}:00:00Z",
        window_end=f"2024-01-01T{(idx % 24):02d}:59:00Z",
        created_at=f"2024-01-01T{idx % 24:02d}:30:00Z",
        updated_at=f"2024-01-01T{idx % 24:02d}:30:00Z",
        consecutive_green_count=idx % 5,
        metadata={"counter": idx},
    )


def _seed_incidents(resolver: IncidentResolver, total: int = 96) -> None:
    for idx in range(total):
        resolver._store[f"inc_{idx:03d}"] = _build_sample_incident(idx)


def build_benchmark_app(total_incidents: int = 96) -> tuple[TestClient, ManualClock]:
    """Create FastAPI TestClient seeded with deterministic data."""
    clock = ManualClock(start=DEFAULT_START)
    app = create_ops_app(clock=clock, secret_key="rg5_secret")

    resolver = IncidentResolver(clock=clock, ledger_dir=None)
    _seed_incidents(resolver, total_incidents)
    app.state.incident_resolver = resolver

    async def inject_principal(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request.state.principal = Principal(
            user_id="ops.console@test.qa",
            roles=["analyst", "admin"],
        )
        response = await call_next(request)
        return response

    app.middleware("http")(inject_principal)

    return TestClient(app), clock


def _percentile(samples: list[float], pct: float) -> float:
    if not samples:
        return 0.0
    index = max(0, min(len(samples) - 1, int(len(samples) * pct)))
    return samples[index]


def _measure_route(client: TestClient, path: str, iterations: int = 40) -> dict[str, float]:
    latencies: list[float] = []
    for _ in range(iterations):
        start = time.perf_counter()
        response = client.get(path)
        if response.status_code != 200:
            raise AssertionError(f"{path} returned {response.status_code}")
        latencies.append((time.perf_counter() - start) * 1000)
    latencies.sort()
    return {
        "p50_ms": round(_percentile(latencies, 0.50), 3),
        "p95_ms": round(_percentile(latencies, 0.95), 3),
        "p99_ms": round(_percentile(latencies, 0.99), 3),
        "max_ms": round(latencies[-1], 3),
        "avg_ms": round(sum(latencies) / len(latencies), 3),
    }


def _measure_sse_enqueue(iterations: int = 200) -> dict[str, float]:
    stream = SSEStream()
    event = create_incident_update_event(
        incident_id="inc_perf",
        state="RESOLVED",
        actor="ops.console@test.qa",
        timestamp="2024-01-01T12:00:00Z",
    )
    latencies: list[float] = []

    async def _run() -> None:
        for _ in range(iterations):
            start = time.perf_counter()
            await stream.send_event(event)
            latencies.append((time.perf_counter() - start) * 1000)
        await stream.close()

    asyncio.run(_run())
    latencies.sort()
    return {
        "p50_ms": round(_percentile(latencies, 0.50), 4),
        "p95_ms": round(_percentile(latencies, 0.95), 4),
        "max_ms": round(latencies[-1], 4),
        "avg_ms": round(sum(latencies) / len(latencies), 4),
        "samples": len(latencies),
    }


def _measure_csrf_latency(iterations: int = 200) -> dict[str, float]:
    csrf = CSRFProtection(secret_key="rg5_secret")
    clock = ManualClock(start=DEFAULT_START)
    latencies: list[float] = []
    for _ in range(iterations):
        token = csrf.generate_token(clock.utcnow())
        start = time.perf_counter()
        csrf.verify_token(token.token, clock.utcnow())
        latencies.append((time.perf_counter() - start) * 1000)
        clock.advance(0.5)
    latencies.sort()
    return {
        "p50_ms": round(_percentile(latencies, 0.50), 4),
        "p95_ms": round(_percentile(latencies, 0.95), 4),
        "max_ms": round(latencies[-1], 4),
        "avg_ms": round(sum(latencies) / len(latencies), 4),
        "samples": len(latencies),
    }


def collect_ui_metrics(clock: ManualClock | None = None) -> dict[str, Any]:
    """Collect render, SSE, and CSRF metrics."""
    if clock is None:
        clock = ManualClock("2025-01-01T00:00:00Z")
    client, _ = build_benchmark_app()
    incidents_metrics = _measure_route(client, "/incidents")
    detail_metrics = _measure_route(client, "/incidents/inc_000")
    sse_metrics = _measure_sse_enqueue()
    csrf_metrics = _measure_csrf_latency()
    return {
        "generated_at": clock.now(),
        "render": {
            "incidents": incidents_metrics,
            "incident_detail": detail_metrics,
        },
        "sse": sse_metrics,
        "csrf": {
            "verify": csrf_metrics,
            "verify_p95_ms": csrf_metrics["p95_ms"],
        },
    }


def persist_ui_metrics(metrics: dict[str, Any], path: Path | None = None) -> Path:
    """Write metrics to audit folder."""
    target = path or DEFAULT_METRICS_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return target
