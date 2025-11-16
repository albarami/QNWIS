"""
Unit tests for sentence-transformers embeddings in RAG system.

Tests the SentenceEmbedder class and its integration with DocumentStore.
"""

import pytest
import numpy as np


def test_sentence_embedder_import():
    """Test that embeddings module can be imported."""
    try:
        from qnwis.rag.embeddings import SentenceEmbedder
        assert SentenceEmbedder is not None
    except ImportError as e:
        pytest.skip(f"sentence-transformers not installed: {e}")


def test_sentence_embedder_initialization():
    """Test embedder loads successfully with default model."""
    try:
        from qnwis.rag.embeddings import SentenceEmbedder
        
        embedder = SentenceEmbedder(model_name="all-MiniLM-L6-v2")
        
        assert embedder.dimension == 384
        assert embedder.model_name == "all-MiniLM-L6-v2"
        
    except ImportError:
        pytest.skip("sentence-transformers not installed")


def test_single_embedding():
    """Test single text embedding."""
    try:
        from qnwis.rag.embeddings import SentenceEmbedder
        
        embedder = SentenceEmbedder(model_name="all-MiniLM-L6-v2")
        embedding = embedder.embed("Qatar unemployment rate")
        
        assert isinstance(embedding, np.ndarray)
        assert embedding.shape == (384,)
        assert not np.isnan(embedding).any()
        assert not np.isinf(embedding).any()
        
    except ImportError:
        pytest.skip("sentence-transformers not installed")


def test_batch_embedding():
    """Test batch embedding efficiency."""
    try:
        from qnwis.rag.embeddings import SentenceEmbedder
        
        embedder = SentenceEmbedder(model_name="all-MiniLM-L6-v2")
        texts = [
            "Qatar labour market",
            "GCC unemployment",
            "workforce development"
        ]
        embeddings = embedder.embed_batch(texts)
        
        assert embeddings.shape == (3, 384)
        assert not np.isnan(embeddings).any()
        assert not np.isinf(embeddings).any()
        
    except ImportError:
        pytest.skip("sentence-transformers not installed")


def test_similarity_high():
    """Test similarity between similar texts."""
    try:
        from qnwis.rag.embeddings import SentenceEmbedder
        
        embedder = SentenceEmbedder(model_name="all-MiniLM-L6-v2")
        
        # Similar texts should have high similarity
        emb1 = embedder.embed("Qatar unemployment rate")
        emb2 = embedder.embed("joblessness in Qatar")
        similarity = embedder.similarity(emb1, emb2)
        
        assert 0.4 < similarity <= 1.0, f"Expected high similarity, got {similarity}"
        
    except ImportError:
        pytest.skip("sentence-transformers not installed")


def test_similarity_low():
    """Test similarity between dissimilar texts."""
    try:
        from qnwis.rag.embeddings import SentenceEmbedder
        
        embedder = SentenceEmbedder(model_name="all-MiniLM-L6-v2")
        
        # Dissimilar texts should have low similarity
        emb1 = embedder.embed("Qatar unemployment rate")
        emb2 = embedder.embed("climate change policy")
        similarity = embedder.similarity(emb1, emb2)
        
        assert 0.0 <= similarity < 0.5, f"Expected low similarity, got {similarity}"
        
    except ImportError:
        pytest.skip("sentence-transformers not installed")


def test_similarity_matrix():
    """Test efficient batch similarity computation."""
    try:
        from qnwis.rag.embeddings import SentenceEmbedder
        
        embedder = SentenceEmbedder(model_name="all-MiniLM-L6-v2")
        
        query_emb = embedder.embed("Qatar employment")
        doc_texts = [
            "Qatar labour market statistics",
            "GCC unemployment rates", 
            "renewable energy policies"
        ]
        doc_embs = embedder.embed_batch(doc_texts)
        
        similarities = embedder.similarity_matrix(query_emb, doc_embs)
        
        assert similarities.shape == (3,)
        assert np.all((similarities >= 0) & (similarities <= 1))
        
        # Employment docs should be more relevant than energy doc
        assert similarities[0] > similarities[2]
        assert similarities[1] > similarities[2]
        
    except ImportError:
        pytest.skip("sentence-transformers not installed")


def test_get_model_info():
    """Test model info retrieval."""
    try:
        from qnwis.rag.embeddings import SentenceEmbedder
        
        embedder = SentenceEmbedder(model_name="all-MiniLM-L6-v2")
        info = embedder.get_model_info()
        
        assert "model_name" in info
        assert "embedding_dimension" in info
        assert "max_sequence_length" in info
        
        assert info["model_name"] == "all-MiniLM-L6-v2"
        assert info["embedding_dimension"] == 384
        
    except ImportError:
        pytest.skip("sentence-transformers not installed")


def test_document_store_with_sentence_embeddings():
    """Test DocumentStore uses sentence embeddings when available."""
    try:
        from qnwis.rag.embeddings import SentenceEmbedder
        from qnwis.rag.retriever import DocumentStore, Document
        
        store = DocumentStore(
            embedding_model="all-MiniLM-L6-v2",
            use_simple_fallback=False  # Require sentence-transformers
        )
        
        assert store.use_sentence_embeddings is True
        
        # Add documents
        docs = [
            Document("doc1", "Qatar unemployment is very low", "Test", doc_type="test"),
            Document("doc2", "GCC labour market trends", "Test", doc_type="test"),
            Document("doc3", "Climate policy framework", "Test", doc_type="test")
        ]
        store.add_documents(docs)
        
        # Verify embeddings were created
        assert all(doc.embedding is not None for doc in store.documents.values())
        assert all(doc.embedding.shape == (384,) for doc in store.documents.values())
        
        # Search
        results = store.search("joblessness in Qatar", top_k=2, min_score=0.05)
        
        assert len(results) >= 1
        # Should match employment-related docs more than climate doc
        assert results[0][0].doc_id in ["doc1", "doc2"]
        assert results[0][1] > 0.2  # Should have decent relevance
        
    except ImportError:
        pytest.skip("sentence-transformers not installed")


def test_document_store_fallback():
    """Test DocumentStore falls back to SimpleEmbedder gracefully."""
    from qnwis.rag.retriever import DocumentStore, Document
    
    # Test with fallback enabled (should always work)
    store = DocumentStore(use_simple_fallback=True)
    
    # Should either use sentence embeddings or simple embedder
    assert hasattr(store, 'use_sentence_embeddings')
    
    # Add documents (should work with either embedder)
    docs = [
        Document("doc1", "Qatar unemployment rate", "Test", doc_type="test"),
        Document("doc2", "GCC labour market", "Test", doc_type="test")
    ]
    store.add_documents(docs)
    
    # Search should work
    results = store.search("unemployment", top_k=2)
    assert len(results) >= 1


def test_empty_text_handling():
    """Test handling of empty texts."""
    try:
        from qnwis.rag.embeddings import SentenceEmbedder
        
        embedder = SentenceEmbedder(model_name="all-MiniLM-L6-v2")
        
        # Empty string should still produce embedding
        embedding = embedder.embed("")
        assert isinstance(embedding, np.ndarray)
        assert embedding.shape == (384,)
        
        # Batch with empty string
        embeddings = embedder.embed_batch(["text1", "", "text3"])
        assert embeddings.shape == (3, 384)
        
    except ImportError:
        pytest.skip("sentence-transformers not installed")


def test_long_text_handling():
    """Test handling of very long texts."""
    try:
        from qnwis.rag.embeddings import SentenceEmbedder
        
        embedder = SentenceEmbedder(model_name="all-MiniLM-L6-v2")
        
        # Create very long text (beyond max_seq_length)
        long_text = "Qatar unemployment " * 200  # Much longer than 512 tokens
        
        # Should handle gracefully (truncate)
        embedding = embedder.embed(long_text)
        assert isinstance(embedding, np.ndarray)
        assert embedding.shape == (384,)
        assert not np.isnan(embedding).any()
        
    except ImportError:
        pytest.skip("sentence-transformers not installed")
