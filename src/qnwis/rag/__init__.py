"""
RAG (Retrieval-Augmented Generation) for fact verification.

GPU-accelerated semantic search for real-time fact checking.
"""

import logging
from typing import Optional
from .gpu_verifier import GPUFactVerifier

logger = logging.getLogger(__name__)

# Global instance (initialized at app startup)
_global_fact_verifier: Optional[GPUFactVerifier] = None


def initialize_fact_verifier(verifier: GPUFactVerifier) -> None:
    """
    Initialize global fact verifier instance.
    
    Called at app startup after pre-indexing documents.
    
    Args:
        verifier: Pre-initialized GPUFactVerifier instance
    """
    global _global_fact_verifier
    _global_fact_verifier = verifier
    logger.info("✅ Global fact verifier initialized")


def get_fact_verifier() -> Optional[GPUFactVerifier]:
    """
    Get pre-initialized fact verifier instance.
    
    Returns:
        GPUFactVerifier instance or None if verification is disabled
    """
    return _global_fact_verifier


__all__ = [
    'GPUFactVerifier',
    'initialize_fact_verifier',
    'get_fact_verifier',
    'load_source_documents'
]
