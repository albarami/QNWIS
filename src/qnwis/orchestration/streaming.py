"""
Streaming adapter for LLM workflow.

Converts LangGraph workflow execution into streaming events for UI.
This is now a simple wrapper around graph_llm.py!
"""

import logging
import asyncio
from typing import AsyncIterator, Optional, Dict, Any
from datetime import datetime, timezone

from src.qnwis.agents.base import DataClient
from src.qnwis.llm.client import LLMClient
from src.qnwis.classification.classifier import Classifier
from src.qnwis.orchestration.graph_llm import build_workflow

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


async def run_workflow_stream(
    question: str,
    data_client: DataClient,
    llm_client: LLMClient,
    query_registry: Optional[Any] = None,
    classifier: Optional[Classifier] = None,
    provider: str = "anthropic",
    request_id: Optional[str] = None
) -> AsyncIterator[WorkflowEvent]:
    """
    Run LangGraph workflow with streaming events.
    
    This function is now a SIMPLE WRAPPER around the LangGraph workflow!
    All the complexity (classification, prefetch, RAG, agent selection,
    agent execution, verification, synthesis) is handled by graph_llm.py.
    
    Yields events for each stage:
    - classify: Question classification
    - prefetch: Intelligent data prefetch
    - rag: RAG context retrieval
    - agent_selection: Intelligent agent selection
    - agent:<name>: Individual agent execution with streaming tokens
    - verify: Numeric verification & citation checks
    - synthesize: Synthesis with streaming tokens
    - done: Final completion
    
    Args:
        question: User's question
        data_client: Data client for deterministic queries
        llm_client: LLM client for agent reasoning
        query_registry: Query registry (optional, for compatibility)
        classifier: Question classifier (optional)
        provider: LLM provider (for logging)
        request_id: Request ID (for logging)
        
    Yields:
        WorkflowEvent objects
    """
    # Build LangGraph workflow
    workflow = build_workflow(data_client, llm_client, classifier)
    
    # Create event queue for streaming
    events_queue = asyncio.Queue()
    
    async def event_callback(
        stage: str, 
        status: str, 
        payload: Optional[Dict] = None, 
        latency_ms: Optional[float] = None
    ):
        """Callback for workflow events - puts them in queue."""
        event = WorkflowEvent(
            stage=stage,
            status=status,
            payload=payload,
            latency_ms=latency_ms
        )
        await events_queue.put(event)
    
    # Run workflow in background task
    async def execute_workflow():
        try:
            logger.info(f"Starting LangGraph workflow for question: {question[:100]}...")
            await workflow.run_stream(question, event_callback)
            await events_queue.put(None)  # Signal completion
        except Exception as e:
            logger.error(f"LangGraph workflow failed: {e}", exc_info=True)
            await events_queue.put(WorkflowEvent(
                stage="error",
                status="error",
                payload={"error": str(e), "error_type": type(e).__name__}
            ))
            await events_queue.put(None)
    
    # Start workflow execution
    workflow_task = asyncio.create_task(execute_workflow())
    
    try:
        # Yield events as they arrive from the graph
        while True:
            event = await events_queue.get()
            if event is None:
                # Workflow complete
                break
            yield event
    
    finally:
        # Ensure task is cleaned up
        if not workflow_task.done():
            workflow_task.cancel()
            try:
                await workflow_task
            except asyncio.CancelledError:
                pass
