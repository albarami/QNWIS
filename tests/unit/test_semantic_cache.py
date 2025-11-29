"""
Unit tests for NSIC Semantic Cache.

Tests cache functionality, similarity matching, and eviction policies.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch


class TestSemanticCache:
    """Test suite for SemanticCache."""

    def test_import_semantic_cache(self):
        """Test that semantic cache imports correctly."""
        from src.nsic.orchestration.semantic_cache import (
            SemanticCache,
            CacheEntry,
            CacheStats,
            create_semantic_cache,
        )
        assert SemanticCache is not None
        assert CacheEntry is not None
        assert create_semantic_cache is not None
        print("[PASS] Semantic cache imports successfully")

    def test_create_semantic_cache(self):
        """Test creating semantic cache with default settings."""
        from src.nsic.orchestration.semantic_cache import create_semantic_cache

        cache = create_semantic_cache()

        assert cache.similarity_threshold == 0.92
        assert cache.max_entries == 1000
        assert cache.ttl_hours == 24.0
        print("[PASS] Semantic cache created with defaults")

    def test_create_semantic_cache_custom(self):
        """Test creating semantic cache with custom settings."""
        from src.nsic.orchestration.semantic_cache import create_semantic_cache

        cache = create_semantic_cache(
            similarity_threshold=0.85,
            max_entries=500,
            ttl_hours=12.0,
        )

        assert cache.similarity_threshold == 0.85
        assert cache.max_entries == 500
        assert cache.ttl_hours == 12.0
        print("[PASS] Semantic cache created with custom settings")

    def test_cosine_similarity(self):
        """Test cosine similarity calculation."""
        from src.nsic.orchestration.semantic_cache import SemanticCache

        cache = SemanticCache()

        # Identical vectors
        a = [1.0, 0.0, 0.0]
        b = [1.0, 0.0, 0.0]
        assert cache._cosine_similarity(a, b) == 1.0

        # Orthogonal vectors
        a = [1.0, 0.0, 0.0]
        b = [0.0, 1.0, 0.0]
        assert cache._cosine_similarity(a, b) == 0.0

        # Similar vectors
        a = [1.0, 0.5, 0.0]
        b = [1.0, 0.6, 0.0]
        sim = cache._cosine_similarity(a, b)
        assert 0.95 < sim < 1.0  # Should be very similar

        print("[PASS] Cosine similarity works correctly")

    def test_hash_query(self):
        """Test query hashing."""
        from src.nsic.orchestration.semantic_cache import SemanticCache

        cache = SemanticCache()

        hash1 = cache._hash_query("What is the impact of oil prices?")
        hash2 = cache._hash_query("What is the impact of oil prices?")
        hash3 = cache._hash_query("What is the effect of oil prices?")

        # Same query = same hash
        assert hash1 == hash2

        # Different query = different hash
        assert hash1 != hash3

        # Hash is proper length (SHA256)
        assert len(hash1) == 64

        print("[PASS] Query hashing works correctly")

    def test_cache_entry_expiry(self):
        """Test cache entry expiration."""
        from src.nsic.orchestration.semantic_cache import CacheEntry

        # Create entry with 1 hour TTL
        entry = CacheEntry(
            query="test",
            query_hash="abc",
            embedding=[0.1, 0.2],
            result={"data": "test"},
            confidence=0.8,
            created_at=datetime.now(),
            accessed_at=datetime.now(),
            ttl_hours=1.0,
        )

        # Should not be expired
        assert not entry.is_expired()

        # Create already expired entry
        expired_entry = CacheEntry(
            query="test",
            query_hash="abc",
            embedding=[0.1, 0.2],
            result={"data": "test"},
            confidence=0.8,
            created_at=datetime.now() - timedelta(hours=2),
            accessed_at=datetime.now() - timedelta(hours=2),
            ttl_hours=1.0,
        )

        # Should be expired
        assert expired_entry.is_expired()

        print("[PASS] Cache entry expiration works correctly")

    def test_cache_entry_touch(self):
        """Test cache entry access tracking."""
        from src.nsic.orchestration.semantic_cache import CacheEntry

        entry = CacheEntry(
            query="test",
            query_hash="abc",
            embedding=[0.1, 0.2],
            result={"data": "test"},
            confidence=0.8,
            created_at=datetime.now(),
            accessed_at=datetime.now(),
            ttl_hours=1.0,
        )

        assert entry.access_count == 0

        entry.touch()
        assert entry.access_count == 1

        entry.touch()
        assert entry.access_count == 2

        print("[PASS] Cache entry touch tracking works")

    def test_stats_hit_rate(self):
        """Test cache statistics hit rate calculation."""
        from src.nsic.orchestration.semantic_cache import CacheStats

        stats = CacheStats()

        # No queries yet
        assert stats.hit_rate == 0.0

        # Add some queries
        stats.total_queries = 100
        stats.cache_hits = 25
        stats.cache_misses = 75

        assert stats.hit_rate == 0.25

        print("[PASS] Cache stats hit rate calculation works")

    def test_stats_to_dict(self):
        """Test cache statistics serialization."""
        from src.nsic.orchestration.semantic_cache import CacheStats

        stats = CacheStats(
            total_queries=100,
            cache_hits=30,
            cache_misses=70,
            entries_added=50,
        )

        stats_dict = stats.to_dict()

        assert stats_dict["total_queries"] == 100
        assert stats_dict["cache_hits"] == 30
        assert stats_dict["hit_rate"] == "30.00%"

        print("[PASS] Cache stats serialization works")

    @pytest.mark.asyncio
    async def test_cache_put_and_get_mock(self):
        """Test cache put and get with mocked embeddings."""
        from src.nsic.orchestration.semantic_cache import SemanticCache

        cache = SemanticCache()

        # Mock the embedding function
        test_embedding = [0.1, 0.2, 0.3, 0.4, 0.5]

        async def mock_get_embedding(text):
            return test_embedding

        cache._get_embedding = mock_get_embedding

        # Put an entry
        result = {"answer": "Test answer", "confidence": 0.85}
        success = await cache.put("What is the impact of oil prices?", result)
        assert success is True

        # Get the same query (should hit)
        cached = await cache.get("What is the impact of oil prices?")
        assert cached is not None
        cached_result, similarity = cached
        assert similarity == 1.0  # Exact same embedding
        assert cached_result["answer"] == "Test answer"

        print("[PASS] Cache put and get works with mocked embeddings")

    @pytest.mark.asyncio
    async def test_cache_miss_different_query(self):
        """Test cache miss for different queries."""
        from src.nsic.orchestration.semantic_cache import SemanticCache

        cache = SemanticCache(similarity_threshold=0.92)

        # Different embeddings for different queries
        embeddings = {
            "oil prices": [1.0, 0.0, 0.0],
            "weather patterns": [0.0, 1.0, 0.0],  # Orthogonal
        }

        async def mock_get_embedding(text):
            for key, emb in embeddings.items():
                if key in text.lower():
                    return emb
            return [0.5, 0.5, 0.0]

        cache._get_embedding = mock_get_embedding

        # Put an entry about oil
        await cache.put(
            "What is the impact of oil prices?",
            {"answer": "Oil impact analysis"},
        )

        # Try to get something about weather (should miss)
        cached = await cache.get("What are the weather patterns?")
        assert cached is None

        print("[PASS] Cache correctly misses for different queries")

    @pytest.mark.asyncio
    async def test_cache_similarity_threshold(self):
        """Test that similarity threshold is respected."""
        from src.nsic.orchestration.semantic_cache import SemanticCache

        cache = SemanticCache(similarity_threshold=0.95)

        # Similar but not identical embeddings
        base_embedding = [1.0, 0.0, 0.0, 0.0]

        call_count = [0]

        async def mock_get_embedding(text):
            call_count[0] += 1
            if call_count[0] == 1:
                return base_embedding  # First put
            elif call_count[0] == 2:
                return [0.98, 0.1, 0.0, 0.0]  # Similar (>0.95)
            else:
                return [0.8, 0.5, 0.0, 0.0]  # Less similar (<0.95)

        cache._get_embedding = mock_get_embedding

        # Put base entry
        await cache.put("original query", {"answer": "original"})

        # Get with similar embedding (should hit)
        cached = await cache.get("similar query")
        assert cached is not None

        # Reset and get with less similar (should miss)
        call_count[0] = 2
        cached = await cache.get("different query")
        assert cached is None

        print("[PASS] Similarity threshold is respected")

    def test_lru_eviction(self):
        """Test LRU eviction when cache is full."""
        from src.nsic.orchestration.semantic_cache import SemanticCache, CacheEntry

        cache = SemanticCache(max_entries=3)

        # Manually add entries with different access times
        now = datetime.now()

        # hash_0: 3 hours ago (oldest - LRU)
        # hash_1: 1 hour ago (most recent)
        # hash_2: 2 hours ago
        for i, offset in enumerate([3, 1, 2]):
            entry = CacheEntry(
                query=f"query_{i}",
                query_hash=f"hash_{i}",
                embedding=[float(i)],
                result={"id": i},
                confidence=0.8,
                created_at=now,
                accessed_at=now - timedelta(hours=offset),
                ttl_hours=24.0,
            )
            cache._cache[f"hash_{i}"] = entry

        # Evict LRU
        cache._evict_lru()

        # Entry 0 (offset=3, oldest access time) should be evicted
        assert "hash_0" not in cache._cache
        assert "hash_1" in cache._cache
        assert "hash_2" in cache._cache

        print("[PASS] LRU eviction works correctly")

    def test_clean_expired(self):
        """Test cleaning of expired entries."""
        from src.nsic.orchestration.semantic_cache import SemanticCache, CacheEntry

        cache = SemanticCache()

        now = datetime.now()

        # Add valid entry
        valid_entry = CacheEntry(
            query="valid",
            query_hash="valid_hash",
            embedding=[1.0],
            result={"valid": True},
            confidence=0.8,
            created_at=now,
            accessed_at=now,
            ttl_hours=24.0,
        )
        cache._cache["valid_hash"] = valid_entry

        # Add expired entry
        expired_entry = CacheEntry(
            query="expired",
            query_hash="expired_hash",
            embedding=[2.0],
            result={"valid": False},
            confidence=0.8,
            created_at=now - timedelta(hours=48),
            accessed_at=now - timedelta(hours=48),
            ttl_hours=24.0,
        )
        cache._cache["expired_hash"] = expired_entry

        # Clean expired
        cache._clean_expired()

        # Valid should remain, expired should be gone
        assert "valid_hash" in cache._cache
        assert "expired_hash" not in cache._cache

        print("[PASS] Expired entry cleaning works")

    def test_cache_get_stats(self):
        """Test cache statistics retrieval."""
        from src.nsic.orchestration.semantic_cache import SemanticCache

        cache = SemanticCache(
            similarity_threshold=0.92,
            max_entries=500,
            ttl_hours=12.0,
        )

        stats = cache.get_stats()

        assert stats["similarity_threshold"] == 0.92
        assert stats["max_entries"] == 500
        assert stats["ttl_hours"] == 12.0
        assert stats["current_entries"] == 0
        assert "hit_rate" in stats

        print("[PASS] Cache stats retrieval works")

    def test_invalidate(self):
        """Test cache entry invalidation."""
        from src.nsic.orchestration.semantic_cache import SemanticCache, CacheEntry

        cache = SemanticCache()

        # Add an entry directly
        entry = CacheEntry(
            query="test query",
            query_hash=cache._hash_query("test query"),
            embedding=[1.0],
            result={"data": "test"},
            confidence=0.8,
            created_at=datetime.now(),
            accessed_at=datetime.now(),
            ttl_hours=24.0,
        )
        cache._cache[entry.query_hash] = entry

        # Invalidate
        result = cache.invalidate("test query")
        assert result is True
        assert entry.query_hash not in cache._cache

        # Invalidate non-existent
        result = cache.invalidate("non-existent")
        assert result is False

        print("[PASS] Cache invalidation works")

    def test_clear(self):
        """Test clearing all cache entries."""
        from src.nsic.orchestration.semantic_cache import SemanticCache, CacheEntry

        cache = SemanticCache()

        # Add some entries
        for i in range(5):
            entry = CacheEntry(
                query=f"query_{i}",
                query_hash=f"hash_{i}",
                embedding=[float(i)],
                result={"id": i},
                confidence=0.8,
                created_at=datetime.now(),
                accessed_at=datetime.now(),
                ttl_hours=24.0,
            )
            cache._cache[f"hash_{i}"] = entry

        assert len(cache._cache) == 5

        cache.clear()

        assert len(cache._cache) == 0

        print("[PASS] Cache clear works")


if __name__ == "__main__":
    import sys

    test = TestSemanticCache()

    # Run sync tests
    test.test_import_semantic_cache()
    test.test_create_semantic_cache()
    test.test_create_semantic_cache_custom()
    test.test_cosine_similarity()
    test.test_hash_query()
    test.test_cache_entry_expiry()
    test.test_cache_entry_touch()
    test.test_stats_hit_rate()
    test.test_stats_to_dict()
    test.test_lru_eviction()
    test.test_clean_expired()
    test.test_cache_get_stats()
    test.test_invalidate()
    test.test_clear()

    # Run async tests
    asyncio.run(test.test_cache_put_and_get_mock())
    asyncio.run(test.test_cache_miss_different_query())
    asyncio.run(test.test_cache_similarity_threshold())

    print("\n" + "=" * 50)
    print("ALL SEMANTIC CACHE TESTS PASSED")
    print("=" * 50)
