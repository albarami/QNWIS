"""Tests for cache backend implementations."""

from __future__ import annotations

import time

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
