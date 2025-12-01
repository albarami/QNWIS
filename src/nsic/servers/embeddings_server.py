"""
NSIC Embeddings Server - CPU Service

Enterprise-grade embedding service running on CPU:
- Runs on CPU (frees GPU for DeepSeek instances)
- Port 8100
- instructor-xl model loaded at startup
- Slightly slower than GPU but same quality

Endpoints:
- POST /embed - Encode texts to embeddings
- POST /search - Semantic search
- POST /similarity - Compute similarity scores
- GET /health - Health check
- GET /stats - Service statistics

Usage:
    python -m src.nsic.servers.embeddings_server --port 8100
"""

import logging
import os
import sys
import time
from typing import List, Optional
from contextlib import asynccontextmanager

import numpy as np
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

class EmbedRequest(BaseModel):
    """Request to encode texts to embeddings."""
    texts: List[str] = Field(..., description="List of texts to embed", min_length=1)
    task: str = Field("default", description="Task type: query, document, passage, summary, default")


class EmbedResponse(BaseModel):
    """Response with embeddings."""
    embeddings: List[List[float]] = Field(..., description="List of embedding vectors")
    dimension: int = Field(..., description="Embedding dimension")
    count: int = Field(..., description="Number of embeddings")
    latency_ms: float = Field(..., description="Processing time in milliseconds")


class SearchRequest(BaseModel):
    """Request for semantic search."""
    query: str = Field(..., description="Search query")
    documents: List[str] = Field(..., description="Documents to search")
    top_k: int = Field(10, description="Number of top results", ge=1, le=100)


class SearchResponse(BaseModel):
    """Response with search results."""
    results: List[dict] = Field(..., description="Search results with scores")
    query: str = Field(..., description="Original query")
    latency_ms: float = Field(..., description="Processing time in milliseconds")


class SimilarityRequest(BaseModel):
    """Request for similarity computation."""
    text1: str = Field(..., description="First text")
    text2: str = Field(..., description="Second text")


class SimilarityResponse(BaseModel):
    """Response with similarity score."""
    similarity: float = Field(..., description="Cosine similarity score")
    latency_ms: float = Field(..., description="Processing time in milliseconds")


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(..., description="Service status")
    model_loaded: bool = Field(..., description="Whether model is loaded")
    device: str = Field(..., description="GPU device being used")
    multi_gpu: bool = Field(False, description="Whether multi-GPU is enabled")
    gpu_ids: list = Field(default_factory=list, description="GPU IDs being used")
    gpu_memory_gb: float = Field(..., description="GPU memory used in GB")


class StatsResponse(BaseModel):
    """Service statistics response."""
    model_name: str
    device: str
    embedding_dim: int
    encode_calls: int
    total_texts_encoded: int
    uptime_seconds: float
    gpu_memory_gb: float


# ============================================================================
# Global State
# ============================================================================

embedding_service = None
start_time = None


def get_gpu_memory():
    """Get current GPU memory usage."""
    try:
        import torch
        if torch.cuda.is_available():
            return torch.cuda.memory_allocated(0) / 1e9
    except Exception:
        pass
    return 0.0


# ============================================================================
# Lifespan - Load model at startup
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load embedding model at startup, keep in GPU memory."""
    global embedding_service, start_time
    
    logger.info("=" * 60)
    logger.info("NSIC EMBEDDINGS SERVER - STARTUP")
    logger.info("=" * 60)
    
    try:
        # Import here to avoid issues when module is imported elsewhere
        from src.nsic.rag.premium_embeddings import PremiumEmbeddingService
        
        logger.info("Loading instructor-xl model to CPU...")
        load_start = time.time()
        
        embedding_service = PremiumEmbeddingService(
            device="cpu",
            gpu_ids=[],  # No GPUs - running on CPU
            cache_enabled=True,
            batch_size=32,
        )
        
        load_time = time.time() - load_start
        logger.info(f"Model loaded in {load_time:.2f}s")
        logger.info(f"Embedding dimension: {embedding_service.embedding_dim}")
        logger.info("Running on CPU (GPU freed for DeepSeek instances)")
        
        start_time = time.time()
        
        logger.info("=" * 60)
        logger.info("EMBEDDINGS SERVER READY - Models loaded on CPU")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Failed to load embedding model: {e}")
        raise
    
    yield
    
    # Cleanup
    logger.info("Shutting down embeddings server...")
    if embedding_service:
        embedding_service.close()


# ============================================================================
# FastAPI App
# ============================================================================

app = FastAPI(
    title="NSIC Embeddings Server",
    description="Enterprise-grade embedding service using instructor-xl on CPU",
    version="1.0.0",
    lifespan=lifespan,
)


def get_total_gpu_memory(gpu_ids):
    """Get total GPU memory across all specified GPUs."""
    try:
        import torch
        if torch.cuda.is_available():
            total = 0
            for gpu_id in gpu_ids:
                if gpu_id < torch.cuda.device_count():
                    total += torch.cuda.memory_allocated(gpu_id)
            return total / 1e9
    except Exception:
        pass
    return 0.0


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Check service health and GPU status."""
    global embedding_service
    
    gpu_ids = embedding_service.gpu_ids if embedding_service else [0]
    multi_gpu = embedding_service.multi_gpu if embedding_service else False
    
    return HealthResponse(
        status="healthy" if embedding_service is not None else "unhealthy",
        model_loaded=embedding_service is not None,
        device=str(embedding_service.device) if embedding_service else "none",
        multi_gpu=multi_gpu,
        gpu_ids=gpu_ids,
        gpu_memory_gb=get_total_gpu_memory(gpu_ids),
    )


@app.get("/stats", response_model=StatsResponse)
async def get_stats():
    """Get service statistics."""
    global embedding_service, start_time
    
    if embedding_service is None:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    uptime = time.time() - start_time if start_time else 0
    
    return StatsResponse(
        model_name=embedding_service.model_name,
        device=str(embedding_service.device),
        embedding_dim=embedding_service.embedding_dim,
        encode_calls=embedding_service._encode_calls,
        total_texts_encoded=embedding_service._total_texts,
        uptime_seconds=uptime,
        gpu_memory_gb=get_gpu_memory(),
    )


@app.post("/embed", response_model=EmbedResponse)
async def embed_texts(request: EmbedRequest):
    """
    Encode texts to embeddings.
    
    Args:
        texts: List of texts to encode
        task: Task type for instruction (query, document, passage, summary, default)
        
    Returns:
        List of embedding vectors
    """
    global embedding_service
    
    if embedding_service is None:
        raise HTTPException(status_code=503, detail="Embedding service not initialized")
    
    start = time.time()
    
    try:
        embeddings = embedding_service.encode(
            texts=request.texts,
            task=request.task,
        )
        
        # Convert to list format
        if isinstance(embeddings, np.ndarray):
            if len(embeddings.shape) == 1:
                embeddings = embeddings.reshape(1, -1)
            embeddings_list = embeddings.tolist()
        else:
            embeddings_list = [embeddings.tolist()]
        
        latency = (time.time() - start) * 1000
        
        return EmbedResponse(
            embeddings=embeddings_list,
            dimension=embedding_service.embedding_dim,
            count=len(embeddings_list),
            latency_ms=latency,
        )
        
    except Exception as e:
        logger.error(f"Embedding error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search", response_model=SearchResponse)
async def semantic_search(request: SearchRequest):
    """
    Perform semantic search over documents.
    
    Args:
        query: Search query
        documents: List of documents to search
        top_k: Number of top results to return
        
    Returns:
        Ranked search results with similarity scores
    """
    global embedding_service
    
    if embedding_service is None:
        raise HTTPException(status_code=503, detail="Embedding service not initialized")
    
    start = time.time()
    
    try:
        # Compute similarities
        similarities = embedding_service.similarity(
            query=request.query,
            documents=request.documents,
        )
        
        # Rank results
        indices = np.argsort(similarities)[::-1][:request.top_k]
        
        results = [
            {
                "index": int(idx),
                "document": request.documents[idx][:200] + "..." if len(request.documents[idx]) > 200 else request.documents[idx],
                "score": float(similarities[idx]),
            }
            for idx in indices
        ]
        
        latency = (time.time() - start) * 1000
        
        return SearchResponse(
            results=results,
            query=request.query,
            latency_ms=latency,
        )
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/similarity", response_model=SimilarityResponse)
async def compute_similarity(request: SimilarityRequest):
    """
    Compute cosine similarity between two texts.
    
    Args:
        text1: First text
        text2: Second text
        
    Returns:
        Cosine similarity score
    """
    global embedding_service
    
    if embedding_service is None:
        raise HTTPException(status_code=503, detail="Embedding service not initialized")
    
    start = time.time()
    
    try:
        emb1 = embedding_service.encode(request.text1)
        emb2 = embedding_service.encode(request.text2)
        
        # Cosine similarity (embeddings are normalized)
        similarity = float(np.dot(emb1, emb2))
        
        latency = (time.time() - start) * 1000
        
        return SimilarityResponse(
            similarity=similarity,
            latency_ms=latency,
        )
        
    except Exception as e:
        logger.error(f"Similarity error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Run the embeddings server."""
    import argparse
    
    parser = argparse.ArgumentParser(description="NSIC Embeddings Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8100, help="Port to listen on")
    parser.add_argument("--workers", type=int, default=1, help="Number of workers")
    
    args = parser.parse_args()
    
    logger.info(f"Starting Embeddings Server on {args.host}:{args.port}")
    
    uvicorn.run(
        "src.nsic.servers.embeddings_server:app",
        host=args.host,
        port=args.port,
        workers=args.workers,
        log_level="info",
    )


if __name__ == "__main__":
    main()

