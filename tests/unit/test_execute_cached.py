"""Tests for cached query execution."""

from __future__ import annotations

import json

import pytest

from src.qnwis.data.cache.backends import MemoryCacheBackend
from src.qnwis.data.deterministic import cache_access as cache_module
from src.qnwis.data.deterministic.cache_access import (
    COUNTERS,
    _key_for,
    execute_cached,
    invalidate_query,
)
from src.qnwis.data.deterministic.models import (
    Freshness,
    Provenance,
    QueryResult,
    QuerySpec,
    Row,
)


@pytest.fixture(autouse=True)
def reset_counters() -> None:
    COUNTERS["hits"] = 0
    COUNTERS["misses"] = 0
    COUNTERS["invalidations"] = 0


def test_key_for_deterministic():
    """Test that _key_for generates deterministic cache keys."""
    spec1 = QuerySpec(
        id="q",
        title="t",
        description="d",
        source="csv",
        params={"pattern": "x.csv"},
    )
    spec2 = QuerySpec(
        id="q",
        title="t",
        description="d",
        source="csv",
        params={"pattern": "x.csv"},
    )
    assert _key_for(spec1) == _key_for(spec2)


def test_key_for_different_params():
    """Test that different params produce different keys."""
    spec1 = QuerySpec(
        id="q", title="t", description="d", source="csv", params={"pattern": "a.csv"}
    )
    spec2 = QuerySpec(
        id="q", title="t", description="d", source="csv", params={"pattern": "b.csv"}
    )
    assert _key_for(spec1) != _key_for(spec2)


def test_execute_cached_uses_cache(monkeypatch):
    """Test that execute_cached uses cache on second call."""
    spec = QuerySpec(
        id="q",
        title="t",
        description="d",
        source="csv",
        expected_unit="percent",
        params={"pattern": "x.csv"},
    )

    class MockRegistry:
        def get(self, _):
            return spec

    reg = MockRegistry()
    called = {"n": 0}

    def fake_execute(query_id, registry, spec_override=None):
        called["n"] += 1
        return QueryResult(
            query_id="q",
            rows=[
                Row(
                    data={
                        "year": 2023,
                        "male_percent": 60.0,
                        "female_percent": 40.0,
                    }
                )
            ],
            unit="percent",
            provenance=Provenance(
                source="csv",
                dataset_id="x",
                locator="x.csv",
                fields=["year", "male_percent", "female_percent"],
            ),
            freshness=Freshness(asof_date="auto"),
        )

    # Create shared cache backend instance
    cache_backend = MemoryCacheBackend()

    monkeypatch.setattr(cache_module, "execute_uncached", fake_execute)
    # Force memory backend - return same instance every time
    monkeypatch.setattr(cache_module, "get_cache_backend", lambda: cache_backend)

    # First call populates cache
    _ = execute_cached("q", reg, ttl_s=300)
    # Second call hits cache
    out2 = execute_cached("q", reg, ttl_s=300)

    assert called["n"] == 1
    assert out2.rows[0].data["male_percent"] == 60.0
    assert COUNTERS["misses"] == 1
    assert COUNTERS["hits"] == 1


def test_execute_cached_invalidate_forces_refetch(monkeypatch):
    """Test that invalidate=True forces cache bypass."""
    spec = QuerySpec(
        id="q",
        title="t",
        description="d",
        source="csv",
        expected_unit="percent",
        params={"pattern": "x.csv"},
    )

    class MockRegistry:
        def get(self, _):
            return spec

    reg = MockRegistry()
    called = {"n": 0}

    def fake_execute(query_id, registry, spec_override=None):
        called["n"] += 1
        return QueryResult(
            query_id="q",
            rows=[Row(data={"year": 2023, "value": called["n"]})],
            unit="percent",
            provenance=Provenance(
                source="csv",
                dataset_id="x",
                locator="x.csv",
                fields=["year", "value"],
            ),
            freshness=Freshness(asof_date="auto"),
        )

    # Create shared cache backend instance
    cache_backend = MemoryCacheBackend()

    monkeypatch.setattr(cache_module, "execute_uncached", fake_execute)
    monkeypatch.setattr(cache_module, "get_cache_backend", lambda: cache_backend)

    # First call
    first = execute_cached("q", reg, ttl_s=300)
    assert first.rows[0].data["value"] == 1

    # Second call with invalidate should refetch
    out2 = execute_cached("q", reg, ttl_s=300, invalidate=True)
    assert out2.rows[0].data["value"] == 2
    assert called["n"] == 2
    assert COUNTERS["misses"] == 2
    assert COUNTERS["hits"] == 0
    assert COUNTERS["invalidations"] == 1


def test_execute_cached_ttl_zero_disables_cache(monkeypatch):
    """TTL of zero should bypass cache storage."""
    spec = QuerySpec(
        id="q",
        title="t",
        description="d",
        source="csv",
        expected_unit="percent",
        params={"pattern": "x.csv"},
    )

    class MockRegistry:
        def get(self, _):
            return spec

    reg = MockRegistry()
    calls = {"n": 0}

    def fake_execute(query_id, registry, spec_override=None):
        calls["n"] += 1
        return QueryResult(
            query_id="q",
            rows=[Row(data={"year": 2023, "value": calls["n"]})],
            unit="percent",
            provenance=Provenance(
                source="csv",
                dataset_id="x",
                locator="x.csv",
                fields=["year", "value"],
            ),
            freshness=Freshness(asof_date="auto"),
        )

    cache_backend = MemoryCacheBackend()
    monkeypatch.setattr(cache_module, "execute_uncached", fake_execute)
    monkeypatch.setattr(cache_module, "get_cache_backend", lambda: cache_backend)

    result1 = execute_cached("q", reg, ttl_s=0)
    result2 = execute_cached("q", reg, ttl_s=0)

    assert result1.rows[0].data["value"] == 1
    assert result2.rows[0].data["value"] == 2
    assert calls["n"] == 2
    assert cache_backend.get(_key_for(spec)) is None
    assert COUNTERS["misses"] == 2
    assert COUNTERS["hits"] == 0
    assert COUNTERS["invalidations"] == 0


def test_execute_cached_rejects_ttl_above_24h(monkeypatch):
    """TTL greater than 24 hours should be rejected."""
    spec = QuerySpec(
        id="q",
        title="t",
        description="d",
        source="csv",
        expected_unit="percent",
        params={"pattern": "x.csv"},
    )

    class MockRegistry:
        def get(self, _):
            return spec

    monkeypatch.setattr(cache_module, "get_cache_backend", lambda: MemoryCacheBackend())

    reg = MockRegistry()
    with pytest.raises(ValueError):
        execute_cached("q", reg, ttl_s=(24 * 60 * 60) + 1)


def test_execute_cached_compresses_large_payload(monkeypatch):
    """Large payloads are compressed with zlib in the cache."""
    spec = QuerySpec(
        id="q",
        title="t",
        description="d",
        source="csv",
        expected_unit="percent",
        params={"pattern": "x.csv"},
    )

    class MockRegistry:
        def get(self, _):
            return spec

    reg = MockRegistry()
    calls = {"n": 0}
    payload = "x" * (cache_module.COMPRESS_THRESHOLD_BYTES + 1024)

    def fake_execute(query_id, registry, spec_override=None):
        calls["n"] += 1
        return QueryResult(
            query_id="q",
            rows=[Row(data={"blob": payload})],
            unit="percent",
            provenance=Provenance(
                source="csv",
                dataset_id="x",
                locator="x.csv",
                fields=["blob"],
            ),
            freshness=Freshness(asof_date="auto"),
        )

    cache_backend = MemoryCacheBackend()
    monkeypatch.setattr(cache_module, "execute_uncached", fake_execute)
    monkeypatch.setattr(cache_module, "get_cache_backend", lambda: cache_backend)

    _ = execute_cached("q", reg, ttl_s=300)
    key = _key_for(spec)
    cached_raw = cache_backend.get(key)
    assert cached_raw is not None
    envelope = json.loads(cached_raw)
    assert envelope["_meta"]["content_encoding"] == "zlib"

    second = execute_cached("q", reg, ttl_s=300)
    assert second.rows[0].data["blob"] == payload
    assert calls["n"] == 1
    assert COUNTERS["misses"] == 1
    assert COUNTERS["hits"] == 1


def test_invalidate_query_helper(monkeypatch):
    """invalidate_query removes cached entries."""
    spec = QuerySpec(
        id="q",
        title="t",
        description="d",
        source="csv",
        expected_unit="percent",
        params={"pattern": "x.csv"},
    )

    class MockRegistry:
        def get(self, _):
            return spec

    reg = MockRegistry()

    def fake_execute(query_id, registry, spec_override=None):
        return QueryResult(
            query_id="q",
            rows=[Row(data={"value": 1})],
            unit="percent",
            provenance=Provenance(
                source="csv",
                dataset_id="x",
                locator="x.csv",
                fields=["value"],
            ),
            freshness=Freshness(asof_date="auto"),
        )

    cache_backend = MemoryCacheBackend()
    monkeypatch.setattr(cache_module, "execute_uncached", fake_execute)
    monkeypatch.setattr(cache_module, "get_cache_backend", lambda: cache_backend)

    execute_cached("q", reg, ttl_s=300)
    assert cache_backend.get(_key_for(spec)) is not None

    invalidate_query("q", reg)
    assert cache_backend.get(_key_for(spec)) is None
    assert COUNTERS["invalidations"] == 1
