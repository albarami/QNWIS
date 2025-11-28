"""
NSIC RAG Connector - Connects to the existing QNWIS RAG system.

Uses the REAL:
- 1,959 R&D document chunks
- 768-dimensional embeddings
- Sentence-transformers semantic search

NO MOCKS. REAL DATA ONLY.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
import numpy as np

# Import the REAL QNWIS RAG system
from src.qnwis.rag.retriever import (
    get_document_store,
    retrieve_external_context,
    format_rag_context_for_prompt,
    Document,
    DocumentStore,
)

logger = logging.getLogger(__name__)


class NSICRAGConnector:
    """
    Connects NSIC to the existing QNWIS RAG system.
    
    Provides access to:
    - 1,959 R&D document chunks
    - Semantic search over embedded documents
    - Real-time context retrieval
    """
    
    def __init__(self):
        """Initialize with real RAG store."""
        self.store = get_document_store()
        self._stats = {
            "queries": 0,
            "chunks_retrieved": 0,
        }
        
        doc_count = len(self.store.documents)
        logger.info(f"NSICRAGConnector initialized with {doc_count} documents")
    
    def search(
        self,
        query: str,
        top_k: int = 10,
        min_score: float = 0.3,
        source_filter: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search R&D documents using semantic similarity.
        
        Args:
            query: Search query
            top_k: Number of results
            min_score: Minimum similarity threshold
            source_filter: Filter by source
            
        Returns:
            List of matching document chunks with scores
        """
        results = self.store.search(
            query=query,
            top_k=top_k,
            min_score=min_score,
            source_filter=source_filter,
        )
        
        self._stats["queries"] += 1
        self._stats["chunks_retrieved"] += len(results)
        
        return [
            {
                "text": doc.text,
                "source": doc.source,
                "score": score,
                "freshness": doc.freshness,
                "doc_type": doc.doc_type,
                "metadata": doc.metadata,
            }
            for doc, score in results
        ]
    
    def search_rd_reports(
        self,
        query: str,
        top_k: int = 10,
        min_score: float = 0.3,
    ) -> List[Dict[str, Any]]:
        """Search only R&D reports."""
        # Filter for R&D sources
        results = self.search(
            query=query,
            top_k=top_k * 2,  # Get more to filter
            min_score=min_score,
        )
        
        # Filter for R&D reports
        rd_results = [
            r for r in results
            if "R&D" in r["source"]
        ]
        
        return rd_results[:top_k]
    
    async def get_context_for_scenario(
        self,
        scenario: str,
        max_chunks: int = 10,
    ) -> str:
        """
        Get relevant context for scenario analysis.
        
        Args:
            scenario: Scenario description
            max_chunks: Maximum chunks to include
            
        Returns:
            Formatted context string
        """
        # Get context using existing RAG function
        context = await retrieve_external_context(
            query=scenario,
            max_snippets=max_chunks,
            include_api_data=True,
            min_relevance=0.2,
        )
        
        return format_rag_context_for_prompt(context)
    
    def get_related_research(
        self,
        topic: str,
        min_chunks: int = 5,
    ) -> Dict[str, Any]:
        """
        Get research insights on a topic from R&D documents.
        
        Args:
            topic: Research topic
            min_chunks: Minimum chunks to retrieve
            
        Returns:
            Dict with research insights and sources
        """
        chunks = self.search_rd_reports(
            query=topic,
            top_k=min_chunks * 2,
            min_score=0.25,
        )
        
        # Group by source document
        by_source = {}
        for chunk in chunks:
            source = chunk["source"]
            if source not in by_source:
                by_source[source] = []
            by_source[source].append(chunk)
        
        return {
            "topic": topic,
            "total_chunks": len(chunks),
            "sources_count": len(by_source),
            "chunks": chunks[:min_chunks],
            "sources": list(by_source.keys()),
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connector statistics."""
        return {
            **self._stats,
            "total_documents": len(self.store.documents),
            "store_stats": self.store.get_stats(),
        }


def get_nsic_rag() -> NSICRAGConnector:
    """Factory function to get NSIC RAG connector."""
    return NSICRAGConnector()

