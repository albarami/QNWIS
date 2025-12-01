"""
NSIC Verification Server - CPU Service

Enterprise-grade verification service running on CPU:
- Runs on CPU (frees GPU for DeepSeek instances)
- Port 8102
- CrossEncoder + DeBERTa NLI loaded at startup
- Slightly slower than GPU but same quality

Endpoints:
- POST /verify - Verify a claim against evidence
- POST /verify_batch - Verify multiple claims
- POST /verify_against_sources - Verify claim against multiple sources
- GET /health - Health check
- GET /stats - Service statistics

Usage:
    python -m src.nsic.servers.verification_server --port 8102
"""

import logging
import os
import sys
import time
from typing import List, Optional
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

class VerifyRequest(BaseModel):
    """Request to verify a claim."""
    claim: str = Field(..., description="Claim to verify")
    evidence: str = Field(..., description="Evidence text")


class VerifyResponse(BaseModel):
    """Verification result."""
    claim: str = Field(..., description="Original claim")
    score: float = Field(..., description="Verification score (0-1)")
    label: str = Field(..., description="Label: entailment, neutral, contradiction")
    confidence: float = Field(..., description="Model confidence")
    latency_ms: float = Field(..., description="Processing time")


class VerifyBatchRequest(BaseModel):
    """Request to verify multiple claims."""
    claims: List[str] = Field(..., description="List of claims to verify")
    evidences: List[str] = Field(..., description="List of evidence texts (same length as claims)")


class VerifyBatchResponse(BaseModel):
    """Batch verification results."""
    results: List[dict] = Field(..., description="Verification results")
    count: int = Field(..., description="Number of claims verified")
    latency_ms: float = Field(..., description="Total processing time")


class VerifyAgainstSourcesRequest(BaseModel):
    """Request to verify claim against multiple sources."""
    claim: str = Field(..., description="Claim to verify")
    sources: List[str] = Field(..., description="List of source texts")
    top_k: int = Field(3, description="Number of top sources to consider", ge=1, le=10)


class VerifyAgainstSourcesResponse(BaseModel):
    """Verification result against multiple sources."""
    claim: str = Field(..., description="Original claim")
    verified: bool = Field(..., description="Whether claim is verified")
    confidence: float = Field(..., description="Aggregated confidence")
    label: str = Field(..., description="Overall label")
    score: float = Field(..., description="Aggregated score")
    sources_checked: int = Field(..., description="Number of sources checked")
    top_sources: List[dict] = Field(..., description="Top matching sources")
    latency_ms: float = Field(..., description="Processing time")


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(..., description="Service status")
    cross_encoder_loaded: bool = Field(..., description="CrossEncoder loaded")
    nli_model_loaded: bool = Field(..., description="NLI model loaded")
    device: str = Field(..., description="GPU device")
    gpu_memory_gb: float = Field(..., description="GPU memory used")


class StatsResponse(BaseModel):
    """Service statistics."""
    verifications: int
    batches_processed: int
    total_time_ms: float
    avg_time_per_verification_ms: float
    device: str
    cross_encoder_enabled: bool
    nli_enabled: bool
    uptime_seconds: float
    gpu_memory_gb: float


# ============================================================================
# Global State
# ============================================================================

verifier = None
start_time = None


def get_gpu_memory():
    """Get current GPU memory usage."""
    try:
        import torch
        if torch.cuda.is_available():
            return torch.cuda.memory_allocated(0) / 1e9  # First visible device
    except Exception:
        pass
    return 0.0


# ============================================================================
# Lifespan - Load models at startup
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load verification models at startup, keep in GPU memory."""
    global verifier, start_time
    
    logger.info("=" * 60)
    logger.info("NSIC VERIFICATION SERVER - STARTUP")
    logger.info("=" * 60)
    
    try:
        from src.nsic.verification.deep_verifier import DeepVerifier
        
        logger.info("Loading CrossEncoder + DeBERTa NLI models to CPU...")
        load_start = time.time()
        
        verifier = DeepVerifier(
            device="cpu",  # Running on CPU to free GPU for DeepSeek
            gpu_id=None,
            batch_size=8,
            window_ms=15.0,
            enable_cross_encoder=True,
            enable_nli=True,
        )
        
        load_time = time.time() - load_start
        logger.info(f"Models loaded in {load_time:.2f}s")
        logger.info(f"CrossEncoder loaded: {verifier.cross_encoder is not None}")
        logger.info(f"NLI model loaded: {verifier.nli_model is not None}")
        logger.info("Running on CPU (GPU freed for DeepSeek instances)")
        
        # Warm up models with a test verification
        logger.info("Warming up models...")
        _ = verifier.verify("test claim", "test evidence")
        logger.info(f"Warm-up complete. GPU memory: {get_gpu_memory():.2f} GB")
        
        start_time = time.time()
        
        logger.info("=" * 60)
        logger.info("VERIFICATION SERVER READY - Models PERSISTENT in GPU memory")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Failed to load verification models: {e}")
        raise
    
    yield
    
    # Cleanup
    logger.info("Shutting down verification server...")


# ============================================================================
# FastAPI App
# ============================================================================

app = FastAPI(
    title="NSIC Verification Server",
    description="Enterprise-grade persistent verification service using CrossEncoder + DeBERTa NLI on GPU 5",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Check service health and GPU status."""
    global verifier
    
    return HealthResponse(
        status="healthy" if verifier is not None else "unhealthy",
        cross_encoder_loaded=verifier.cross_encoder is not None if verifier else False,
        nli_model_loaded=verifier.nli_model is not None if verifier else False,
        device=str(verifier.device) if verifier else "none",
        gpu_memory_gb=get_gpu_memory(),
    )


@app.get("/stats", response_model=StatsResponse)
async def get_stats():
    """Get service statistics."""
    global verifier, start_time
    
    if verifier is None:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    stats = verifier.get_stats()
    uptime = time.time() - start_time if start_time else 0
    
    return StatsResponse(
        verifications=stats["verifications"],
        batches_processed=stats["batches_processed"],
        total_time_ms=stats["total_time_ms"],
        avg_time_per_verification_ms=stats["avg_time_per_verification_ms"],
        device=stats["device"],
        cross_encoder_enabled=stats["cross_encoder_enabled"],
        nli_enabled=stats["nli_enabled"],
        uptime_seconds=uptime,
        gpu_memory_gb=get_gpu_memory(),
    )


@app.post("/verify", response_model=VerifyResponse)
async def verify_claim(request: VerifyRequest):
    """
    Verify a single claim against evidence.
    
    Uses 3-layer verification:
    1. CrossEncoder relevance scoring
    2. NLI entailment classification
    3. Contradiction detection
    
    Args:
        claim: Claim to verify
        evidence: Evidence text
        
    Returns:
        Verification result with score and label
    """
    global verifier
    
    if verifier is None:
        raise HTTPException(status_code=503, detail="Verification service not initialized")
    
    start = time.time()
    
    try:
        result = verifier.verify(
            claim=request.claim,
            evidence=request.evidence,
        )
        
        latency = (time.time() - start) * 1000
        
        return VerifyResponse(
            claim=result.claim,
            score=result.score,
            label=result.label,
            confidence=result.confidence,
            latency_ms=latency,
        )
        
    except Exception as e:
        logger.error(f"Verification error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/verify_batch", response_model=VerifyBatchResponse)
async def verify_batch(request: VerifyBatchRequest):
    """
    Verify multiple claims against their evidence.
    
    Uses micro-batching for efficient GPU utilization.
    
    Args:
        claims: List of claims
        evidences: List of evidence texts (same length as claims)
        
    Returns:
        Verification results for all claims
    """
    global verifier
    
    if verifier is None:
        raise HTTPException(status_code=503, detail="Verification service not initialized")
    
    if len(request.claims) != len(request.evidences):
        raise HTTPException(
            status_code=400,
            detail=f"Claims ({len(request.claims)}) and evidences ({len(request.evidences)}) must have same length"
        )
    
    start = time.time()
    
    try:
        results = verifier.verify_batch(
            claims=request.claims,
            evidences=request.evidences,
        )
        
        results_data = [
            {
                "claim": r.claim,
                "evidence": r.evidence[:100] + "..." if len(r.evidence) > 100 else r.evidence,
                "score": r.score,
                "label": r.label,
                "confidence": r.confidence,
                "timing_ms": r.timing_ms,
            }
            for r in results
        ]
        
        latency = (time.time() - start) * 1000
        
        return VerifyBatchResponse(
            results=results_data,
            count=len(results_data),
            latency_ms=latency,
        )
        
    except Exception as e:
        logger.error(f"Batch verification error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/verify_against_sources", response_model=VerifyAgainstSourcesResponse)
async def verify_against_sources(request: VerifyAgainstSourcesRequest):
    """
    Verify a claim against multiple sources.
    
    Aggregates results from top_k sources to determine verification.
    
    Args:
        claim: Claim to verify
        sources: List of source texts
        top_k: Number of top sources to consider
        
    Returns:
        Aggregated verification result
    """
    global verifier
    
    if verifier is None:
        raise HTTPException(status_code=503, detail="Verification service not initialized")
    
    start = time.time()
    
    try:
        result = verifier.verify_claim_against_sources(
            claim=request.claim,
            sources=request.sources,
            top_k=request.top_k,
        )
        
        latency = (time.time() - start) * 1000
        
        return VerifyAgainstSourcesResponse(
            claim=result["claim"],
            verified=result["verified"],
            confidence=result["confidence"],
            label=result["label"],
            score=result["score"],
            sources_checked=result["sources_checked"],
            top_sources=result["top_sources"],
            latency_ms=latency,
        )
        
    except Exception as e:
        logger.error(f"Source verification error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Run the verification server."""
    import argparse
    
    parser = argparse.ArgumentParser(description="NSIC Verification Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8102, help="Port to listen on")
    parser.add_argument("--workers", type=int, default=1, help="Number of workers")
    
    args = parser.parse_args()
    
    logger.info(f"Starting Verification Server on {args.host}:{args.port}")
    
    uvicorn.run(
        "src.nsic.servers.verification_server:app",
        host=args.host,
        port=args.port,
        workers=args.workers,
        log_level="info",
    )


if __name__ == "__main__":
    main()

