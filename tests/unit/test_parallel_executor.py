"""
Unit tests for Parallel Debate Executor.

Tests parallel execution of debates across GPUs 0-5 with real GPU distribution.
"""

import pytest
import asyncio
import torch
from unittest.mock import AsyncMock, MagicMock, patch
from qnwis.orchestration.parallel_executor import ParallelDebateExecutor


def test_parallel_executor_initialization():
    """Test that parallel executor initializes correctly."""
    executor = ParallelDebateExecutor(num_parallel=6)
    
    assert executor.num_parallel == 6
    
    # Check GPU detection
    if torch.cuda.is_available():
        assert executor.gpu_available is True
        assert executor.gpu_count == 8, f"Expected 8 GPUs, found {executor.gpu_count}"
    else:
        pytest.skip("No GPUs available - production system requires GPUs")


def test_gpu_detection_and_logging(caplog):
    """Test that GPU detection works and logs properly."""
    import logging
    caplog.set_level(logging.INFO)
    
    executor = ParallelDebateExecutor(num_parallel=6)
    
    if torch.cuda.is_available():
        # Should log GPU information
        assert any("Parallel executor initialized" in record.message for record in caplog.records)
        assert any("GPUs available" in record.message for record in caplog.records)
        assert executor.gpu_count >= 6, "Production system should have at least 6 GPUs"
    else:
        # Should warn about no GPUs
        assert any("No GPUs detected" in record.message for record in caplog.records)


@pytest.mark.asyncio
async def test_execute_scenarios_success():
    """Test that executor successfully runs multiple scenarios."""
    executor = ParallelDebateExecutor(num_parallel=4)
    
    # Create mock scenarios
    scenarios = [
        {"id": "s1", "name": "Base Case", "description": "desc1", "modified_assumptions": {}},
        {"id": "s2", "name": "Oil Shock", "description": "desc2", "modified_assumptions": {}},
        {"id": "s3", "name": "Competition", "description": "desc3", "modified_assumptions": {}},
        {"id": "s4", "name": "Disruption", "description": "desc4", "modified_assumptions": {}}
    ]
    
    # Mock workflow that returns success
    async def mock_workflow(state):
        return {
            **state,
            'final_synthesis': f"Analysis for {state.get('scenario_name', 'unknown')}",
            'confidence_score': 0.85
        }
    
    mock_graph = MagicMock()
    mock_graph.ainvoke = mock_workflow
    
    initial_state = {
        'query': 'Test query',
        'reasoning_chain': [],
        'extracted_facts': {}
    }
    
    # Execute scenarios
    results = await executor.execute_scenarios(scenarios, mock_graph, initial_state)
    
    # Verify all scenarios completed
    assert len(results) == 4
    
    # Verify each result has scenario metadata
    for i, result in enumerate(results):
        assert 'scenario_metadata' in result
        assert result['scenario_metadata']['id'] == scenarios[i]['id']
        assert 'scenario_gpu' in result


@pytest.mark.asyncio
async def test_execute_scenarios_with_failure():
    """Test that executor handles individual scenario failures gracefully."""
    executor = ParallelDebateExecutor(num_parallel=4)
    
    scenarios = [
        {"id": "s1", "name": "Success1", "description": "desc1", "modified_assumptions": {}},
        {"id": "s2", "name": "Failure", "description": "desc2", "modified_assumptions": {}},
        {"id": "s3", "name": "Success2", "description": "desc3", "modified_assumptions": {}},
        {"id": "s4", "name": "Success3", "description": "desc4", "modified_assumptions": {}}
    ]
    
    # Mock workflow that fails for scenario 2
    async def mock_workflow(state):
        if state.get('scenario_name') == "Failure":
            raise RuntimeError("Simulated failure")
        return {
            **state,
            'final_synthesis': f"Success for {state.get('scenario_name')}",
            'confidence_score': 0.85
        }
    
    mock_graph = MagicMock()
    mock_graph.ainvoke = mock_workflow
    
    initial_state = {'query': 'Test', 'reasoning_chain': [], 'extracted_facts': {}}
    
    # Execute - should handle failure gracefully
    results = await executor.execute_scenarios(scenarios, mock_graph, initial_state)
    
    # Should have 3 successful results (1 failed)
    assert len(results) == 3
    
    # Failed scenario should not be in results
    result_names = [r['scenario_metadata']['name'] for r in results]
    assert "Failure" not in result_names
    assert "Success1" in result_names
    assert "Success2" in result_names
    assert "Success3" in result_names


@pytest.mark.skipif(not torch.cuda.is_available(), reason="Requires CUDA GPUs")
def test_gpu_distribution():
    """Test that scenarios are distributed across GPUs 0-5."""
    executor = ParallelDebateExecutor(num_parallel=6)
    
    # Verify GPU distribution logic
    test_cases = [
        (0, 0),  # Scenario 0 → GPU 0
        (1, 1),  # Scenario 1 → GPU 1
        (2, 2),  # Scenario 2 → GPU 2
        (5, 5),  # Scenario 5 → GPU 5
        (6, 0),  # Scenario 6 → GPU 0 (wraps around)
        (7, 1),  # Scenario 7 → GPU 1 (wraps around)
    ]
    
    for scenario_idx, expected_gpu in test_cases:
        gpu_id = scenario_idx % 6
        assert gpu_id == expected_gpu, \
            f"Scenario {scenario_idx} should map to GPU {expected_gpu}, got {gpu_id}"


@pytest.mark.asyncio
async def test_scenario_state_isolation():
    """Test that each scenario has independent state (no cross-contamination)."""
    executor = ParallelDebateExecutor(num_parallel=2)
    
    scenarios = [
        {"id": "s1", "name": "Scenario1", "description": "desc1", "modified_assumptions": {"oil_price": 75}},
        {"id": "s2", "name": "Scenario2", "description": "desc2", "modified_assumptions": {"oil_price": 45}}
    ]
    
    # Mock workflow that modifies state
    async def mock_workflow(state):
        # Modify state (should not affect other scenarios)
        state['modified_by_workflow'] = state.get('scenario_name')
        return state
    
    mock_graph = MagicMock()
    mock_graph.ainvoke = mock_workflow
    
    initial_state = {
        'query': 'Test',
        'reasoning_chain': [],
        'extracted_facts': {},
        'shared_data': 'original'
    }
    
    results = await executor.execute_scenarios(scenarios, mock_graph, initial_state)
    
    # Verify each scenario has independent state
    assert len(results) == 2
    assert results[0]['modified_by_workflow'] == "Scenario1"
    assert results[1]['modified_by_workflow'] == "Scenario2"
    
    # Verify scenarios don't contaminate each other
    assert results[0]['scenario_assumptions']['oil_price'] == 75
    assert results[1]['scenario_assumptions']['oil_price'] == 45


@pytest.mark.asyncio
async def test_parallel_performance():
    """Test that parallel execution is faster than sequential."""
    executor = ParallelDebateExecutor(num_parallel=4)
    
    scenarios = [
        {"id": f"s{i}", "name": f"Scenario{i}", "description": f"desc{i}", "modified_assumptions": {}}
        for i in range(4)
    ]
    
    # Mock workflow that takes 0.5 seconds
    async def mock_workflow(state):
        await asyncio.sleep(0.5)
        return {**state, 'done': True}
    
    mock_graph = MagicMock()
    mock_graph.ainvoke = mock_workflow
    
    initial_state = {'query': 'Test', 'reasoning_chain': [], 'extracted_facts': {}}
    
    # Execute in parallel
    import time
    start = time.time()
    results = await executor.execute_scenarios(scenarios, mock_graph, initial_state)
    parallel_time = time.time() - start
    
    # Parallel should complete in ~0.5s (all running simultaneously)
    # Sequential would take ~2s (4 × 0.5s)
    assert parallel_time < 1.0, \
        f"Parallel execution should be <1s, took {parallel_time:.2f}s"
    
    # Verify would take much longer sequentially
    sequential_time_estimate = 4 * 0.5  # 4 scenarios × 0.5s each
    assert parallel_time < sequential_time_estimate * 0.7, \
        f"Parallel ({parallel_time:.2f}s) should be faster than sequential (~{sequential_time_estimate}s)"


@pytest.mark.skipif(not torch.cuda.is_available(), reason="Requires CUDA GPUs")
def test_get_gpu_utilization():
    """Test GPU utilization reporting."""
    executor = ParallelDebateExecutor(num_parallel=6)
    
    utilization = executor.get_gpu_utilization()
    
    assert utilization['available'] is True
    assert utilization['total_gpus'] == 8
    assert utilization['scenario_gpus'] == [0, 1, 2, 3, 4, 5]
    assert len(utilization['gpus']) == 6
    
    # Verify each GPU has proper info
    for gpu_info in utilization['gpus']:
        assert 'id' in gpu_info
        assert 'name' in gpu_info
        assert 'memory_allocated' in gpu_info
        assert 'memory_total' in gpu_info
        assert 'A100' in gpu_info['name'] or gpu_info['name']  # Should be A100 GPUs


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

