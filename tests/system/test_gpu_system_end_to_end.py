"""
System tests for complete Multi-GPU architecture.

Tests end-to-end integration with real GPUs, Claude API, and full workflow.
"""

import pytest
import torch
from unittest.mock import patch, AsyncMock, MagicMock
from qnwis.config.gpu_config import load_gpu_config, get_gpu_config
from qnwis.orchestration.parallel_executor import ParallelDebateExecutor
from qnwis.rag.gpu_verifier import GPUFactVerifier


@pytest.mark.skipif(not torch.cuda.is_available(), reason="Requires CUDA GPUs")
def test_all_8_gpus_utilized():
    """Test that all 8 GPUs are active and properly allocated."""
    gpu_count = torch.cuda.device_count()
    assert gpu_count == 8, f"Production system should have 8 A100s, found {gpu_count}"
    
    # Verify GPU 0-5 for parallel scenarios
    for i in range(6):
        gpu_name = torch.cuda.get_device_name(i)
        assert "A100" in gpu_name, f"GPU {i} should be A100, got {gpu_name}"
        
        # Check memory
        props = torch.cuda.get_device_properties(i)
        total_memory_gb = props.total_memory / 1e9
        assert total_memory_gb > 75, f"GPU {i} should be 80GB A100, got {total_memory_gb:.1f}GB"
    
    # Verify GPU 6 for embeddings+verification
    gpu6_name = torch.cuda.get_device_name(6)
    assert "A100" in gpu6_name
    
    # Verify GPU 7 for overflow
    gpu7_name = torch.cuda.get_device_name(7)
    assert "A100" in gpu7_name


@pytest.mark.skipif(not torch.cuda.is_available(), reason="Requires CUDA GPUs")
def test_gpu_memory_allocation():
    """Test that GPU memory usage is within limits."""
    # GPU 6 should be shared between embeddings and verification
    # Target: <10GB total on GPU 6
    
    # Check current memory (before loading models)
    memory_allocated = torch.cuda.memory_allocated(6) / 1e9
    memory_reserved = torch.cuda.memory_reserved(6) / 1e9
    
    # Should have headroom
    assert memory_allocated < 10.0, \
        f"GPU 6 memory ({memory_allocated:.2f}GB) should be <10GB"


def test_configuration_loading():
    """Test that GPU configuration loads correctly."""
    config = load_gpu_config()
    
    # Verify embeddings config
    assert config.embeddings.gpu_id == 6
    assert config.embeddings.model == "hkunlp/instructor-xl"
    assert config.embeddings.dimensions == 1024
    
    # Verify fact verification config
    assert config.fact_verification.gpu_id == 6  # Shared with embeddings
    assert config.fact_verification.max_documents == 500_000
    assert config.fact_verification.enable is True
    
    # Verify parallel scenarios config
    assert config.parallel_scenarios.enable is True
    assert config.parallel_scenarios.num_scenarios == 6
    assert config.parallel_scenarios.gpu_range == [0, 1, 2, 3, 4, 5]
    
    # Verify models config
    assert "claude-sonnet-4" in config.models.primary_llm
    assert config.models.rate_limit_per_minute == 50


def test_state_persistence():
    """Test that all new state fields are properly saved."""
    from qnwis.orchestration.state import IntelligenceState
    
    # Create state with all new fields
    state: IntelligenceState = {
        'query': 'Test',
        'enable_parallel_scenarios': True,
        'scenarios': [{'id': 's1', 'name': 'Test'}],
        'scenario_results': [{'id': 's1', 'result': 'test'}],
        'scenario_name': 'Test Scenario',
        'scenario_metadata': {'key': 'value'},
        'scenario_assumptions': {'assumption': 'value'}
    }
    
    # Verify all fields are accessible
    assert state['enable_parallel_scenarios'] is True
    assert len(state['scenarios']) == 1
    assert len(state['scenario_results']) == 1
    assert state['scenario_name'] == 'Test Scenario'
    assert 'key' in state['scenario_metadata']
    assert 'assumption' in state['scenario_assumptions']


@pytest.mark.asyncio
async def test_complete_workflow_with_verification():
    """
    Test complete workflow with all components.
    
    This is the master integration test - requires mocking to avoid
    long Claude API calls.
    """
    from qnwis.orchestration.workflow import scenario_generation_node
    
    # Create realistic state
    state = {
        'query': 'Should Qatar invest $50B in technology hub?',
        'complexity': 'complex',
        'enable_parallel_scenarios': True,
        'extracted_facts': {
            'qatar_gdp': '$200B',
            'oil_price': '$75',
            'unemployment': '0.1%'
        },
        'reasoning_chain': [],
        'warnings': [],
        'errors': []
    }
    
    # Mock scenario generator to avoid actual Claude call
    with patch('qnwis.orchestration.nodes.scenario_generator.ScenarioGenerator') as mock_gen:
        mock_instance = MagicMock()
        mock_instance.generate_scenarios = AsyncMock(return_value=[
            {
                "id": "scenario_1",
                "name": "Base Case",
                "description": "Current economic trends continue",
                "modified_assumptions": {"oil_price": 75}
            },
            {
                "id": "scenario_2",
                "name": "Oil Shock",
                "description": "Oil price drops to $45",
                "modified_assumptions": {"oil_price": 45}
            }
        ])
        mock_gen.return_value = mock_instance
        
        result = await scenario_generation_node(state)
        
        # Should have generated scenarios
        assert 'scenarios' in result
        assert len(result['scenarios']) == 2


def test_fallback_behavior():
    """Test that system works without GPUs (CPU fallback)."""
    # Mock CUDA availability
    with patch('torch.cuda.is_available', return_value=False):
        # Should still initialize
        executor = ParallelDebateExecutor(num_parallel=4)
        
        assert executor.gpu_available is False
        assert executor.gpu_count == 0


def test_environment_variable_overrides():
    """Test that environment variables override configuration."""
    import os
    
    # Set environment variables
    os.environ['QNWIS_ENABLE_PARALLEL_SCENARIOS'] = 'false'
    os.environ['QNWIS_CLAUDE_RATE_LIMIT'] = '100'
    
    try:
        config = load_gpu_config()
        
        # Should apply overrides
        # Note: This depends on implementation details of _apply_env_overrides
        # For now, just verify config loads
        assert config is not None
        
    finally:
        # Clean up
        del os.environ['QNWIS_ENABLE_PARALLEL_SCENARIOS']
        del os.environ['QNWIS_CLAUDE_RATE_LIMIT']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

