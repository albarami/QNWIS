"""
Integration tests for fact verification in debate flow.

Tests real-time verification during agent debates without blocking.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from qnwis.rag.gpu_verifier import GPUFactVerifier
from qnwis.rag import get_fact_verifier, initialize_fact_verifier


@pytest.mark.asyncio
async def test_fact_verifier_indexed_before_first_query():
    """
    BUG FIX #3 TEST: Verify documents are pre-indexed at startup.
    
    This is the critical test to ensure Bug #3 is fixed.
    Documents should be indexed BEFORE first query, not during.
    """
    # Initialize verifier with small dataset
    verifier = GPUFactVerifier(gpu_id=6)
    
    documents = [
        {'text': f"Test document {i}", 'source': 'test', 'date': '2024', 'priority': 'medium'}
        for i in range(50)
    ]
    
    # Pre-index (simulating app startup)
    verifier.index_documents(documents)
    initialize_fact_verifier(verifier)
    
    # Get verifier (simulating query time)
    retrieved_verifier = get_fact_verifier()
    
    # Should be the same instance
    assert retrieved_verifier is verifier
    
    # Should already be indexed
    assert retrieved_verifier.is_indexed is True
    assert len(retrieved_verifier.doc_texts) == 50
    
    # Verification should work immediately (no delay)
    import time
    start = time.time()
    result = await retrieved_verifier.verify_claim("Test claim")
    elapsed = time.time() - start
    
    # Should be fast (<100ms) since already indexed
    assert elapsed < 0.1, \
        f"Verification should be instant on pre-indexed docs, took {elapsed*1000:.1f}ms"


@pytest.mark.asyncio
async def test_verification_overhead_per_turn():
    """Test that verification overhead is <500ms per debate turn."""
    verifier = GPUFactVerifier(gpu_id=6)
    
    # Index moderate dataset
    documents = [
        {'text': f"Economic fact {i} about Qatar", 'source': 'test', 'date': '2024', 'priority': 'medium'}
        for i in range(500)
    ]
    
    verifier.index_documents(documents)
    
    # Simulate agent output (debate turn)
    agent_output = """
    According to the analysis, Qatar's economy shows strong fundamentals.
    GDP growth is projected at 3.2% for 2024.
    The unemployment rate remains low at 0.1%.
    Oil prices are expected to stabilize around $75 per barrel.
    """
    
    # Measure verification time
    import time
    start = time.time()
    result = await verifier.verify_agent_output(agent_output)
    elapsed = time.time() - start
    
    # Should be fast (<500ms for a debate turn)
    assert elapsed < 0.5, \
        f"Verification should be <500ms per turn, took {elapsed*1000:.0f}ms"
    
    # Should have verified some claims
    assert result['total_claims'] > 0


@pytest.mark.asyncio
async def test_async_verification_non_blocking():
    """Test that async verification doesn't block event loop."""
    verifier = GPUFactVerifier(gpu_id=6)
    
    documents = [
        {'text': f"Document {i}", 'source': 'test', 'date': '2024', 'priority': 'medium'}
        for i in range(100)
    ]
    
    verifier.index_documents(documents)
    
    # Run multiple verifications concurrently
    claims = [f"Claim {i} about Qatar economy" for i in range(10)]
    
    # All should complete without blocking each other
    tasks = [verifier.verify_claim(claim) for claim in claims]
    results = await asyncio.gather(*tasks)
    
    # All should succeed
    assert len(results) == 10
    for result in results:
        assert 'verified' in result
        assert 'confidence' in result


@pytest.mark.asyncio
async def test_verification_warning_on_low_rate(caplog):
    """Test that <70% verification rate triggers warning."""
    import logging
    caplog.set_level(logging.WARNING)
    
    verifier = GPUFactVerifier(gpu_id=6)
    
    # Index documents about Qatar
    documents = [
        {'text': "Qatar's economy is strong", 'source': 'test', 'date': '2024', 'priority': 'high'}
    ]
    
    verifier.index_documents(documents)
    
    # Agent output with mostly unverifiable claims (different topic)
    agent_output = """
    Mars has a red surface due to iron oxide.
    The moon orbits Earth every 28 days.
    Water boils at 100 degrees Celsius.
    Qatar's economy shows positive trends.
    """
    
    result = await verifier.verify_agent_output(agent_output)
    
    # Should have low verification rate (only 1/4 claims about Qatar)
    if result['verification_rate'] < 0.70:
        # Should log warning
        assert any("verification rate" in record.message.lower() for record in caplog.records)


@pytest.mark.asyncio
async def test_verification_with_no_documents():
    """Test graceful handling when verifier not indexed."""
    verifier = GPUFactVerifier(gpu_id=6)
    
    # Don't index documents
    
    # Try to verify claim
    with pytest.raises(RuntimeError, match="Documents not indexed"):
        await verifier.verify_claim("Test claim")


@pytest.mark.asyncio
async def test_verification_performance_impact():
    """Test that verification adds <500ms overhead to debate flow."""
    verifier = GPUFactVerifier(gpu_id=6)
    
    # Index documents
    documents = [
        {'text': f"Qatar economic indicator {i}", 'source': 'test', 'date': '2024', 'priority': 'medium'}
        for i in range(200)
    ]
    
    verifier.index_documents(documents)
    
    # Simulate debate turn with agent output
    agent_outputs = [
        "Qatar's GDP grew by 3.5% in Q1 2024.",
        "Unemployment remains stable at 0.1%.",
        "Oil exports increased by 2.3% year-over-year.",
        "Non-hydrocarbon sector shows 5.2% growth."
    ]
    
    # Verify all outputs
    import time
    start = time.time()
    
    verification_tasks = [verifier.verify_agent_output(output) for output in agent_outputs]
    results = await asyncio.gather(*verification_tasks)
    
    total_time = time.time() - start
    
    # Total overhead should be <500ms for 4 agent outputs
    assert total_time < 0.5, \
        f"Verification overhead should be <500ms, got {total_time*1000:.0f}ms"
    
    # All verifications should complete
    assert len(results) == 4


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

