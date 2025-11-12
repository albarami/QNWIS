"""
Unit tests for Chainlit orchestration and UI components.

Tests the workflow adapter, UI components, and verification bridge
with mocked graph and verification outputs.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.qnwis.orchestration.workflow_adapter import StageEvent, run_workflow_stream
from src.qnwis.verification.ui_bridge import (
    render_verification_panel,
    render_audit_panel,
    render_agent_finding_panel,
    render_raw_evidence_panel,
)
from src.qnwis.ui.components import (
    render_timeline_widget,
    render_stage_card,
    sanitize_markdown,
    format_metric_value,
)


class TestWorkflowAdapter:
    """Test workflow adapter streaming functionality."""
    
    @pytest.mark.asyncio
    async def test_workflow_stream_basic(self):
        """Test basic workflow streaming with all stages."""
        question = "What is Qatar unemployment?"
        
        stages_seen = []
        async for event in run_workflow_stream(question):
            stages_seen.append(event.stage)
            assert isinstance(event, StageEvent)
            assert event.stage is not None
            assert event.payload is not None
            assert event.timestamp is not None
            
            # Break after a few stages to avoid long test
            if len(stages_seen) >= 3:
                break
        
        # Should see at least classify and prefetch
        assert "classify" in stages_seen
        assert "prefetch" in stages_seen
    
    @pytest.mark.asyncio
    async def test_stage_event_structure(self):
        """Test StageEvent dataclass structure."""
        event = StageEvent(
            stage="test",
            payload={"key": "value"},
            latency_ms=100
        )
        
        assert event.stage == "test"
        assert event.payload == {"key": "value"}
        assert event.latency_ms == 100
        assert event.timestamp is not None
    
    @pytest.mark.asyncio
    async def test_workflow_with_user_context(self):
        """Test workflow with user context."""
        question = "Test question"
        user_ctx = {"request_id": "test_123", "user": "test_user"}
        
        async for event in run_workflow_stream(question, user_ctx):
            # Should complete without errors
            assert event is not None
            break  # Just test first event


class TestVerificationUIBridge:
    """Test verification UI rendering functions."""
    
    def test_render_verification_panel_pass(self):
        """Test rendering verification panel with all checks passing."""
        report = {
            "citations": {"status": "pass", "details": []},
            "numeric_checks": {"status": "pass", "issues": []},
            "confidence": {"min": 0.80, "avg": 0.85, "max": 0.92},
            "freshness": {"oldest": "2025-10-15", "newest": "2025-11-08"},
            "issues": []
        }
        
        result = render_verification_panel(report)
        
        assert "✅" in result
        assert "Citations" in result
        assert "Numeric Validation" in result
        assert "85%" in result or "0.85" in result
        assert "2025-11-08" in result
    
    def test_render_verification_panel_with_warnings(self):
        """Test rendering verification panel with warnings."""
        report = {
            "citations": {"status": "pass", "details": []},
            "numeric_checks": {
                "status": "warn",
                "issues": [{"detail": "Value outside expected range"}]
            },
            "confidence": {"min": 0.65, "avg": 0.72, "max": 0.85},
            "issues": [{"level": "warn", "code": "range_check", "detail": "Test warning"}]
        }
        
        result = render_verification_panel(report)
        
        assert "⚠️" in result
        assert "warn" in result.lower() or "Warning" in result
    
    def test_render_audit_panel(self):
        """Test rendering audit trail panel."""
        audit_data = {
            "request_id": "req_abc123",
            "query_ids": ["q_demo", "syn_employment_latest"],
            "sources": ["aggregates/employment.csv", "World Bank API"],
            "timestamps": {
                "start": "2025-11-12T10:00:00Z",
                "end": "2025-11-12T10:00:05Z"
            },
            "cache_stats": {"hits": 2, "misses": 1},
            "latency_ms": 245
        }
        
        result = render_audit_panel(audit_data)
        
        assert "req_abc123" in result
        assert "q_demo" in result
        assert "2" in result  # query count or cache hits
        assert "245" in result or "0.24" in result  # latency
    
    def test_render_raw_evidence_panel(self):
        """Test rendering of raw evidence tables."""
        tables = [
            {
                "query_id": "syn_demo",
                "dataset_id": "aggregates/demo.csv",
                "freshness": "2025-11-08",
                "rows": [
                    {"year": 2024, "value": 1.2},
                    {"year": 2023, "value": 1.0},
                ],
            }
        ]
        
        result = render_raw_evidence_panel("TimeMachine", "Baseline Finding", tables)
        
        assert "syn_demo" in result
        assert "aggregates/demo.csv" in result
        assert "year" in result
        assert "value" in result
    
    def test_render_agent_finding_panel(self):
        """Test rendering agent finding panel."""
        finding = {
            "title": "Employment Trends",
            "summary": "Male employment is 69.38%, female is 30.62%",
            "metrics": {
                "male_percent": 69.38,
                "female_percent": 30.62,
                "total_percent": 100.0
            },
            "evidence": [
                {
                    "query_id": "syn_employment_latest",
                    "dataset_id": "aggregates/employment.csv",
                    "freshness_as_of": "2025-11-08"
                }
            ],
            "warnings": [],
            "confidence_score": 0.9
        }
        
        result = render_agent_finding_panel("LabourEconomist", finding)
        
        assert "LabourEconomist" in result
        assert "Employment Trends" in result
        assert "69.38" in result or "69.4" in result
        assert "syn_employment_latest" in result
        assert "90%" in result or "0.9" in result  # confidence


class TestUIComponents:
    """Test UI component rendering functions."""
    
    def test_render_timeline_widget(self):
        """Test timeline widget rendering."""
        completed = ["classify", "prefetch"]
        current = "agents"
        
        result = render_timeline_widget(completed, current)
        assert "Stage timeline" in result  # sticky heading present
        assert "qnwis-stage-complete" in result
        assert "qnwis-stage-active" in result
        assert "Classify" in result
        assert "Prefetch" in result
    
    def test_render_stage_card_classify(self):
        """Test rendering classify stage card."""
        payload = {
            "intent": "baseline.employment",
            "complexity": "simple",
            "confidence": 0.85,
            "entities": {
                "sectors": ["Construction"],
                "metrics": ["employment"],
                "horizon_months": 12
            },
            "status": "completed"
        }
        
        result = render_stage_card("classify", payload, 45)
        
        assert "Intent" in result
        assert "baseline.employment" in result
        assert "85%" in result or "0.85" in result
        assert "45ms" in result
    
    def test_render_stage_card_agent(self):
        """Test rendering agent stage card."""
        payload = {
            "agent": "TimeMachine",
            "findings": [{"title": "Test"}],
            "finding_count": 1,
            "status": "completed"
        }
        
        result = render_stage_card("agent:TimeMachine", payload, 120)
        
        assert "TimeMachine" in result
        assert "1" in result  # finding count
        assert "120ms" in result
    
    def test_sanitize_markdown_removes_scripts(self):
        """Test markdown sanitization removes script tags."""
        dangerous = "Hello <script>alert('xss')</script> world"
        
        result = sanitize_markdown(dangerous)
        
        assert "<script>" not in result
        assert "alert" not in result
        assert "Hello" in result
        assert "world" in result
    
    def test_sanitize_markdown_removes_event_handlers(self):
        """Test markdown sanitization removes event handlers."""
        dangerous = '<a href="#" onclick="alert(\'xss\')">Click</a>'
        
        result = sanitize_markdown(dangerous)
        
        assert "onclick" not in result
    
    def test_format_metric_value_percentage(self):
        """Test metric value formatting for percentages."""
        assert "69.4%" in format_metric_value("male_percent", 69.38)
        assert "0.50%" in format_metric_value("retention_rate", 0.005)
    
    def test_format_metric_value_large_numbers(self):
        """Test metric value formatting for large numbers."""
        result = format_metric_value("employee_count", 150000)
        assert "150,000" in result
    
    def test_format_metric_value_scores(self):
        """Test metric value formatting for scores."""
        result = format_metric_value("confidence_score", 0.8542)
        assert "0.85" in result


class TestRAGRetriever:
    """Test RAG retrieval functionality."""
    
    @pytest.mark.asyncio
    async def test_retrieve_external_context(self):
        """Test RAG context retrieval."""
        from src.qnwis.rag.retriever import retrieve_external_context
        
        result = await retrieve_external_context("Qatar unemployment trends")
        
        assert "snippets" in result
        assert "sources" in result
        assert "freshness" in result
        assert "metadata" in result
        
        # Should have some snippets
        assert len(result["snippets"]) > 0
        
        # Each snippet should have required fields
        for snippet in result["snippets"]:
            assert "text" in snippet
            assert "source" in snippet
            assert "freshness" in snippet
    
    @pytest.mark.asyncio
    async def test_rag_context_carries_citations(self):
        """Test that RAG context always carries source citations."""
        from src.qnwis.rag.retriever import retrieve_external_context
        
        result = await retrieve_external_context("GCC comparison")
        
        for snippet in result["snippets"]:
            assert snippet["source"] is not None
            assert len(snippet["source"]) > 0


class TestModelSelector:
    """Test model selection and fallback logic."""
    
    def test_resolve_models_default(self):
        """Test default model resolution."""
        from src.qnwis.config.model_select import resolve_models
        
        primary, fallback = resolve_models()
        
        assert primary is not None
        assert fallback is not None
        assert "claude" in primary.lower()
        assert "gpt" in fallback.lower()
    
    def test_get_anthropic_model(self):
        """Test getting Anthropic model."""
        from src.qnwis.config.model_select import get_anthropic_model
        
        model = get_anthropic_model()
        
        assert model is not None
        assert "claude" in model.lower()
    
    def test_get_openai_model(self):
        """Test getting OpenAI model."""
        from src.qnwis.config.model_select import get_openai_model
        
        model = get_openai_model()
        
        assert model is not None
        assert "gpt" in model.lower()
    
    def test_get_model_provider(self):
        """Test model provider detection."""
        from src.qnwis.config.model_select import get_model_provider
        
        assert get_model_provider("claude-sonnet-4-5") == "anthropic"
        assert get_model_provider("gpt-4o") == "openai"

    def test_call_with_model_fallback_success(self):
        """Primary model succeeds without invoking fallback."""
        from src.qnwis.config.model_select import call_with_model_fallback
        
        result, used_fallback = call_with_model_fallback(lambda: "primary", lambda: "fallback")
        
        assert result == "primary"
        assert used_fallback is False

    def test_call_with_model_fallback_on_http_404(self):
        """Anthropic 404 should trigger immediate fallback to OpenAI."""
        from src.qnwis.config.model_select import call_with_model_fallback

        class DummyError(RuntimeError):
            def __init__(self, status_code: int):
                super().__init__("HTTP error")
                self.response = type("Resp", (), {"status_code": status_code})()
        
        def primary():
            raise DummyError(404)
        
        result, used_fallback = call_with_model_fallback(primary, lambda: "fallback")
        
        assert result == "fallback"
        assert used_fallback is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
