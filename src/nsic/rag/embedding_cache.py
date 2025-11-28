"""
NSIC Embedding Cache with SHA256 Deterministic Hashing

This module provides deterministic caching for embeddings using SHA256 hashing.
The hash is computed from: sha256(text + model_version) for reproducibility.

Key features:
- Deterministic: Same input always produces same cache key
- Version-aware: Model version changes invalidate cache
- Thread-safe: Uses diskcache with proper locking
- GPU-accelerated: Supports CUDA tensor caching
"""

import hashlib
import json
import logging
from pathlib import Path
from typing import Optional, Union, List
import numpy as np

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

try:
    import diskcache
    DISKCACHE_AVAILABLE = True
except ImportError:
    DISKCACHE_AVAILABLE = False

logger = logging.getLogger(__name__)


class EmbeddingCache:
    """
    Deterministic embedding cache using SHA256 hashing.
    
    The cache key is computed as: sha256(text + model_name + model_version)
    This ensures:
    - Same text always gets same embedding (reproducibility)
    - Model updates invalidate old embeddings (correctness)
    - No collisions between different models (isolation)
    """
    
    def __init__(
        self,
        cache_dir: Optional[Union[str, Path]] = None,
        model_name: str = "hkunlp/instructor-xl",
        model_version: str = "1.0.0",
        max_size_gb: float = 10.0,
        eviction_policy: str = "least-recently-used",
    ):
        """
        Initialize the embedding cache.
        
        Args:
            cache_dir: Directory for cache storage. Defaults to ~/.cache/nsic/embeddings
            model_name: Name of the embedding model (used in hash)
            model_version: Version of the model (used in hash for invalidation)
            max_size_gb: Maximum cache size in gigabytes
            eviction_policy: Cache eviction policy (default: LRU)
        """
        if not DISKCACHE_AVAILABLE:
            raise ImportError("diskcache is required for EmbeddingCache. Install with: pip install diskcache")
        
        self.model_name = model_name
        self.model_version = model_version
        
        # Set up cache directory
        if cache_dir is None:
            cache_dir = Path.home() / ".cache" / "nsic" / "embeddings"
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize diskcache with size limit
        max_size_bytes = int(max_size_gb * 1024 * 1024 * 1024)
        self.cache = diskcache.Cache(
            str(self.cache_dir),
            size_limit=max_size_bytes,
            eviction_policy=eviction_policy,
        )
        
        # Stats tracking
        self._hits = 0
        self._misses = 0
        
        logger.info(
            f"EmbeddingCache initialized: dir={self.cache_dir}, "
            f"model={model_name}@{model_version}, max_size={max_size_gb}GB"
        )
    
    def _compute_cache_key(self, text: str) -> str:
        """
        Compute deterministic cache key using SHA256.
        
        The key is: sha256(text + model_name + model_version)
        
        Args:
            text: Input text to hash
            
        Returns:
            Hex string of SHA256 hash
        """
        # Normalize text (strip whitespace, ensure UTF-8)
        normalized_text = text.strip()
        
        # Create hash input: text + separator + model info
        hash_input = f"{normalized_text}\x00{self.model_name}\x00{self.model_version}"
        
        # Compute SHA256
        hash_bytes = hashlib.sha256(hash_input.encode('utf-8')).hexdigest()
        
        return hash_bytes
    
    def _compute_batch_keys(self, texts: List[str]) -> List[str]:
        """Compute cache keys for a batch of texts."""
        return [self._compute_cache_key(text) for text in texts]
    
    def get(self, text: str) -> Optional[np.ndarray]:
        """
        Get cached embedding for text.
        
        Args:
            text: Input text
            
        Returns:
            Cached embedding as numpy array, or None if not in cache
        """
        key = self._compute_cache_key(text)
        
        try:
            result = self.cache.get(key)
            if result is not None:
                self._hits += 1
                logger.debug(f"Cache HIT for key {key[:16]}...")
                return np.array(result)
            else:
                self._misses += 1
                logger.debug(f"Cache MISS for key {key[:16]}...")
                return None
        except Exception as e:
            logger.warning(f"Cache get error: {e}")
            self._misses += 1
            return None
    
    def get_batch(self, texts: List[str]) -> tuple[List[Optional[np.ndarray]], List[int]]:
        """
        Get cached embeddings for a batch of texts.
        
        Args:
            texts: List of input texts
            
        Returns:
            Tuple of (cached_embeddings, missing_indices)
            - cached_embeddings: List of embeddings (None for misses)
            - missing_indices: List of indices that need to be computed
        """
        results = []
        missing_indices = []
        
        for i, text in enumerate(texts):
            embedding = self.get(text)
            results.append(embedding)
            if embedding is None:
                missing_indices.append(i)
        
        return results, missing_indices
    
    def set(self, text: str, embedding: Union[np.ndarray, 'torch.Tensor']) -> bool:
        """
        Cache an embedding for text.
        
        Args:
            text: Input text (used to compute key)
            embedding: Embedding vector (numpy array or torch tensor)
            
        Returns:
            True if successfully cached, False otherwise
        """
        key = self._compute_cache_key(text)
        
        try:
            # Convert torch tensor to numpy if needed
            if TORCH_AVAILABLE and isinstance(embedding, torch.Tensor):
                embedding = embedding.cpu().numpy()
            
            # Store as list for JSON serialization compatibility
            self.cache.set(key, embedding.tolist())
            logger.debug(f"Cached embedding for key {key[:16]}...")
            return True
        except Exception as e:
            logger.warning(f"Cache set error: {e}")
            return False
    
    def set_batch(self, texts: List[str], embeddings: Union[np.ndarray, 'torch.Tensor']) -> int:
        """
        Cache embeddings for a batch of texts.
        
        Args:
            texts: List of input texts
            embeddings: Embedding matrix (N x D)
            
        Returns:
            Number of successfully cached embeddings
        """
        if TORCH_AVAILABLE and isinstance(embeddings, torch.Tensor):
            embeddings = embeddings.cpu().numpy()
        
        success_count = 0
        for i, text in enumerate(texts):
            if self.set(text, embeddings[i]):
                success_count += 1
        
        return success_count
    
    def contains(self, text: str) -> bool:
        """Check if text is in cache."""
        key = self._compute_cache_key(text)
        return key in self.cache
    
    def clear(self) -> None:
        """Clear all cached embeddings."""
        self.cache.clear()
        self._hits = 0
        self._misses = 0
        logger.info("Cache cleared")
    
    def get_stats(self) -> dict:
        """
        Get cache statistics.
        
        Returns:
            Dict with hits, misses, hit_rate, size_bytes, item_count
        """
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0.0
        
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": hit_rate,
            "size_bytes": self.cache.volume(),
            "item_count": len(self.cache),
            "model_name": self.model_name,
            "model_version": self.model_version,
        }
    
    def close(self) -> None:
        """Close the cache (releases file handles)."""
        self.cache.close()
        logger.info(f"Cache closed. Stats: {self.get_stats()}")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
    
    def __len__(self) -> int:
        return len(self.cache)
    
    def __contains__(self, text: str) -> bool:
        return self.contains(text)


def create_embedding_cache(
    model_name: str = "hkunlp/instructor-xl",
    model_version: str = "1.0.0",
    cache_dir: Optional[str] = None,
    max_size_gb: float = 10.0,
) -> EmbeddingCache:
    """
    Factory function to create an embedding cache.
    
    Args:
        model_name: Name of the embedding model
        model_version: Version string for cache invalidation
        cache_dir: Optional custom cache directory
        max_size_gb: Maximum cache size in GB
        
    Returns:
        Configured EmbeddingCache instance
    """
    return EmbeddingCache(
        cache_dir=cache_dir,
        model_name=model_name,
        model_version=model_version,
        max_size_gb=max_size_gb,
    )

