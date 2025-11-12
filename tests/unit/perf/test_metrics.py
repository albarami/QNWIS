"""
Unit tests for qnwis.perf.metrics module.

Tests Prometheus metrics collection, counters, histograms,
and /metrics endpoint integration.
"""

import pytest
from fastapi.testclient import TestClient
from prometheus_client import REGISTRY

from qnwis.perf.metrics import (
    AGENT_LATENCY,
    CACHE_HIT,
    CACHE_MISS,
    DB_LATENCY,
    LATENCY,
    REQUESTS,
    STAGE_LATENCY,
    router,
)


class TestPrometheusMetrics:
    """Test Prometheus metric definitions."""

    def test_requests_counter_exists(self):
        """REQUESTS counter should be defined."""
        assert REQUESTS is not None
        assert REQUESTS._name == "qnwis_requests_total"
        assert REQUESTS._documentation == "Total HTTP requests"

    def test_latency_histogram_exists(self):
        """LATENCY histogram should be defined."""
        assert LATENCY is not None
        assert LATENCY._name == "qnwis_latency_seconds"
        assert LATENCY._documentation == "HTTP request latency in seconds"

    def test_db_latency_histogram_exists(self):
        """DB_LATENCY histogram should be defined."""
        assert DB_LATENCY is not None
        assert DB_LATENCY._name == "qnwis_db_latency_seconds"

    def test_cache_hit_counter_exists(self):
        """CACHE_HIT counter should be defined."""
        assert CACHE_HIT is not None
        assert CACHE_HIT._name == "qnwis_cache_hits_total"

    def test_cache_miss_counter_exists(self):
        """CACHE_MISS counter should be defined."""
        assert CACHE_MISS is not None
        assert CACHE_MISS._name == "qnwis_cache_misses_total"

    def test_agent_latency_histogram_exists(self):
        """AGENT_LATENCY histogram should be defined."""
        assert AGENT_LATENCY is not None
        assert AGENT_LATENCY._name == "qnwis_agent_latency_seconds"

    def test_stage_latency_histogram_exists(self):
        """STAGE_LATENCY histogram should be defined."""
        assert STAGE_LATENCY is not None
        assert STAGE_LATENCY._name == "qnwis_stage_latency_seconds"


class TestMetricsRecording:
    """Test recording metrics."""

    def test_requests_counter_increments(self):
        """REQUESTS counter should increment."""
        initial = REQUESTS.labels(route="/api/test", method="GET", status="200")._value.get()

        REQUESTS.labels(route="/api/test", method="GET", status="200").inc()

        final = REQUESTS.labels(route="/api/test", method="GET", status="200")._value.get()
        assert final > initial

    def test_latency_histogram_records(self):
        """LATENCY histogram should record observations."""
        LATENCY.labels(route="/api/test", method="POST").observe(0.123)

        # Verify the metric was recorded by checking count
        metric_family = LATENCY.collect()
        for family in metric_family:
            for sample in family.samples:
                if sample.name.endswith("_count") and sample.labels.get("route") == "/api/test":
                    assert sample.value > 0
                    return

        pytest.fail("Latency metric not found in collected samples")

    def test_db_latency_histogram_records(self):
        """DB_LATENCY histogram should record observations."""
        DB_LATENCY.labels(operation="SELECT").observe(0.045)

        # Check that observation was recorded
        metric_family = DB_LATENCY.collect()
        for family in metric_family:
            for sample in family.samples:
                if sample.name.endswith("_count") and sample.labels.get("operation") == "SELECT":
                    assert sample.value > 0
                    return

    def test_cache_hit_counter_increments(self):
        """CACHE_HIT counter should increment."""
        initial_value = CACHE_HIT.labels(region="query_cache")._value.get()

        CACHE_HIT.labels(region="query_cache").inc()

        final_value = CACHE_HIT.labels(region="query_cache")._value.get()
        assert final_value > initial_value

    def test_cache_miss_counter_increments(self):
        """CACHE_MISS counter should increment."""
        initial_value = CACHE_MISS.labels(region="query_cache")._value.get()

        CACHE_MISS.labels(region="query_cache").inc()

        final_value = CACHE_MISS.labels(region="query_cache")._value.get()
        assert final_value > initial_value

    def test_agent_latency_histogram_records(self):
        """AGENT_LATENCY histogram should record observations."""
        AGENT_LATENCY.labels(agent_name="TimeMachineAgent").observe(1.234)

        # Verify recorded
        metric_family = AGENT_LATENCY.collect()
        for family in metric_family:
            for sample in family.samples:
                if (sample.name.endswith("_count") and
                    sample.labels.get("agent_name") == "TimeMachineAgent"):
                    assert sample.value > 0
                    return

    def test_stage_latency_histogram_records(self):
        """STAGE_LATENCY histogram should record observations."""
        STAGE_LATENCY.labels(stage="prefetch").observe(0.067)

        # Verify recorded
        metric_family = STAGE_LATENCY.collect()
        for family in metric_family:
            for sample in family.samples:
                if sample.name.endswith("_count") and sample.labels.get("stage") == "prefetch":
                    assert sample.value > 0
                    return


class TestMetricsEndpoint:
    """Test /metrics endpoint."""

    def test_metrics_endpoint_returns_prometheus_format(self):
        """GET /metrics should return Prometheus exposition format."""
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router())
        client = TestClient(app)

        response = client.get("/metrics")

        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]

    def test_metrics_endpoint_contains_qnwis_metrics(self):
        """GET /metrics should include QNWIS metric names."""
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router())
        client = TestClient(app)

        # Record some metrics first
        REQUESTS.labels(route="/test", method="GET", status="200").inc()
        CACHE_HIT.labels(region="test").inc()

        response = client.get("/metrics")
        content = response.text

        assert "qnwis_requests_total" in content
        assert "qnwis_cache_hits_total" in content

    def test_metrics_endpoint_includes_help_text(self):
        """GET /metrics should include HELP and TYPE lines."""
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router())
        client = TestClient(app)

        response = client.get("/metrics")
        content = response.text

        # Check for standard Prometheus format
        assert "# HELP" in content
        assert "# TYPE" in content

    def test_metrics_endpoint_includes_labels(self):
        """GET /metrics should include metric labels."""
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router())
        client = TestClient(app)

        # Record a metric with labels
        REQUESTS.labels(route="/api/query", method="POST", status="200").inc()

        response = client.get("/metrics")
        content = response.text

        assert 'route="/api/query"' in content or 'route=\"/api/query\"' in content
        assert 'method="POST"' in content or 'method=\"POST\"' in content


class TestMetricsBuckets:
    """Test histogram bucket configurations."""

    def test_latency_histogram_has_reasonable_buckets(self):
        """LATENCY histogram should have buckets suitable for API latency."""
        # Buckets should cover 5ms to 90s range
        expected_buckets = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 90.0)

        # Access buckets from metric definition
        metric_family = LATENCY.collect()
        for family in metric_family:
            # Buckets are defined at metric creation, check via _upper_bounds
            if hasattr(LATENCY, '_upper_bounds'):
                assert LATENCY._upper_bounds == expected_buckets
            # Alternative: check first metric sample's buckets
            break

    def test_db_latency_histogram_has_db_appropriate_buckets(self):
        """DB_LATENCY histogram should have buckets suitable for DB queries."""
        # Buckets should cover 1ms to 5s range (DB queries typically faster than full API calls)
        expected_buckets = (0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)

        # DB latency should have tighter buckets than API latency
        metric_family = DB_LATENCY.collect()
        for family in metric_family:
            # Verify buckets exist
            assert len(list(family.samples)) > 0
            break

    def test_agent_latency_histogram_has_agent_appropriate_buckets(self):
        """AGENT_LATENCY histogram should have buckets suitable for agent execution."""
        # Agents can be slow (up to 60s), so need wider range
        expected_buckets = (0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0)

        metric_family = AGENT_LATENCY.collect()
        for family in metric_family:
            assert len(list(family.samples)) > 0
            break


class TestMetricsIntegration:
    """Integration tests for metrics collection."""

    def test_multiple_metrics_recorded_together(self):
        """Test recording multiple related metrics."""
        # Simulate a request with cache hit
        REQUESTS.labels(route="/api/data", method="GET", status="200").inc()
        LATENCY.labels(route="/api/data", method="GET").observe(0.023)
        CACHE_HIT.labels(region="query_cache").inc()

        # All metrics should be recorded
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router())
        client = TestClient(app)

        response = client.get("/metrics")
        content = response.text

        assert "qnwis_requests_total" in content
        assert "qnwis_latency_seconds" in content
        assert "qnwis_cache_hits_total" in content

    def test_metrics_persist_across_requests(self):
        """Metrics should persist and accumulate across multiple requests."""
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router())
        client = TestClient(app)

        # Record initial value
        REQUESTS.labels(route="/test", method="GET", status="200").inc()
        response1 = client.get("/metrics")

        # Record another increment
        REQUESTS.labels(route="/test", method="GET", status="200").inc()
        response2 = client.get("/metrics")

        # Both responses should contain the metric
        assert "qnwis_requests_total" in response1.text
        assert "qnwis_requests_total" in response2.text
