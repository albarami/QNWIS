"""
Performance tests for ops console rendering.

Tests p95 page render latency and SSE enqueue performance.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from src.qnwis.notify.models import Incident, IncidentState, Severity
from src.qnwis.notify.resolver import IncidentResolver
from src.qnwis.ops_console.app import create_ops_app
from src.qnwis.ops_console.perf_metrics import collect_ui_metrics, persist_ui_metrics
from src.qnwis.ops_console.sse import SSEStream, create_incident_update_event
from src.qnwis.security import Principal
from src.qnwis.utils.clock import ManualClock


@pytest.fixture
def manual_clock():
    """Manual clock for deterministic timestamps."""
    return ManualClock(start=datetime(2024, 1, 1, 12, 0, tzinfo=UTC))


@pytest.fixture
def ops_app_with_96_incidents(manual_clock):
    """Create ops console app with 96 test incidents."""
    app = create_ops_app(clock=manual_clock, secret_key="test_secret")

    # Initialize resolver with 96 incidents
    resolver = IncidentResolver(clock=manual_clock, ledger_dir=None)

    for i in range(96):
        incident = Incident(
            incident_id=f"inc_{i:03d}",
            notification_id=f"notif_{i:03d}",
            rule_id=f"rule_{i % 10}",
            severity=Severity.CRITICAL if i % 3 == 0 else Severity.WARNING,
            state=IncidentState.OPEN if i % 4 == 0 else IncidentState.RESOLVED,
            message=f"Test incident {i} with some details about the issue",
            scope={"level": "sector", "code": f"{i:03d}"},
            window_start=f"2024-01-01T{i % 24:02d}:00:00Z",
            window_end=f"2024-01-01T{(i % 24) + 1:02d}:00:00Z",
            created_at=f"2024-01-01T{i % 24:02d}:30:00Z",
            updated_at=f"2024-01-01T{i % 24:02d}:30:00Z",
            consecutive_green_count=i % 5,
            metadata={"test_data": f"value_{i}", "counter": i},
        )
        resolver._store[incident.incident_id] = incident

    app.state.incident_resolver = resolver

    # Add middleware to inject principal
    @app.middleware("http")
    async def inject_principal(request, call_next):
        request.state.principal = Principal(
            user_id="test@example.com",
            roles=["analyst", "admin"],
        )
        response = await call_next(request)
        return response

    return app


class TestPageRenderPerformance:
    """Test page rendering performance."""

    def test_incidents_list_render_p95(self, ops_app_with_96_incidents):
        """Incidents list p95 render time < 150ms (96 incidents)."""
        client = TestClient(ops_app_with_96_incidents)

        # Warm up
        for _ in range(5):
            client.get("/incidents")

        # Measure render times
        render_times = []
        for _ in range(20):
            start = time.perf_counter()
            response = client.get("/incidents")
            elapsed_ms = (time.perf_counter() - start) * 1000

            assert response.status_code == 200
            render_times.append(elapsed_ms)

        # Calculate p95
        render_times.sort()
        p95_index = int(len(render_times) * 0.95)
        p95_render = render_times[p95_index]

        # p95 should be < 150ms
        assert p95_render < 150.0, f"p95 render time {p95_render:.2f}ms exceeds 150ms"

    def test_incident_detail_render_p95(self, ops_app_with_96_incidents):
        """Incident detail p95 render time < 150ms."""
        client = TestClient(ops_app_with_96_incidents)

        # Warm up
        for _ in range(5):
            client.get("/incidents/inc_000")

        # Measure render times
        render_times = []
        for i in range(20):
            incident_id = f"inc_{i % 96:03d}"
            start = time.perf_counter()
            response = client.get(f"/incidents/{incident_id}")
            elapsed_ms = (time.perf_counter() - start) * 1000

            assert response.status_code == 200
            render_times.append(elapsed_ms)

        # Calculate p95
        render_times.sort()
        p95_index = int(len(render_times) * 0.95)
        p95_render = render_times[p95_index]

        # p95 should be < 150ms
        assert p95_render < 150.0, f"p95 render time {p95_render:.2f}ms exceeds 150ms"

    def test_ops_index_render_p95(self, ops_app_with_96_incidents):
        """Ops index p95 render time < 150ms."""
        client = TestClient(ops_app_with_96_incidents)

        # Warm up
        for _ in range(5):
            client.get("/")

        # Measure render times
        render_times = []
        for _ in range(20):
            start = time.perf_counter()
            response = client.get("/")
            elapsed_ms = (time.perf_counter() - start) * 1000

            assert response.status_code == 200
            render_times.append(elapsed_ms)

        # Calculate p95
        render_times.sort()
        p95_index = int(len(render_times) * 0.95)
        p95_render = render_times[p95_index]

        # p95 should be < 150ms
        assert p95_render < 150.0, f"p95 render time {p95_render:.2f}ms exceeds 150ms"

    def test_filtered_list_render_performance(self, ops_app_with_96_incidents):
        """Filtered incidents list renders efficiently."""
        client = TestClient(ops_app_with_96_incidents)

        # Measure with filters
        render_times = []
        for _ in range(10):
            start = time.perf_counter()
            response = client.get("/incidents?state=open&severity=critical")
            elapsed_ms = (time.perf_counter() - start) * 1000

            assert response.status_code == 200
            render_times.append(elapsed_ms)

        # Average should be reasonable
        avg_render = sum(render_times) / len(render_times)
        assert avg_render < 150.0


class TestSSEEnqueuePerformance:
    """Test SSE event enqueue performance."""

    @pytest.mark.asyncio
    async def test_sse_enqueue_latency(self):
        """SSE enqueue latency < 5ms."""
        stream = SSEStream(heartbeat_interval=100)

        event = create_incident_update_event(
            incident_id="inc_perf",
            state="ACK",
            timestamp="2024-01-01T12:00:00Z",
        )

        # Measure enqueue times
        enqueue_times = []
        for _ in range(100):
            start = time.perf_counter()
            await stream.send_event(event)
            elapsed_ms = (time.perf_counter() - start) * 1000
            enqueue_times.append(elapsed_ms)

        await stream.close()

        # Calculate p95
        enqueue_times.sort()
        p95_index = int(len(enqueue_times) * 0.95)
        p95_enqueue = enqueue_times[p95_index]

        # p95 should be < 5ms
        assert p95_enqueue < 5.0, f"p95 enqueue time {p95_enqueue:.3f}ms exceeds 5ms"

    @pytest.mark.asyncio
    async def test_sse_format_performance(self):
        """SSE event format is fast."""
        event = create_incident_update_event(
            incident_id="inc_perf",
            state="RESOLVED",
            actor="user@test.com",
            timestamp="2024-01-01T12:00:00Z",
        )

        # Measure format times
        format_times = []
        for _ in range(1000):
            start = time.perf_counter()
            formatted = event.format()
            elapsed_ms = (time.perf_counter() - start) * 1000
            format_times.append(elapsed_ms)

        # Calculate average
        avg_format = sum(format_times) / len(format_times)

        # Average should be < 0.1ms
        assert avg_format < 0.1, f"Average format time {avg_format:.4f}ms exceeds 0.1ms"


class TestRenderDeterminism:
    """Test render time consistency."""

    def test_render_time_stability(self, ops_app_with_96_incidents):
        """Render times are stable across multiple runs."""
        client = TestClient(ops_app_with_96_incidents)

        # Warmup phase to eliminate cold-start effects
        for _ in range(5):
            client.get("/incidents")

        # Measure multiple times
        render_times = []
        for _ in range(50):
            start = time.perf_counter()
            response = client.get("/incidents")
            elapsed_ms = (time.perf_counter() - start) * 1000

            assert response.status_code == 200
            render_times.append(elapsed_ms)

        # Remove outliers (top and bottom 10%) to reduce variance from GC, OS noise
        sorted_times = sorted(render_times)
        trimmed_count = int(len(sorted_times) * 0.1)
        if trimmed_count > 0:
            trimmed_times = sorted_times[trimmed_count:-trimmed_count]
        else:
            trimmed_times = sorted_times

        # Calculate coefficient of variation (CV) on trimmed data
        mean = sum(trimmed_times) / len(trimmed_times)
        variance = sum((x - mean) ** 2 for x in trimmed_times) / len(trimmed_times)
        std_dev = variance ** 0.5
        cv = std_dev / mean if mean > 0 else 0

        # CV should be reasonable (< 0.5 for stable performance)
        assert cv < 0.5, f"Render time CV {cv:.2f} indicates unstable performance"


class TestPerfMetricsHelpers:
    """Validate helper functions that back RG-5 metrics."""

    def test_collect_ui_metrics_shapes(self, tmp_path):
        """collect_ui_metrics returns required keys."""
        metrics = collect_ui_metrics()
        incidents = metrics["render"]["incidents"]
        detail = metrics["render"]["incident_detail"]
        sse = metrics["sse"]
        csrf = metrics["csrf"]["verify"]
        assert incidents["p95_ms"] < 150.0
        assert detail["p95_ms"] < 150.0
        assert sse["p95_ms"] < 5.0
        assert csrf["p95_ms"] < 1.0

    def test_persist_ui_metrics(self, tmp_path):
        """persist_ui_metrics writes JSON to disk."""
        sample = {"render": {"incidents": {"p95_ms": 1}}}
        path = tmp_path / "ui_metrics.json"
        persisted = persist_ui_metrics(sample, path=path)
        assert persisted == path
        assert path.exists()


@pytest.mark.benchmark
class TestBenchmarkMetrics:
    """Benchmark metrics for reporting."""

    def test_benchmark_incidents_list_100_items(self, ops_app_with_96_incidents):
        """Benchmark incidents list with 96 items."""
        client = TestClient(ops_app_with_96_incidents)

        # Warm up
        for _ in range(10):
            client.get("/incidents")

        # Benchmark run
        render_times = []
        for _ in range(100):
            start = time.perf_counter()
            response = client.get("/incidents")
            elapsed_ms = (time.perf_counter() - start) * 1000
            render_times.append(elapsed_ms)

        render_times.sort()

        # Calculate percentiles
        p50 = render_times[int(len(render_times) * 0.50)]
        p95 = render_times[int(len(render_times) * 0.95)]
        p99 = render_times[int(len(render_times) * 0.99)]

        print("\n=== Incidents List Render Benchmark (96 items) ===")
        print(f"p50: {p50:.2f}ms")
        print(f"p95: {p95:.2f}ms")
        print(f"p99: {p99:.2f}ms")
        print(f"min: {render_times[0]:.2f}ms")
        print(f"max: {render_times[-1]:.2f}ms")

        # Assert targets
        assert p95 < 150.0

    def test_benchmark_incident_detail(self, ops_app_with_96_incidents):
        """Benchmark incident detail page."""
        client = TestClient(ops_app_with_96_incidents)

        # Warm up
        for _ in range(10):
            client.get("/incidents/inc_000")

        # Benchmark run
        render_times = []
        for i in range(100):
            incident_id = f"inc_{i % 96:03d}"
            start = time.perf_counter()
            response = client.get(f"/incidents/{incident_id}")
            elapsed_ms = (time.perf_counter() - start) * 1000
            render_times.append(elapsed_ms)

        render_times.sort()

        p50 = render_times[int(len(render_times) * 0.50)]
        p95 = render_times[int(len(render_times) * 0.95)]
        p99 = render_times[int(len(render_times) * 0.99)]

        print("\n=== Incident Detail Render Benchmark ===")
        print(f"p50: {p50:.2f}ms")
        print(f"p95: {p95:.2f}ms")
        print(f"p99: {p99:.2f}ms")

        assert p95 < 150.0
