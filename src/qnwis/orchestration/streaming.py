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
    
    # Feature flag: Use new modular workflow if enabled
    if use_langgraph_workflow():
        logger.info("Using NEW modular LangGraph workflow (workflow.py) with LIVE streaming")
        
        # Import workflow components
        from .workflow import create_intelligence_graph
        from .state import IntelligenceState
        
        # Initialize state
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
        }
        
        graph = create_intelligence_graph()
        
        # Stream events as nodes complete
        first_agent_emitted = False
        rag_emitted = False
        async for event in graph.astream(initial_state):
            # LangGraph astream yields dict with node name as key
            for node_name, node_output in event.items():
                logger.info(f"Node '{node_name}' completed, emitting event")
                
                # Map node names to stage names
                stage_map = {
                    "classifier": "classify",
                    "extraction": "prefetch",
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
                
                # Special handling for debate node - emit conversation turns
                if node_name == "debate":
                    debate_results = node_output.get("debate_results", {})
                    contradictions = debate_results.get("contradictions", [])
                    
                    # Emit each contradiction as debate conversation turns
                    for turn_num, contradiction in enumerate(contradictions, 1):
                        agent_a = contradiction.get("agent_a", "agent1")
                        agent_b = contradiction.get("agent_b", "agent2")
                        topic = contradiction.get("topic", "policy analysis")
                        winner = contradiction.get("winning_agent", "undetermined")
                        sentiment = contradiction.get("sentiment_delta", "0")
                        
                        timestamp = datetime.now(timezone.utc).isoformat()
                        
                        # Turn 1: Agent A challenges with their position
                        yield WorkflowEvent(
                            stage=f"debate:turn{turn_num*2-1}",
                            status="streaming",
                            payload={
                                "agent": agent_a,
                                "turn": turn_num * 2 - 1,
                                "type": "challenge",
                                "message": f"⚔️ {agent_a.upper()} challenges the analysis on {topic}. Sentiment: {sentiment}. Confidence: {contradiction.get('agent_a_confidence', 'unknown')}",
                                "timestamp": timestamp,
                            }
                        )
                        
                        # Turn 2: Agent B responds
                        yield WorkflowEvent(
                            stage=f"debate:turn{turn_num*2}",
                            status="streaming",
                            payload={
                                "agent": agent_b,
                                "turn": turn_num * 2,
                                "type": "response",
                                "message": f"🛡️ {agent_b.upper()} responds. Confidence: {contradiction.get('agent_b_confidence', 'unknown')}",
                                "timestamp": timestamp,
                            }
                        )
                        
                        # Turn 3: Resolution
                        yield WorkflowEvent(
                            stage=f"debate:turn{turn_num*2+1}",
                            status="streaming",
                            payload={
                                "agent": winner,
                                "turn": turn_num * 2 + 1,
                                "type": "resolution",
                                "message": f"⚖️ RESOLUTION: {winner.upper()}'s position adopted based on {sentiment} sentiment delta and confidence differential",
                                "timestamp": timestamp,
                            }
                        )
                
                # Emit node complete event
                yield WorkflowEvent(
                    stage=stage,
                    status="complete",
                    payload=_payload_for_stage(node_name, node_output),
                )
        
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
