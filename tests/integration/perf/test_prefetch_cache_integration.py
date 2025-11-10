"""
Integration test for prefetch + cache interaction.

Tests that prefetch writes to cache and subsequent agent runs read from cache,
with proper cache statistics tracking.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.qnwis.agents.base import DataClient
from src.qnwis.cache.middleware import CachedDataClient
from src.qnwis.cache.redis_cache import DeterministicRedisCache
from src.qnwis.data.deterministic.models import (
    Freshness,
    Provenance,
    QueryResult,
    Row,
)
from src.qnwis.orchestration.prefetch import Prefetcher
from src.qnwis.orchestration.types import PrefetchSpec


@pytest.fixture
def mock_redis() -> MagicMock:
    """Mock Redis client."""
    redis_mock = MagicMock()
    redis_mock.get.return_value = None  # Default: cache miss
    redis_mock.info.return_value = {"version": "7.0"}
    return redis_mock


@pytest.fixture
def redis_cache(mock_redis: MagicMock) -> DeterministicRedisCache:
    """DeterministicRedisCache with mocked Redis."""
    with patch("src.qnwis.cache.redis_cache.redis.from_url", return_value=mock_redis):
        return DeterministicRedisCache(namespace="test")


@pytest.fixture
def mock_dataclient() -> MagicMock:
    """Mock DataClient with sample methods."""
    mock = MagicMock(spec=DataClient)

    # Setup sample return values
    def get_retention_by_company(**kwargs):  # type: ignore[no-untyped-def]
        return QueryResult(
            query_id="ret_comp_36m",
            rows=[
                Row(data={"sector": kwargs.get("sector", "Construction"), "retention": 18.5})
            ],
            unit="count",
            provenance=Provenance(
                source="csv",
                dataset_id="lmis_employees",
                locator="s3://bucket/employees.csv",
                fields=["sector", "retention"],
            ),
            freshness=Freshness(asof_date="2024-01-15"),
        )

    def get_salary_statistics(**kwargs):  # type: ignore[no-untyped-def]
        return QueryResult(
            query_id="sal_stats_sector",
            rows=[Row(data={"sector": kwargs.get("sector", "Finance"), "avg_salary": 12000})],
            unit="qar",
            provenance=Provenance(
                source="csv",
                dataset_id="lmis_salaries",
                locator="s3://bucket/salaries.csv",
                fields=["sector", "avg_salary"],
            ),
            freshness=Freshness(asof_date="2024-01-15"),
        )

    mock.get_retention_by_company = get_retention_by_company
    mock.get_salary_statistics = get_salary_statistics

    return mock


class TestPrefetchCacheIntegration:
    """Test prefetch writes to cache and subsequent reads use cache."""

    def test_prefetch_writes_to_cache(
        self,
        mock_dataclient: MagicMock,
        redis_cache: DeterministicRedisCache,
        mock_redis: MagicMock,
    ) -> None:
        """Prefetch executes queries and writes results to Redis cache."""
        specs: list[PrefetchSpec] = [
            {
                "fn": "get_retention_by_company",
                "params": {"sector": "Construction"},
                "cache_key": "ret_construction",
            },
            {
                "fn": "get_salary_statistics",
                "params": {"sector": "Finance"},
                "cache_key": "sal_finance",
            },
        ]

        prefetcher = Prefetcher(
            client=mock_dataclient, cache=redis_cache, cache_version="v1"
        )
        result_cache = prefetcher.run(specs)

        # Verify prefetcher returned results
        assert len(result_cache) == 2
        assert "ret_construction" in result_cache
        assert "sal_finance" in result_cache

        # Verify cache.set was called for each result
        assert mock_redis.set.call_count == 2

        # Verify results are correct
        ret_result = result_cache["ret_construction"]
        assert ret_result.query_id == "ret_comp_36m"
        assert ret_result.rows[0].data["sector"] == "Construction"

        sal_result = result_cache["sal_finance"]
        assert sal_result.query_id == "sal_stats_sector"
        assert sal_result.rows[0].data["sector"] == "Finance"

    def test_cached_client_reads_from_cache_after_prefetch(
        self,
        mock_dataclient: MagicMock,
        redis_cache: DeterministicRedisCache,
        mock_redis: MagicMock,
    ) -> None:
        """CachedDataClient reads from cache after prefetch."""
        # Step 1: Prefetch writes to cache
        specs: list[PrefetchSpec] = [
            {
                "fn": "get_retention_by_company",
                "params": {"sector": "Construction"},
                "cache_key": "ret_construction",
            }
        ]

        prefetcher = Prefetcher(
            client=mock_dataclient, cache=redis_cache, cache_version="v1"
        )
        prefetcher.run(specs)

        # Capture what was written to cache
        cache_call = mock_redis.set.call_args_list[0]
        cached_value = cache_call[0][1]

        # Step 2: Setup mock_redis.get to return cached value
        mock_redis.get.return_value = cached_value

        # Step 3: Create CachedDataClient with peek_query_id helper
        def peek_query_id(op: str, params: dict) -> str:  # type: ignore[type-arg]
            if op == "get_retention_by_company":
                return "ret_comp_36m"
            return "unknown"

        mock_dataclient.peek_query_id = peek_query_id

        cached_client = CachedDataClient(
            delegate=mock_dataclient, cache=redis_cache, version="v1"
        )

        # Step 4: Call through cached client
        result = cached_client.get_retention_by_company(sector="Construction")

        # Verify cache was checked
        assert mock_redis.get.call_count >= 1

        # Verify result came from cache (same query_id)
        assert result.query_id == "ret_comp_36m"

    def test_prefetch_deduplicates_by_cache_key(
        self,
        mock_dataclient: MagicMock,
        redis_cache: DeterministicRedisCache,
        mock_redis: MagicMock,
    ) -> None:
        """Prefetch deduplicates specs with same cache_key."""
        specs: list[PrefetchSpec] = [
            {
                "fn": "get_retention_by_company",
                "params": {"sector": "Construction"},
                "cache_key": "duplicate_key",
            },
            {
                "fn": "get_retention_by_company",
                "params": {"sector": "Finance"},
                "cache_key": "duplicate_key",
            },
        ]

        prefetcher = Prefetcher(
            client=mock_dataclient, cache=redis_cache, cache_version="v1"
        )
        result_cache = prefetcher.run(specs)

        # Only one result should be in cache
        assert len(result_cache) == 1
        assert "duplicate_key" in result_cache

        # Only one call to cache.set (deduplicated)
        assert mock_redis.set.call_count == 1

    def test_prefetch_timeout_raises_error(
        self,
        mock_dataclient: MagicMock,
        redis_cache: DeterministicRedisCache,
    ) -> None:
        """Prefetch raises PrefetchError when timeout is exceeded."""
        # Create a slow method
        import time

        from src.qnwis.orchestration.prefetch import PrefetchError

        def slow_method(**kwargs):  # type: ignore[no-untyped-def]
            time.sleep(0.1)  # 100ms
            return QueryResult(
                query_id="slow",
                rows=[],
                unit="count",
                provenance=Provenance(
                    source="csv",
                    dataset_id="test",
                    locator="path",
                    fields=[],
                ),
                freshness=Freshness(asof_date="2024-01-01"),
            )

        mock_dataclient.slow_operation = slow_method

        specs: list[PrefetchSpec] = [
            {"fn": "slow_operation", "params": {}, "cache_key": "slow1"},
            {"fn": "slow_operation", "params": {}, "cache_key": "slow2"},
        ]

        prefetcher = Prefetcher(
            client=mock_dataclient, cache=redis_cache, timeout_ms=50
        )

        with pytest.raises(PrefetchError, match="Prefetch timeout"):
            prefetcher.run(specs)

    def test_prefetch_invalid_method_raises_error(
        self,
        mock_dataclient: MagicMock,
        redis_cache: DeterministicRedisCache,
    ) -> None:
        """Prefetch raises PrefetchError for invalid method name."""
        from src.qnwis.orchestration.prefetch import PrefetchError

        specs: list[PrefetchSpec] = [
            {"fn": "nonexistent_method", "params": {}, "cache_key": "invalid"}
        ]

        prefetcher = Prefetcher(client=mock_dataclient, cache=redis_cache)

        with pytest.raises(PrefetchError, match="has no method"):
            prefetcher.run(specs)

    def test_prefetch_handles_cache_write_failure_gracefully(
        self,
        mock_dataclient: MagicMock,
        redis_cache: DeterministicRedisCache,
        mock_redis: MagicMock,
    ) -> None:
        """Prefetch continues even if cache write fails."""
        # Make cache.set raise an exception
        mock_redis.set.side_effect = Exception("Redis connection failed")

        specs: list[PrefetchSpec] = [
            {
                "fn": "get_retention_by_company",
                "params": {"sector": "Construction"},
                "cache_key": "ret_construction",
            }
        ]

        prefetcher = Prefetcher(client=mock_dataclient, cache=redis_cache)

        # Should not raise, just log warning
        result_cache = prefetcher.run(specs)

        # Result should still be in local cache
        assert len(result_cache) == 1
        assert "ret_construction" in result_cache

    def test_cached_client_falls_back_to_delegate_on_cache_miss(
        self,
        mock_dataclient: MagicMock,
        redis_cache: DeterministicRedisCache,
        mock_redis: MagicMock,
    ) -> None:
        """CachedDataClient falls back to delegate on cache miss."""
        # Setup cache miss
        mock_redis.get.return_value = None

        cached_client = CachedDataClient(
            delegate=mock_dataclient, cache=redis_cache, version="v1"
        )

        result = cached_client.get_retention_by_company(sector="Construction")

        # Verify delegate was called (cache miss)
        assert result.query_id == "ret_comp_36m"

        # Verify cache was populated after miss
        assert mock_redis.set.call_count == 1
