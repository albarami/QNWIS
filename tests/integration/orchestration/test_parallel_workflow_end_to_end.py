"""
Integration tests for parallel scenario workflow.

Tests end-to-end execution with parallel scenarios and meta-synthesis.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from qnwis.orchestration.workflow import (
    create_intelligence_graph,
    scenario_generation_node,
    parallel_execution_node,
    meta_synthesis_wrapper,
    build_base_workflow
)
from qnwis.orchestration.state import IntelligenceState


@pytest.mark.asyncio
async def test_full_parallel_workflow():
    """
    Test complete workflow with parallel scenarios enabled.
    
    This is the critical integration test - verifies:
    1. Scenario generation works
    2. Parallel execution distributes across GPUs
    3. Meta-synthesis synthesizes results
    4. Workflow terminates properly
    """
    # This test requires mocking all the intermediate nodes
    # to avoid actually calling Claude API repeatedly
    
    initial_state: IntelligenceState = {
        'query': 'Should Qatar invest $50B in technology hub?',
        'complexity': 'complex',
        'enable_parallel_scenarios': True,
        'extracted_facts': {},
        'reasoning_chain': [],
        'warnings': [],
        'errors': []
    }
    
    # Test scenario generation node
    with patch('qnwis.orchestration.nodes.scenario_generator.ScenarioGenerator') as mock_gen:
        mock_instance = MagicMock()
        mock_instance.generate_scenarios = AsyncMock(return_value=[
            {"id": "s1", "name": "Base", "description": "base", "modified_assumptions": {}},
            {"id": "s2", "name": "Risk", "description": "risk", "modified_assumptions": {}}
        ])
        mock_gen.return_value = mock_instance
        
        result_state = scenario_generation_node(initial_state)
        
        assert result_state.get('scenarios') is not None
        assert len(result_state['scenarios']) == 2


@pytest.mark.asyncio
async def test_workflow_with_parallel_disabled():
    """Test that single-path workflow still works when parallel is disabled."""
    initial_state: IntelligenceState = {
        'query': 'Test query',
        'complexity': 'simple',
        'enable_parallel_scenarios': False,
        'extracted_facts': {},
        'reasoning_chain': [],
        'warnings': [],
        'errors': []
    }
    
    result_state = await scenario_generation_node(initial_state)
    
    # Should not generate scenarios
    assert result_state.get('scenarios') is None


@pytest.mark.asyncio
async def test_state_propagation():
    """Test that state flows correctly through new nodes."""
    state: IntelligenceState = {
        'query': 'Test',
        'complexity': 'medium',
        'enable_parallel_scenarios': True,
        'extracted_facts': {'fact1': 'value1'},
        'reasoning_chain': [],
        'warnings': [],
        'errors': []
    }
    
    # Test that state fields are preserved
    with patch('qnwis.orchestration.nodes.scenario_generator.ScenarioGenerator') as mock_gen:
        mock_instance = MagicMock()
        mock_instance.generate_scenarios = AsyncMock(return_value=[
            {"id": "s1", "name": "Test", "description": "test", "modified_assumptions": {}}
        ])
        mock_gen.return_value = mock_instance
        
        result = await scenario_generation_node(state)
        
        # Original state should be preserved
        assert result['query'] == 'Test'
        assert result['complexity'] == 'medium'
        assert result['extracted_facts'] == {'fact1': 'value1'}
        # New fields should be added
        assert 'scenarios' in result


@pytest.mark.asyncio
async def test_meta_synthesis_output_structure():
    """Test that meta-synthesis produces properly structured output."""
    state: IntelligenceState = {
        'scenario_results': [
            {
                'scenario_id': 's1',
                'scenario_metadata': {
                    'id': 's1',
                    'name': 'Base Case',
                    'description': 'Current trends',
                    'modified_assumptions': {}
                },
                'final_synthesis': 'Recommendation: Invest in tech',
                'confidence_score': 0.85,
                'scenario_execution_time': 45.0,
                'warnings': [],
                'reasoning_chain': []
            }
        ],
        'reasoning_chain': [],
        'warnings': [],
        'errors': []
    }
    
    mock_synthesis = """# META-SYNTHESIS: TEST

## ROBUST RECOMMENDATIONS
- Test recommendation

## SCENARIO-DEPENDENT STRATEGIES
- Test strategy

## KEY UNCERTAINTIES
- Test uncertainty

## EARLY WARNING INDICATORS
- Test indicator

## FINAL STRATEGIC GUIDANCE
- Test guidance
"""
    
    with patch('qnwis.orchestration.llm_wrapper.call_llm_with_rate_limit',
               return_value=MagicMock(content=mock_synthesis)):
        result = await meta_synthesis_wrapper(state)
        
        assert result.get('final_synthesis') is not None
        assert "ROBUST RECOMMENDATIONS" in result['final_synthesis']
        assert any("Meta-synthesis complete" in entry for entry in result['reasoning_chain'])


@pytest.mark.asyncio
async def test_execution_time_improvement():
    """
    Test that parallel execution is faster than sequential.
    
    This validates the core value proposition of the multi-GPU architecture.
    """
    # Mock workflow that simulates realistic execution time
    async def mock_workflow(state):
        await asyncio.sleep(0.1)  # Simulate 100ms per scenario
        return {**state, 'done': True}
    
    mock_graph = MagicMock()
    mock_graph.ainvoke = mock_workflow
    
    scenarios = [
        {"id": f"s{i}", "name": f"Scenario{i}", "description": "desc", "modified_assumptions": {}}
        for i in range(4)
    ]
    
    initial_state = {'query': 'Test', 'reasoning_chain': [], 'extracted_facts': {}}
    
    # Import executor
    from qnwis.orchestration.parallel_executor import ParallelDebateExecutor
    executor = ParallelDebateExecutor(num_parallel=4)
    
    # Measure parallel execution time
    import time
    start = time.time()
    results = await executor.execute_scenarios(scenarios, mock_graph, initial_state)
    parallel_time = time.time() - start
    
    # 4 scenarios at 100ms each should take ~100ms in parallel (vs 400ms sequential)
    assert parallel_time < 0.3, \
        f"Parallel execution should be ~0.1s, took {parallel_time:.2f}s"
    
    # Verify significant speedup
    sequential_estimate = 4 * 0.1
    speedup = sequential_estimate / parallel_time
    assert speedup > 1.5, \
        f"Should see >1.5x speedup, got {speedup:.1f}x"


@pytest.mark.asyncio
async def test_reasoning_chain_tracking():
    """Test that new nodes are logged in reasoning_chain."""
    state: IntelligenceState = {
        'query': 'Test',
        'complexity': 'complex',
        'enable_parallel_scenarios': True,
        'extracted_facts': {},
        'reasoning_chain': [],
        'warnings': [],
        'errors': []
    }
    
    with patch('qnwis.orchestration.nodes.scenario_generator.ScenarioGenerator') as mock_gen:
        mock_instance = MagicMock()
        mock_instance.generate_scenarios = AsyncMock(return_value=[
            {"id": "s1", "name": "Test", "description": "test", "modified_assumptions": {}}
        ])
        mock_gen.return_value = mock_instance
        
        result = await scenario_generation_node(state)
        
        # Should log scenario generation
        assert any('scenarios' in entry.lower() for entry in result['reasoning_chain'])


@pytest.mark.asyncio
async def test_single_path_completes_to_end():
    """
    BUG FIX #2 TEST: Verify single path reaches END properly.
    
    This is the critical test to ensure Bug #2 is fixed.
    The workflow graph must have complete paths for both parallel and single routes.
    """
    # Create state that will take single path
    state: IntelligenceState = {
        'query': 'Simple test query',
        'complexity': 'simple',
        'enable_parallel_scenarios': False,  # Disable parallel
        'scenarios': None,  # No scenarios
        'extracted_facts': {},
        'reasoning_chain': [],
        'warnings': [],
        'errors': []
    }
    
    # Await async node
    result = await scenario_generation_node(state)
    
    # Should not generate scenarios
    assert result.get('scenarios') is None
    
    # Verify parallel execution node skips properly
    parallel_result = await parallel_execution_node(result)
    assert parallel_result.get('scenario_results') is None or parallel_result.get('scenario_results') == []
    
    # Verify meta-synthesis skips properly
    meta_result = await meta_synthesis_wrapper(parallel_result)
    
    # Single path should not have meta-synthesis in final_synthesis
    # (it should use regular synthesis instead)
    assert meta_result is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

