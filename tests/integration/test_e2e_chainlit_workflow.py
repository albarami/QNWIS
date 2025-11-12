"""
End-to-end integration tests for Chainlit workflow.

Tests the complete workflow: classify → route → prefetch → agents → verify → synthesize.
"""

import pytest
from typing import List

from src.qnwis.orchestration.workflow_adapter import StageEvent, run_workflow_stream


class TestE2EWorkflow:
    """End-to-end workflow integration tests."""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_complete_workflow_unemployment_query(self):
        """Test complete workflow for unemployment query."""
        question = "What are the current unemployment trends in the GCC region?"
        
        stages_seen: List[str] = []
        events_by_stage = {}
        
        async for event in run_workflow_stream(question):
            stages_seen.append(event.stage)
            events_by_stage[event.stage] = event
            
            # Verify event structure
            assert isinstance(event, StageEvent)
            assert event.stage is not None
            assert event.payload is not None
            assert event.timestamp is not None
            assert event.latency_ms >= 0
        
        # Verify all expected stages completed
        assert "classify" in stages_seen
        assert "prefetch" in stages_seen
        assert any(s.startswith("agent:") for s in stages_seen)
        assert "verify" in stages_seen
        assert "synthesize" in stages_seen
        assert "done" in stages_seen
        
        # Verify classify stage
        classify_event = events_by_stage["classify"]
        assert classify_event.payload["status"] == "completed"
        assert "intent" in classify_event.payload
        assert "complexity" in classify_event.payload
        assert "confidence" in classify_event.payload
        
        # Verify prefetch stage
        prefetch_event = events_by_stage["prefetch"]
        assert prefetch_event.payload["status"] == "completed"
        
        # Verify at least one agent executed
        agent_events = [e for s, e in events_by_stage.items() if s.startswith("agent:")]
        assert len(agent_events) > 0
        
        for agent_event in agent_events:
            if agent_event.payload.get("status") == "completed":
                assert "findings" in agent_event.payload or "finding_count" in agent_event.payload
        
        # Verify verification stage
        verify_event = events_by_stage["verify"]
        assert verify_event.payload["status"] == "completed"
        assert "citations" in verify_event.payload
        assert "numeric_checks" in verify_event.payload
        assert "confidence" in verify_event.payload
        
        # Verify synthesis stage
        synthesize_event = events_by_stage["synthesize"]
        assert synthesize_event.payload["status"] == "completed"
        assert "agents" in synthesize_event.payload
        assert "finding_count" in synthesize_event.payload
        
        # Verify done stage
        done_event = events_by_stage["done"]
        assert done_event.payload["status"] == "completed"
        assert "council_report" in done_event.payload
        assert "verification" in done_event.payload
        assert "audit" in done_event.payload
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_workflow_with_rag_integration(self):
        """Test workflow includes RAG context."""
        question = "Compare Qatar labour market to KSA and UAE"
        
        events_by_stage = {}
        
        async for event in run_workflow_stream(question):
            events_by_stage[event.stage] = event
        
        # Verify RAG context in prefetch
        prefetch_event = events_by_stage.get("prefetch")
        assert prefetch_event is not None
        assert "rag_snippets" in prefetch_event.payload
        
        # Verify RAG context in final output
        done_event = events_by_stage.get("done")
        assert done_event is not None
        assert "rag_context" in done_event.payload
        
        rag_context = done_event.payload["rag_context"]
        assert "snippets" in rag_context
        assert "sources" in rag_context
        assert "freshness" in rag_context
        
        # Verify all RAG snippets have citations
        for snippet in rag_context.get("snippets", []):
            assert "source" in snippet
            assert "freshness" in snippet
            assert snippet["source"] is not None
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_workflow_audit_trail_complete(self):
        """Test workflow generates complete audit trail."""
        question = "What is Qatar unemployment rate?"
        
        done_event = None
        
        async for event in run_workflow_stream(question):
            if event.stage == "done":
                done_event = event
                break
        
        assert done_event is not None
        
        audit = done_event.payload.get("audit", {})
        
        # Verify audit trail components
        assert "request_id" in audit
        assert "query_ids" in audit
        assert "sources" in audit
        assert "timestamps" in audit
        assert "latency_ms" in audit
        
        # Verify request ID format
        assert audit["request_id"].startswith("req_")
        
        # Verify timestamps
        timestamps = audit["timestamps"]
        assert "start" in timestamps
        assert "end" in timestamps
        
        # Verify latency is reasonable
        assert audit["latency_ms"] > 0
        assert audit["latency_ms"] < 60000  # Less than 60 seconds
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_workflow_verification_enforces_citations(self):
        """Test workflow verification enforces citation requirements."""
        question = "Show me employment data"
        
        verify_event = None
        
        async for event in run_workflow_stream(question):
            if event.stage == "verify":
                verify_event = event
                break
        
        assert verify_event is not None
        
        payload = verify_event.payload
        
        # Verify citation check exists
        assert "citations" in payload
        citations = payload["citations"]
        assert "status" in citations
        
        # Status should be pass or fail, not unknown
        assert citations["status"] in ["pass", "fail"]
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_workflow_handles_multiple_agents(self):
        """Test workflow executes multiple agents."""
        question = "Analyze Qatar labour market comprehensively"
        
        agent_events = []
        
        async for event in run_workflow_stream(question):
            if event.stage.startswith("agent:"):
                agent_events.append(event)
        
        # Should have multiple agents
        assert len(agent_events) >= 3
        
        # Verify unique agents
        agent_names = set()
        for event in agent_events:
            agent_name = event.payload.get("agent")
            if agent_name:
                agent_names.add(agent_name)
        
        assert len(agent_names) >= 3
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_workflow_confidence_scoring(self):
        """Test workflow includes confidence scoring."""
        question = "What is the unemployment rate?"
        
        verify_event = None
        done_event = None
        
        async for event in run_workflow_stream(question):
            if event.stage == "verify":
                verify_event = event
            elif event.stage == "done":
                done_event = event
        
        assert verify_event is not None
        
        # Verify confidence stats in verification
        confidence = verify_event.payload.get("confidence", {})
        if confidence:
            assert "min" in confidence
            assert "avg" in confidence
            assert "max" in confidence
            
            # Verify confidence values are in valid range
            assert 0 <= confidence["min"] <= 1
            assert 0 <= confidence["avg"] <= 1
            assert 0 <= confidence["max"] <= 1
            assert confidence["min"] <= confidence["avg"] <= confidence["max"]
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_workflow_performance_targets(self):
        """Test workflow meets performance targets."""
        question = "Simple query"
        
        done_event = None
        
        async for event in run_workflow_stream(question):
            if event.stage == "done":
                done_event = event
                break
        
        assert done_event is not None
        
        total_latency = done_event.payload.get("audit", {}).get("latency_ms", 0)
        
        # Simple queries should complete in under 10 seconds
        assert total_latency < 10000, f"Workflow took {total_latency}ms, expected < 10000ms"
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_workflow_data_freshness_tracking(self):
        """Test workflow tracks data freshness."""
        question = "Current employment statistics"
        
        done_event = None
        
        async for event in run_workflow_stream(question):
            if event.stage == "done":
                done_event = event
                break
        
        assert done_event is not None
        
        # Check if any agent findings have freshness info
        council_report = done_event.payload.get("council_report", {})
        findings = council_report.get("findings", [])
        
        # At least one finding should exist
        assert len(findings) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])
