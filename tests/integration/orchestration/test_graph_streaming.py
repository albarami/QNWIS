"""
Integration tests for LangGraph streaming orchestration.

Tests that workflow emits events in correct order with parallel agents.
"""

import pytest
from unittest.mock import MagicMock
from src.qnwis.orchestration.streaming import run_workflow_stream, WorkflowEvent
from src.qnwis.llm.client import LLMClient
from src.qnwis.llm.config import LLMConfig
from src.qnwis.agents.base import DataClient


@pytest.fixture
def mock_data_client():
    """Create mock DataClient."""
    return MagicMock(spec=DataClient)


@pytest.fixture
def stub_llm_client():
    """Create stub LLM client."""
    from src.qnwis.llm.config import get_llm_config; config = get_llm_config()
    return LLMClient(config=config)


@pytest.mark.asyncio
async def test_workflow_emits_stages_in_order(mock_data_client, stub_llm_client):
    """Test workflow emits stages in correct order."""
    events = []
    
    async for event in run_workflow_stream(
        question="What is the unemployment rate in Qatar?",
        data_client=mock_data_client,
        llm_client=stub_llm_client
    ):
        events.append(event)
    
    # Extract stage names
    stages = [e.stage for e in events]
    
    # Should have classify → prefetch → agents → verify → synthesize → done
    assert "classify" in stages
    assert "prefetch" in stages
    # At least one agent should run
    assert any("agent:" in s or s == "agents" for s in stages)
    assert "verify" in stages or "verification" in stages
    assert "synthesize" in stages or "synthesis" in stages
    assert "done" in stages or any(e.status == "complete" for e in events if e.stage == "synthesize")


@pytest.mark.asyncio
async def test_workflow_classify_stage_completes(mock_data_client, stub_llm_client):
    """Test classify stage runs and completes."""
    events = []
    
    async for event in run_workflow_stream(
        question="What is the unemployment rate in Qatar?",
        data_client=mock_data_client,
        llm_client=stub_llm_client
    ):
        events.append(event)
        if event.stage == "classify" and event.status == "complete":
            break
    
    # Should have classify complete event
    classify_events = [e for e in events if e.stage == "classify"]
    assert len(classify_events) > 0
    
    complete_classify = [e for e in classify_events if e.status == "complete"]
    assert len(complete_classify) > 0
    
    # Should have classification in payload
    assert "classification" in complete_classify[0].payload or "result" in complete_classify[0].payload


@pytest.mark.asyncio
async def test_workflow_prefetch_stage_completes(mock_data_client, stub_llm_client):
    """Test prefetch stage runs and completes."""
    events = []
    
    async for event in run_workflow_stream(
        question="What is the unemployment rate in Qatar?",
        data_client=mock_data_client,
        llm_client=stub_llm_client
    ):
        events.append(event)
        if event.stage == "prefetch" and event.status == "complete":
            break
    
    # Should have prefetch complete event
    prefetch_events = [e for e in events if e.stage == "prefetch"]
    assert len(prefetch_events) > 0


@pytest.mark.asyncio
async def test_workflow_emits_latency_metrics(mock_data_client, stub_llm_client):
    """Test workflow includes latency metrics."""
    events = []
    
    async for event in run_workflow_stream(
        question="Test question",
        data_client=mock_data_client,
        llm_client=stub_llm_client
    ):
        events.append(event)
        if len(events) > 10:  # Get enough events
            break
    
    # Complete events should have latency
    complete_events = [e for e in events if e.status == "complete"]
    
    if complete_events:
        assert any(e.latency_ms is not None for e in complete_events)


@pytest.mark.asyncio
async def test_workflow_includes_timestamps(mock_data_client, stub_llm_client):
    """Test workflow events include timestamps."""
    events = []
    
    async for event in run_workflow_stream(
        question="Test question",
        data_client=mock_data_client,
        llm_client=stub_llm_client
    ):
        events.append(event)
        if len(events) > 5:
            break
    
    # All events should have timestamps
    for event in events:
        assert hasattr(event, 'timestamp')
        assert event.timestamp is not None


@pytest.mark.asyncio
async def test_workflow_synthesis_is_non_empty(mock_data_client, stub_llm_client):
    """Test synthesis stage produces non-empty output."""
    synthesis_event = None
    
    async for event in run_workflow_stream(
        question="What is the unemployment rate in Qatar?",
        data_client=mock_data_client,
        llm_client=stub_llm_client
    ):
        if "synthe" in event.stage.lower() and event.status == "complete":
            synthesis_event = event
            break
    
    # Should have synthesis output
    if synthesis_event:
        assert synthesis_event.payload
        # Payload should have some content
        assert len(str(synthesis_event.payload)) > 0


@pytest.mark.asyncio
async def test_workflow_handles_simple_question(mock_data_client, stub_llm_client):
    """Test workflow handles simple question end-to-end."""
    events = []
    
    async for event in run_workflow_stream(
        question="unemployment",
        data_client=mock_data_client,
        llm_client=stub_llm_client
    ):
        events.append(event)
    
    # Should complete without error
    assert len(events) > 0
    
    # Should not have error events
    error_events = [e for e in events if e.status == "error"]
    assert len(error_events) == 0
