"""
Production-grade sentence embeddings using sentence-transformers.

Provides semantic embeddings for RAG system with significantly better quality
than simple TF-IDF-based approaches. Uses pre-trained transformer models
optimized for semantic similarity tasks.

Models:
- all-mpnet-base-v2: Best quality (768 dim) - recommended for production
- all-MiniLM-L6-v2: Fast, good quality (384 dim) - good for development
- paraphrase-multilingual-mpnet-base-v2: Multilingual support
"""

from __future__ import annotations

import logging
from typing import List

import numpy as np

logger = logging.getLogger(__name__)

# Global cache for embedder instances to avoid reloading models
_EMBEDDER_CACHE = {}


class SentenceEmbedder:
    """
    Production-grade sentence embeddings using sentence-transformers.
    
    Provides high-quality semantic embeddings for document retrieval
    and similarity computation.
    """
    
    def __init__(self, model_name: str = "all-mpnet-base-v2"):
        """
        Initialize with sentence-transformers model.
        
        Args:
            model_name: Model name from sentence-transformers library
                Recommended models:
                - all-mpnet-base-v2: Best quality (768 dim)
                - all-MiniLM-L6-v2: Fast, good quality (384 dim)
                - paraphrase-multilingual-mpnet-base-v2: Multilingual
        """
        logger.info(f"Loading sentence-transformers model: {model_name}")
        
        try:
            from sentence_transformers import SentenceTransformer
            
            self.model = SentenceTransformer(model_name)
            self.dimension = self.model.get_sentence_embedding_dimension()
            self.model_name = model_name
            
            logger.info(f"Model loaded successfully. Embedding dimension: {self.dimension}")
            
        except ImportError as e:
            logger.error(
                "sentence-transformers not installed. "
                "Install with: pip install sentence-transformers"
            )
            raise ImportError(
                "sentence-transformers required for SentenceEmbedder. "
                "Install with: pip install sentence-transformers"
            ) from e
        except Exception as e:
            logger.error(f"Failed to load model {model_name}: {e}")
            raise
    
    def embed(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text to embed
            
        Returns:
            Numpy array of embedding vector
        """
        return self.model.encode(text, convert_to_numpy=True)
    
    def embed_batch(self, texts: List[str], show_progress: bool = False) -> np.ndarray:
        """
        Generate embeddings for multiple texts (more efficient than individual calls).
        
        Args:
            texts: List of texts to embed
            show_progress: Whether to show progress bar
            
        Returns:
            Numpy array of embeddings (shape: [len(texts), embedding_dim])
        """
        if not texts:
            return np.array([])
        
        return self.model.encode(
            texts, 
            convert_to_numpy=True, 
            show_progress_bar=show_progress
        )
    
    def similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Compute cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Cosine similarity score (0.0 to 1.0, higher is more similar)
        """
        # Normalize embeddings
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        # Compute cosine similarity
        similarity = float(np.dot(embedding1, embedding2) / (norm1 * norm2))
        
        # Clamp to [0, 1] range (can have small negative values due to float precision)
        return max(0.0, min(1.0, similarity))
    
    def similarity_matrix(
        self, 
        query_embedding: np.ndarray, 
        doc_embeddings: np.ndarray
    ) -> np.ndarray:
        """
        Compute similarities between query and multiple documents efficiently.
        
        Args:
            query_embedding: Query embedding vector (1D array)
            doc_embeddings: Document embeddings matrix (2D array: [num_docs, embedding_dim])
            
        Returns:
            Numpy array of similarity scores (shape: [num_docs])
        """
        if len(doc_embeddings) == 0:
            return np.array([])
        
        # Normalize query embedding
        query_norm = query_embedding / np.linalg.norm(query_embedding)
        
        # Normalize document embeddings
        doc_norms = np.linalg.norm(doc_embeddings, axis=1, keepdims=True)
        doc_norms = np.where(doc_norms == 0, 1, doc_norms)  # Avoid division by zero
        doc_embeddings_normalized = doc_embeddings / doc_norms
        
        # Compute similarities (matrix multiplication)
        similarities = np.dot(doc_embeddings_normalized, query_norm)
        
        # Clamp to [0, 1] range
        similarities = np.clip(similarities, 0.0, 1.0)
        
        return similarities
    
    def get_model_info(self) -> dict:
        """
        Get information about the loaded model.
        
        Returns:
            Dictionary with model information
        """
        return {
            "model_name": self.model_name,
            "embedding_dimension": self.dimension,
            "max_sequence_length": self.model.max_seq_length,
        }


def get_embedder(model_name: str = "all-mpnet-base-v2") -> SentenceEmbedder:
    """
    Get or create a sentence embedder instance (cached to avoid reloading models).
    
    Args:
        model_name: Model name to load
        
    Returns:
        SentenceEmbedder instance (cached)
    """
    if model_name not in _EMBEDDER_CACHE:
        logger.info(f"Creating new embedder for model: {model_name}")
        _EMBEDDER_CACHE[model_name] = SentenceEmbedder(model_name=model_name)
    else:
        logger.debug(f"Reusing cached embedder for model: {model_name}")
    return _EMBEDDER_CACHE[model_name]
