"""
Streaming adapter for the LangGraph intelligence workflow.

Supports feature-flag based switching between:
- Legacy graph_llm.py (monolithic, 2016 lines)
- New workflow.py (modular, 10 nodes)
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Dict, Optional

from .feature_flags import use_langgraph_workflow
from .workflow import run_intelligence_query

logger = logging.getLogger(__name__)


class WorkflowEvent:
    """Event emitted during workflow execution."""
    
    def __init__(
        self,
        stage: str,
        status: str = "running",
        payload: Optional[Dict[str, Any]] = None,
        latency_ms: Optional[float] = None
    ):
        """
        Initialize workflow event.
        
        Args:
            stage: Stage name (classify, prefetch, rag, agents, verify, synthesize, done)
            status: Status (running, streaming, complete, error)
            payload: Event payload
            latency_ms: Stage latency in milliseconds
        """
        self.stage = stage
        self.status = status
        self.payload = payload or {}
        self.latency_ms = latency_ms
        self.timestamp = datetime.now(timezone.utc).isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        return {
            "stage": self.stage,
            "status": self.status,
            "payload": self.payload,
            "latency_ms": self.latency_ms,
            "timestamp": self.timestamp
        }


def _payload_for_stage(stage: str, state: Dict[str, Any]) -> Dict[str, Any]:
    """Return a compact payload for UI consumption."""

    if stage == "classifier":
        return {"complexity": state.get("complexity")}
    if stage == "extraction":
        return {
            "sources": state.get("data_sources", []),
            "facts": len(state.get("extracted_facts", [])),
        }
    if stage in {"financial", "market", "operations", "research"}:
        key = f"{stage}_analysis"
        return {"summary": state.get(key)}
    if stage == "debate":
        return state.get("debate_results", {})
    if stage == "critique":
        return {"critique": state.get("critique_report")}
    if stage == "verification":
        return state.get("fact_check_results", {})
    if stage == "synthesis":
        return {
            "confidence": state.get("confidence_score"),
            "summary": state.get("final_synthesis"),
        }
    return {}


async def run_workflow_stream(
    question: str,
    data_client: Any = None,
    llm_client: Any = None,
    query_registry: Optional[Any] = None,
    classifier: Optional[Any] = None,
    provider: str = "anthropic",
    request_id: Optional[str] = None
) -> AsyncIterator[WorkflowEvent]:
    """
    Run the LangGraph workflow and emit stage events in execution order.
    
    Supports feature-flag based switching:
    - QNWIS_WORKFLOW_IMPL=langgraph: Use new modular workflow.py
    - QNWIS_WORKFLOW_IMPL=legacy: Use old graph_llm.py (default)
    
    Args:
        question: User's question
        data_client: DataClient (for legacy compatibility)
        llm_client: LLMClient (for legacy compatibility)
        query_registry: Query registry (for legacy compatibility)
        classifier: Classifier (for legacy compatibility)
        provider: LLM provider
        request_id: Request ID for logging
    
    Yields:
        WorkflowEvent objects
    """
    
    # Feature flag: Use new modular workflow if enabled
    if use_langgraph_workflow():
        logger.info("Using NEW modular LangGraph workflow (workflow.py)")
        result = await run_intelligence_query(question)
    else:
        # Fallback to legacy graph_llm.py
        logger.info("Using LEGACY monolithic workflow (graph_llm.py)")
        from .graph_llm import build_workflow
        
        # Import required clients if not provided
        if data_client is None:
            from ..agents.base import DataClient
            data_client = DataClient()
        if llm_client is None:
            from ..llm.client import LLMClient
            llm_client = LLMClient(provider=provider)
        if classifier is None:
            from ..classification.classifier import Classifier
            classifier = Classifier()
        
        workflow = build_workflow(data_client, llm_client, classifier)
        
        # Run legacy workflow and convert to new format
        legacy_result = await workflow.run_stream(question, lambda *args: None)
        
        # Map legacy result to new state format
        result = {
            "query": question,
            "complexity": legacy_result.get("classification", {}).get("complexity", "medium"),
            "extracted_facts": [],
            "data_sources": [],
            "data_quality_score": 0.8,
            "agent_reports": legacy_result.get("agent_reports", []),
            "final_synthesis": legacy_result.get("synthesis"),
            "confidence_score": 0.7,
            "reasoning_chain": ["Legacy workflow executed"],
            "nodes_executed": ["legacy_workflow"],
            "warnings": legacy_result.get("warnings", []),
            "errors": legacy_result.get("errors", []),
            "debate_results": legacy_result.get("debate_results", {}),
            "fact_check_results": legacy_result.get("verification", {}),
        }

    for stage in result.get("nodes_executed", []):
        if stage == "debate":
            for detail in result.get("debate_results", {}).get("details", []):
                yield WorkflowEvent(stage="debate:turn", status="streaming", payload=detail)

        yield WorkflowEvent(
            stage=stage,
            status="complete",
            payload=_payload_for_stage(stage, result),
        )

    yield WorkflowEvent(
        stage="done",
        status="complete",
        payload={
            "confidence": result.get("confidence_score"),
            "warnings": result.get("warnings", []),
            "errors": result.get("errors", []),
        },
    )
