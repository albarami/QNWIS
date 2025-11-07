"""
Unit tests for cache key generation and TTL policy.
"""

from datetime import datetime

from src.qnwis.cache.keys import make_cache_key, stable_params_hash


class TestStableParamsHash:
    """Test deterministic parameter hashing."""

    def test_identical_params_produce_same_hash(self) -> None:
        """Same parameters in different order produce identical hash."""
        params1 = {"a": 1, "b": 2, "c": 3}
        params2 = {"c": 3, "a": 1, "b": 2}
        assert stable_params_hash(params1) == stable_params_hash(params2)

    def test_nested_dict_sorted_keys(self) -> None:
        """Nested dictionaries are normalized with sorted keys."""
        params1 = {"outer": {"z": 1, "a": 2}}
        params2 = {"outer": {"a": 2, "z": 1}}
        assert stable_params_hash(params1) == stable_params_hash(params2)

    def test_date_normalization(self) -> None:
        """Datetime objects are normalized to ISO format."""
        dt = datetime(2024, 1, 15, 10, 30, 0)
        params1 = {"date": dt}
        # The hash should be deterministic
        hash1 = stable_params_hash(params1)
        assert len(hash1) == 16
        assert all(c in "0123456789abcdef" for c in hash1)

    def test_list_ordering_preserved(self) -> None:
        """List order is significant - different orders produce different hashes."""
        params1 = {"items": [1, 2, 3]}
        params2 = {"items": [3, 2, 1]}
        assert stable_params_hash(params1) != stable_params_hash(params2)

    def test_hash_length_is_16_chars(self) -> None:
        """Hash is truncated to 16 hex characters."""
        params = {"key": "value"}
        h = stable_params_hash(params)
        assert len(h) == 16
        assert all(c in "0123456789abcdef" for c in h)


class TestMakeCacheKey:
    """Test cache key generation with TTL policy."""

    def test_cache_key_format(self) -> None:
        """Cache key has correct format: qr:{op}:{query_id}:{hash}:{version}."""
        key, ttl = make_cache_key(
            "get_retention_by_company", "ret_comp_36m", {"sector": "Construction"}, "v1"
        )
        assert key.startswith("qr:get_retention_by_company:ret_comp_36m:")
        assert key.endswith(":v1")
        parts = key.split(":")
        assert len(parts) == 5
        assert parts[0] == "qr"
        assert parts[1] == "get_retention_by_company"
        assert parts[2] == "ret_comp_36m"
        assert len(parts[3]) == 16  # hash
        assert parts[4] == "v1"

    def test_ttl_policy_known_operation(self) -> None:
        """Known operations get their configured TTL."""
        key, ttl = make_cache_key(
            "get_retention_by_company", "qid", {}, "v1"
        )
        assert ttl == 24 * 3600  # 1 day

        key, ttl = make_cache_key(
            "get_employee_transitions", "qid", {}, "v1"
        )
        assert ttl == 12 * 3600  # 12 hours

    def test_ttl_policy_unknown_operation(self) -> None:
        """Unknown operations get default 24h TTL."""
        key, ttl = make_cache_key("unknown_operation", "qid", {}, "v1")
        assert ttl == 24 * 3600

    def test_same_params_same_key(self) -> None:
        """Identical parameters produce identical keys."""
        params1 = {"sector": "Construction", "year": 2023}
        params2 = {"year": 2023, "sector": "Construction"}
        key1, _ = make_cache_key("op", "qid", params1, "v1")
        key2, _ = make_cache_key("op", "qid", params2, "v1")
        assert key1 == key2

    def test_version_affects_key(self) -> None:
        """Different versions produce different keys."""
        params = {"key": "value"}
        key_v1, _ = make_cache_key("op", "qid", params, "v1")
        key_v2, _ = make_cache_key("op", "qid", params, "v2")
        assert key_v1 != key_v2
