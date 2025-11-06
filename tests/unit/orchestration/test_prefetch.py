"""
Unit tests for prefetch functionality.

Tests the Prefetcher class for cache key deduplication, DataClient method
invocation, timeout handling, and security (bad function name raises clear error).
"""

import time
from unittest.mock import Mock

import pytest

from src.qnwis.data.deterministic.models import (
    Freshness,
    Provenance,
    QueryResult,
    Row,
)
from src.qnwis.orchestration.prefetch import (
    Prefetcher,
    PrefetchError,
    generate_cache_key,
)
from src.qnwis.orchestration.types import PrefetchSpec


class MockDataClient:
    """Mock DataClient for testing prefetch operations."""

    def __init__(self):
        """Initialize mock with call tracking."""
        self.calls = []

    def run(self, query_id: str) -> QueryResult:
        """Mock run method returning deterministic QueryResult."""
        self.calls.append(("run", {"query_id": query_id}))
        return QueryResult(
            query_id=query_id,
            rows=[Row(data={"value": 42})],
            unit="count",
            provenance=Provenance(
                source="csv",
                dataset_id="test_dataset",
                locator="test.csv",
                fields=["value"],
            ),
            freshness=Freshness(asof_date="2024-01-01"),
        )

    def get_metrics(self, sector: str, period: str) -> QueryResult:
        """Mock get_metrics method for testing multiple parameters."""
        self.calls.append(("get_metrics", {"sector": sector, "period": period}))
        return QueryResult(
            query_id="metrics_query",
            rows=[Row(data={"metric": sector, "value": 100})],
            unit="count",
            provenance=Provenance(
                source="csv",
                dataset_id="metrics_dataset",
                locator="metrics.csv",
                fields=["metric", "value"],
            ),
            freshness=Freshness(asof_date="2024-01-02"),
        )


class TestPrefetcher:
    """Test Prefetcher execution and error handling."""

    def test_prefetch_single_spec(self):
        """Test prefetching a single specification."""
        client = MockDataClient()
        prefetcher = Prefetcher(client)

        specs = [
            PrefetchSpec(
                fn="run",
                params={"query_id": "test_query"},
                cache_key="test_key",
            )
        ]

        cache = prefetcher.run(specs)

        assert len(cache) == 1
        assert "test_key" in cache
        assert cache["test_key"].query_id == "test_query"
        assert len(client.calls) == 1
        assert client.calls[0] == ("run", {"query_id": "test_query"})

    def test_prefetch_multiple_specs(self):
        """Test prefetching multiple specifications."""
        client = MockDataClient()
        prefetcher = Prefetcher(client)

        specs = [
            PrefetchSpec(
                fn="run",
                params={"query_id": "query1"},
                cache_key="key1",
            ),
            PrefetchSpec(
                fn="run",
                params={"query_id": "query2"},
                cache_key="key2",
            ),
        ]

        cache = prefetcher.run(specs)

        assert len(cache) == 2
        assert "key1" in cache
        assert "key2" in cache
        assert len(client.calls) == 2

    def test_prefetch_deduplicates_by_cache_key(self):
        """Test that duplicate cache_keys are skipped."""
        client = MockDataClient()
        prefetcher = Prefetcher(client)

        specs = [
            PrefetchSpec(
                fn="run",
                params={"query_id": "query1"},
                cache_key="duplicate_key",
            ),
            PrefetchSpec(
                fn="run",
                params={"query_id": "query2"},
                cache_key="duplicate_key",
            ),
            PrefetchSpec(
                fn="run",
                params={"query_id": "query3"},
                cache_key="unique_key",
            ),
        ]

        cache = prefetcher.run(specs)

        # Only 2 unique cache keys should be processed
        assert len(cache) == 2
        assert "duplicate_key" in cache
        assert "unique_key" in cache
        # Only 2 DataClient calls should be made
        assert len(client.calls) == 2
        # First duplicate should win
        assert cache["duplicate_key"].query_id == "query1"

    def test_prefetch_calls_correct_dataclient_method(self):
        """Test that prefetcher calls the specified DataClient method."""
        client = MockDataClient()
        prefetcher = Prefetcher(client)

        specs = [
            PrefetchSpec(
                fn="get_metrics",
                params={"sector": "health", "period": "2024-Q1"},
                cache_key="metrics_key",
            )
        ]

        cache = prefetcher.run(specs)

        assert len(cache) == 1
        assert "metrics_key" in cache
        assert len(client.calls) == 1
        assert client.calls[0] == (
            "get_metrics",
            {"sector": "health", "period": "2024-Q1"},
        )

    def test_prefetch_bad_function_name_raises_error(self):
        """Test that bad function names raise clear security error."""
        client = MockDataClient()
        prefetcher = Prefetcher(client)

        specs = [
            PrefetchSpec(
                fn="malicious_method",
                params={},
                cache_key="bad_key",
            )
        ]

        with pytest.raises(PrefetchError, match="DataClient has no method"):
            prefetcher.run(specs)

        # No calls should have been made
        assert len(client.calls) == 0

    def test_prefetch_non_callable_attribute_raises_error(self):
        """Test that non-callable attributes raise clear error."""
        client = MockDataClient()
        client.not_a_method = "I'm a string"  # type: ignore[attr-defined]
        prefetcher = Prefetcher(client)

        specs = [
            PrefetchSpec(
                fn="not_a_method",
                params={},
                cache_key="bad_key",
            )
        ]

        with pytest.raises(PrefetchError, match="is not callable"):
            prefetcher.run(specs)

    def test_prefetch_invalid_return_type_raises_error(self):
        """Test that methods not returning QueryResult raise error."""
        client = Mock()
        client.bad_method = Mock(return_value="not a QueryResult")
        prefetcher = Prefetcher(client)

        specs = [
            PrefetchSpec(
                fn="bad_method",
                params={},
                cache_key="key",
            )
        ]

        with pytest.raises(PrefetchError, match="returned str, expected QueryResult"):
            prefetcher.run(specs)

    def test_prefetch_timeout_raises_error(self):
        """Test that prefetch respects timeout and raises error."""
        # Note: Timeout is checked between specs, not during individual fetches
        # This test verifies timeout behavior with multiple slow specs
        client = MockDataClient()

        # Create a slow method that exceeds timeout when run multiple times
        def slow_run(query_id: str) -> QueryResult:
            time.sleep(0.03)  # 30ms per call
            return QueryResult(
                query_id=query_id,
                rows=[],
                unit="count",
                provenance=Provenance(
                    source="csv", dataset_id="test", locator="test.csv", fields=[]
                ),
                freshness=Freshness(asof_date="2024-01-01"),
            )

        client.run = slow_run  # type: ignore[method-assign]

        # Set timeout that will be exceeded after a few specs
        prefetcher = Prefetcher(client, timeout_ms=50)

        # Multiple specs will accumulate time and exceed timeout
        specs = [
            PrefetchSpec(fn="run", params={"query_id": f"query{i}"}, cache_key=f"key{i}")
            for i in range(10)
        ]

        with pytest.raises(PrefetchError, match="Prefetch timeout"):
            prefetcher.run(specs)

    def test_prefetch_method_exception_raises_prefetch_error(self):
        """Test that exceptions during method calls are wrapped in PrefetchError."""
        client = Mock()
        client.failing_method = Mock(side_effect=ValueError("Database error"))
        prefetcher = Prefetcher(client)

        specs = [
            PrefetchSpec(
                fn="failing_method",
                params={"arg": "value"},
                cache_key="key",
            )
        ]

        with pytest.raises(PrefetchError, match="Prefetch failed"):
            prefetcher.run(specs)

    def test_prefetch_empty_specs(self):
        """Test prefetching with empty specs list."""
        client = MockDataClient()
        prefetcher = Prefetcher(client)

        cache = prefetcher.run([])

        assert len(cache) == 0
        assert len(client.calls) == 0

    def test_prefetch_returns_correct_query_result_structure(self):
        """Test that cached results have correct QueryResult structure."""
        client = MockDataClient()
        prefetcher = Prefetcher(client)

        specs = [
            PrefetchSpec(
                fn="run",
                params={"query_id": "test_query"},
                cache_key="test_key",
            )
        ]

        cache = prefetcher.run(specs)
        result = cache["test_key"]

        assert isinstance(result, QueryResult)
        assert result.query_id == "test_query"
        assert len(result.rows) == 1
        assert result.rows[0].data == {"value": 42}
        assert result.provenance.dataset_id == "test_dataset"
        assert result.freshness.asof_date == "2024-01-01"

    def test_prefetch_sanitizes_params_for_logging(self):
        """Test that long parameter values are sanitized in logs."""
        client = MockDataClient()
        prefetcher = Prefetcher(client)

        long_value = "x" * 100
        sanitized = prefetcher._sanitize_params({"long_param": long_value})

        assert len(sanitized["long_param"]) == 53  # 50 + "..."
        assert sanitized["long_param"].endswith("...")

    def test_prefetch_does_not_sanitize_short_params(self):
        """Test that short parameters are not sanitized."""
        client = MockDataClient()
        prefetcher = Prefetcher(client)

        short_value = "short"
        sanitized = prefetcher._sanitize_params({"param": short_value})

        assert sanitized["param"] == "short"


class TestGenerateCacheKey:
    """Test cache key generation for determinism."""

    def test_generate_cache_key_deterministic(self):
        """Test that cache key generation is deterministic."""
        key1 = generate_cache_key("run", {"query_id": "test"})
        key2 = generate_cache_key("run", {"query_id": "test"})

        assert key1 == key2

    def test_generate_cache_key_different_fn(self):
        """Test that different function names produce different keys."""
        key1 = generate_cache_key("run", {"query_id": "test"})
        key2 = generate_cache_key("execute", {"query_id": "test"})

        assert key1 != key2

    def test_generate_cache_key_different_params(self):
        """Test that different parameters produce different keys."""
        key1 = generate_cache_key("run", {"query_id": "test1"})
        key2 = generate_cache_key("run", {"query_id": "test2"})

        assert key1 != key2

    def test_generate_cache_key_param_order_independent(self):
        """Test that parameter order doesn't affect cache key."""
        key1 = generate_cache_key("run", {"a": 1, "b": 2})
        key2 = generate_cache_key("run", {"b": 2, "a": 1})

        assert key1 == key2

    def test_generate_cache_key_format(self):
        """Test that cache key has expected format (16 hex chars)."""
        key = generate_cache_key("run", {"query_id": "test"})

        assert len(key) == 16
        assert all(c in "0123456789abcdef" for c in key)

    def test_generate_cache_key_complex_params(self):
        """Test cache key generation with complex parameter types."""
        params = {
            "string": "value",
            "int": 42,
            "float": 3.14,
            "list": [1, 2, 3],
            "dict": {"nested": "data"},
        }

        key1 = generate_cache_key("run", params)
        key2 = generate_cache_key("run", params)

        assert key1 == key2
        assert len(key1) == 16
