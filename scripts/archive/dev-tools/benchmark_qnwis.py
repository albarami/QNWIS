#!/usr/bin/env python3
"""
QNWIS Performance Benchmark Suite (Step 35 refresh).

Runs configurable scenarios against the FastAPI surface (either over HTTP
or in-process via TestClient), captures latency percentiles, CPU/memory
snapshots, and emits JSON/CSV/PNG artifacts for CI.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import os

import requests

try:  # pragma: no cover - optional dependency
    import matplotlib.pyplot as plt
except Exception:  # pragma: no cover
    plt = None

try:  # pragma: no cover - optional dependency
    import psutil
except Exception:  # pragma: no cover
    psutil = None


DEFAULT_BASE_URL = "http://localhost:8000"


@dataclass
class RequestPayload:
    """Request body and query params for a scenario invocation."""

    json: dict[str, Any] | None = None
    params: dict[str, Any] | None = None


@dataclass
class ScenarioConfig:
    """Benchmark scenario definition."""

    key: str
    name: str
    method: Literal["GET", "POST"]
    endpoint: str
    target_ms: int
    payload_factory: Callable[[int], RequestPayload]


@dataclass
class BenchmarkResult:
    """Single HTTP invocation result."""

    status_code: int
    duration_ms: float


@dataclass
class ScenarioStats:
    """Aggregated statistics for a scenario run."""

    scenario: str
    total_requests: int
    successful: int
    failed: int
    p50_ms: float
    p90_ms: float
    p95_ms: float
    p99_ms: float
    mean_ms: float
    min_ms: float
    max_ms: float
    throughput_rps: float

    def meets_target(self, target_ms: float) -> bool:
        return self.p95_ms <= target_ms

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario": self.scenario,
            "total_requests": self.total_requests,
            "successful": self.successful,
            "failed": self.failed,
            "p50_ms": round(self.p50_ms, 2),
            "p90_ms": round(self.p90_ms, 2),
            "p95_ms": round(self.p95_ms, 2),
            "p99_ms": round(self.p99_ms, 2),
            "mean_ms": round(self.mean_ms, 2),
            "min_ms": round(self.min_ms, 2),
            "max_ms": round(self.max_ms, 2),
            "throughput_rps": round(self.throughput_rps, 2),
        }


class BaseTransport:
    """Transport abstraction used by both HTTP and in-process modes."""

    def request(self, method: str, path: str, payload: RequestPayload) -> BenchmarkResult:
        raise NotImplementedError


class HttpTransport(BaseTransport):
    """Real HTTP transport hitting a running uvicorn instance."""

    def __init__(
        self,
        *,
        base_url: str,
        timeout: float,
        api_key: str | None = None,
        jwt_token: str | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.timeout = timeout
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if api_key:
            headers["X-API-Key"] = api_key
        if jwt_token:
            headers["Authorization"] = f"Bearer {jwt_token}"
        self.headers = headers

    def request(self, method: str, path: str, payload: RequestPayload) -> BenchmarkResult:
        url = f"{self.base_url}{path}"
        start = time.perf_counter()
        response = self.session.request(
            method,
            url,
            json=payload.json,
            params=payload.params,
            timeout=self.timeout,
            headers=self.headers,
        )
        duration_ms = (time.perf_counter() - start) * 1000
        return BenchmarkResult(status_code=response.status_code, duration_ms=duration_ms)


class InProcessTransport(BaseTransport):
    """FastAPI TestClient transport (no network, auth bypass)."""

    def __init__(self) -> None:
        from fastapi.testclient import TestClient
        from qnwis.api.server import create_app

        os.environ.setdefault("QNWIS_BYPASS_AUTH", "true")
        self.client = TestClient(create_app())

    def request(self, method: str, path: str, payload: RequestPayload) -> BenchmarkResult:
        start = time.perf_counter()
        response = self.client.request(
            method,
            path,
            json=payload.json,
            params=payload.params,
        )
        duration_ms = (time.perf_counter() - start) * 1000
        return BenchmarkResult(status_code=response.status_code, duration_ms=duration_ms)


def _simple_query_payload(_: int) -> RequestPayload:
    return RequestPayload(
        json={"override_params": {"year": "2024"}},
    )


def _strategy_payload(_: int) -> RequestPayload:
    return RequestPayload(
        json={
            "intent": "strategy.benchmark",
            "params": {"min_countries": 3},
        }
    )


def _time_agent_payload(iteration: int) -> RequestPayload:
    sector = "Energy" if iteration % 2 == 0 else "Construction"
    return RequestPayload(
        json={
            "intent": "time.trend",
            "params": {
                "metric": "retention",
                "sector": sector,
            },
        }
    )


def _dashboard_payload(_: int) -> RequestPayload:
    return RequestPayload(params={"ttl_s": 120})


SCENARIOS: dict[str, ScenarioConfig] = {
    "simple": ScenarioConfig(
        key="simple",
        name="Simple Query",
        method="POST",
        endpoint="/v1/queries/syn_employment_share_by_gender_latest/run",
        target_ms=500,
        payload_factory=_simple_query_payload,
    ),
    "medium": ScenarioConfig(
        key="medium",
        name="Strategy Benchmark",
        method="POST",
        endpoint="/agents/strategy/benchmark",
        target_ms=2000,
        payload_factory=_strategy_payload,
    ),
    "complex": ScenarioConfig(
        key="complex",
        name="Time Trend Agent",
        method="POST",
        endpoint="/agents/time/trend",
        target_ms=5000,
        payload_factory=_time_agent_payload,
    ),
    "dashboard": ScenarioConfig(
        key="dashboard",
        name="Dashboard Summary",
        method="GET",
        endpoint="/v1/ui/dashboard/summary",
        target_ms=300,
        payload_factory=_dashboard_payload,
    ),
}


def _select_scenarios(arg: str) -> list[ScenarioConfig]:
    if arg == "all":
        return list(SCENARIOS.values())
    if arg not in SCENARIOS:
        raise SystemExit(f"Unknown scenario '{arg}'. Choose from {', '.join(SCENARIOS)} or 'all'.")
    return [SCENARIOS[arg]]


def _collect_process_stats() -> dict[str, float]:
    if psutil is None:
        return {}
    proc = psutil.Process()
    with proc.oneshot():
        rss_mb = proc.memory_info().rss / (1024 * 1024)
        cpu_percent = proc.cpu_percent(interval=None)
    return {"rss_mb": round(rss_mb, 2), "cpu_percent": cpu_percent}


def _run_scenario(
    transport: BaseTransport,
    scenario: ScenarioConfig,
    num_requests: int,
    concurrency: int,
) -> ScenarioStats:
    results: list[BenchmarkResult] = []
    total_start = time.perf_counter()

    def _invoke(iteration: int) -> BenchmarkResult:
        payload = scenario.payload_factory(iteration)
        return transport.request(scenario.method, scenario.endpoint, payload)

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = {
            executor.submit(_invoke, idx): idx for idx in range(num_requests)
        }
        for future in as_completed(futures):
            try:
                results.append(future.result())
            except Exception as exc:  # pragma: no cover - network failure
                results.append(BenchmarkResult(status_code=599, duration_ms=0.0))
                print(f"[WARN] Scenario {scenario.key} request failed: {exc}", file=sys.stderr)

    durations = [r.duration_ms for r in results]
    successes = [r for r in results if 200 <= r.status_code < 300]
    total_time = max(time.perf_counter() - total_start, 1e-6)

    if not durations:
        return ScenarioStats(
            scenario=scenario.key,
            total_requests=num_requests,
            successful=0,
            failed=num_requests,
            p50_ms=0,
            p90_ms=0,
            p95_ms=0,
            p99_ms=0,
            mean_ms=0,
            min_ms=0,
            max_ms=0,
            throughput_rps=0,
        )

    sorted_durations = sorted(durations)
    def percentile(p: float) -> float:
        index = min(int(len(sorted_durations) * p), len(sorted_durations) - 1)
        return sorted_durations[index]

    stats = ScenarioStats(
        scenario=scenario.key,
        total_requests=num_requests,
        successful=len(successes),
        failed=num_requests - len(successes),
        p50_ms=percentile(0.50),
        p90_ms=percentile(0.90),
        p95_ms=percentile(0.95),
        p99_ms=percentile(0.99),
        mean_ms=statistics.mean(durations),
        min_ms=min(durations),
        max_ms=max(durations),
        throughput_rps=len(results) / total_time,
    )
    return stats


def _write_csv(path: Path, stats: list[ScenarioStats]) -> None:
    lines = [
        "scenario,p50_ms,p90_ms,p95_ms,p99_ms,mean_ms,min_ms,max_ms,throughput_rps"
    ]
    for stat in stats:
        lines.append(
            f"{stat.scenario},{stat.p50_ms:.2f},{stat.p90_ms:.2f},{stat.p95_ms:.2f},"
            f"{stat.p99_ms:.2f},{stat.mean_ms:.2f},{stat.min_ms:.2f},{stat.max_ms:.2f},"
            f"{stat.throughput_rps:.2f}"
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_plot(path: Path, stats: list[ScenarioStats]) -> None:
    if plt is None:  # pragma: no cover - optional dependency
        return
    labels = [s.scenario for s in stats]
    p95_values = [s.p95_ms for s in stats]
    targets = [SCENARIOS[s.scenario].target_ms for s in stats if s.scenario in SCENARIOS]
    plt.figure(figsize=(8, 4))
    plt.bar(labels, p95_values, color="#1f77b4", label="p95 (ms)")
    plt.plot(labels, targets, color="red", linestyle="--", label="Target")
    plt.ylabel("Milliseconds")
    plt.title("QNWIS Benchmark p95 Latency")
    plt.legend()
    plt.tight_layout()
    plt.savefig(path)
    plt.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="QNWIS Performance Benchmarks")
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"Base API URL (default: {DEFAULT_BASE_URL})",
    )
    parser.add_argument(
        "--scenario",
        choices=list(SCENARIOS.keys()) + ["all"],
        default="all",
        help="Scenario to run",
    )
    parser.add_argument(
        "--requests",
        type=int,
        default=10,
        help="Requests per scenario",
    )
    parser.add_argument(
        "--users",
        type=int,
        default=4,
        help="Concurrent users (threads)",
    )
    parser.add_argument(
        "--output",
        default="benchmark_results.json",
        help="Path to JSON results file",
    )
    parser.add_argument(
        "--transport",
        choices=["http", "inprocess"],
        default="http",
        help="Transport mode",
    )
    parser.add_argument(
        "--api-key",
        default=os.getenv("QNWIS_BENCHMARK_API_KEY"),
        help="API key for authenticated requests",
    )
    parser.add_argument(
        "--jwt",
        default=None,
        help="JWT bearer token for authenticated requests",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="HTTP timeout seconds",
    )
    parser.add_argument(
        "--label",
        default="step35",
        help="Label included in JSON artifact",
    )
    args = parser.parse_args()

    scenarios = _select_scenarios(args.scenario)
    if args.transport == "http":
        if not args.api_key and not args.jwt:
            print("WARNING: no API key/JWT supplied; requests may be rejected.", file=sys.stderr)
        transport: BaseTransport = HttpTransport(
            base_url=args.base_url,
            timeout=args.timeout,
            api_key=args.api_key,
            jwt_token=args.jwt,
        )
    else:
        transport = InProcessTransport()

    stats: list[ScenarioStats] = []
    for scenario in scenarios:
        stats.append(_run_scenario(transport, scenario, args.requests, args.users))

    json_path = Path(args.output)
    csv_path = json_path.with_suffix(".csv")
    png_path = json_path.with_suffix(".png")

    proc_stats = _collect_process_stats()
    payload = {
        "label": args.label,
        "transport": args.transport,
        "config": {
            "base_url": args.base_url,
            "requests": args.requests,
            "users": args.users,
            "timeout": args.timeout,
        },
        "system": proc_stats,
        "scenarios": [stat.to_dict() for stat in stats],
    }
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    _write_csv(csv_path, stats)
    _write_plot(png_path, stats)

    print("\nBenchmark Summary")
    print("=================")
    for stat in stats:
        target = SCENARIOS[stat.scenario].target_ms
        status = "PASS" if stat.meets_target(target) else "FAIL"
        print(
            f"{stat.scenario:10s} {status}  "
            f"p95={stat.p95_ms:.1f}ms (target {target}ms)  "
            f"success={stat.successful}/{stat.total_requests}"
        )

    if not all(stat.meets_target(SCENARIOS[stat.scenario].target_ms) for stat in stats):
        sys.exit(1)


if __name__ == "__main__":
    main()
