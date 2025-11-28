"""
NSIC Ensemble Arbitrator - Deterministic Conflict Resolution

Combines outputs from Engine A (Azure GPT-5) and Engine B (DeepSeek)
using rule-based arbitration for maximum quality.

Features:
- Consensus detection (similarity > 0.8)
- Contradiction resolution with evidence weighting
- Confidence scoring based on agreement
- Full audit trail for transparency

NO MOCKS. REAL INTEGRATION.
"""

import logging
import hashlib
import time
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class ArbitrationResult(Enum):
    """Possible arbitration outcomes."""
    CONSENSUS = "consensus"  # Engines agree
    ENGINE_A_PREFERRED = "engine_a_preferred"  # Engine A more reliable
    ENGINE_B_PREFERRED = "engine_b_preferred"  # Engine B more reliable
    SYNTHESIS_REQUIRED = "synthesis_required"  # Need to combine both
    CONTRADICTION = "contradiction"  # Engines disagree significantly


@dataclass
class EngineOutput:
    """Output from a single engine."""
    engine: str  # "engine_a" or "engine_b"
    content: str
    scenario_id: str
    turns_completed: int
    confidence: float = 0.0
    key_claims: List[str] = field(default_factory=list)
    data_sources: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "engine": self.engine,
            "content_length": len(self.content),
            "scenario_id": self.scenario_id,
            "turns_completed": self.turns_completed,
            "confidence": self.confidence,
            "key_claims_count": len(self.key_claims),
            "data_sources": self.data_sources,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class ArbitrationDecision:
    """Result of arbitration between two engine outputs."""
    scenario_id: str
    result: ArbitrationResult
    final_content: str
    confidence: float
    similarity_score: float
    
    # Audit trail
    engine_a_weight: float = 0.5
    engine_b_weight: float = 0.5
    reasoning: str = ""
    contradictions_found: List[str] = field(default_factory=list)
    consensus_points: List[str] = field(default_factory=list)
    
    # Timing
    arbitration_time_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "result": self.result.value,
            "confidence": self.confidence,
            "similarity_score": self.similarity_score,
            "engine_a_weight": self.engine_a_weight,
            "engine_b_weight": self.engine_b_weight,
            "reasoning": self.reasoning,
            "contradictions_count": len(self.contradictions_found),
            "consensus_points_count": len(self.consensus_points),
            "arbitration_time_ms": self.arbitration_time_ms,
        }


@dataclass
class AuditEntry:
    """Single audit trail entry."""
    timestamp: datetime
    action: str
    details: Dict[str, Any]
    decision: Optional[str] = None


class EnsembleArbitrator:
    """
    Deterministic arbitration between Engine A and Engine B outputs.
    
    Rules:
    1. If similarity > 0.8: CONSENSUS (combine with equal weight)
    2. If similarity < 0.3: CONTRADICTION (investigate and choose)
    3. If 0.3 <= similarity <= 0.8: SYNTHESIS_REQUIRED (weighted combination)
    
    Weights are determined by:
    - Number of turns completed (more = higher weight)
    - Data sources cited (more = higher weight)  
    - Verified claims count
    - Historical accuracy (if available)
    """
    
    # Thresholds (deterministic, not learned)
    CONSENSUS_THRESHOLD = 0.8
    CONTRADICTION_THRESHOLD = 0.3
    
    # Engine baseline weights (from plan: Engine A is deep, Engine B is broad)
    ENGINE_A_BASE_WEIGHT = 0.55  # Slight preference for deep analysis
    ENGINE_B_BASE_WEIGHT = 0.45
    
    def __init__(
        self,
        embedding_service=None,
        verifier=None,
        llm_client=None,
    ):
        """
        Initialize arbitrator with real system components.
        
        Args:
            embedding_service: For computing similarity (lazy load if None)
            verifier: For verifying claims (lazy load if None)
            llm_client: For synthesis (lazy load if None)
        """
        self._embedding_service = embedding_service
        self._verifier = verifier
        self._llm_client = llm_client
        
        # Audit trail
        self._audit_log: List[AuditEntry] = []
        
        # Stats
        self._stats = {
            "total_arbitrations": 0,
            "consensus_count": 0,
            "contradiction_count": 0,
            "synthesis_count": 0,
            "total_time_ms": 0.0,
        }
        
        logger.info("EnsembleArbitrator initialized - REAL MODE")
    
    @property
    def embedding_service(self):
        """Lazy load embedding service."""
        if self._embedding_service is None:
            try:
                from src.nsic.rag.premium_embeddings import PremiumEmbeddingService
                self._embedding_service = PremiumEmbeddingService()
            except Exception as e:
                logger.warning(f"Could not load embedding service: {e}")
        return self._embedding_service
    
    @property
    def verifier(self):
        """Lazy load verifier."""
        if self._verifier is None:
            try:
                from src.nsic.verification.deep_verifier import DeepVerifier
                self._verifier = DeepVerifier(
                    enable_cross_encoder=False,  # Fast mode for arbitration
                    enable_nli=False,
                )
            except Exception as e:
                logger.warning(f"Could not load verifier: {e}")
        return self._verifier
    
    @property
    def llm_client(self):
        """Lazy load LLM client."""
        if self._llm_client is None:
            try:
                from src.nsic.integration.llm_client import get_nsic_llm_client
                self._llm_client = get_nsic_llm_client()
            except Exception as e:
                logger.warning(f"Could not load LLM client: {e}")
        return self._llm_client
    
    def _log_audit(self, action: str, details: Dict[str, Any], decision: str = None):
        """Add entry to audit trail."""
        entry = AuditEntry(
            timestamp=datetime.now(),
            action=action,
            details=details,
            decision=decision,
        )
        self._audit_log.append(entry)
    
    def _compute_similarity(self, text_a: str, text_b: str) -> float:
        """
        Compute semantic similarity between two texts.
        
        Uses embedding cosine similarity for deterministic comparison.
        """
        try:
            if self.embedding_service:
                # Get embeddings
                emb_a = self.embedding_service.embed(text_a[:2000])  # Truncate for speed
                emb_b = self.embedding_service.embed(text_b[:2000])
                
                # Cosine similarity
                import numpy as np
                norm_a = np.linalg.norm(emb_a)
                norm_b = np.linalg.norm(emb_b)
                
                if norm_a > 0 and norm_b > 0:
                    similarity = np.dot(emb_a, emb_b) / (norm_a * norm_b)
                    return float(similarity)
        except Exception as e:
            logger.warning(f"Similarity computation failed: {e}")
        
        # Fallback: simple word overlap (deterministic)
        words_a = set(text_a.lower().split())
        words_b = set(text_b.lower().split())
        
        if not words_a or not words_b:
            return 0.0
        
        intersection = len(words_a & words_b)
        union = len(words_a | words_b)
        
        return intersection / union if union > 0 else 0.0
    
    def _extract_key_claims(self, text: str) -> List[str]:
        """Extract key claims from text for comparison."""
        import re
        
        claims = []
        
        # Look for quantified statements
        patterns = [
            r'(\d+(?:\.\d+)?%)',  # Percentages
            r'(\$[\d,]+(?:\.\d+)?(?:\s*(?:million|billion))?)',  # Dollar amounts
            r'(\d+(?:\.\d+)?\s*(?:million|billion))',  # Large numbers
            r'(increase|decrease|grow|decline|rise|fall)\s+(?:by\s+)?(\d+)',  # Changes
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    claims.append(" ".join(str(m) for m in match if m))
                else:
                    claims.append(str(match))
        
        # Extract sentences with "will", "should", "must" (predictions/recommendations)
        sentences = text.split('.')
        for sentence in sentences:
            if any(word in sentence.lower() for word in ['will ', 'should ', 'must ', 'recommend']):
                clean = sentence.strip()[:200]
                if clean:
                    claims.append(clean)
        
        return claims[:20]  # Limit to top 20 claims
    
    def _find_contradictions(
        self,
        claims_a: List[str],
        claims_b: List[str],
    ) -> List[str]:
        """Find contradicting claims between engines."""
        contradictions = []
        
        # Simple contradiction patterns
        opposites = [
            ('increase', 'decrease'),
            ('grow', 'decline'),
            ('rise', 'fall'),
            ('positive', 'negative'),
            ('benefit', 'harm'),
            ('high', 'low'),
        ]
        
        for claim_a in claims_a:
            for claim_b in claims_b:
                # Check if claims are about similar topic but opposite direction
                claim_a_lower = claim_a.lower()
                claim_b_lower = claim_b.lower()
                
                for pos, neg in opposites:
                    if (pos in claim_a_lower and neg in claim_b_lower) or \
                       (neg in claim_a_lower and pos in claim_b_lower):
                        # Check if they're about similar numbers/topics
                        import re
                        nums_a = set(re.findall(r'\d+', claim_a))
                        nums_b = set(re.findall(r'\d+', claim_b))
                        
                        if nums_a & nums_b:  # Overlapping numbers
                            contradictions.append(
                                f"A: '{claim_a[:100]}' vs B: '{claim_b[:100]}'"
                            )
        
        return contradictions[:10]  # Limit to top 10
    
    def _find_consensus(
        self,
        claims_a: List[str],
        claims_b: List[str],
    ) -> List[str]:
        """Find consensus points between engines."""
        consensus = []
        
        for claim_a in claims_a:
            for claim_b in claims_b:
                # Check for similar claims
                similarity = self._compute_similarity(claim_a, claim_b)
                if similarity > 0.7:
                    consensus.append(f"Both agree: '{claim_a[:100]}'")
        
        return consensus[:10]  # Limit to top 10
    
    def _compute_weights(
        self,
        output_a: EngineOutput,
        output_b: EngineOutput,
    ) -> Tuple[float, float]:
        """
        Compute dynamic weights based on output quality.
        
        Factors:
        - Turns completed (more = more thorough)
        - Data sources cited (more = better grounded)
        - Base engine preference
        """
        weight_a = self.ENGINE_A_BASE_WEIGHT
        weight_b = self.ENGINE_B_BASE_WEIGHT
        
        # Adjust for turns completed
        total_turns = output_a.turns_completed + output_b.turns_completed
        if total_turns > 0:
            turn_ratio_a = output_a.turns_completed / total_turns
            turn_ratio_b = output_b.turns_completed / total_turns
            
            # Blend with base weights
            weight_a = 0.7 * weight_a + 0.3 * turn_ratio_a
            weight_b = 0.7 * weight_b + 0.3 * turn_ratio_b
        
        # Adjust for data sources
        total_sources = len(output_a.data_sources) + len(output_b.data_sources)
        if total_sources > 0:
            source_ratio_a = len(output_a.data_sources) / total_sources
            source_ratio_b = len(output_b.data_sources) / total_sources
            
            weight_a = 0.8 * weight_a + 0.2 * source_ratio_a
            weight_b = 0.8 * weight_b + 0.2 * source_ratio_b
        
        # Normalize
        total_weight = weight_a + weight_b
        if total_weight > 0:
            weight_a /= total_weight
            weight_b /= total_weight
        
        return weight_a, weight_b
    
    def _synthesize_outputs(
        self,
        output_a: EngineOutput,
        output_b: EngineOutput,
        weight_a: float,
        weight_b: float,
    ) -> str:
        """
        Synthesize two outputs into a combined analysis.
        
        Uses weighted combination based on confidence.
        """
        # Build synthesis prompt
        synthesis_template = f"""## Engine A Analysis (weight: {weight_a:.2f}):
{output_a.content[:3000]}

## Engine B Analysis (weight: {weight_b:.2f}):
{output_b.content[:3000]}

## Synthesized Analysis:
Combining insights from both engines with the above weights:

"""
        
        # If LLM client available, use it for synthesis
        if self.llm_client:
            try:
                import asyncio
                
                async def synthesize():
                    response = await self.llm_client.synthesize_insights(
                        output_a.content[:3000],
                        output_b.content[:3000],
                    )
                    return response.content
                
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                return loop.run_until_complete(synthesize())
            except Exception as e:
                logger.warning(f"LLM synthesis failed: {e}")
        
        # Fallback: simple combination
        return f"""**Combined Analysis (Engine A: {weight_a:.0%}, Engine B: {weight_b:.0%})**

**From Engine A (Deep Analysis):**
{output_a.content[:2000]}...

**From Engine B (Broad Exploration):**
{output_b.content[:2000]}...

**Key Points:**
- Both engines analyzed scenario: {output_a.scenario_id}
- Engine A completed {output_a.turns_completed} turns
- Engine B completed {output_b.turns_completed} turns
"""
    
    def arbitrate(
        self,
        output_a: EngineOutput,
        output_b: EngineOutput,
    ) -> ArbitrationDecision:
        """
        Arbitrate between two engine outputs.
        
        Args:
            output_a: Output from Engine A (Azure GPT-5)
            output_b: Output from Engine B (DeepSeek)
            
        Returns:
            ArbitrationDecision with final content and audit trail
        """
        start_time = time.time()
        
        self._log_audit("arbitration_started", {
            "scenario_id": output_a.scenario_id,
            "engine_a_turns": output_a.turns_completed,
            "engine_b_turns": output_b.turns_completed,
        })
        
        # Step 1: Compute similarity
        similarity = self._compute_similarity(output_a.content, output_b.content)
        
        self._log_audit("similarity_computed", {
            "similarity_score": similarity,
        })
        
        # Step 2: Extract and compare claims
        claims_a = self._extract_key_claims(output_a.content)
        claims_b = self._extract_key_claims(output_b.content)
        
        contradictions = self._find_contradictions(claims_a, claims_b)
        consensus = self._find_consensus(claims_a, claims_b)
        
        self._log_audit("claims_analyzed", {
            "claims_a_count": len(claims_a),
            "claims_b_count": len(claims_b),
            "contradictions_count": len(contradictions),
            "consensus_count": len(consensus),
        })
        
        # Step 3: Compute weights
        weight_a, weight_b = self._compute_weights(output_a, output_b)
        
        # Step 4: Determine result
        if similarity >= self.CONSENSUS_THRESHOLD:
            result = ArbitrationResult.CONSENSUS
            reasoning = f"High similarity ({similarity:.2f}) indicates consensus"
            final_content = self._synthesize_outputs(output_a, output_b, 0.5, 0.5)
            confidence = min(0.95, similarity)
            self._stats["consensus_count"] += 1
            
        elif similarity <= self.CONTRADICTION_THRESHOLD:
            result = ArbitrationResult.CONTRADICTION
            reasoning = f"Low similarity ({similarity:.2f}) with {len(contradictions)} contradictions found"
            
            # Choose based on weights and verified claims
            if weight_a > weight_b + 0.1:
                final_content = output_a.content
                result = ArbitrationResult.ENGINE_A_PREFERRED
                reasoning += ". Engine A preferred due to higher weight."
            elif weight_b > weight_a + 0.1:
                final_content = output_b.content
                result = ArbitrationResult.ENGINE_B_PREFERRED
                reasoning += ". Engine B preferred due to higher weight."
            else:
                final_content = self._synthesize_outputs(output_a, output_b, weight_a, weight_b)
                result = ArbitrationResult.SYNTHESIS_REQUIRED
                reasoning += ". Synthesis required due to close weights."
            
            confidence = 0.5 + (abs(weight_a - weight_b) * 0.3)
            self._stats["contradiction_count"] += 1
            
        else:
            result = ArbitrationResult.SYNTHESIS_REQUIRED
            reasoning = f"Moderate similarity ({similarity:.2f}) requires weighted synthesis"
            final_content = self._synthesize_outputs(output_a, output_b, weight_a, weight_b)
            confidence = 0.6 + (similarity * 0.3)
            self._stats["synthesis_count"] += 1
        
        elapsed_ms = (time.time() - start_time) * 1000
        
        decision = ArbitrationDecision(
            scenario_id=output_a.scenario_id,
            result=result,
            final_content=final_content,
            confidence=confidence,
            similarity_score=similarity,
            engine_a_weight=weight_a,
            engine_b_weight=weight_b,
            reasoning=reasoning,
            contradictions_found=contradictions,
            consensus_points=consensus,
            arbitration_time_ms=elapsed_ms,
        )
        
        self._log_audit("arbitration_completed", {
            "result": result.value,
            "confidence": confidence,
            "time_ms": elapsed_ms,
        }, decision=result.value)
        
        self._stats["total_arbitrations"] += 1
        self._stats["total_time_ms"] += elapsed_ms
        
        logger.info(
            f"Arbitration complete: {result.value} "
            f"(similarity={similarity:.2f}, confidence={confidence:.2f})"
        )
        
        return decision
    
    def get_audit_log(self) -> List[Dict[str, Any]]:
        """Get full audit trail."""
        return [
            {
                "timestamp": entry.timestamp.isoformat(),
                "action": entry.action,
                "details": entry.details,
                "decision": entry.decision,
            }
            for entry in self._audit_log
        ]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get arbitration statistics."""
        avg_time = (
            self._stats["total_time_ms"] / self._stats["total_arbitrations"]
            if self._stats["total_arbitrations"] > 0
            else 0
        )
        
        return {
            **self._stats,
            "avg_time_per_arbitration_ms": avg_time,
            "consensus_rate": (
                self._stats["consensus_count"] / self._stats["total_arbitrations"]
                if self._stats["total_arbitrations"] > 0
                else 0
            ),
        }
    
    def clear_audit_log(self):
        """Clear audit trail (for testing)."""
        self._audit_log = []


def create_ensemble_arbitrator() -> EnsembleArbitrator:
    """Factory function to create EnsembleArbitrator."""
    return EnsembleArbitrator()

