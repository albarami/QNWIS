"""
Unit tests for qnwis.perf.cache_tuning module.

Tests TTL heuristics, cache key generation, and caching decisions
for different operation types and result sizes.
"""

import pytest

from qnwis.perf.cache_tuning import cache_key, should_cache, ttl_for


class TestTTLCalculation:
    """Test adaptive TTL calculation."""

    def test_ttl_for_known_operation(self):
        """TTL should use operation-specific base for known operations."""
        # Static reference data - long TTL
        ttl = ttl_for("get_occupations", row_count=100)
        assert ttl == 3600  # 1 hour (base) * 1.0 (100 rows)

        # Dynamic data - short TTL
        ttl = ttl_for("get_job_postings", row_count=100)
        assert ttl == 360  # 300 (base) * 1.2 (100 rows)

        # Real-time data - very short TTL
        ttl = ttl_for("get_live_metrics", row_count=100)
        assert ttl == 60  # Clamped to min_ttl

    def test_ttl_for_unknown_operation_uses_base(self):
        """TTL should use default base for unknown operations."""
        ttl = ttl_for("unknown_operation", row_count=100, base=600)
        assert ttl == 600  # base * 1.0 (100 rows)

    def test_ttl_adjusts_for_small_result_sets(self):
        """Smaller result sets should have shorter TTL (may be volatile)."""
        # Small result (< 10 rows) → 0.8 multiplier
        ttl = ttl_for("get_salary_statistics", row_count=5)
        assert ttl == 720  # 900 (base) * 0.8

    def test_ttl_adjusts_for_normal_result_sets(self):
        """Normal result sets (10-99 rows) should use 1.0 multiplier."""
        # Normal result → 1.0 multiplier
        ttl = ttl_for("get_salary_statistics", row_count=50)
        assert ttl == 900  # 900 (base) * 1.0

    def test_ttl_adjusts_for_large_result_sets(self):
        """Larger result sets should have longer TTL (expensive to recompute)."""
        # Large result (100-999 rows) → 1.2 multiplier
        ttl = ttl_for("get_salary_statistics", row_count=500)
        assert ttl == 1080  # 900 (base) * 1.2

    def test_ttl_adjusts_for_very_large_result_sets(self):
        """Very large result sets (1000+ rows) should have longest TTL."""
        # Very large result (≥1000 rows) → 1.5 multiplier
        ttl = ttl_for("get_salary_statistics", row_count=2000)
        assert ttl == 1350  # 900 (base) * 1.5

    def test_ttl_clamped_to_minimum(self):
        """TTL should never go below min_ttl."""
        # Real-time data with small result
        ttl = ttl_for("get_live_metrics", row_count=5, min_ttl=60)
        assert ttl == 60  # 30 * 0.8 = 24, clamped to 60

    def test_ttl_clamped_to_maximum(self):
        """TTL should never exceed max_ttl."""
        # Static data with very large result
        ttl = ttl_for("get_occupations", row_count=10000, max_ttl=3600)
        assert ttl == 3600  # 3600 * 1.5 = 5400, clamped to 3600

    def test_ttl_custom_bounds(self):
        """TTL should respect custom min/max bounds."""
        ttl = ttl_for(
            "get_salary_statistics",
            row_count=100,
            min_ttl=120,
            max_ttl=600,
        )
        assert 120 <= ttl <= 600


class TestCacheKey:
    """Test deterministic cache key generation."""

    def test_cache_key_includes_operation_and_query_id(self):
        """Cache key should include operation and query_id."""
        key = cache_key("get_salary", "sal_001")
        assert key.startswith("get_salary:sal_001:")
        assert len(key) > len("get_salary:sal_001:")  # Has hash suffix

    def test_cache_key_includes_params(self):
        """Cache key should include parameters in hash."""
        key1 = cache_key("get_salary", "sal_001", {"year": "2024"})
        key2 = cache_key("get_salary", "sal_001", {"year": "2023"})
        assert key1 != key2  # Different params → different keys

    def test_cache_key_deterministic_param_order(self):
        """Cache key should be deterministic regardless of param order."""
        key1 = cache_key("get_data", "q1", {"a": "1", "b": "2", "c": "3"})
        key2 = cache_key("get_data", "q1", {"c": "3", "a": "1", "b": "2"})
        assert key1 == key2  # Same params → same key

    def test_cache_key_without_params(self):
        """Cache key should work without params."""
        key = cache_key("get_all", "all_001")
        assert key.startswith("get_all:all_001:")

    def test_cache_key_hash_collision_resistant(self):
        """Different inputs should produce different keys."""
        key1 = cache_key("op1", "q1", {"x": "1"})
        key2 = cache_key("op1", "q2", {"x": "1"})
        key3 = cache_key("op2", "q1", {"x": "1"})
        key4 = cache_key("op1", "q1", {"x": "2"})

        keys = {key1, key2, key3, key4}
        assert len(keys) == 4  # All different


class TestShouldCache:
    """Test caching decision heuristics."""

    def test_should_cache_expensive_queries(self):
        """Should cache queries that take >100ms."""
        assert should_cache("get_salary_statistics", row_count=500, duration_ms=250.0)
        assert should_cache("get_data", row_count=10, duration_ms=150.0)

    def test_should_cache_moderate_queries_with_decent_size(self):
        """Should cache moderate queries (>50ms) with ≥20 rows."""
        assert should_cache("get_data", row_count=50, duration_ms=75.0)
        assert should_cache("get_data", row_count=20, duration_ms=60.0)

    def test_should_not_cache_small_result_sets(self):
        """Should not cache very small result sets (<5 rows)."""
        assert not should_cache("get_single_record", row_count=1, duration_ms=200.0)
        assert not should_cache("get_few_records", row_count=3, duration_ms=150.0)

    def test_should_not_cache_fast_queries_with_small_results(self):
        """Should not cache fast queries with small-to-medium results."""
        assert not should_cache("get_data", row_count=10, duration_ms=30.0)
        assert not should_cache("get_data", row_count=15, duration_ms=40.0)

    def test_should_not_cache_excluded_operations(self):
        """Should not cache operations in exclusion list."""
        # Audit log - always fresh
        assert not should_cache("get_audit_log", row_count=1000, duration_ms=500.0)

        # User session - user-specific
        assert not should_cache("get_user_session", row_count=50, duration_ms=200.0)

        # Token validation - security-sensitive
        assert not should_cache("validate_token", row_count=10, duration_ms=100.0)

    def test_should_cache_large_expensive_results(self):
        """Should cache large, expensive query results."""
        assert should_cache("get_employment_trends", row_count=5000, duration_ms=800.0)

    def test_should_cache_boundary_cases(self):
        """Test boundary conditions for caching decisions."""
        # Just above expensive threshold
        assert should_cache("operation", row_count=10, duration_ms=101.0)

        # Just below expensive threshold, but above moderate with enough rows
        assert should_cache("operation", row_count=20, duration_ms=51.0)

        # Just below moderate threshold
        assert not should_cache("operation", row_count=20, duration_ms=49.0)

        # Exactly at row threshold
        assert not should_cache("operation", row_count=5, duration_ms=200.0)


class TestCacheTuningIntegration:
    """Integration tests for cache tuning components."""

    def test_realistic_workflow_expensive_query(self):
        """Test realistic workflow for expensive query caching."""
        operation = "get_salary_statistics"
        query_id = "sal_monthly_2024"
        params = {"year": "2024", "month": "11"}
        row_count = 1500
        duration_ms = 450.0

        # Should cache?
        assert should_cache(operation, row_count, duration_ms)

        # Generate cache key
        key = cache_key(operation, query_id, params)
        assert key.startswith("get_salary_statistics:sal_monthly_2024:")

        # Calculate TTL
        ttl = ttl_for(operation, row_count)
        assert ttl == 1350  # 900 (base) * 1.5 (large result)

    def test_realistic_workflow_fast_query(self):
        """Test realistic workflow for fast query that shouldn't be cached."""
        operation = "get_single_user"
        query_id = "user_123"
        params = {}
        row_count = 1
        duration_ms = 5.0

        # Should not cache
        assert not should_cache(operation, row_count, duration_ms)

    def test_realistic_workflow_moderate_query(self):
        """Test realistic workflow for moderate query."""
        operation = "get_job_postings"
        query_id = "jobs_active"
        params = {"sector": "IT"}
        row_count = 45
        duration_ms = 75.0

        # Should cache
        assert should_cache(operation, row_count, duration_ms)

        # Generate key
        key = cache_key(operation, query_id, params)

        # Calculate TTL - job postings are dynamic, so short TTL
        ttl = ttl_for(operation, row_count)
        assert ttl == 300  # 300 (base) * 1.0 (normal result size)
