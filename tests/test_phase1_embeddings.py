"""
Phase 1: Premium Embeddings + Cache Tests

These tests verify the embedding cache and premium embedding service.
ALL tests must pass before proceeding to Phase 2.

Run with: pytest tests/test_phase1_embeddings.py -v
"""

import pytest
import sys
import tempfile
import shutil
import hashlib
from pathlib import Path
import numpy as np

# Add src to path
src_path = Path(__file__).parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))


class TestEmbeddingCache:
    """Test the deterministic embedding cache."""
    
    def test_cache_import(self):
        """Cache module must be importable."""
        from nsic.rag.embedding_cache import EmbeddingCache, create_embedding_cache
        assert EmbeddingCache is not None
        assert create_embedding_cache is not None
    
    def test_cache_creation(self):
        """Cache can be created with default settings."""
        from nsic.rag.embedding_cache import EmbeddingCache
        
        tmpdir = tempfile.mkdtemp()
        try:
            cache = EmbeddingCache(cache_dir=tmpdir)
            assert cache is not None
            assert cache.model_name == "hkunlp/instructor-xl"
            cache.close()
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    
    def test_cache_key_deterministic(self):
        """Same text must produce same cache key (SHA256 determinism)."""
        from nsic.rag.embedding_cache import EmbeddingCache
        
        tmpdir = tempfile.mkdtemp()
        try:
            cache = EmbeddingCache(cache_dir=tmpdir)
            
            text = "What is the unemployment rate in Qatar?"
            key1 = cache._compute_cache_key(text)
            key2 = cache._compute_cache_key(text)
            
            assert key1 == key2, "Same text must produce same key"
            assert len(key1) == 64, "SHA256 produces 64 hex chars"
            
            cache.close()
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    
    def test_cache_key_different_texts(self):
        """Different texts must produce different cache keys."""
        from nsic.rag.embedding_cache import EmbeddingCache
        
        tmpdir = tempfile.mkdtemp()
        try:
            cache = EmbeddingCache(cache_dir=tmpdir)
            
            key1 = cache._compute_cache_key("unemployment rate")
            key2 = cache._compute_cache_key("employment rate")
            
            assert key1 != key2, "Different texts must produce different keys"
            
            cache.close()
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    
    def test_cache_key_version_aware(self):
        """Different model versions must produce different cache keys."""
        from nsic.rag.embedding_cache import EmbeddingCache
        
        tmpdir = tempfile.mkdtemp()
        try:
            cache_v1 = EmbeddingCache(cache_dir=tmpdir, model_version="1.0.0")
            cache_v2 = EmbeddingCache(cache_dir=tmpdir, model_version="2.0.0")
            
            text = "test text"
            key_v1 = cache_v1._compute_cache_key(text)
            key_v2 = cache_v2._compute_cache_key(text)
            
            assert key_v1 != key_v2, "Different versions must produce different keys"
            
            cache_v1.close()
            cache_v2.close()
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    
    def test_cache_set_get(self):
        """Cache can store and retrieve embeddings."""
        from nsic.rag.embedding_cache import EmbeddingCache
        
        tmpdir = tempfile.mkdtemp()
        try:
            cache = EmbeddingCache(cache_dir=tmpdir)
            
            text = "test embedding"
            embedding = np.random.randn(768).astype(np.float32)
            
            # Set
            success = cache.set(text, embedding)
            assert success, "Cache set should succeed"
            
            # Get
            retrieved = cache.get(text)
            assert retrieved is not None, "Cache get should return embedding"
            np.testing.assert_array_almost_equal(
                embedding, retrieved, decimal=5,
                err_msg="Retrieved embedding should match original"
            )
            
            cache.close()
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    
    def test_cache_miss(self):
        """Cache returns None for missing keys."""
        from nsic.rag.embedding_cache import EmbeddingCache
        
        tmpdir = tempfile.mkdtemp()
        try:
            cache = EmbeddingCache(cache_dir=tmpdir)
            
            result = cache.get("nonexistent text")
            assert result is None, "Missing key should return None"
            
            cache.close()
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    
    def test_cache_batch_operations(self):
        """Cache batch operations work correctly."""
        from nsic.rag.embedding_cache import EmbeddingCache
        
        tmpdir = tempfile.mkdtemp()
        try:
            cache = EmbeddingCache(cache_dir=tmpdir)
            
            texts = ["text 1", "text 2", "text 3"]
            embeddings = np.random.randn(3, 768).astype(np.float32)
            
            # Set batch
            count = cache.set_batch(texts, embeddings)
            assert count == 3, "All embeddings should be cached"
            
            # Get batch
            results, missing = cache.get_batch(texts)
            assert len(missing) == 0, "No embeddings should be missing"
            assert len(results) == 3, "All embeddings should be returned"
            
            cache.close()
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    
    def test_cache_stats(self):
        """Cache tracks hit/miss statistics."""
        from nsic.rag.embedding_cache import EmbeddingCache
        
        tmpdir = tempfile.mkdtemp()
        try:
            cache = EmbeddingCache(cache_dir=tmpdir)
            
            # Generate a miss
            cache.get("nonexistent")
            
            # Set and hit
            cache.set("test", np.zeros(768))
            cache.get("test")
            
            stats = cache.get_stats()
            assert stats["hits"] == 1
            assert stats["misses"] == 1
            assert stats["hit_rate"] == 0.5
            
            cache.close()
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    
    def test_cache_contains(self):
        """Cache contains check works."""
        from nsic.rag.embedding_cache import EmbeddingCache
        
        tmpdir = tempfile.mkdtemp()
        try:
            cache = EmbeddingCache(cache_dir=tmpdir)
            
            text = "cached text"
            assert text not in cache
            
            cache.set(text, np.zeros(768))
            assert text in cache
            
            cache.close()
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


class TestPremiumEmbeddings:
    """Test the premium embedding service."""
    
    def test_service_import(self):
        """Embedding service must be importable."""
        from nsic.rag.premium_embeddings import (
            PremiumEmbeddingService,
            get_embedding_service,
            encode,
        )
        assert PremiumEmbeddingService is not None
        assert get_embedding_service is not None
        assert encode is not None
    
    def test_task_instructions(self):
        """Task instructions are defined."""
        from nsic.rag.premium_embeddings import TASK_INSTRUCTIONS
        
        assert "query" in TASK_INSTRUCTIONS
        assert "document" in TASK_INSTRUCTIONS
        assert "passage" in TASK_INSTRUCTIONS
        assert "default" in TASK_INSTRUCTIONS
    
    @pytest.mark.skipif(
        not pytest.importorskip("sentence_transformers", reason="sentence-transformers not installed"),
        reason="sentence-transformers required"
    )
    def test_service_creation_with_smaller_model(self):
        """Service can be created with a smaller model for testing."""
        from nsic.rag.premium_embeddings import PremiumEmbeddingService
        
        # Use smaller model for faster testing
        service = PremiumEmbeddingService(
            model_name="all-MiniLM-L6-v2",
            cache_enabled=False,
        )
        assert service is not None
        assert service.device is not None
        service.close()
    
    @pytest.mark.skipif(
        not pytest.importorskip("sentence_transformers", reason="sentence-transformers not installed"),
        reason="sentence-transformers required"
    )
    def test_encode_single_text(self):
        """Service can encode a single text."""
        from nsic.rag.premium_embeddings import PremiumEmbeddingService
        
        service = PremiumEmbeddingService(
            model_name="all-MiniLM-L6-v2",
            cache_enabled=False,
        )
        
        embedding = service.encode("test text")
        
        assert isinstance(embedding, np.ndarray)
        assert embedding.ndim == 1
        assert len(embedding) == service.embedding_dim  # Dynamically detected
        
        service.close()
    
    @pytest.mark.skipif(
        not pytest.importorskip("sentence_transformers", reason="sentence-transformers not installed"),
        reason="sentence-transformers required"
    )
    def test_encode_batch(self):
        """Service can encode a batch of texts."""
        from nsic.rag.premium_embeddings import PremiumEmbeddingService
        
        service = PremiumEmbeddingService(
            model_name="all-MiniLM-L6-v2",
            cache_enabled=False,
        )
        
        texts = ["text one", "text two", "text three"]
        embeddings = service.encode(texts)
        
        assert isinstance(embeddings, np.ndarray)
        assert embeddings.shape == (3, service.embedding_dim)
        
        service.close()
    
    @pytest.mark.skipif(
        not pytest.importorskip("sentence_transformers", reason="sentence-transformers not installed"),
        reason="sentence-transformers required"
    )
    def test_encode_with_cache(self):
        """Service uses cache when enabled."""
        from nsic.rag.premium_embeddings import PremiumEmbeddingService
        
        tmpdir = tempfile.mkdtemp()
        try:
            service = PremiumEmbeddingService(
                model_name="all-MiniLM-L6-v2",
                cache_enabled=True,
                cache_dir=tmpdir,
            )
            
            text = "cached text"
            
            # First encode - cache miss
            emb1 = service.encode(text)
            stats1 = service.cache.get_stats()
            
            # Second encode - cache hit
            emb2 = service.encode(text)
            stats2 = service.cache.get_stats()
            
            # Verify cache was used
            assert stats2["hits"] > stats1["hits"], "Second call should hit cache"
            
            # Verify embeddings match
            np.testing.assert_array_almost_equal(emb1, emb2, decimal=5)
            
            service.close()
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    
    @pytest.mark.skipif(
        not pytest.importorskip("sentence_transformers", reason="sentence-transformers not installed"),
        reason="sentence-transformers required"
    )
    def test_similarity(self):
        """Service can compute similarities."""
        from nsic.rag.premium_embeddings import PremiumEmbeddingService
        
        service = PremiumEmbeddingService(
            model_name="all-MiniLM-L6-v2",
            cache_enabled=False,
        )
        
        query = "unemployment rate"
        documents = [
            "The unemployment rate is 5%",
            "The weather is sunny today",
            "Employment statistics show growth",
        ]
        
        similarities = service.similarity(query, documents)
        
        assert len(similarities) == 3
        # First doc should be most similar
        assert similarities[0] > similarities[1], "Relevant doc should score higher"
        
        service.close()
    
    @pytest.mark.skipif(
        not pytest.importorskip("sentence_transformers", reason="sentence-transformers not installed"),
        reason="sentence-transformers required"
    )
    def test_service_stats(self):
        """Service tracks statistics."""
        from nsic.rag.premium_embeddings import PremiumEmbeddingService
        
        service = PremiumEmbeddingService(
            model_name="all-MiniLM-L6-v2",
            cache_enabled=False,
        )
        
        service.encode("test 1")
        service.encode(["test 2", "test 3"])
        
        stats = service.get_stats()
        assert stats["encode_calls"] == 2
        assert stats["total_texts_encoded"] == 3
        
        service.close()


class TestCacheIntegration:
    """Test cache and embedding service integration."""
    
    @pytest.mark.skipif(
        not pytest.importorskip("sentence_transformers", reason="sentence-transformers not installed"),
        reason="sentence-transformers required"
    )
    def test_cache_persistence(self):
        """Cache persists embeddings across service restarts."""
        from nsic.rag.premium_embeddings import PremiumEmbeddingService
        
        tmpdir = tempfile.mkdtemp()
        try:
            text = "persistent text"
            
            # First service instance - encode and cache
            service1 = PremiumEmbeddingService(
                model_name="all-MiniLM-L6-v2",
                cache_enabled=True,
                cache_dir=tmpdir,
            )
            emb1 = service1.encode(text)
            service1.close()
            
            # Second service instance - should hit cache
            service2 = PremiumEmbeddingService(
                model_name="all-MiniLM-L6-v2",
                cache_enabled=True,
                cache_dir=tmpdir,
            )
            emb2 = service2.encode(text)
            stats = service2.cache.get_stats()
            
            assert stats["hits"] == 1, "Should hit cache from previous instance"
            np.testing.assert_array_almost_equal(emb1, emb2, decimal=5)
            
            service2.close()
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


# Summary fixture for test report
@pytest.fixture(scope="session", autouse=True)
def test_summary(request):
    """Print summary after all tests."""
    yield
    print("\n" + "=" * 60)
    print("PHASE 1 EMBEDDING TESTS COMPLETE")
    print("=" * 60)
    print("\nIf all tests passed, proceed with:")
    print("  git add .")
    print('  git commit -m "feat(phase1): Premium embeddings with SHA256 cache"')
    print("  git push origin HEAD")
    print("\nThen start Phase 2: Deep Verification with Micro-Batching")
    print("=" * 60)

