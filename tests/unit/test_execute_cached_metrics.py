"""Tests for cache metrics, compression, TTL edges, and invalidation."""

from __future__ import annotations

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


def _fake_result(rows=50, year=2022):
    """Create a fake query result with specified number of rows."""
    return QueryResult(
        query_id="q",
        rows=[Row(data={"year": year, "v": i}) for i in range(rows)],
        unit="count",
        provenance=Provenance(
            source="csv",
            dataset_id="x",
            locator="x.csv",
            fields=["year", "v"],
        ),
        freshness=Freshness(asof_date="auto"),
    )


def test_cache_hit_miss_and_invalidate(monkeypatch):
    """Test cache hit/miss counters and invalidate_query helper."""
    # Reset counters
    COUNTERS["hits"] = 0
    COUNTERS["misses"] = 0
    COUNTERS["invalidations"] = 0

    spec = QuerySpec(
        id="q",
        title="t",
        description="d",
        source="csv",
        params={"pattern": "x.csv"},
    )
    reg = type("R", (object,), {"get": lambda self, _: spec})()
    store = MemoryCacheBackend()
    calls = {"n": 0}

    def fake_uncached(qid, r, spec_override=None):
        calls["n"] += 1
        return _fake_result(rows=5)

    monkeypatch.setattr(cache_module, "execute_uncached", fake_uncached)
    monkeypatch.setattr(cache_module, "get_cache_backend", lambda: store)

    # miss -> populate
    _ = execute_cached("q", reg, ttl_s=300)
    assert COUNTERS["misses"] == 1
    assert COUNTERS["hits"] == 0

    # hit
    r2 = execute_cached("q", reg, ttl_s=300)
    assert COUNTERS["misses"] == 1
    assert COUNTERS["hits"] == 1

    # invalidate forces refetch
    invalidate_query("q", reg)
    r3 = execute_cached("q", reg, ttl_s=300)
    assert COUNTERS["misses"] == 2
    assert COUNTERS["hits"] == 1

    assert calls["n"] == 2
    assert len(r2.rows) == 5 and len(r3.rows) == 5
    assert COUNTERS["invalidations"] == 1


def test_cache_compression_large_payload(monkeypatch):
    """Large payloads trigger compression path (>=8KB)."""
    # Reset counters
    COUNTERS["hits"] = 0
    COUNTERS["misses"] = 0
    COUNTERS["invalidations"] = 0

    spec = QuerySpec(
        id="q",
        title="t",
        description="d",
        source="csv",
        params={"pattern": "x.csv"},
    )
    reg = type("R", (object,), {"get": lambda self, _: spec})()
    store = MemoryCacheBackend()

    def fake_uncached(qid, r, spec_override=None):
        # many rows to exceed compression threshold
        return _fake_result(rows=500, year=2020)

    monkeypatch.setattr(cache_module, "execute_uncached", fake_uncached)
    monkeypatch.setattr(cache_module, "get_cache_backend", lambda: store)

    r = execute_cached("q", reg, ttl_s=300)
    assert r.rows and r.rows[0].data["year"] == 2020
    assert len(r.rows) == 500

    # Verify it cached and can be retrieved
    r2 = execute_cached("q", reg, ttl_s=300)
    assert len(r2.rows) == 500
    assert COUNTERS["hits"] == 1
    assert COUNTERS["invalidations"] == 0


def test_ttl_zero_disables_caching(monkeypatch):
    """TTL of zero bypasses cache storage."""
    # Reset counters
    COUNTERS["hits"] = 0
    COUNTERS["misses"] = 0
    COUNTERS["invalidations"] = 0

    spec = QuerySpec(
        id="q",
        title="t",
        description="d",
        source="csv",
        params={"pattern": "x.csv"},
    )
    reg = type("R", (object,), {"get": lambda self, _: spec})()
    store = MemoryCacheBackend()
    calls = {"n": 0}

    def fake_uncached(qid, r, spec_override=None):
        calls["n"] += 1
        return _fake_result()

    monkeypatch.setattr(cache_module, "execute_uncached", fake_uncached)
    monkeypatch.setattr(cache_module, "get_cache_backend", lambda: store)

    execute_cached("q", reg, ttl_s=0)
    execute_cached("q", reg, ttl_s=0)

    # Both calls should miss and execute
    assert calls["n"] == 2
    assert COUNTERS["misses"] == 2
    assert COUNTERS["hits"] == 0
    # Verify nothing cached
    assert store.get(_key_for(spec)) is None
    assert COUNTERS["invalidations"] == 0


def test_ttl_capping_24h(monkeypatch):
    """TTL greater than 24 hours raises ValueError."""
    spec = QuerySpec(
        id="q",
        title="t",
        description="d",
        source="csv",
        params={"pattern": "x.csv"},
    )
    reg = type("R", (object,), {"get": lambda self, _: spec})()
    monkeypatch.setattr(cache_module, "get_cache_backend", lambda: MemoryCacheBackend())

    try:
        execute_cached("q", reg, ttl_s=(24 * 60 * 60) + 1)
        raise AssertionError("Should have raised ValueError for TTL > 24h")
    except ValueError as e:
        assert "24 hours" in str(e)


def test_ttl_none_stores_without_expiration(monkeypatch):
    """TTL of None stores result without expiration."""
    # Reset counters
    COUNTERS["hits"] = 0
    COUNTERS["misses"] = 0

    spec = QuerySpec(
        id="q",
        title="t",
        description="d",
        source="csv",
        params={"pattern": "x.csv"},
    )
    reg = type("R", (object,), {"get": lambda self, _: spec})()
    store = MemoryCacheBackend()

    def fake_uncached(qid, r, spec_override=None):
        return _fake_result(rows=3)

    monkeypatch.setattr(cache_module, "execute_uncached", fake_uncached)
    monkeypatch.setattr(cache_module, "get_cache_backend", lambda: store)

    r1 = execute_cached("q", reg, ttl_s=None)
    r2 = execute_cached("q", reg, ttl_s=None)

    assert len(r1.rows) == 3
    assert len(r2.rows) == 3
    assert COUNTERS["misses"] == 1
    assert COUNTERS["hits"] == 1
    assert COUNTERS["invalidations"] == 0
