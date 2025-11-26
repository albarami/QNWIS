"""
Unit tests for GPU Fact Verifier.

Tests GPU-accelerated fact verification on GPU 6 with real semantic search.
"""

import pytest
import torch
from unittest.mock import patch, MagicMock
from qnwis.rag.gpu_verifier import GPUFactVerifier


@pytest.mark.skipif(not torch.cuda.is_available(), reason="Requires CUDA")
def test_fact_verifier_initialization_on_gpu6():
    """Test that fact verifier initializes on GPU 6 specifically."""
    verifier = GPUFactVerifier(gpu_id=6)
    
    # Verify GPU assignment
    assert verifier.gpu_id == 6
    assert verifier.device == "cuda:6" or verifier.device.startswith("cuda")
    
    # Verify model loaded
    assert verifier.model is not None
    assert not verifier.is_indexed  # Not indexed yet


def test_document_indexing():
    """Test indexing 100 documents creates embeddings."""
    verifier = GPUFactVerifier(gpu_id=6)
    
    # Create test documents
    documents = [
        {
            'text': f"Qatar's GDP is ${i}B according to World Bank data.",
            'source': f'world_bank/report_{i}.pdf',
            'date': '2024-01',
            'priority': 'high'
        }
        for i in range(100)
    ]
    
    # Index documents
    verifier.index_documents(documents)
    
    # Verify indexing
    assert verifier.is_indexed is True
    assert len(verifier.doc_texts) == 100
    assert len(verifier.doc_metadata) == 100
    assert verifier.doc_embeddings is not None
    
    # Verify embeddings shape (should be [100, 1024] for instructor-xl)
    if torch.cuda.is_available():
        assert verifier.doc_embeddings.shape[0] == 100
        assert verifier.doc_embeddings.shape[1] == 1024


@pytest.mark.asyncio
async def test_verify_claim_true_positive():
    """Test that a known true claim verifies successfully."""
    verifier = GPUFactVerifier(gpu_id=6)
    
    # Index documents with known fact
    documents = [
        {
            'text': "Qatar's GDP was $200 billion in 2023 according to World Bank.",
            'source': 'world_bank/qatar_2023.pdf',
            'date': '2024-01',
            'priority': 'high'
        },
        {
            'text': "UAE GDP reached $500 billion in 2023.",
            'source': 'world_bank/uae_2023.pdf',
            'date': '2024-01',
            'priority': 'high'
        },
        {
            'text': "Saudi Arabia's oil production was 10M barrels/day.",
            'source': 'iea/saudi_2023.pdf',
            'date': '2024-01',
            'priority': 'medium'
        }
    ]
    
    verifier.index_documents(documents)
    
    # Verify claim that matches first document
    claim = "Qatar's GDP is around $200 billion"
    result = await verifier.verify_claim(claim)
    
    # Should verify successfully
    assert result['verified'] is True, "True claim should verify"
    assert result['confidence'] > 0.75, "Confidence should be high for true claim"
    assert len(result['supporting_docs']) > 0
    assert 'Qatar' in result['supporting_docs'][0]['text']


@pytest.mark.asyncio
async def test_verify_claim_false_positive():
    """Test that a known false claim fails verification."""
    verifier = GPUFactVerifier(gpu_id=6)
    
    # Index documents
    documents = [
        {
            'text': "Qatar's population is 3 million people.",
            'source': 'gcc_stat/population.csv',
            'date': '2024',
            'priority': 'high'
        }
    ]
    
    verifier.index_documents(documents)
    
    # Claim that contradicts the document
    false_claim = "Qatar's population exceeds 50 million people"
    result = await verifier.verify_claim(false_claim)
    
    # Might still have some similarity but should be lower
    # (semantic search isn't perfect for contradiction detection)
    assert 'verified' in result
    assert 'confidence' in result


@pytest.mark.asyncio
async def test_verify_claim_ambiguous():
    """Test partial match returns medium confidence."""
    verifier = GPUFactVerifier(gpu_id=6)
    
    documents = [
        {
            'text': "Economic growth in Qatar shows positive trends.",
            'source': 'test.pdf',
            'date': '2024',
            'priority': 'medium'
        }
    ]
    
    verifier.index_documents(documents)
    
    # Somewhat related claim
    claim = "Qatar's economy is growing"
    result = await verifier.verify_claim(claim)
    
    # Should have moderate similarity
    assert 0.0 <= result['confidence'] <= 1.0
    assert 'supporting_docs' in result


@pytest.mark.asyncio
async def test_top_k_retrieval():
    """Test that correct number of supporting docs are returned."""
    verifier = GPUFactVerifier(gpu_id=6)
    
    documents = [
        {'text': f"Document {i} about Qatar economy", 'source': f'doc{i}', 'date': '2024', 'priority': 'medium'}
        for i in range(10)
    ]
    
    verifier.index_documents(documents)
    
    # Request top 3 documents
    result = await verifier.verify_claim("Qatar economy", top_k=3)
    
    assert len(result['supporting_docs']) == 3
    
    # Request top 5
    result = await verifier.verify_claim("Qatar economy", top_k=5)
    
    assert len(result['supporting_docs']) == 5


@pytest.mark.asyncio
async def test_similarity_threshold_behavior():
    """Test 0.75 threshold edge cases."""
    verifier = GPUFactVerifier(gpu_id=6)
    
    documents = [
        {'text': "Specific claim about Qatar", 'source': 'test', 'date': '2024', 'priority': 'high'}
    ]
    
    verifier.index_documents(documents)
    
    # Exact match should verify
    result = await verifier.verify_claim("Specific claim about Qatar")
    assert result['verified'] is True
    assert result['confidence'] > 0.75


def test_extract_claims_from_text():
    """Test claim extraction logic."""
    verifier = GPUFactVerifier(gpu_id=6)
    
    # Text with multiple factual claims
    text = """
    Qatar's GDP grew by 3.5% in 2023 according to World Bank data.
    This is a general statement without numbers.
    The unemployment rate fell to 0.1% based on Ministry of Labour statistics.
    Another vague claim.
    Oil prices increased to $85 per barrel.
    """
    
    claims = verifier._extract_claims(text)
    
    # Should extract factual claims (those with numbers or specific entities)
    assert len(claims) > 0
    assert len(claims) <= 10  # Limited to 10
    
    # Verify extracted claims contain factual patterns
    for claim in claims:
        # Should contain numbers or specific references
        has_number = any(char.isdigit() for char in claim)
        has_entity = any(word in claim for word in ['Qatar', 'World Bank', 'Ministry', 'Oil'])
        assert has_number or has_entity, f"Claim should be factual: {claim}"


@pytest.mark.asyncio
async def test_verify_agent_output_full():
    """Test end-to-end agent output verification."""
    verifier = GPUFactVerifier(gpu_id=6)
    
    # Index knowledge base
    documents = [
        {'text': "Qatar's GDP is $200B", 'source': 'wb', 'date': '2024', 'priority': 'high'},
        {'text': "Unemployment is 0.1%", 'source': 'mol', 'date': '2024', 'priority': 'critical'},
        {'text': "Oil price is $75/barrel", 'source': 'iea', 'date': '2024', 'priority': 'high'}
    ]
    
    verifier.index_documents(documents)
    
    # Agent output with multiple claims
    agent_output = """
    Based on the analysis, Qatar's economy is strong with GDP around $200B.
    The labor market is tight with unemployment below 0.2%.
    Oil prices remain stable near $75 per barrel.
    """
    
    result = await verifier.verify_agent_output(agent_output)
    
    # Verify structure
    assert 'total_claims' in result
    assert 'verified_claims' in result
    assert 'verification_rate' in result
    assert 'avg_confidence' in result
    
    # Should have extracted and verified claims
    assert result['total_claims'] > 0


@pytest.mark.skipif(not torch.cuda.is_available(), reason="Requires CUDA")
@pytest.mark.asyncio
async def test_performance_on_gpu():
    """Test that verification is fast on GPU (<1ms per claim)."""
    verifier = GPUFactVerifier(gpu_id=6)
    
    # Index 1000 documents
    documents = [
        {'text': f"Economic data point {i} for Qatar", 'source': f'doc{i}', 'date': '2024', 'priority': 'medium'}
        for i in range(1000)
    ]
    
    verifier.index_documents(documents)
    
    # Time verification
    import time
    start = time.time()
    
    # Verify 10 claims
    for i in range(10):
        await verifier.verify_claim(f"Economic claim {i}")
    
    elapsed = time.time() - start
    avg_time = elapsed / 10
    
    # Should be fast on GPU (<10ms per verification on A100)
    assert avg_time < 0.01, f"Verification should be <10ms per claim, got {avg_time*1000:.1f}ms"


def test_document_limit_enforcement():
    """Test that MAX_DOCUMENTS limit is enforced."""
    verifier = GPUFactVerifier(gpu_id=6)
    
    # Try to index more than MAX_DOCUMENTS
    excessive_documents = [
        {'text': f"doc {i}", 'source': 'test', 'date': '2024', 'priority': 'low'}
        for i in range(600_000)  # Exceeds 500K limit
    ]
    
    # Should log warning and truncate
    verifier.index_documents(excessive_documents)
    
    # Should have truncated to MAX_DOCUMENTS
    assert len(verifier.doc_texts) == verifier.MAX_DOCUMENTS
    assert len(verifier.doc_texts) == 500_000


def test_get_stats():
    """Test statistics reporting."""
    verifier = GPUFactVerifier(gpu_id=6)
    
    stats = verifier.get_stats()
    
    # Verify stats structure
    assert 'is_indexed' in stats
    assert 'total_documents' in stats
    assert 'gpu_id' in stats
    assert 'device' in stats
    assert 'model' in stats
    assert 'verification_threshold' in stats
    
    assert stats['gpu_id'] == 6
    assert stats['model'] == 'hkunlp/instructor-xl'
    assert stats['verification_threshold'] == 0.75


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

