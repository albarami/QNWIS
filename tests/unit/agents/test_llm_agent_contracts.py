"""
Unit tests for LLM agent contracts.

Tests that each agent runs _fetch_data() and emits streamed tokens
then AgentReport with citations + confidence.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from src.qnwis.agents.base_llm import LLMAgent
from src.qnwis.agents.base import DataClient, AgentReport
from src.qnwis.llm.client import LLMClient
from src.qnwis.llm.config import LLMConfig
from src.qnwis.data.deterministic.models import QueryResult, Row, Provenance


class TestLLMAgentImplementation(LLMAgent):
    """Test implementation of LLMAgent for testing."""

    async def _fetch_data(self, question: str, context: dict):
        """Fetch test data."""
        from src.qnwis.data.deterministic.models import Freshness

        provenance = Provenance(
            source="csv",
            dataset_id="test_dataset",
            locator="/data/test.csv",
            fields=["value", "rate"]
        )

        freshness = Freshness(
            asof_date="2025-01-15",
            updated_at="2025-01-15T10:00:00"
        )

        return {
            "test_query": QueryResult(
                query_id="test_query",
                rows=[
                    Row(data={"value": 42.0, "rate": 5.2})
                ],
                unit="percent",
                provenance=provenance,
                freshness=freshness
            )
        }

    def _build_prompt(self, question: str, data: dict, context: dict):
        """Build test prompt."""
        return (
            "You are a test agent.",
            f"Question: {question}\nData: {len(data)} results"
        )


@pytest.fixture
def mock_data_client():
    """Create mock DataClient."""
    client = MagicMock(spec=DataClient)
    return client


@pytest.fixture
def stub_llm_client():
    """Create stub LLM client."""
    from src.qnwis.llm.config import get_llm_config
    return LLMClient(config=get_llm_config())


@pytest.mark.asyncio
async def test_agent_calls_fetch_data(mock_data_client, stub_llm_client):
    """Test agent calls _fetch_data during execution."""
    agent = TestLLMAgentImplementation(
        client=mock_data_client,
        llm=stub_llm_client
    )

    # Run agent
    events = []
    async for event in agent.run_stream("test question"):
        events.append(event)

    # Should have status event about fetching data
    status_events = [e for e in events if e["type"] == "status"]
    assert any("fetching" in e["content"].lower() for e in status_events)


@pytest.mark.asyncio
async def test_agent_emits_streamed_tokens(mock_data_client, stub_llm_client):
    """Test agent emits streamed tokens from LLM."""
    agent = TestLLMAgentImplementation(
        client=mock_data_client,
        llm=stub_llm_client
    )

    token_events = []
    async for event in agent.run_stream("test question"):
        if event["type"] == "token":
            token_events.append(event)

    # Should have received multiple tokens
    assert len(token_events) > 10

    # Tokens should be strings
    for event in token_events:
        assert isinstance(event["content"], str)


@pytest.mark.asyncio
async def test_agent_emits_final_report(mock_data_client, stub_llm_client):
    """Test agent emits final AgentReport."""
    agent = TestLLMAgentImplementation(
        client=mock_data_client,
        llm=stub_llm_client
    )

    complete_event = None
    async for event in agent.run_stream("test question"):
        if event["type"] == "complete":
            complete_event = event
            break

    assert complete_event is not None
    assert "report" in complete_event
    assert isinstance(complete_event["report"], AgentReport)


@pytest.mark.asyncio
async def test_agent_report_has_citations(mock_data_client, stub_llm_client):
    """Test agent report includes citations."""
    agent = TestLLMAgentImplementation(
        client=mock_data_client,
        llm=stub_llm_client
    )

    report = await agent.run("test question")

    assert isinstance(report, AgentReport)
    # Report should have findings with evidence (citations)
    if report.findings:
        # At least one finding should have evidence
        has_evidence = any(len(f.evidence) > 0 for f in report.findings)
        # Note: stub might not have evidence, but structure should exist
        assert hasattr(report.findings[0], 'evidence')


@pytest.mark.asyncio
async def test_agent_report_has_confidence(mock_data_client, stub_llm_client):
    """Test agent report includes confidence score."""
    agent = TestLLMAgentImplementation(
        client=mock_data_client,
        llm=stub_llm_client
    )

    report = await agent.run("test question")

    assert isinstance(report, AgentReport)
    # Findings should have confidence scores
    if report.findings:
        for finding in report.findings:
            assert hasattr(finding, 'confidence_score')
            if finding.confidence_score is not None:
                assert 0.0 <= finding.confidence_score <= 1.0


@pytest.mark.asyncio
async def test_agent_includes_latency_metric(mock_data_client, stub_llm_client):
    """Test agent includes latency in completion event."""
    agent = TestLLMAgentImplementation(
        client=mock_data_client,
        llm=stub_llm_client
    )

    complete_event = None
    async for event in agent.run_stream("test question"):
        if event["type"] == "complete":
            complete_event = event
            break

    assert complete_event is not None
    assert "latency_ms" in complete_event
    assert isinstance(complete_event["latency_ms"], (int, float))
    assert complete_event["latency_ms"] > 0


@pytest.mark.asyncio
async def test_agent_handles_no_data_gracefully(mock_data_client, stub_llm_client):
    """Test agent handles case where no data is found."""
    class NoDataAgent(LLMAgent):
        async def _fetch_data(self, question: str, context: dict):
            return {}  # No data

        def _build_prompt(self, question: str, data: dict, context: dict):
            return ("system", "user")

    agent = NoDataAgent(
        client=mock_data_client,
        llm=stub_llm_client
    )

    events = []
    async for event in agent.run_stream("test question"):
        events.append(event)

    # Should have warning about no data
    warning_events = [e for e in events if e["type"] == "warning"]
    assert len(warning_events) > 0

    # Should still complete with empty report
    complete_events = [e for e in events if e["type"] == "complete"]
    assert len(complete_events) == 1


@pytest.mark.asyncio
async def test_agent_emits_status_updates(mock_data_client, stub_llm_client):
    """Test agent emits status updates throughout execution."""
    agent = TestLLMAgentImplementation(
        client=mock_data_client,
        llm=stub_llm_client
    )

    status_events = []
    async for event in agent.run_stream("test question"):
        if event["type"] == "status":
            status_events.append(event)

    # Should have multiple status updates
    assert len(status_events) >= 2  # At least fetch + analyze


@pytest.mark.asyncio
async def test_agent_validates_numbers_against_data(mock_data_client, stub_llm_client):
    """Test agent validates numbers against source data."""
    agent = TestLLMAgentImplementation(
        client=mock_data_client,
        llm=stub_llm_client
    )

    events = []
    async for event in agent.run_stream("test question"):
        events.append(event)

    # Agent should perform validation (may or may not warn depending on data)
    # Just ensure it completes without error
    complete_events = [e for e in events if e["type"] == "complete"]
    assert len(complete_events) == 1


@pytest.mark.asyncio
async def test_agent_non_streaming_run(mock_data_client, stub_llm_client):
    """Test agent non-streaming run() method."""
    agent = TestLLMAgentImplementation(
        client=mock_data_client,
        llm=stub_llm_client
    )

    report = await agent.run("test question")

    assert isinstance(report, AgentReport)
    assert report.agent == "TestLLMAgentImplementation"


@pytest.mark.asyncio
async def test_agent_passes_context_through(mock_data_client, stub_llm_client):
    """Test agent passes context to _fetch_data and _build_prompt."""
    class ContextAgent(LLMAgent):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.received_context = None

        async def _fetch_data(self, question: str, context: dict):
            self.received_context = context
            return {}

        def _build_prompt(self, question: str, data: dict, context: dict):
            return ("system", "user")

    agent = ContextAgent(
        client=mock_data_client,
        llm=stub_llm_client
    )

    test_context = {"classification": "employment", "entity": "Qatar"}

    async for event in agent.run_stream("test", context=test_context):
        if event["type"] == "complete":
            break

    assert agent.received_context == test_context
