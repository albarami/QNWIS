"""
Tests for parallel executor event emissions.

Verifies that the parallel executor properly emits events during scenario execution.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock
from src.qnwis.orchestration.parallel_executor import ParallelDebateExecutor


@pytest.mark.asyncio
async def test_parallel_executor_emits_start_event():
    """Test that parallel executor emits start event."""
    emitted_events = []
    
    async def mock_callback(stage, status, payload, latency_ms=None):
        emitted_events.append({
            'stage': stage,
            'status': status,
            'payload': payload
        })
    
    executor = ParallelDebateExecutor(num_parallel=2, event_callback=mock_callback)
    
    # Mock scenarios
    scenarios = [
        {"name": "Base Case", "description": "Normal conditions"},
        {"name": "Oil Shock", "description": "Oil price collapse"}
    ]
    
    # Mock workflow that returns immediately
    mock_workflow = Mock()
    mock_workflow.ainvoke = AsyncMock(return_value={
        'final_synthesis': 'Test synthesis',
        'confidence_score': 0.8,
        'reasoning_chain': [],
        'debate_results': {'total_turns': 30}
    })
    
    mock_state = {
        'query': 'Test query',
        'reasoning_chain': [],
        'emit_event_fn': mock_callback
    }
    
    # Execute
    results = await executor.execute_scenarios(scenarios, mock_workflow, mock_state)
    
    # Verify start event was emitted
    start_events = [e for e in emitted_events if e['stage'] == 'parallel_exec' and e['status'] == 'started']
    assert len(start_events) == 1, "Should emit one parallel_exec started event"
    assert start_events[0]['payload']['total_scenarios'] == 2
    
    print("✅ Test passed: parallel_exec start event emitted")


@pytest.mark.asyncio
async def test_parallel_executor_emits_scenario_events():
    """Test that parallel executor emits events for each scenario."""
    emitted_events = []
    
    async def mock_callback(stage, status, payload, latency_ms=None):
        emitted_events.append({
            'stage': stage,
            'status': status,
            'payload': payload
        })
    
    executor = ParallelDebateExecutor(num_parallel=2, event_callback=mock_callback)
    
    scenarios = [
        {"name": "Scenario 1", "description": "Test 1"},
        {"name": "Scenario 2", "description": "Test 2"}
    ]
    
    mock_workflow = Mock()
    mock_workflow.ainvoke = AsyncMock(return_value={
        'final_synthesis': 'Test',
        'confidence_score': 0.7,
        'reasoning_chain': [],
        'debate_results': {'total_turns': 30}
    })
    
    mock_state = {'query': 'Test', 'reasoning_chain': [], 'emit_event_fn': mock_callback}
    
    results = await executor.execute_scenarios(scenarios, mock_workflow, mock_state)
    
    # Verify scenario start events
    scenario_start_events = [e for e in emitted_events if e['stage'].startswith('scenario:') and e['status'] == 'started']
    assert len(scenario_start_events) == 2, "Should emit start event for each scenario"
    
    # Verify scenario complete events
    scenario_complete_events = [e for e in emitted_events if e['stage'].startswith('scenario:') and e['status'] == 'complete']
    assert len(scenario_complete_events) == 2, "Should emit complete event for each scenario"
    
    print("✅ Test passed: scenario start/complete events emitted")


@pytest.mark.asyncio
async def test_parallel_executor_emits_progress_events():
    """Test that parallel executor emits progress updates."""
    emitted_events = []
    
    async def mock_callback(stage, status, payload, latency_ms=None):
        emitted_events.append({
            'stage': stage,
            'status': status,
            'payload': payload
        })
    
    executor = ParallelDebateExecutor(num_parallel=3, event_callback=mock_callback)
    
    scenarios = [
        {"name": "S1", "description": "T1"},
        {"name": "S2", "description": "T2"},
        {"name": "S3", "description": "T3"}
    ]
    
    mock_workflow = Mock()
    mock_workflow.ainvoke = AsyncMock(return_value={
        'final_synthesis': 'Test',
        'confidence_score': 0.75,
        'reasoning_chain': [],
        'debate_results': None
    })
    
    mock_state = {'query': 'Test', 'reasoning_chain': [], 'emit_event_fn': mock_callback}
    
    results = await executor.execute_scenarios(scenarios, mock_workflow, mock_state)
    
    # Verify progress events
    progress_events = [e for e in emitted_events if e['stage'] == 'parallel_progress']
    assert len(progress_events) == 3, f"Should emit progress after each completion, got {len(progress_events)}"
    
    # Verify final progress shows 100%
    final_progress = progress_events[-1]
    assert final_progress['payload']['percent'] == 100
    assert final_progress['payload']['completed'] == 3
    
    print("✅ Test passed: progress events emitted correctly")


@pytest.mark.asyncio
async def test_parallel_executor_emits_complete_event():
    """Test that parallel executor emits final complete event."""
    emitted_events = []
    
    async def mock_callback(stage, status, payload, latency_ms=None):
        emitted_events.append({
            'stage': stage,
            'status': status,
            'payload': payload
        })
    
    executor = ParallelDebateExecutor(num_parallel=2, event_callback=mock_callback)
    
    scenarios = [
        {"name": "Test 1", "description": "D1"},
        {"name": "Test 2", "description": "D2"}
    ]
    
    mock_workflow = Mock()
    mock_workflow.ainvoke = AsyncMock(return_value={
        'final_synthesis': 'Synthesis text',
        'confidence_score': 0.85,
        'reasoning_chain': [],
        'debate_results': {'total_turns': 30}
    })
    
    mock_state = {'query': 'Test', 'reasoning_chain': [], 'emit_event_fn': mock_callback}
    
    results = await executor.execute_scenarios(scenarios, mock_workflow, mock_state)
    
    # Verify complete event
    complete_events = [e for e in emitted_events if e['stage'] == 'parallel_exec' and e['status'] == 'complete']
    assert len(complete_events) == 1, "Should emit one parallel_exec complete event"
    assert complete_events[0]['payload']['scenarios_completed'] == 2
    assert complete_events[0]['payload']['scenarios_failed'] == 0
    
    print("✅ Test passed: parallel_exec complete event emitted")


@pytest.mark.asyncio
async def test_parallel_executor_without_callback():
    """Test that parallel executor works without event callback (graceful degradation)."""
    executor = ParallelDebateExecutor(num_parallel=1, event_callback=None)
    
    scenarios = [{"name": "Test", "description": "Test scenario"}]
    
    mock_workflow = Mock()
    mock_workflow.ainvoke = AsyncMock(return_value={
        'final_synthesis': 'Test',
        'confidence_score': 0.9,
        'reasoning_chain': [],
        'debate_results': None
    })
    
    mock_state = {'query': 'Test', 'reasoning_chain': []}
    
    # Should not raise error
    results = await executor.execute_scenarios(scenarios, mock_workflow, mock_state)
    
    assert len(results) == 1
    print("✅ Test passed: works without callback (graceful degradation)")


if __name__ == "__main__":
    print("Running parallel executor event tests...")
    asyncio.run(test_parallel_executor_emits_start_event())
    asyncio.run(test_parallel_executor_emits_scenario_events())
    asyncio.run(test_parallel_executor_emits_progress_events())
    asyncio.run(test_parallel_executor_emits_complete_event())
    asyncio.run(test_parallel_executor_without_callback())
    print("\n✅ All tests passed!")

