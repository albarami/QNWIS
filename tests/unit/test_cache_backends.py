"""Tests for cache backend implementations."""

from __future__ import annotations

import sys
import time
import types

from src.qnwis.data.cache import backends
from src.qnwis.data.cache.backends import MemoryCacheBackend


def test_memory_cache_set_get():
    """Test basic set and get operations."""
    c = MemoryCacheBackend()
    c.set("key1", "value1")
    assert c.get("key1") == "value1"


def test_memory_cache_get_missing():
    """Test get for non-existent key returns None."""
    c = MemoryCacheBackend()
    assert c.get("missing") is None


def test_memory_cache_set_get_ttl(monkeypatch):
    """Test TTL expiration."""
    c = MemoryCacheBackend()
    c.set("k", "v", ttl_s=1)
    assert c.get("k") == "v"

    # Simulate expiry
    base = time.time()
    monkeypatch.setattr(time, "time", lambda: base + 2)
    assert c.get("k") is None


def test_memory_cache_set_without_ttl():
    """Test that values without TTL persist."""
    c = MemoryCacheBackend()
    c.set("k", "v", ttl_s=None)
    assert c.get("k") == "v"


def test_memory_cache_delete():
    """Test delete operation."""
    c = MemoryCacheBackend()
    c.set("k", "v")
    assert c.get("k") == "v"
    c.delete("k")
    assert c.get("k") is None


def test_memory_cache_delete_missing():
    """Test that deleting non-existent key does not raise error."""
    c = MemoryCacheBackend()
    c.delete("missing")  # Should not raise


def test_memory_cache_zero_ttl():
    """Test that zero TTL is treated as no expiration."""
    c = MemoryCacheBackend()
    c.set("k", "v", ttl_s=0)
    assert c.get("k") == "v"


def test_redis_cache_backend_basic(monkeypatch):
    """Exercise Redis backend operations without a real Redis server."""
    store: dict[str, str] = {}
    calls: dict[str, tuple] = {}

    class FakeRedis:
        def __init__(self, host, port, decode_responses):
            calls["init"] = (host, port, decode_responses)

        def get(self, key: str):
            return store.get(key)

        def set(self, key: str, value: str):
            store[key] = value
            calls.setdefault("set", []).append((key, value))

        def setex(self, key: str, ttl: int, value: str):
            store[key] = value
            calls.setdefault("setex", []).append((key, ttl, value))

        def delete(self, key: str):
            store.pop(key, None)
            calls.setdefault("delete", []).append(key)

    fake_module = types.SimpleNamespace(Redis=FakeRedis)
    monkeypatch.setitem(sys.modules, "redis", fake_module)

    backend = backends.RedisCacheBackend("localhost", 6380)
    backend.set("a", "1", ttl_s=10)
    backend.set("b", "2", ttl_s=0)

    assert backend.get("a") == "1"
    assert backend.get("b") == "2"

    backend.delete("a")
    assert backend.get("a") is None

    assert calls["init"] == ("localhost", 6380, True)
    assert ("a", 10, "1") in calls["setex"]
    assert ("b", "2") in calls["set"]
    assert "a" in calls["delete"]


def test_get_cache_backend_redis_env(monkeypatch):
    """get_cache_backend returns Redis backend when env is configured."""
    store: dict[str, str] = {}

    class FakeRedis:
        def __init__(self, host, port, decode_responses):
            self._host = host
            self._port = port
            self._decode = decode_responses

        def get(self, key):
            return store.get(key)

        def set(self, key, value):
            store[key] = value

        def delete(self, key):
            store.pop(key, None)

    fake_module = types.SimpleNamespace(Redis=FakeRedis)
    monkeypatch.setitem(sys.modules, "redis", fake_module)
    monkeypatch.setenv("QNWIS_CACHE_BACKEND", "redis")
    monkeypatch.setenv("REDIS_HOST", "cache.local")
    monkeypatch.setenv("REDIS_PORT", "6385")

    backend = backends.get_cache_backend()
    assert isinstance(backend, backends.RedisCacheBackend)
    backend.set("x", "y")
    assert backend.get("x") == "y"

    # reset env to avoid side effects
    monkeypatch.delenv("QNWIS_CACHE_BACKEND", raising=False)
    monkeypatch.delenv("REDIS_HOST", raising=False)
    monkeypatch.delenv("REDIS_PORT", raising=False)
