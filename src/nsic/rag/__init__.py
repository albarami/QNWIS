"""
NSIC RAG (Retrieval-Augmented Generation) Module

This module provides premium embeddings and caching for the NSIC system.

Components:
- EmbeddingCache: SHA256-based deterministic embedding cache
- PremiumEmbeddingService: instructor-xl embeddings with GPU acceleration
"""

from .embedding_cache import EmbeddingCache, create_embedding_cache
from .premium_embeddings import (
    PremiumEmbeddingService,
    get_embedding_service,
    encode,
    TASK_INSTRUCTIONS,
)

__all__ = [
    "EmbeddingCache",
    "create_embedding_cache",
    "PremiumEmbeddingService",
    "get_embedding_service",
    "encode",
    "TASK_INSTRUCTIONS",
]
