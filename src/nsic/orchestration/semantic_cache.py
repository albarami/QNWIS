"""
NSIC Semantic Cache - Intelligent caching for similar queries.

Reduces computation by returning cached results for semantically similar queries.
Uses cosine similarity between query embeddings to determine cache hits.

Integration:
- Used by DualEngineOrchestrator before processing
- Leverages existing embeddings server (port 8005)
- Configurable similarity threshold (default 0.92)
"""

import logging
import time
import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """A cached query result with metadata."""
    query: str
    query_hash: str
    embedding: List[float]
    result: Dict[str, Any]
    confidence: float
    created_at: datetime
    accessed_at: datetime
    access_count: int = 0
    ttl_hours: float = 24.0

    def is_expired(self) -> bool:
        """Check if entry has expired."""
        expiry = self.created_at + timedelta(hours=self.ttl_hours)
        return datetime.now() > expiry

    def touch(self):
        """Update access metadata."""
        self.accessed_at = datetime.now()
        self.access_count += 1


@dataclass
class CacheStats:
    """Cache performance statistics."""
    total_queries: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    entries_added: int = 0
    entries_evicted: int = 0
    entries_expired: int = 0
    total_embedding_time_ms: float = 0.0
    total_similarity_time_ms: float = 0.0

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        if self.total_queries == 0:
            return 0.0
        return self.cache_hits / self.total_queries

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_queries": self.total_queries,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "hit_rate": f"{self.hit_rate:.2%}",
            "entries_added": self.entries_added,
            "entries_evicted": self.entries_evicted,
            "entries_expired": self.entries_expired,
            "avg_embedding_time_ms": (
                self.total_embedding_time_ms / max(self.total_queries, 1)
            ),
            "avg_similarity_time_ms": (
                self.total_similarity_time_ms / max(self.cache_hits + self.cache_misses, 1)
            ),
        }


class SemanticCache:
    """
    Semantic caching for similar query detection.

    Uses embedding similarity to find cached results for semantically similar queries.
    This avoids reprocessing the same question asked in slightly different ways.
    """

    def __init__(
        self,
        similarity_threshold: float = 0.92,
        max_entries: int = 1000,
        ttl_hours: float = 24.0,
        embeddings_url: str = "http://localhost:8005",
    ):
        """
        Initialize semantic cache.

        Args:
            similarity_threshold: Minimum cosine similarity for cache hit (0.92 recommended)
            max_entries: Maximum cache entries before LRU eviction
            ttl_hours: Time-to-live for cache entries
            embeddings_url: URL of embeddings server
        """
        self.similarity_threshold = similarity_threshold
        self.max_entries = max_entries
        self.ttl_hours = ttl_hours
        self.embeddings_url = embeddings_url

        self._cache: Dict[str, CacheEntry] = {}
        self._stats = CacheStats()

        logger.info(
            f"SemanticCache initialized: "
            f"threshold={similarity_threshold}, max_entries={max_entries}, ttl={ttl_hours}h"
        )

    async def get(self, query: str) -> Optional[Tuple[Dict[str, Any], float]]:
        """
        Check cache for a similar query.

        Args:
            query: The user query to check

        Returns:
            Tuple of (cached result, similarity score) or None if no hit
        """
        self._stats.total_queries += 1

        # Get embedding for query
        start_time = time.time()
        query_embedding = await self._get_embedding(query)
        self._stats.total_embedding_time_ms += (time.time() - start_time) * 1000

        if query_embedding is None:
            logger.warning("Could not get embedding for query, cache miss")
            self._stats.cache_misses += 1
            return None

        # Clean expired entries periodically
        if self._stats.total_queries % 100 == 0:
            self._clean_expired()

        # Search for similar cached queries
        start_time = time.time()
        best_match = self._find_best_match(query_embedding)
        self._stats.total_similarity_time_ms += (time.time() - start_time) * 1000

        if best_match:
            entry, similarity = best_match
            entry.touch()
            self._stats.cache_hits += 1
            logger.info(
                f"Cache HIT: similarity={similarity:.3f}, "
                f"original_query='{entry.query[:50]}...'"
            )
            return entry.result, similarity
        else:
            self._stats.cache_misses += 1
            return None

    async def put(
        self,
        query: str,
        result: Dict[str, Any],
        confidence: float = 0.8,
    ) -> bool:
        """
        Add a query result to the cache.

        Args:
            query: The original query
            result: The computed result to cache
            confidence: Confidence score of the result

        Returns:
            True if successfully cached
        """
        # Get embedding
        query_embedding = await self._get_embedding(query)
        if query_embedding is None:
            logger.warning("Could not get embedding for caching")
            return False

        # Evict if at capacity
        if len(self._cache) >= self.max_entries:
            self._evict_lru()

        # Create cache entry
        query_hash = self._hash_query(query)
        entry = CacheEntry(
            query=query,
            query_hash=query_hash,
            embedding=query_embedding,
            result=result,
            confidence=confidence,
            created_at=datetime.now(),
            accessed_at=datetime.now(),
            ttl_hours=self.ttl_hours,
        )

        self._cache[query_hash] = entry
        self._stats.entries_added += 1

        logger.debug(f"Cached query: '{query[:50]}...' (hash={query_hash[:8]})")
        return True

    def invalidate(self, query: str) -> bool:
        """
        Invalidate a cached entry.

        Args:
            query: The query to invalidate

        Returns:
            True if entry was found and removed
        """
        query_hash = self._hash_query(query)
        if query_hash in self._cache:
            del self._cache[query_hash]
            logger.debug(f"Invalidated cache entry: {query_hash[:8]}")
            return True
        return False

    def clear(self):
        """Clear all cache entries."""
        count = len(self._cache)
        self._cache.clear()
        logger.info(f"Cleared {count} cache entries")

    async def _get_embedding(self, text: str) -> Optional[List[float]]:
        """
        Get embedding for text from embeddings server.

        Args:
            text: Text to embed

        Returns:
            Embedding vector or None on failure
        """
        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.embeddings_url}/embed",
                    json={"text": text},
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("embedding", data.get("embeddings", [None])[0])
                    else:
                        logger.warning(f"Embeddings server returned {response.status}")
                        return None

        except ImportError:
            # Fallback to requests if aiohttp not available
            try:
                import requests
                response = requests.post(
                    f"{self.embeddings_url}/embed",
                    json={"text": text},
                    timeout=10,
                )
                if response.status_code == 200:
                    data = response.json()
                    return data.get("embedding", data.get("embeddings", [None])[0])
            except Exception as e:
                logger.warning(f"Embeddings request failed: {e}")
                return None

        except Exception as e:
            logger.warning(f"Failed to get embedding: {e}")
            return None

    def _find_best_match(
        self, query_embedding: List[float]
    ) -> Optional[Tuple[CacheEntry, float]]:
        """
        Find the best matching cache entry.

        Args:
            query_embedding: Embedding of the query

        Returns:
            Tuple of (best entry, similarity) or None if no match above threshold
        """
        best_entry = None
        best_similarity = 0.0

        for entry in self._cache.values():
            if entry.is_expired():
                continue

            similarity = self._cosine_similarity(query_embedding, entry.embedding)
            if similarity > best_similarity and similarity >= self.similarity_threshold:
                best_entry = entry
                best_similarity = similarity

        if best_entry:
            return best_entry, best_similarity
        return None

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """
        Calculate cosine similarity between two vectors.

        Args:
            a: First vector
            b: Second vector

        Returns:
            Cosine similarity (0 to 1)
        """
        if len(a) != len(b) or len(a) == 0:
            return 0.0

        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot_product / (norm_a * norm_b)

    def _hash_query(self, query: str) -> str:
        """Create a hash for the query."""
        return hashlib.sha256(query.encode()).hexdigest()

    def _evict_lru(self):
        """Evict least recently used entry."""
        if not self._cache:
            return

        # Find LRU entry
        lru_key = min(
            self._cache.keys(),
            key=lambda k: self._cache[k].accessed_at
        )

        del self._cache[lru_key]
        self._stats.entries_evicted += 1
        logger.debug(f"Evicted LRU entry: {lru_key[:8]}")

    def _clean_expired(self):
        """Remove expired entries."""
        expired_keys = [
            key for key, entry in self._cache.items()
            if entry.is_expired()
        ]

        for key in expired_keys:
            del self._cache[key]
            self._stats.entries_expired += 1

        if expired_keys:
            logger.debug(f"Cleaned {len(expired_keys)} expired entries")

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            **self._stats.to_dict(),
            "current_entries": len(self._cache),
            "max_entries": self.max_entries,
            "similarity_threshold": self.similarity_threshold,
            "ttl_hours": self.ttl_hours,
        }


def create_semantic_cache(
    similarity_threshold: float = 0.92,
    max_entries: int = 1000,
    ttl_hours: float = 24.0,
) -> SemanticCache:
    """Factory function to create SemanticCache."""
    return SemanticCache(
        similarity_threshold=similarity_threshold,
        max_entries=max_entries,
        ttl_hours=ttl_hours,
    )
