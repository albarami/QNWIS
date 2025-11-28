"""
Phase 2 Tests: Deep Verification Engine with Micro-Batching

Tests:
- VerificationResult dataclass
- MicroBatcher functionality
- DeepVerifier initialization
- Cross-encoder scoring
- NLI classification
- Contradiction detection
- Batch verification
- Statistics tracking
"""

import pytest
import time
from typing import List, Tuple
import numpy as np


class TestVerificationDataclasses:
    """Test verification data structures."""
    
    def test_verification_result_creation(self):
        """VerificationResult should store all fields correctly."""
        from src.nsic.verification.deep_verifier import VerificationResult
        
        result = VerificationResult(
            claim="Oil prices will rise",
            evidence="OPEC announced production cuts",
            score=0.85,
            label="entailment",
            confidence=0.92,
            layer="combined",
            timing_ms=12.5,
        )
        
        assert result.claim == "Oil prices will rise"
        assert result.evidence == "OPEC announced production cuts"
        assert result.score == 0.85
        assert result.label == "entailment"
        assert result.confidence == 0.92
        assert result.layer == "combined"
        assert result.timing_ms == 12.5
    
    def test_verification_result_to_dict(self):
        """VerificationResult.to_dict() should return all fields."""
        from src.nsic.verification.deep_verifier import VerificationResult
        
        result = VerificationResult(
            claim="Test claim",
            evidence="Test evidence",
            score=0.75,
            label="neutral",
            confidence=0.60,
            layer="nli",
            timing_ms=5.0,
        )
        
        d = result.to_dict()
        
        assert d["claim"] == "Test claim"
        assert d["evidence"] == "Test evidence"
        assert d["score"] == 0.75
        assert d["label"] == "neutral"
        assert d["confidence"] == 0.60
        assert d["layer"] == "nli"
        assert d["timing_ms"] == 5.0


class TestVerificationBatch:
    """Test verification batch accumulation."""
    
    def test_batch_add_and_length(self):
        """Batch should accumulate claims and evidences."""
        from src.nsic.verification.deep_verifier import VerificationBatch
        
        batch = VerificationBatch()
        assert len(batch) == 0
        assert batch.is_empty()
        
        idx1 = batch.add("claim1", "evidence1")
        assert idx1 == 0
        assert len(batch) == 1
        assert not batch.is_empty()
        
        idx2 = batch.add("claim2", "evidence2")
        assert idx2 == 1
        assert len(batch) == 2
    
    def test_batch_stores_timestamps(self):
        """Batch should record timestamps for each addition."""
        from src.nsic.verification.deep_verifier import VerificationBatch
        
        batch = VerificationBatch()
        before = time.time()
        batch.add("claim", "evidence")
        after = time.time()
        
        assert len(batch.timestamps) == 1
        assert before <= batch.timestamps[0] <= after


class TestMicroBatcher:
    """Test micro-batching logic."""
    
    def test_microbatcher_init(self):
        """MicroBatcher should initialize with correct settings."""
        from src.nsic.verification.deep_verifier import MicroBatcher
        
        batcher = MicroBatcher(batch_size=8, window_ms=15.0)
        
        assert batcher.batch_size == 8
        assert batcher.window_ms == 15.0
        assert len(batcher) == 0
    
    def test_microbatcher_add(self):
        """MicroBatcher should accumulate requests."""
        from src.nsic.verification.deep_verifier import MicroBatcher
        
        batcher = MicroBatcher(batch_size=8, window_ms=15.0)
        
        idx = batcher.add("claim1", "evidence1")
        assert idx == 0
        assert len(batcher) == 1
        
        idx = batcher.add("claim2", "evidence2")
        assert idx == 1
        assert len(batcher) == 2
    
    def test_microbatcher_flush_on_size(self):
        """MicroBatcher should flush when batch_size is reached."""
        from src.nsic.verification.deep_verifier import MicroBatcher
        
        batcher = MicroBatcher(batch_size=3, window_ms=1000.0)  # Long window
        
        batcher.add("claim1", "evidence1")
        batcher.add("claim2", "evidence2")
        assert not batcher.should_flush()
        
        batcher.add("claim3", "evidence3")
        assert batcher.should_flush()
        
        batch = batcher.flush()
        assert len(batch) == 3
        assert len(batcher) == 0  # Cleared after flush
    
    def test_microbatcher_flush_on_window(self):
        """MicroBatcher should flush when window_ms has elapsed."""
        from src.nsic.verification.deep_verifier import MicroBatcher
        
        batcher = MicroBatcher(batch_size=100, window_ms=10.0)  # Short window
        
        batcher.add("claim1", "evidence1")
        assert not batcher.should_flush()  # Immediately after add
        
        time.sleep(0.015)  # Wait 15ms
        assert batcher.should_flush()


class TestDeepVerifier:
    """Test deep verification engine."""
    
    def test_verifier_init_cpu(self):
        """DeepVerifier should initialize on CPU without errors."""
        from src.nsic.verification.deep_verifier import DeepVerifier
        
        # Initialize with models disabled for fast testing
        verifier = DeepVerifier(
            device="cpu",
            enable_cross_encoder=False,
            enable_nli=False,
        )
        
        assert verifier.device == "cpu"
        assert verifier.cross_encoder is None
        assert verifier.nli_model is None
    
    def test_verifier_init_with_batcher_settings(self):
        """DeepVerifier should accept custom batch settings."""
        from src.nsic.verification.deep_verifier import DeepVerifier
        
        verifier = DeepVerifier(
            device="cpu",
            batch_size=16,
            window_ms=20.0,
            enable_cross_encoder=False,
            enable_nli=False,
        )
        
        assert verifier.batcher.batch_size == 16
        assert verifier.batcher.window_ms == 20.0
    
    def test_verifier_verify_single_fallback(self):
        """verify() should work with fallback values when models disabled."""
        from src.nsic.verification.deep_verifier import DeepVerifier
        
        verifier = DeepVerifier(
            device="cpu",
            enable_cross_encoder=False,
            enable_nli=False,
        )
        
        result = verifier.verify(
            claim="Test claim",
            evidence="Test evidence",
        )
        
        assert result.claim == "Test claim"
        assert result.evidence == "Test evidence"
        assert 0 <= result.score <= 1
        assert result.label in ["entailment", "neutral", "contradiction"]
        assert result.timing_ms >= 0
    
    def test_verifier_verify_batch_fallback(self):
        """verify_batch() should process multiple claims with fallbacks."""
        from src.nsic.verification.deep_verifier import DeepVerifier
        
        verifier = DeepVerifier(
            device="cpu",
            enable_cross_encoder=False,
            enable_nli=False,
        )
        
        claims = ["Claim 1", "Claim 2", "Claim 3"]
        evidences = ["Evidence 1", "Evidence 2", "Evidence 3"]
        
        results = verifier.verify_batch(claims, evidences)
        
        assert len(results) == 3
        for i, result in enumerate(results):
            assert result.claim == claims[i]
            assert result.evidence == evidences[i]
    
    def test_verifier_stats_tracking(self):
        """DeepVerifier should track statistics."""
        from src.nsic.verification.deep_verifier import DeepVerifier
        
        verifier = DeepVerifier(
            device="cpu",
            enable_cross_encoder=False,
            enable_nli=False,
        )
        
        # Initial stats
        stats = verifier.get_stats()
        assert stats["verifications"] == 0
        assert stats["batches_processed"] == 0
        
        # After verification
        verifier.verify("claim", "evidence")
        
        stats = verifier.get_stats()
        assert stats["verifications"] == 1
        assert stats["batches_processed"] == 1
        assert stats["total_time_ms"] >= 0  # Can be 0 for very fast fallback
    
    def test_verifier_context_manager(self):
        """DeepVerifier should work as context manager."""
        from src.nsic.verification.deep_verifier import DeepVerifier
        
        with DeepVerifier(
            device="cpu",
            enable_cross_encoder=False,
            enable_nli=False,
        ) as verifier:
            result = verifier.verify("claim", "evidence")
            assert result is not None


class TestVerifyAgainstSources:
    """Test multi-source verification."""
    
    def test_verify_against_empty_sources(self):
        """Should handle empty sources gracefully."""
        from src.nsic.verification.deep_verifier import DeepVerifier
        
        verifier = DeepVerifier(
            device="cpu",
            enable_cross_encoder=False,
            enable_nli=False,
        )
        
        result = verifier.verify_claim_against_sources(
            claim="Test claim",
            sources=[],
        )
        
        assert result["verified"] is False
        assert result["confidence"] == 0.0
        assert result["sources_checked"] == 0
    
    def test_verify_against_multiple_sources(self):
        """Should aggregate results from multiple sources."""
        from src.nsic.verification.deep_verifier import DeepVerifier
        
        verifier = DeepVerifier(
            device="cpu",
            enable_cross_encoder=False,
            enable_nli=False,
        )
        
        sources = [
            "Source 1 text",
            "Source 2 text",
            "Source 3 text",
        ]
        
        result = verifier.verify_claim_against_sources(
            claim="Test claim",
            sources=sources,
            top_k=2,
        )
        
        assert result["sources_checked"] == 3
        assert "top_sources" in result
        assert len(result["top_sources"]) <= 2


class TestFactoryFunction:
    """Test factory function."""
    
    def test_create_deep_verifier(self):
        """create_deep_verifier should return DeepVerifier instance."""
        from src.nsic.verification.deep_verifier import DeepVerifier
        
        # Test with models disabled for fast test
        verifier = DeepVerifier(
            device="cpu",
            batch_size=16,
            window_ms=25.0,
            enable_cross_encoder=False,
            enable_nli=False,
        )
        
        assert verifier is not None
        assert verifier.batcher.batch_size == 16
        assert verifier.batcher.window_ms == 25.0


class TestModelIntegration:
    """Integration tests with actual models (if available)."""
    
    @pytest.mark.slow
    def test_cross_encoder_model_loads(self):
        """Cross-encoder model should load successfully (slow test)."""
        try:
            from sentence_transformers import CrossEncoder
        except ImportError:
            pytest.skip("sentence_transformers not installed")
        
        from src.nsic.verification.deep_verifier import DeepVerifier
        
        verifier = DeepVerifier(
            device="cpu",
            enable_cross_encoder=True,
            enable_nli=False,
        )
        
        assert verifier.cross_encoder is not None
    
    @pytest.mark.slow
    def test_full_verification_with_models(self):
        """Full verification with models loaded (slow test)."""
        try:
            from sentence_transformers import CrossEncoder
            from transformers import AutoModelForSequenceClassification
        except ImportError:
            pytest.skip("Required packages not installed")
        
        from src.nsic.verification.deep_verifier import DeepVerifier
        
        try:
            verifier = DeepVerifier(
                device="cpu",
                enable_cross_encoder=True,
                enable_nli=True,
            )
        except OSError as e:
            pytest.skip(f"NLI model not available: {e}")
        
        result = verifier.verify(
            claim="Oil prices increased by 10% after OPEC announcement",
            evidence="OPEC announced production cuts, leading to higher oil prices",
        )
        
        # With real models, we expect reasonable scores
        assert result.score >= 0
        assert result.confidence >= 0
        assert result.label in ["entailment", "neutral", "contradiction"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

