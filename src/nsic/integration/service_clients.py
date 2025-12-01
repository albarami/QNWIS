"""
NSIC Service Clients - HTTP Clients for Persistent GPU Services

Provides clients for the persistent GPU services:
- EmbeddingsClient: Connect to embeddings server (port 8003)
- KGClient: Connect to knowledge graph server (port 8004)
- VerificationClient: Connect to verification server (port 8005)

Usage:
    from src.nsic.integration.service_clients import (
        EmbeddingsClient,
        KGClient,
        VerificationClient,
    )
    
    embeddings = EmbeddingsClient()
    result = await embeddings.embed(["text1", "text2"])
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)


# ============================================================================
# Configuration
# ============================================================================

DEFAULT_EMBEDDINGS_URL = "http://localhost:8100"
DEFAULT_KG_URL = "http://localhost:8101"
DEFAULT_VERIFICATION_URL = "http://localhost:8102"
DEFAULT_TIMEOUT = 7200.0  # 2 hours


# ============================================================================
# Embeddings Client
# ============================================================================

class EmbeddingsClient:
    """
    HTTP client for the persistent embeddings server.
    
    Endpoints:
    - POST /embed: Encode texts to embeddings
    - POST /search: Semantic search
    - POST /similarity: Compute similarity
    - GET /health: Health check
    """
    
    def __init__(
        self,
        base_url: str = DEFAULT_EMBEDDINGS_URL,
        timeout: float = DEFAULT_TIMEOUT,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
            )
        return self._client
    
    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
    
    async def health_check(self) -> Dict[str, Any]:
        """Check embeddings server health."""
        client = await self._get_client()
        response = await client.get("/health")
        response.raise_for_status()
        return response.json()
    
    async def embed(
        self,
        texts: List[str],
        task: str = "default",
    ) -> Dict[str, Any]:
        """
        Encode texts to embeddings.
        
        Args:
            texts: List of texts to embed
            task: Task type (query, document, passage, summary, default)
            
        Returns:
            Dict with embeddings, dimension, count, latency_ms
        """
        client = await self._get_client()
        response = await client.post(
            "/embed",
            json={"texts": texts, "task": task},
        )
        response.raise_for_status()
        return response.json()
    
    async def search(
        self,
        query: str,
        documents: List[str],
        top_k: int = 10,
    ) -> Dict[str, Any]:
        """
        Perform semantic search over documents.
        
        Args:
            query: Search query
            documents: Documents to search
            top_k: Number of top results
            
        Returns:
            Dict with results, query, latency_ms
        """
        client = await self._get_client()
        response = await client.post(
            "/search",
            json={"query": query, "documents": documents, "top_k": top_k},
        )
        response.raise_for_status()
        return response.json()
    
    async def similarity(
        self,
        text1: str,
        text2: str,
    ) -> float:
        """
        Compute similarity between two texts.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Similarity score
        """
        client = await self._get_client()
        response = await client.post(
            "/similarity",
            json={"text1": text1, "text2": text2},
        )
        response.raise_for_status()
        return response.json()["similarity"]
    
    def embed_sync(
        self,
        texts: List[str],
        task: str = "default",
    ) -> Dict[str, Any]:
        """Synchronous wrapper for embed."""
        return asyncio.get_event_loop().run_until_complete(
            self.embed(texts, task)
        )


# ============================================================================
# Knowledge Graph Client
# ============================================================================

class KGClient:
    """
    HTTP client for the persistent knowledge graph server.
    
    Endpoints:
    - POST /causal_chains: Find causal chains
    - POST /query: Query the graph
    - POST /similar_nodes: Find similar nodes
    - POST /blocking_factors: Find blocking factors
    - POST /subgraph: Get subgraph
    - GET /health: Health check
    """
    
    def __init__(
        self,
        base_url: str = DEFAULT_KG_URL,
        timeout: float = DEFAULT_TIMEOUT,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
            )
        return self._client
    
    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
    
    async def health_check(self) -> Dict[str, Any]:
        """Check KG server health."""
        client = await self._get_client()
        response = await client.get("/health")
        response.raise_for_status()
        return response.json()
    
    async def find_causal_chains(
        self,
        source_id: str,
        target_id: str,
        max_length: int = 5,
        min_strength: float = 0.3,
    ) -> Dict[str, Any]:
        """
        Find causal chains between two nodes.
        
        Args:
            source_id: Source node ID
            target_id: Target node ID
            max_length: Maximum chain length
            min_strength: Minimum edge strength
            
        Returns:
            Dict with chains, count, latency_ms
        """
        client = await self._get_client()
        response = await client.post(
            "/causal_chains",
            json={
                "source_id": source_id,
                "target_id": target_id,
                "max_length": max_length,
                "min_strength": min_strength,
            },
        )
        response.raise_for_status()
        return response.json()
    
    async def query(
        self,
        question: str,
        entity: Optional[str] = None,
        domain: Optional[str] = None,
        max_results: int = 10,
    ) -> Dict[str, Any]:
        """
        Query the knowledge graph.
        
        Args:
            question: Natural language question
            entity: Optional entity to focus on
            domain: Optional domain filter
            max_results: Maximum results
            
        Returns:
            Dict with results, entities_found, latency_ms
        """
        client = await self._get_client()
        response = await client.post(
            "/query",
            json={
                "question": question,
                "entity": entity,
                "domain": domain,
                "max_results": max_results,
            },
        )
        response.raise_for_status()
        return response.json()
    
    async def find_similar_nodes(
        self,
        query_text: str,
        top_k: int = 10,
        domain_filter: Optional[str] = None,
        type_filter: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Find nodes similar to query text.
        
        Args:
            query_text: Query text
            top_k: Number of results
            domain_filter: Optional domain filter
            type_filter: Optional type filter
            
        Returns:
            Dict with nodes, count, latency_ms
        """
        client = await self._get_client()
        response = await client.post(
            "/similar_nodes",
            json={
                "query_text": query_text,
                "top_k": top_k,
                "domain_filter": domain_filter,
                "type_filter": type_filter,
            },
        )
        response.raise_for_status()
        return response.json()
    
    async def find_blocking_factors(
        self,
        target_id: str,
        max_depth: int = 3,
    ) -> Dict[str, Any]:
        """
        Find factors that block or mitigate effects on target.
        
        Args:
            target_id: Target node ID
            max_depth: Maximum search depth
            
        Returns:
            Dict with factors, count, latency_ms
        """
        client = await self._get_client()
        response = await client.post(
            "/blocking_factors",
            json={"target_id": target_id, "max_depth": max_depth},
        )
        response.raise_for_status()
        return response.json()
    
    async def get_subgraph(
        self,
        center_node_id: str,
        radius: int = 2,
    ) -> Dict[str, Any]:
        """
        Get a subgraph around a center node.
        
        Args:
            center_node_id: Center node ID
            radius: Number of hops
            
        Returns:
            Dict with nodes, edges, latency_ms
        """
        client = await self._get_client()
        response = await client.post(
            "/subgraph",
            json={"center_node_id": center_node_id, "radius": radius},
        )
        response.raise_for_status()
        return response.json()


# ============================================================================
# Verification Client
# ============================================================================

@dataclass
class VerificationResult:
    """Result of a verification check."""
    claim: str
    evidence: str
    score: float
    label: str
    confidence: float
    timing_ms: float


class VerificationClient:
    """
    HTTP client for the persistent verification server.
    
    Endpoints:
    - POST /verify: Verify a single claim
    - POST /verify_batch: Verify multiple claims
    - POST /verify_against_sources: Verify against multiple sources
    - GET /health: Health check
    """
    
    def __init__(
        self,
        base_url: str = DEFAULT_VERIFICATION_URL,
        timeout: float = DEFAULT_TIMEOUT,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
            )
        return self._client
    
    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
    
    async def health_check(self) -> Dict[str, Any]:
        """Check verification server health."""
        client = await self._get_client()
        response = await client.get("/health")
        response.raise_for_status()
        return response.json()
    
    async def verify(
        self,
        claim: str,
        evidence: str,
    ) -> VerificationResult:
        """
        Verify a single claim against evidence.
        
        Args:
            claim: Claim to verify
            evidence: Evidence text
            
        Returns:
            VerificationResult with score and label
        """
        client = await self._get_client()
        response = await client.post(
            "/verify",
            json={"claim": claim, "evidence": evidence},
        )
        response.raise_for_status()
        data = response.json()
        
        return VerificationResult(
            claim=data["claim"],
            evidence=evidence[:100] + "..." if len(evidence) > 100 else evidence,
            score=data["score"],
            label=data["label"],
            confidence=data["confidence"],
            timing_ms=data["latency_ms"],
        )
    
    async def verify_batch(
        self,
        claims: List[str],
        evidences: List[str],
    ) -> List[VerificationResult]:
        """
        Verify multiple claims against their evidence.
        
        Args:
            claims: List of claims
            evidences: List of evidence texts
            
        Returns:
            List of VerificationResult objects
        """
        client = await self._get_client()
        response = await client.post(
            "/verify_batch",
            json={"claims": claims, "evidences": evidences},
        )
        response.raise_for_status()
        data = response.json()
        
        results = []
        for r in data["results"]:
            results.append(VerificationResult(
                claim=r["claim"],
                evidence=r["evidence"],
                score=r["score"],
                label=r["label"],
                confidence=r["confidence"],
                timing_ms=r["timing_ms"],
            ))
        return results
    
    async def verify_against_sources(
        self,
        claim: str,
        sources: List[str],
        top_k: int = 3,
    ) -> Dict[str, Any]:
        """
        Verify a claim against multiple sources.
        
        Args:
            claim: Claim to verify
            sources: List of source texts
            top_k: Number of top sources to consider
            
        Returns:
            Dict with verification result and top sources
        """
        client = await self._get_client()
        response = await client.post(
            "/verify_against_sources",
            json={"claim": claim, "sources": sources, "top_k": top_k},
        )
        response.raise_for_status()
        return response.json()
    
    def verify_sync(
        self,
        claim: str,
        evidence: str,
    ) -> VerificationResult:
        """Synchronous wrapper for verify."""
        return asyncio.get_event_loop().run_until_complete(
            self.verify(claim, evidence)
        )


# ============================================================================
# Factory Functions
# ============================================================================

_embeddings_client: Optional[EmbeddingsClient] = None
_kg_client: Optional[KGClient] = None
_verification_client: Optional[VerificationClient] = None


def get_embeddings_client() -> EmbeddingsClient:
    """Get singleton embeddings client."""
    global _embeddings_client
    if _embeddings_client is None:
        _embeddings_client = EmbeddingsClient()
    return _embeddings_client


def get_kg_client() -> KGClient:
    """Get singleton KG client."""
    global _kg_client
    if _kg_client is None:
        _kg_client = KGClient()
    return _kg_client


def get_verification_client() -> VerificationClient:
    """Get singleton verification client."""
    global _verification_client
    if _verification_client is None:
        _verification_client = VerificationClient()
    return _verification_client


async def check_all_services() -> Dict[str, Any]:
    """
    Check health of all persistent services.
    
    Returns:
        Dict with health status of all services
    """
    results = {
        "embeddings": {"status": "unknown"},
        "kg": {"status": "unknown"},
        "verification": {"status": "unknown"},
    }
    
    try:
        embeddings = get_embeddings_client()
        results["embeddings"] = await embeddings.health_check()
    except Exception as e:
        results["embeddings"] = {"status": "error", "error": str(e)}
    
    try:
        kg = get_kg_client()
        results["kg"] = await kg.health_check()
    except Exception as e:
        results["kg"] = {"status": "error", "error": str(e)}
    
    try:
        verification = get_verification_client()
        results["verification"] = await verification.health_check()
    except Exception as e:
        results["verification"] = {"status": "error", "error": str(e)}
    
    return results

