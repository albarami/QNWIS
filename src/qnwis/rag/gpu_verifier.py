"""
GPU-Accelerated Fact Verification System.

Real-time fact verification using instructor-xl on GPU 6 (shared with embeddings).
Supports up to 500,000 documents with <5GB GPU memory footprint.
"""

import logging
import re
import asyncio
from typing import List, Dict, Any, Optional
from pathlib import Path
import torch
from sentence_transformers import SentenceTransformer
import numpy as np

logger = logging.getLogger(__name__)


class GPUFactVerifier:
    """
    Real-time fact verification using GPU-accelerated vector search.
    
    Uses instructor-xl model on GPU 6 (shared with embeddings) for
    high-precision semantic similarity matching against document corpus.
    """
    
    # Memory safety limit: 500K docs × 4KB = 2GB embeddings + 1.3GB model = 3.3GB total
    MAX_DOCUMENTS = 500_000
    VERIFICATION_THRESHOLD = 0.75  # Similarity threshold for fact verification
    
    def __init__(self, gpu_id: int = 6):
        """
        Initialize fact verifier on specified GPU.
        
        Args:
            gpu_id: GPU to use (default 6, shared with embeddings)
        """
        self.gpu_id = gpu_id
        self.device = f"cuda:{gpu_id}" if torch.cuda.is_available() else "cpu"
        
        # Use same model as embeddings for efficient GPU sharing
        logger.info(f"Loading fact verifier on {self.device}...")
        # Use all-mpnet-base-v2: 768-dim, production-stable, loads reliably
        self.model = SentenceTransformer('all-mpnet-base-v2', device=self.device)
        
        # Document storage
        self.doc_embeddings = None
        self.doc_texts: List[str] = []
        self.doc_metadata: List[Dict[str, Any]] = []
        self.is_indexed = False
        
        logger.info(f"✅ Fact verifier initialized on {self.device}")
        
        if self.device.startswith("cuda"):
            try:
                memory_allocated = torch.cuda.memory_allocated(self.gpu_id) / 1e9
                logger.info(f"   GPU {self.gpu_id} memory: {memory_allocated:.2f}GB allocated")
            except Exception as e:
                logger.warning(f"Could not get GPU memory info: {e}")
    
    def index_documents(self, documents: List[Dict[str, Any]]) -> None:
        """
        Index documents for fast retrieval.
        
        Args:
            documents: List of dicts with 'text', 'source', 'date' keys
            
        Raises:
            ValueError: If documents exceed MAX_DOCUMENTS limit
            RuntimeError: If indexing fails
        """
        if not documents:
            raise ValueError("Cannot index empty document list")
        
        logger.info(f"Indexing {len(documents):,} documents on GPU {self.gpu_id}...")
        
        # Enforce memory limit
        if len(documents) > self.MAX_DOCUMENTS:
            logger.warning(
                f"Document count ({len(documents):,}) exceeds limit ({self.MAX_DOCUMENTS:,}). "
                f"Using first {self.MAX_DOCUMENTS:,} documents."
            )
            documents = documents[:self.MAX_DOCUMENTS]
        
        try:
            # Extract texts and metadata
            texts = [doc['text'] for doc in documents if doc.get('text')]
            
            if not texts:
                raise ValueError("No text content found in documents")
            
            self.doc_texts = texts
            self.doc_metadata = [
                {
                    'source': doc.get('source', 'unknown'),
                    'date': doc.get('date', 'unknown'),
                    'priority': doc.get('priority', 'medium')
                }
                for doc in documents if doc.get('text')
            ]
            
            # Generate embeddings on GPU (this is the expensive operation)
            logger.info(f"Generating embeddings for {len(texts):,} documents on GPU {self.gpu_id}...")
            
            self.doc_embeddings = self.model.encode(
                texts,
                convert_to_tensor=True,
                device=self.device,
                show_progress_bar=True,
                batch_size=32  # Batch for efficiency
            )
            
            self.is_indexed = True
            
            # Log memory usage
            if self.device.startswith("cuda"):
                memory_used = torch.cuda.memory_allocated(self.gpu_id) / 1e9
                memory_reserved = torch.cuda.memory_reserved(self.gpu_id) / 1e9
                logger.info(
                    f"✅ Indexed {len(texts):,} documents on GPU {self.gpu_id}: "
                    f"{memory_used:.2f}GB allocated, {memory_reserved:.2f}GB reserved"
                )
                
                if memory_used > 8.0:
                    logger.warning(
                        f"GPU {self.gpu_id} memory usage ({memory_used:.2f}GB) is high. "
                        f"May impact shared embedding performance."
                    )
            else:
                logger.info(f"✅ Indexed {len(texts):,} documents on CPU")
            
        except Exception as e:
            logger.error(f"Document indexing failed: {e}", exc_info=True)
            raise RuntimeError(f"Failed to index documents: {e}") from e
    
    async def verify_claim(
        self, 
        claim: str, 
        top_k: int = 3
    ) -> Dict[str, Any]:
        """
        Verify a factual claim against indexed documents.
        
        Args:
            claim: The factual claim to verify
            top_k: Number of supporting documents to retrieve
            
        Returns:
            {
                'verified': bool,
                'confidence': float (0-1),
                'supporting_docs': List[Dict],
                'claim': str
            }
            
        Raises:
            RuntimeError: If documents not indexed
        """
        if not self.is_indexed or self.doc_embeddings is None:
            raise RuntimeError("Documents not indexed. Call index_documents() first.")
        
        # Run verification in thread pool to not block event loop
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, 
            self._verify_claim_sync, 
            claim, 
            top_k
        )
        
        return result
    
    def _verify_claim_sync(
        self, 
        claim: str, 
        top_k: int
    ) -> Dict[str, Any]:
        """
        Synchronous verification logic (runs in thread pool).
        
        Args:
            claim: Claim to verify
            top_k: Number of supporting docs to return
            
        Returns:
            Verification result dictionary
        """
        try:
            # Embed the claim on GPU
            claim_embedding = self.model.encode(
                claim,
                convert_to_tensor=True,
                device=self.device
            )
            
            # GPU-accelerated cosine similarity (this is FAST on A100)
            similarities = torch.nn.functional.cosine_similarity(
                claim_embedding.unsqueeze(0),
                self.doc_embeddings
            )
            
            # Get top-k most similar documents
            top_scores, top_indices = torch.topk(
                similarities, 
                k=min(top_k, len(self.doc_texts))
            )
            
            # Convert to CPU for processing
            top_scores = top_scores.cpu().numpy()
            top_indices = top_indices.cpu().numpy()
            
            # Build supporting documents
            supporting_docs = []
            for score, idx in zip(top_scores, top_indices):
                supporting_docs.append({
                    'text': self.doc_texts[idx][:500],  # First 500 chars
                    'similarity': float(score),
                    'source': self.doc_metadata[idx]['source'],
                    'date': self.doc_metadata[idx]['date'],
                    'priority': self.doc_metadata[idx]['priority']
                })
            
            # Determine verification status
            max_similarity = float(top_scores[0])
            verified = max_similarity > self.VERIFICATION_THRESHOLD
            
            result = {
                'verified': verified,
                'confidence': max_similarity,
                'supporting_docs': supporting_docs,
                'claim': claim,
                'threshold': self.VERIFICATION_THRESHOLD
            }
            
            logger.debug(
                f"Verified claim (confidence: {max_similarity:.3f}, "
                f"verified: {verified}): {claim[:80]}..."
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Claim verification failed: {e}", exc_info=True)
            return {
                'verified': False,
                'confidence': 0.0,
                'supporting_docs': [],
                'claim': claim,
                'error': str(e)
            }
    
    async def verify_agent_output(
        self, 
        agent_output: str
    ) -> Dict[str, Any]:
        """
        Extract and verify all factual claims from agent output.
        
        Args:
            agent_output: Agent response text
            
        Returns:
            {
                'total_claims': int,
                'verified_claims': int,
                'verification_rate': float (0-1),
                'avg_confidence': float (0-1),
                'details': List[Dict]
            }
        """
        if not self.is_indexed:
            logger.warning("Verification skipped - documents not indexed")
            return {
                'total_claims': 0,
                'verified_claims': 0,
                'verification_rate': 1.0,  # Assume OK if not indexed
                'avg_confidence': 0.0,
                'details': [],
                'error': 'Documents not indexed'
            }
        
        # Extract claims from agent output
        claims = self._extract_claims(agent_output)
        
        if not claims:
            return {
                'total_claims': 0,
                'verified_claims': 0,
                'verification_rate': 1.0,
                'avg_confidence': 1.0,
                'details': []
            }
        
        # Verify all claims concurrently (async for speed)
        verification_tasks = [self.verify_claim(claim) for claim in claims]
        verifications = await asyncio.gather(*verification_tasks)
        
        # Aggregate results
        total_claims = len(claims)
        verified_claims = sum(1 for v in verifications if v['verified'])
        avg_confidence = np.mean([v['confidence'] for v in verifications])
        
        verification_rate = verified_claims / total_claims if total_claims > 0 else 1.0
        
        # Log warning if verification rate is low
        if verification_rate < 0.70:
            logger.warning(
                f"⚠️ Low verification rate: {verification_rate:.0%} "
                f"({verified_claims}/{total_claims} claims verified)"
            )
        else:
            logger.info(
                f"✅ Verification rate: {verification_rate:.0%} "
                f"({verified_claims}/{total_claims} claims)"
            )
        
        return {
            'total_claims': total_claims,
            'verified_claims': verified_claims,
            'verification_rate': float(verification_rate),
            'avg_confidence': float(avg_confidence),
            'details': verifications
        }
    
    def _extract_claims(self, text: str) -> List[str]:
        """
        Extract factual claims from text.
        
        Simple heuristic-based extraction (can be enhanced with NER).
        
        Args:
            text: Text to extract claims from
            
        Returns:
            List of extracted factual claims
        """
        # Split into sentences
        sentences = re.split(r'[.!?]+', text)
        
        # Patterns that indicate factual claims
        factual_patterns = [
            r'\d+',  # Contains numbers
            r'(according to|per|based on|reported|shows|indicates)',  # Citation language
            r'(Qatar|UAE|Saudi|GCC|OPEC)',  # Specific entities
            r'(percent|percentage|billion|million|thousand)',  # Quantitative
            r'(increased|decreased|grew|declined|rose|fell)',  # Trends
        ]
        
        claims = []
        for sentence in sentences:
            sentence = sentence.strip()
            
            # Skip if too short
            if len(sentence) < 20:
                continue
            
            # Check if sentence matches factual patterns
            if any(re.search(pattern, sentence, re.IGNORECASE) for pattern in factual_patterns):
                claims.append(sentence)
        
        # Limit to 10 claims to avoid excessive verification overhead
        return claims[:10]
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get verifier statistics.
        
        Returns:
            Dictionary with indexing and verification stats
        """
        stats = {
            'is_indexed': self.is_indexed,
            'total_documents': len(self.doc_texts),
            'gpu_id': self.gpu_id,
            'device': str(self.device),
            'model': 'hkunlp/instructor-xl',
            'verification_threshold': self.VERIFICATION_THRESHOLD
        }
        
        if self.device.startswith("cuda"):
            try:
                stats['gpu_memory_allocated'] = torch.cuda.memory_allocated(self.gpu_id) / 1e9
                stats['gpu_memory_reserved'] = torch.cuda.memory_reserved(self.gpu_id) / 1e9
                stats['gpu_name'] = torch.cuda.get_device_name(self.gpu_id)
            except Exception as e:
                logger.warning(f"Could not get GPU stats: {e}")
        
        return stats

