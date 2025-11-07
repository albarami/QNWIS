"""
Unit tests for Redis cache implementation.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.qnwis.cache.redis_cache import DeterministicRedisCache
from src.qnwis.data.deterministic.models import (
    Freshness,
    Provenance,
    QueryResult,
    Row,
)


@pytest.fixture
def mock_redis() -> MagicMock:
    """Mock Redis client."""
    return MagicMock()


@pytest.fixture
def cache(mock_redis: MagicMock) -> DeterministicRedisCache:
    """DeterministicRedisCache with mocked Redis."""
    with patch("src.qnwis.cache.redis_cache.redis.from_url", return_value=mock_redis):
        return DeterministicRedisCache(namespace="test")


@pytest.fixture
def sample_query_result() -> QueryResult:
    """Sample QueryResult for testing."""
    return QueryResult(
        query_id="test_query",
        rows=[Row(data={"sector": "Construction", "avg_retention": 18.5})],
        unit="count",
        provenance=Provenance(
            source="csv",
            dataset_id="lmis_employees",
            locator="s3://bucket/path",
            fields=["sector", "avg_retention"],
        ),
        freshness=Freshness(
            asof_date="2024-01-15",
            updated_at="2024-01-10T00:00:00",
        ),
    )


class TestDeterministicRedisCache:
    """Test Redis cache operations."""

    def test_namespace_prefix(self, cache: DeterministicRedisCache) -> None:
        """Keys are prefixed with namespace."""
        assert cache._ns("mykey") == "test:mykey"

    def test_set_and_get(
        self, cache: DeterministicRedisCache, mock_redis: MagicMock, sample_query_result: QueryResult
    ) -> None:
        """Set stores serialized QueryResult, get retrieves it."""
        import json

        cache.set("test_key", sample_query_result, 60)

        # Verify set was called with correct arguments
        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        assert call_args[0][0] == "test:test_key"
        stored_json = call_args[0][1]
        assert isinstance(stored_json, str)
        stored_data = json.loads(stored_json)
        assert stored_data["query_id"] == "test_query"
        assert call_args[1]["ex"] == 60

    def test_get_miss_returns_none(
        self, cache: DeterministicRedisCache, mock_redis: MagicMock
    ) -> None:
        """Cache miss returns None."""
        mock_redis.get.return_value = None
        result = cache.get("nonexistent")
        assert result is None
        mock_redis.get.assert_called_once_with("test:nonexistent")

    def test_get_hit_deserializes_query_result(
        self, cache: DeterministicRedisCache, mock_redis: MagicMock
    ) -> None:
        """Cache hit deserializes JSON to QueryResult."""
        import json

        cached_data = {
            "query_id": "cached_query",
            "rows": [{"data": {"value": 42}}],
            "unit": "count",
            "provenance": {
                "source": "csv",
                "dataset_id": "test",
                "locator": "path",
                "fields": ["value"],
            },
            "freshness": {"asof_date": "2024-01-01"},
            "warnings": [],
        }
        mock_redis.get.return_value = json.dumps(cached_data)

        result = cache.get("cached_key")
        assert result is not None
        assert isinstance(result, QueryResult)
        assert result.query_id == "cached_query"
        assert len(result.rows) == 1
        assert result.rows[0].data["value"] == 42

    def test_delete_prefix_no_keys(
        self, cache: DeterministicRedisCache, mock_redis: MagicMock
    ) -> None:
        """Delete prefix with no matching keys returns 0."""
        mock_redis.scan_iter.return_value = iter([])
        count = cache.delete_prefix("prefix")
        assert count == 0
        mock_redis.delete.assert_not_called()

    def test_delete_prefix_with_keys(
        self, cache: DeterministicRedisCache, mock_redis: MagicMock
    ) -> None:
        """Delete prefix removes all matching keys."""
        mock_redis.scan_iter.return_value = iter([b"test:prefix1", b"test:prefix2"])
        mock_redis.delete.return_value = 2

        count = cache.delete_prefix("prefix")
        assert count == 2
        mock_redis.scan_iter.assert_called_once_with("test:prefix*")
        mock_redis.delete.assert_called_once()

    def test_info_returns_redis_info(
        self, cache: DeterministicRedisCache, mock_redis: MagicMock
    ) -> None:
        """Info returns Redis INFO output."""
        mock_redis.info.return_value = {"version": "7.0"}
        info = cache.info()
        assert info["version"] == "7.0"
        mock_redis.info.assert_called_once()
