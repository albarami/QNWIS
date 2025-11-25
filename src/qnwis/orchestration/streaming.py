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
logger.info("📦 streaming.py MODULE LOADED!")


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


def _is_json_serializable(obj: Any) -> bool:
    """Check if an object is JSON serializable."""
    import json
    try:
        json.dumps(obj)
        return True
    except (TypeError, ValueError):
        return False


def _sanitize_dict(d: Dict[str, Any]) -> Dict[str, Any]:
    """Remove non-serializable values from a dictionary recursively."""
    if not isinstance(d, dict):
        return d
    
    result = {}
    for k, v in d.items():
        # Skip known non-serializable fields
        if k in ('event_callback', 'emit_event_fn'):
            continue
        # Skip functions and callables
        if callable(v):
            continue
        # Recursively handle nested dicts
        if isinstance(v, dict):
            result[k] = _sanitize_dict(v)
        elif isinstance(v, list):
            result[k] = [_sanitize_dict(item) if isinstance(item, dict) else item 
                        for item in v if not callable(item)]
        else:
            # Only include serializable values
            if _is_json_serializable(v):
                result[k] = v
    return result


def _payload_for_stage(stage: str, state: Dict[str, Any]) -> Dict[str, Any]:
    """Return a compact payload for UI consumption."""

    if stage == "classifier":
        return {
            "complexity": state.get("complexity"),
            "reasoning": state.get("reasoning_chain", [])
        }
    if stage == "extraction":
        return {
            "extracted_facts": state.get("extracted_facts", []),
            "data_sources": state.get("data_sources", []),
            "facts_count": len(state.get("extracted_facts", [])),
        }
    if stage in {"financial", "market", "operations", "research"}:
        key = f"{stage}_analysis"
        analysis = state.get(key)
        return {
            "agent_name": stage,
            "analysis": analysis,
            "report": analysis  # For compatibility
        }
    if stage == "debate":
        debate_results = state.get("debate_results", {})
        # Return full debate with conversation turns
        return debate_results
    if stage == "critique":
        return {
            "critique": state.get("critique_report"),
            "critique_report": state.get("critique_report")  # For compatibility
        }
    if stage == "verification":
        return {
            "verification": state.get("fact_check_results", {}),
            "fact_check_results": state.get("fact_check_results", {})  # For compatibility
        }
    if stage == "scenario_gen":
        return {
            "scenarios": state.get("scenarios", []),
            "num_scenarios": len(state.get("scenarios", []))
        }
    if stage == "parallel_exec":
        # Sanitize scenario_results to remove non-serializable fields
        scenario_results = state.get("scenario_results", [])
        sanitized_results = [_sanitize_dict(r) if isinstance(r, dict) else r for r in scenario_results]
        return {
            "scenario_results": sanitized_results,
            "scenarios_completed": len(scenario_results),
            "scenarios": state.get("scenarios", [])
        }
    if stage == "meta_synthesis":
        # Sanitize scenario_results to remove non-serializable fields
        scenario_results = state.get("scenario_results", [])
        sanitized_results = [_sanitize_dict(r) if isinstance(r, dict) else r for r in scenario_results]
        return {
            "meta_synthesis": state.get("meta_synthesis"),
            "final_synthesis": state.get("final_synthesis"),
            "scenario_results": sanitized_results,
            "confidence_score": state.get("confidence_score", 0)
        }
    if stage == "synthesis":
        return {
            "confidence_score": state.get("confidence_score"),
            "final_synthesis": state.get("final_synthesis"),
            "text": state.get("final_synthesis"),  # For compatibility
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

    # DIAGNOSTIC - REMOVE AFTER VERIFICATION
    import os
    import sys
    logger.critical("🔥🔥🔥 STREAMING.PY FUNCTION EXECUTING - FRESH CODE! 🔥🔥🔥")
    logger.critical(f"🔥 Python PID: {os.getpid()}, Bytecode tag: {sys.implementation.cache_tag}")
    # END DIAGNOSTIC

    logger.info(f"🚀 run_workflow_stream CALLED! QNWIS_WORKFLOW_IMPL={os.getenv('QNWIS_WORKFLOW_IMPL', 'NOT SET')}")
    logger.info(f"🎯 use_langgraph_workflow()={use_langgraph_workflow()}")
    
    # Feature flag: Use new modular workflow if enabled
    if use_langgraph_workflow():
        logger.info("Using NEW modular LangGraph workflow (workflow.py) with LIVE streaming")

        # Import workflow components
        from .workflow import create_intelligence_graph
        from .state import IntelligenceState

        # Create event queue for real-time debate turn streaming
        event_queue = asyncio.Queue()
        workflow_complete = False

        async def emit_event_fn(stage: str, status: str, payload=None, latency_ms=None):
            """
            Event callback for nodes to emit real-time events (e.g., debate turns).
            This allows LegendaryDebateOrchestrator to stream conversation turns live.
            """
            event = WorkflowEvent(
                stage=stage,
                status=status,
                payload=payload or {},
                latency_ms=latency_ms
            )
            await event_queue.put(event)
            logger.info(f"📤 Queued debate event: {stage} - {status}")  # Changed to INFO level

        # Initialize state with emit callback
        initial_state: IntelligenceState = {
            "query": question,
            "complexity": "",
            "agent_reports": [],
            "extracted_facts": [],
            "data_sources": [],
            "data_quality_score": 0.0,
            "financial_analysis": None,
            "market_analysis": None,
            "operations_analysis": None,
            "research_analysis": None,
            "debate_synthesis": None,
            "debate_results": None,
            "critique_report": None,
            "fact_check_results": None,
            "fabrication_detected": False,
            "final_synthesis": None,
            "confidence_score": 0.0,
            "reasoning_chain": [],
            "nodes_executed": [],
            "metadata": {},
            "execution_time": None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "warnings": [],
            "errors": [],
            "emit_event_fn": emit_event_fn,  # Pass callback to nodes for real-time events
        }

        graph = create_intelligence_graph()

        # Run workflow in background task
        async def run_workflow():
            nonlocal workflow_complete
            try:
                async for event in graph.astream(initial_state):
                    # Forward node completion events to queue
                    for node_name, node_output in event.items():
                        await event_queue.put(("node_complete", node_name, node_output))
            except Exception as e:
                logger.error(f"Workflow execution error: {e}", exc_info=True)
                await event_queue.put(("error", str(e), None))
            finally:
                workflow_complete = True
                await event_queue.put(("done", None, None))

        # Start workflow in background
        workflow_task = asyncio.create_task(run_workflow())

        # Stream events from queue as they arrive (real-time!)
        first_agent_emitted = False
        rag_emitted = False

        while True:
            # Get next event from queue (blocks until available)
            queue_item = await event_queue.get()

            # Handle different event types
            if isinstance(queue_item, WorkflowEvent):
                # Direct event from emit_event_fn (e.g., debate turns)
                logger.info(f"🎪 Yielding debate event to SSE: {queue_item.stage}")
                yield queue_item
                continue

            # Unpack node completion event
            event_type, data1, data2 = queue_item

            if event_type == "done":
                # Workflow complete
                break

            if event_type == "error":
                # Workflow error
                yield WorkflowEvent(
                    stage="error",
                    status="error",
                    payload={"error": data1}
                )
                break

            # Node completion event
            node_name = data1
            node_output = data2

            logger.info(f"Node '{node_name}' completed, emitting event")

            # Map node names to stage names
            stage_map = {
                "classifier": "classify",
                "extraction": "prefetch",
                "scenario_gen": "scenario_gen",
                "parallel_exec": "parallel_exec",
                "meta_synthesis": "meta_synthesis",
                "financial": "agent:financial",
                "market": "agent:market",
                "operations": "agent:operations",
                "research": "agent:research",
                "debate": "debate",
                "critique": "critique",
                "verification": "verify",
                "synthesis": "synthesize",
            }

            stage = stage_map.get(node_name, node_name)

            # Emit synthetic RAG stage after prefetch (extraction)
            if node_name == "extraction" and not rag_emitted:
                rag_emitted = True
                # Emit prefetch first
                yield WorkflowEvent(
                    stage="prefetch",
                    status="complete",
                    payload=_payload_for_stage(node_name, node_output),
                )
                # Then emit RAG
                yield WorkflowEvent(
                    stage="rag",
                    status="complete",
                    payload={
                        "retrieved_docs": [],
                        "context": "RAG context retrieved"
                    },
                )
                continue  # Skip the normal emit below

            # Emit agent_selection stage BEFORE first agent
            if node_name in {"financial", "market", "operations", "research"} and not first_agent_emitted:
                first_agent_emitted = True
                yield WorkflowEvent(
                    stage="agent_selection",
                    status="complete",
                    payload={
                        "selected_agents": ["financial", "market", "operations", "research"]
                    },
                )

            # Emit node complete event
            yield WorkflowEvent(
                stage=stage,
                status="complete",
                payload=_payload_for_stage(node_name, node_output),
            )

        # Ensure workflow task completes
        await workflow_task

        # Emit final done event
        yield WorkflowEvent(
            stage="done",
            status="complete",
            payload={
                "confidence": initial_state.get("confidence_score", 0.0),
                "warnings": initial_state.get("warnings", []),
                "errors": initial_state.get("errors", []),
            },
        )
        return  # Exit early for langgraph workflow
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
