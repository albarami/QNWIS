"""
Unit tests for CachedDataClient middleware.
"""

from unittest.mock import MagicMock

import pytest

from src.qnwis.cache.middleware import (
    ALLOWLIST,
    NEGATIVE_CACHE_TTL_DEFAULT,
    CachedDataClient,
)
from src.qnwis.data.deterministic.models import (
    Freshness,
    Provenance,
    QueryResult,
    Row,
)


@pytest.fixture
def mock_delegate() -> MagicMock:
    """Mock DataClient delegate."""
    mock = MagicMock()
    # Setup a sample method
    mock.get_retention_by_company.return_value = QueryResult(
        query_id="ret_comp_36m",
        rows=[Row(data={"sector": "Construction", "retention": 18.5})],
        unit="count",
        provenance=Provenance(
            source="csv",
            dataset_id="lmis",
            locator="path",
            fields=["sector", "retention"],
        ),
        freshness=Freshness(asof_date="2024-01-15"),
    )
    return mock


@pytest.fixture
def mock_cache() -> MagicMock:
    """Mock Redis cache."""
    mock = MagicMock()
    mock.get.return_value = None  # Default: cache miss
    return mock


@pytest.fixture
def cached_client(mock_delegate: MagicMock, mock_cache: MagicMock) -> CachedDataClient:
    """CachedDataClient with mocks."""
    return CachedDataClient(mock_delegate, mock_cache)


class TestCachedDataClient:
    """Test cache middleware wrapper."""

    def test_non_allowlisted_method_bypasses_cache(
        self, cached_client: CachedDataClient, mock_delegate: MagicMock, mock_cache: MagicMock
    ) -> None:
        """Non-allowlisted methods pass through without caching."""
        # Add a non-allowlisted method
        mock_delegate.some_other_method.return_value = "result"

        result = cached_client.some_other_method()
        assert result == "result"
        mock_delegate.some_other_method.assert_called_once()
        mock_cache.get.assert_not_called()
        mock_cache.set.assert_not_called()

    def test_cache_miss_calls_delegate_and_sets_cache(
        self, cached_client: CachedDataClient, mock_delegate: MagicMock, mock_cache: MagicMock
    ) -> None:
        """Cache miss calls delegate and populates cache."""
        mock_cache.get.return_value = None  # Cache miss

        result = cached_client.get_retention_by_company(sector="Construction")

        # Delegate was called
        mock_delegate.get_retention_by_company.assert_called_once_with(
            sector="Construction"
        )
        # Cache was populated
        mock_cache.set.assert_called_once()
        assert result.query_id == "ret_comp_36m"

    def test_cache_hit_returns_immediately(
        self, cached_client: CachedDataClient, mock_delegate: MagicMock, mock_cache: MagicMock
    ) -> None:
        """Cache hit returns cached result without calling delegate."""
        cached_result = QueryResult(
            query_id="cached",
            rows=[Row(data={"cached": True})],
            unit="count",
            provenance=Provenance(
                source="csv",
                dataset_id="cache",
                locator="cache",
                fields=["cached"],
            ),
            freshness=Freshness(asof_date="2024-01-01"),
        )
        mock_cache.get.return_value = cached_result
        # Add peek_query_id helper
        mock_delegate.peek_query_id = lambda op, params: "ret_comp_36m"

        result = cached_client.get_retention_by_company(sector="Construction")

        # Delegate was NOT called
        mock_delegate.get_retention_by_company.assert_not_called()
        # Result is from cache
        assert result.query_id == "cached"
        assert result.rows[0].data["cached"] is True

    def test_allowlist_enforcement(self) -> None:
        """Only specific methods are in ALLOWLIST."""
        expected_methods = {
            "get_retention_by_company",
            "get_salary_statistics",
            "get_employee_transitions",
            "get_qatarization_rates",
            "get_gcc_indicator",
            "get_world_bank_indicator",
        }
        assert expected_methods == ALLOWLIST

    def test_non_callable_attribute_passthrough(
        self, cached_client: CachedDataClient, mock_delegate: MagicMock
    ) -> None:
        """Non-callable attributes pass through unchanged."""
        mock_delegate.some_property = "value"
        assert cached_client.some_property == "value"

    def test_negative_cache_ttl_applied_for_empty_results(
        self, cached_client: CachedDataClient, mock_delegate: MagicMock, mock_cache: MagicMock
    ) -> None:
        """Empty QueryResult uses negative cache TTL."""
        empty_result = QueryResult(
            query_id="ret_comp_empty",
            rows=[],
            unit="count",
            provenance=Provenance(
                source="csv",
                dataset_id="lmis",
                locator="path",
                fields=[],
            ),
            freshness=Freshness(asof_date="2024-01-01"),
        )
        mock_delegate.get_retention_by_company.return_value = empty_result

        cached_client.get_retention_by_company(sector="None")

        mock_cache.set.assert_called_once()
        ttl_used = mock_cache.set.call_args[0][2]
        assert ttl_used == NEGATIVE_CACHE_TTL_DEFAULT

    def test_missing_query_id_raises(
        self, cached_client: CachedDataClient, mock_delegate: MagicMock
    ) -> None:
        """Missing query_id raises descriptive error."""
        bad_result = QueryResult(
            query_id="",
            rows=[Row(data={"value": 1})],
            unit="count",
            provenance=Provenance(
                source="csv",
                dataset_id="bad",
                locator="path",
                fields=["value"],
            ),
            freshness=Freshness(asof_date="2024-02-01"),
        )
        mock_delegate.get_retention_by_company.return_value = bad_result

        with pytest.raises(ValueError, match="missing a valid query_id"):
            cached_client.get_retention_by_company(sector="Construction")
