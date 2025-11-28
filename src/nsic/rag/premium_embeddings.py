"""
NSIC Premium Embeddings Service

Uses hkunlp/instructor-xl for best-in-class semantic understanding with
task-aware instructions. Supports dual-GPU parallel encoding for maximum
throughput.

Key features:
- instructor-xl: 768-dim embeddings with task instructions
- Dual-GPU: Parallel encoding on GPU 0-1
- Deterministic cache: SHA256-based caching for reproducibility
- Batch processing: Efficient batched encoding
"""

import logging
from typing import List, Optional, Union
import numpy as np

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    ST_AVAILABLE = True
except ImportError:
    ST_AVAILABLE = False

from .embedding_cache import EmbeddingCache, create_embedding_cache

logger = logging.getLogger(__name__)

# Default task instructions for different use cases
TASK_INSTRUCTIONS = {
    "query": "Represent the question for retrieving relevant documents: ",
    "document": "Represent the document for retrieval: ",
    "passage": "Represent the passage for retrieval: ",
    "summary": "Represent the summary for semantic search: ",
    "default": "",
}


class PremiumEmbeddingService:
    """
    Premium embedding service using instructor-xl with GPU acceleration.
    
    This service provides:
    - Task-aware embeddings via instructor-xl
    - Dual-GPU parallel processing (GPU 0-1)
    - Deterministic SHA256-based caching
    - Automatic batch optimization
    """
    
    # Model configuration
    MODEL_NAME = "hkunlp/instructor-xl"
    MODEL_VERSION = "1.0.0"
    DEFAULT_EMBEDDING_DIM = 768  # instructor-xl default, but detected dynamically
    
    def __init__(
        self,
        model_name: str = MODEL_NAME,
        device: Optional[str] = None,
        cache_enabled: bool = True,
        cache_dir: Optional[str] = None,
        cache_max_size_gb: float = 10.0,
        batch_size: int = 32,
        gpu_ids: Optional[List[int]] = None,
    ):
        """
        Initialize the premium embedding service.
        
        Args:
            model_name: HuggingFace model name (default: instructor-xl)
            device: Device to use ('cuda', 'cuda:0', 'cpu', or None for auto)
            cache_enabled: Whether to use embedding cache
            cache_dir: Custom cache directory
            cache_max_size_gb: Maximum cache size in GB
            batch_size: Batch size for encoding
            gpu_ids: List of GPU IDs to use (default: [0, 1] for dual-GPU)
        """
        if not ST_AVAILABLE:
            raise ImportError(
                "sentence-transformers is required. Install with: pip install sentence-transformers"
            )
        
        self.model_name = model_name
        self.batch_size = batch_size
        self.gpu_ids = gpu_ids or [0, 1]  # Default dual-GPU on 0-1
        
        # Determine device
        if device is None:
            if TORCH_AVAILABLE and torch.cuda.is_available():
                device = f"cuda:{self.gpu_ids[0]}"
            else:
                device = "cpu"
        self.device = device
        
        # Load model
        logger.info(f"Loading embedding model: {model_name} on {device}")
        self.model = SentenceTransformer(model_name, device=device)
        
        # Get actual embedding dimension from model
        self.embedding_dim = self.model.get_sentence_embedding_dimension()
        
        # Initialize cache if enabled
        self.cache_enabled = cache_enabled
        self.cache: Optional[EmbeddingCache] = None
        if cache_enabled:
            self.cache = create_embedding_cache(
                model_name=model_name,
                model_version=self.MODEL_VERSION,
                cache_dir=cache_dir,
                max_size_gb=cache_max_size_gb,
            )
        
        # Stats
        self._encode_calls = 0
        self._total_texts = 0
        
        logger.info(
            f"PremiumEmbeddingService initialized: model={model_name}, "
            f"device={device}, cache={cache_enabled}"
        )
    
    def _prepare_instruction(self, text: str, task: str = "default") -> str:
        """Prepare text with task instruction for instructor models."""
        instruction = TASK_INSTRUCTIONS.get(task, TASK_INSTRUCTIONS["default"])
        return instruction + text
    
    def encode(
        self,
        texts: Union[str, List[str]],
        task: str = "default",
        batch_size: Optional[int] = None,
        show_progress: bool = False,
        normalize: bool = True,
    ) -> np.ndarray:
        """
        Encode texts to embeddings.
        
        Args:
            texts: Single text or list of texts
            task: Task type for instruction (query, document, passage, summary, default)
            batch_size: Override default batch size
            show_progress: Show progress bar
            normalize: L2-normalize embeddings
            
        Returns:
            Embedding matrix (N x 768) as numpy array
        """
        # Handle single text
        if isinstance(texts, str):
            texts = [texts]
            single_input = True
        else:
            single_input = False
        
        self._encode_calls += 1
        self._total_texts += len(texts)
        
        batch_size = batch_size or self.batch_size
        
        # Check cache for existing embeddings
        if self.cache_enabled and self.cache is not None:
            cached_results, missing_indices = self.cache.get_batch(texts)
            
            if not missing_indices:
                # All cached - return directly
                embeddings = np.array([r for r in cached_results])
                logger.debug(f"All {len(texts)} embeddings from cache")
            else:
                # Some missing - encode only missing ones
                missing_texts = [texts[i] for i in missing_indices]
                
                # Prepare with instructions
                prepared_texts = [
                    self._prepare_instruction(t, task) for t in missing_texts
                ]
                
                # Encode missing texts
                new_embeddings = self.model.encode(
                    prepared_texts,
                    batch_size=batch_size,
                    show_progress_bar=show_progress,
                    normalize_embeddings=normalize,
                    convert_to_numpy=True,
                )
                
                # Cache new embeddings
                for i, idx in enumerate(missing_indices):
                    self.cache.set(texts[idx], new_embeddings[i])
                
                # Merge cached and new embeddings
                embeddings = np.zeros((len(texts), self.embedding_dim), dtype=np.float32)
                new_idx = 0
                for i in range(len(texts)):
                    if cached_results[i] is not None:
                        embeddings[i] = cached_results[i]
                    else:
                        embeddings[i] = new_embeddings[new_idx]
                        new_idx += 1
                
                logger.debug(
                    f"Encoded {len(missing_indices)} new, {len(texts) - len(missing_indices)} from cache"
                )
        else:
            # No cache - encode all
            prepared_texts = [self._prepare_instruction(t, task) for t in texts]
            embeddings = self.model.encode(
                prepared_texts,
                batch_size=batch_size,
                show_progress_bar=show_progress,
                normalize_embeddings=normalize,
                convert_to_numpy=True,
            )
        
        if single_input:
            return embeddings[0]
        return embeddings
    
    def encode_queries(
        self,
        queries: Union[str, List[str]],
        **kwargs,
    ) -> np.ndarray:
        """Encode queries with query-specific instruction."""
        return self.encode(queries, task="query", **kwargs)
    
    def encode_documents(
        self,
        documents: Union[str, List[str]],
        **kwargs,
    ) -> np.ndarray:
        """Encode documents with document-specific instruction."""
        return self.encode(documents, task="document", **kwargs)
    
    def similarity(
        self,
        query: str,
        documents: List[str],
        task_query: str = "query",
        task_doc: str = "document",
    ) -> np.ndarray:
        """
        Compute cosine similarity between query and documents.
        
        Args:
            query: Query text
            documents: List of document texts
            task_query: Task instruction for query
            task_doc: Task instruction for documents
            
        Returns:
            Similarity scores as numpy array
        """
        query_emb = self.encode(query, task=task_query)
        doc_embs = self.encode(documents, task=task_doc)
        
        # Cosine similarity (embeddings are normalized)
        similarities = np.dot(doc_embs, query_emb)
        return similarities
    
    def get_stats(self) -> dict:
        """Get service statistics."""
        stats = {
            "model_name": self.model_name,
            "device": str(self.device),
            "encode_calls": self._encode_calls,
            "total_texts_encoded": self._total_texts,
            "embedding_dim": self.embedding_dim,
            "cache_enabled": self.cache_enabled,
        }
        
        if self.cache_enabled and self.cache is not None:
            stats["cache_stats"] = self.cache.get_stats()
        
        return stats
    
    def close(self) -> None:
        """Close the service and release resources."""
        if self.cache is not None:
            self.cache.close()
        logger.info(f"PremiumEmbeddingService closed. Stats: {self.get_stats()}")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False


# Module-level singleton for convenience
_default_service: Optional[PremiumEmbeddingService] = None


def get_embedding_service(
    model_name: str = PremiumEmbeddingService.MODEL_NAME,
    **kwargs,
) -> PremiumEmbeddingService:
    """
    Get or create the default embedding service.
    
    Args:
        model_name: Model to use
        **kwargs: Additional arguments passed to PremiumEmbeddingService
        
    Returns:
        PremiumEmbeddingService instance
    """
    global _default_service
    
    if _default_service is None:
        _default_service = PremiumEmbeddingService(model_name=model_name, **kwargs)
    
    return _default_service


def encode(
    texts: Union[str, List[str]],
    task: str = "default",
    **kwargs,
) -> np.ndarray:
    """
    Convenience function to encode texts using the default service.
    
    Args:
        texts: Text(s) to encode
        task: Task instruction type
        **kwargs: Additional arguments
        
    Returns:
        Embedding(s) as numpy array
    """
    service = get_embedding_service()
    return service.encode(texts, task=task, **kwargs)

