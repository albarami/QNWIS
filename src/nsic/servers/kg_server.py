"""
NSIC Knowledge Graph Server - CPU Service

Enterprise-grade KG service running on CPU:
- Runs on CPU (frees GPU for DeepSeek instances)
- Port 8101
- Knowledge graph loaded at startup from pickle
- Graph operations are CPU-native (NetworkX)

Endpoints:
- POST /causal_chains - Find causal chains between entities
- POST /query - Query the knowledge graph
- POST /similar_nodes - Find similar nodes
- POST /blocking_factors - Find blocking factors
- GET /health - Health check
- GET /stats - Service statistics

Usage:
    python -m src.nsic.servers.kg_server --port 8101
"""

import logging
import os
import sys
import time
from typing import List, Optional, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import uvicorn

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))


# ============================================================================
# Pydantic Models
# ============================================================================

class CausalChainsRequest(BaseModel):
    """Request to find causal chains."""
    source_id: str = Field(..., description="Source node ID")
    target_id: str = Field(..., description="Target node ID")
    max_length: int = Field(5, description="Maximum chain length", ge=1, le=10)
    min_strength: float = Field(0.3, description="Minimum edge strength", ge=0.0, le=1.0)


class CausalChainsResponse(BaseModel):
    """Response with causal chains."""
    chains: List[dict] = Field(..., description="List of causal chains")
    count: int = Field(..., description="Number of chains found")
    latency_ms: float = Field(..., description="Processing time")


class QueryRequest(BaseModel):
    """Request to query the knowledge graph."""
    question: str = Field(..., description="Natural language question")
    entity: Optional[str] = Field(None, description="Specific entity to focus on")
    domain: Optional[str] = Field(None, description="Domain filter")
    max_results: int = Field(10, description="Maximum results")


class QueryResponse(BaseModel):
    """Response from KG query."""
    results: List[dict] = Field(..., description="Query results")
    entities_found: int = Field(..., description="Number of entities found")
    latency_ms: float = Field(..., description="Processing time")


class SimilarNodesRequest(BaseModel):
    """Request to find similar nodes."""
    query_text: str = Field(..., description="Query text to find similar nodes")
    top_k: int = Field(10, description="Number of results", ge=1, le=50)
    domain_filter: Optional[str] = Field(None, description="Filter by domain")
    type_filter: Optional[str] = Field(None, description="Filter by node type")


class SimilarNodesResponse(BaseModel):
    """Response with similar nodes."""
    nodes: List[dict] = Field(..., description="Similar nodes with scores")
    count: int = Field(..., description="Number of nodes found")
    latency_ms: float = Field(..., description="Processing time")


class BlockingFactorsRequest(BaseModel):
    """Request to find blocking factors."""
    target_id: str = Field(..., description="Target node ID")
    max_depth: int = Field(3, description="Maximum search depth", ge=1, le=5)


class BlockingFactorsResponse(BaseModel):
    """Response with blocking factors."""
    factors: List[dict] = Field(..., description="Blocking factors")
    count: int = Field(..., description="Number of factors found")
    latency_ms: float = Field(..., description="Processing time")


class SubgraphRequest(BaseModel):
    """Request to get a subgraph."""
    center_node_id: str = Field(..., description="Center node ID")
    radius: int = Field(2, description="Radius in hops", ge=1, le=4)


class SubgraphResponse(BaseModel):
    """Response with subgraph data."""
    nodes: List[dict] = Field(..., description="Nodes in subgraph")
    edges: List[dict] = Field(..., description="Edges in subgraph")
    latency_ms: float = Field(..., description="Processing time")


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(..., description="Service status")
    graph_loaded: bool = Field(..., description="Whether graph is loaded")
    node_count: int = Field(..., description="Number of nodes")
    edge_count: int = Field(..., description="Number of edges")
    device: str = Field(..., description="GPU device")
    gpu_memory_gb: float = Field(..., description="GPU memory used")


class StatsResponse(BaseModel):
    """Service statistics."""
    node_count: int
    edge_count: int
    domains: dict
    types: dict
    queries: int
    chains_found: int
    device: str
    uptime_seconds: float
    gpu_memory_gb: float


# ============================================================================
# Global State
# ============================================================================

causal_graph = None
embedding_service = None  # For query embedding
start_time = None
KG_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "knowledge_graph.pkl")


def get_gpu_memory():
    """Get current GPU memory usage."""
    try:
        import torch
        if torch.cuda.is_available():
            # Get memory for GPU 4 (or first visible GPU)
            device_id = int(os.environ.get("CUDA_VISIBLE_DEVICES", "4").split(",")[0])
            return torch.cuda.memory_allocated(0) / 1e9  # First visible device
    except Exception:
        pass
    return 0.0


# ============================================================================
# Lifespan - Load KG at startup
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load knowledge graph at startup, keep in GPU memory."""
    global causal_graph, embedding_service, start_time
    
    logger.info("=" * 60)
    logger.info("NSIC KNOWLEDGE GRAPH SERVER - STARTUP")
    logger.info("=" * 60)
    
    try:
        # Load knowledge graph
        from src.nsic.knowledge.causal_graph import load_causal_graph
        
        kg_path = os.path.abspath(KG_PATH)
        logger.info(f"Loading knowledge graph from: {kg_path}")
        
        load_start = time.time()
        causal_graph = load_causal_graph(kg_path, gpu_device="cpu")  # Running on CPU
        load_time = time.time() - load_start
        
        logger.info(f"Graph loaded in {load_time:.2f}s")
        logger.info(f"Nodes: {len(causal_graph.nodes)}")
        logger.info(f"Edges: {causal_graph.graph.number_of_edges()}")
        
        # Load embedding service for query encoding
        try:
            from src.nsic.rag.premium_embeddings import PremiumEmbeddingService
            logger.info("Loading embedding model for query encoding (CPU)...")
            embedding_service = PremiumEmbeddingService(
                device="cpu",
                cache_enabled=True,
            )
            logger.info(f"Embedding model loaded: dim={embedding_service.embedding_dim}")
        except Exception as e:
            logger.warning(f"Could not load embedding service: {e}")
            embedding_service = None
        
        logger.info("Running on CPU (GPU freed for DeepSeek instances)")
        
        start_time = time.time()
        
        logger.info("=" * 60)
        logger.info("KNOWLEDGE GRAPH SERVER READY - Graph loaded on CPU")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Failed to load knowledge graph: {e}")
        raise
    
    yield
    
    # Cleanup
    logger.info("Shutting down KG server...")
    if embedding_service:
        embedding_service.close()


# ============================================================================
# FastAPI App
# ============================================================================

app = FastAPI(
    title="NSIC Knowledge Graph Server",
    description="Enterprise-grade persistent knowledge graph service on GPU 4",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Check service health."""
    global causal_graph
    
    return HealthResponse(
        status="healthy" if causal_graph is not None else "unhealthy",
        graph_loaded=causal_graph is not None,
        node_count=len(causal_graph.nodes) if causal_graph else 0,
        edge_count=causal_graph.graph.number_of_edges() if causal_graph else 0,
        device=causal_graph.gpu_processor.device if causal_graph else "none",
        gpu_memory_gb=get_gpu_memory(),
    )


@app.get("/stats", response_model=StatsResponse)
async def get_stats():
    """Get service statistics."""
    global causal_graph, start_time
    
    if causal_graph is None:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    stats = causal_graph.get_stats()
    uptime = time.time() - start_time if start_time else 0
    
    return StatsResponse(
        node_count=stats["total_nodes"],
        edge_count=stats["total_edges"],
        domains=stats["domains"],
        types=stats["types"],
        queries=stats["queries"],
        chains_found=stats["chains_found"],
        device=stats["gpu_device"],
        uptime_seconds=uptime,
        gpu_memory_gb=get_gpu_memory(),
    )


@app.post("/causal_chains", response_model=CausalChainsResponse)
async def find_causal_chains(request: CausalChainsRequest):
    """
    Find causal chains between two nodes.
    
    Args:
        source_id: Starting node
        target_id: Ending node
        max_length: Maximum chain length
        min_strength: Minimum edge strength
        
    Returns:
        List of causal chains with strength scores
    """
    global causal_graph
    
    if causal_graph is None:
        raise HTTPException(status_code=503, detail="KG service not initialized")
    
    start = time.time()
    
    try:
        chains = causal_graph.find_causal_chains(
            source_id=request.source_id,
            target_id=request.target_id,
            max_length=request.max_length,
            min_strength=request.min_strength,
        )
        
        chains_data = [chain.to_dict() for chain in chains]
        latency = (time.time() - start) * 1000
        
        return CausalChainsResponse(
            chains=chains_data,
            count=len(chains_data),
            latency_ms=latency,
        )
        
    except Exception as e:
        logger.error(f"Causal chains error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/query", response_model=QueryResponse)
async def query_graph(request: QueryRequest):
    """
    Query the knowledge graph with natural language.
    
    Args:
        question: Natural language question
        entity: Optional entity to focus on
        domain: Optional domain filter
        max_results: Maximum results
        
    Returns:
        Query results
    """
    global causal_graph, embedding_service
    
    if causal_graph is None:
        raise HTTPException(status_code=503, detail="KG service not initialized")
    
    start = time.time()
    
    try:
        results = []
        
        # If we have embedding service, find similar nodes
        if embedding_service is not None:
            query_embedding = embedding_service.encode(request.question, task="query")
            similar = causal_graph.find_similar_nodes(
                query_embedding=query_embedding,
                top_k=request.max_results,
                domain_filter=request.domain,
            )
            
            for node_id, score in similar:
                node = causal_graph.nodes.get(node_id)
                if node:
                    results.append({
                        "id": node_id,
                        "name": node.name,
                        "type": node.node_type,
                        "domain": node.domain,
                        "similarity": score,
                    })
        
        # If entity specified, get subgraph
        if request.entity and request.entity in causal_graph.nodes:
            subgraph = causal_graph.get_subgraph(request.entity, radius=2)
            results.append({
                "type": "subgraph",
                "center": request.entity,
                "data": subgraph,
            })
        
        # List all nodes if no results yet
        if not results:
            for node_id, node in list(causal_graph.nodes.items())[:request.max_results]:
                if request.domain and node.domain != request.domain:
                    continue
                results.append({
                    "id": node_id,
                    "name": node.name,
                    "type": node.node_type,
                    "domain": node.domain,
                })
        
        latency = (time.time() - start) * 1000
        
        return QueryResponse(
            results=results,
            entities_found=len(results),
            latency_ms=latency,
        )
        
    except Exception as e:
        logger.error(f"Query error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/similar_nodes", response_model=SimilarNodesResponse)
async def find_similar_nodes(request: SimilarNodesRequest):
    """
    Find nodes similar to query text using GPU-accelerated embedding search.
    
    Args:
        query_text: Query text
        top_k: Number of results
        domain_filter: Optional domain filter
        type_filter: Optional type filter
        
    Returns:
        Similar nodes with similarity scores
    """
    global causal_graph, embedding_service
    
    if causal_graph is None:
        raise HTTPException(status_code=503, detail="KG service not initialized")
    
    if embedding_service is None:
        raise HTTPException(status_code=503, detail="Embedding service not available")
    
    start = time.time()
    
    try:
        query_embedding = embedding_service.encode(request.query_text, task="query")
        
        similar = causal_graph.find_similar_nodes(
            query_embedding=query_embedding,
            top_k=request.top_k,
            domain_filter=request.domain_filter,
            type_filter=request.type_filter,
        )
        
        nodes = []
        for node_id, score in similar:
            node = causal_graph.nodes.get(node_id)
            if node:
                nodes.append({
                    "id": node_id,
                    "name": node.name,
                    "type": node.node_type,
                    "domain": node.domain,
                    "similarity": score,
                })
        
        latency = (time.time() - start) * 1000
        
        return SimilarNodesResponse(
            nodes=nodes,
            count=len(nodes),
            latency_ms=latency,
        )
        
    except Exception as e:
        logger.error(f"Similar nodes error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/blocking_factors", response_model=BlockingFactorsResponse)
async def find_blocking_factors(request: BlockingFactorsRequest):
    """
    Find factors that block or mitigate effects on target.
    
    Args:
        target_id: Target node ID
        max_depth: Maximum search depth
        
    Returns:
        Blocking factors with details
    """
    global causal_graph
    
    if causal_graph is None:
        raise HTTPException(status_code=503, detail="KG service not initialized")
    
    start = time.time()
    
    try:
        factors = causal_graph.find_blocking_factors(
            target_id=request.target_id,
            max_depth=request.max_depth,
        )
        
        latency = (time.time() - start) * 1000
        
        return BlockingFactorsResponse(
            factors=factors,
            count=len(factors),
            latency_ms=latency,
        )
        
    except Exception as e:
        logger.error(f"Blocking factors error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/subgraph", response_model=SubgraphResponse)
async def get_subgraph(request: SubgraphRequest):
    """
    Get a subgraph around a center node.
    
    Args:
        center_node_id: Center node
        radius: Number of hops
        
    Returns:
        Subgraph with nodes and edges
    """
    global causal_graph
    
    if causal_graph is None:
        raise HTTPException(status_code=503, detail="KG service not initialized")
    
    start = time.time()
    
    try:
        subgraph = causal_graph.get_subgraph(
            center_node_id=request.center_node_id,
            radius=request.radius,
        )
        
        latency = (time.time() - start) * 1000
        
        return SubgraphResponse(
            nodes=subgraph["nodes"],
            edges=subgraph["edges"],
            latency_ms=latency,
        )
        
    except Exception as e:
        logger.error(f"Subgraph error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/nodes")
async def list_nodes(
    domain: Optional[str] = None,
    node_type: Optional[str] = None,
    limit: int = 100,
):
    """List all nodes with optional filtering."""
    global causal_graph
    
    if causal_graph is None:
        raise HTTPException(status_code=503, detail="KG service not initialized")
    
    nodes = []
    for node_id, node in causal_graph.nodes.items():
        if domain and node.domain != domain:
            continue
        if node_type and node.node_type != node_type:
            continue
        
        nodes.append({
            "id": node_id,
            "name": node.name,
            "type": node.node_type,
            "domain": node.domain,
        })
        
        if len(nodes) >= limit:
            break
    
    return {"nodes": nodes, "count": len(nodes)}


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Run the KG server."""
    import argparse
    
    parser = argparse.ArgumentParser(description="NSIC Knowledge Graph Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8101, help="Port to listen on")
    parser.add_argument("--workers", type=int, default=1, help="Number of workers")
    
    args = parser.parse_args()
    
    logger.info(f"Starting KG Server on {args.host}:{args.port}")
    
    uvicorn.run(
        "src.nsic.servers.kg_server:app",
        host=args.host,
        port=args.port,
        workers=args.workers,
        log_level="info",
    )


if __name__ == "__main__":
    main()

