"""
Streaming adapter for LLM workflow.

Converts LangGraph workflow execution into streaming events for UI.
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
            stage: Stage name (classify, prefetch, agents, verify, synthesize, done)
            status: Status (running, complete, error)
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
    classifier: Optional[Classifier] = None
) -> AsyncIterator[WorkflowEvent]:
    """
    Run workflow with streaming events.
    
    Yields events for each stage:
    - classify: Question classification
    - prefetch: Data prefetch
    - agent:<name>: Individual agent execution with streaming tokens
    - verify: Verification
    - synthesize: Synthesis with streaming tokens
    - done: Final completion
    
    Args:
        question: User's question
        data_client: Data client for deterministic queries
        llm_client: LLM client for agent reasoning
        classifier: Question classifier (optional)
        
    Yields:
        WorkflowEvent objects
    """
    workflow_start = datetime.now(timezone.utc)
    
    try:
        # Stage 1: Classify
        yield WorkflowEvent(stage="classify", status="running")
        
        classify_start = datetime.now(timezone.utc)
        classifier = classifier or Classifier()
        classification = classifier.classify_text(question)
        classify_latency = (datetime.now(timezone.utc) - classify_start).total_seconds() * 1000
        
        yield WorkflowEvent(
            stage="classify",
            status="complete",
            payload={"classification": classification},
            latency_ms=classify_latency
        )
        
        # Stage 2: Prefetch
        yield WorkflowEvent(stage="prefetch", status="running")
        
        prefetch_start = datetime.now(timezone.utc)
        # Prefetch common data (placeholder for now)
        await asyncio.sleep(0.05)  # Simulate prefetch
        prefetch_latency = (datetime.now(timezone.utc) - prefetch_start).total_seconds() * 1000
        
        yield WorkflowEvent(
            stage="prefetch",
            status="complete",
            payload={"status": "complete"},
            latency_ms=prefetch_latency
        )
        
        # Stage 3: Agents (with streaming)
        from src.qnwis.agents.labour_economist import LabourEconomistAgent
        from src.qnwis.agents.nationalization import NationalizationAgent
        from src.qnwis.agents.skills import SkillsAgent
        from src.qnwis.agents.pattern_detective_llm import PatternDetectiveLLMAgent
        from src.qnwis.agents.national_strategy_llm import NationalStrategyLLMAgent
        
        agents = [
            ("LabourEconomist", LabourEconomistAgent(data_client, llm_client)),
            ("Nationalization", NationalizationAgent(data_client, llm_client)),
            ("Skills", SkillsAgent(data_client, llm_client)),
            ("PatternDetective", PatternDetectiveLLMAgent(data_client, llm_client)),
            ("NationalStrategy", NationalStrategyLLMAgent(data_client, llm_client)),
        ]
        
        context = {"classification": classification}
        agent_reports = []
        
        for agent_name, agent in agents:
            agent_start = datetime.now(timezone.utc)
            
            # Yield agent start event
            yield WorkflowEvent(
                stage=f"agent:{agent_name}",
                status="running"
            )
            
            # Stream agent execution
            agent_tokens = []
            agent_report = None
            
            async for event in agent.run_stream(question, context):
                if event["type"] == "token":
                    # Stream LLM tokens
                    agent_tokens.append(event["content"])
                    yield WorkflowEvent(
                        stage=f"agent:{agent_name}",
                        status="streaming",
                        payload={"token": event["content"]}
                    )
                
                elif event["type"] == "status":
                    # Stream status updates
                    yield WorkflowEvent(
                        stage=f"agent:{agent_name}",
                        status="running",
                        payload={"status": event["content"]}
                    )
                
                elif event["type"] == "warning":
                    # Stream warnings
                    yield WorkflowEvent(
                        stage=f"agent:{agent_name}",
                        status="warning",
                        payload={"warning": event["content"]}
                    )
                
                elif event["type"] == "complete":
                    # Agent completed
                    agent_report = event["report"]
                    agent_latency = event["latency_ms"]
                    
                    yield WorkflowEvent(
                        stage=f"agent:{agent_name}",
                        status="complete",
                        payload={
                            "report": agent_report,
                            "full_response": "".join(agent_tokens)
                        },
                        latency_ms=agent_latency
                    )
                
                elif event["type"] == "error":
                    # Agent error
                    logger.error(f"Agent {agent_name} error: {event['content']}")
                    yield WorkflowEvent(
                        stage=f"agent:{agent_name}",
                        status="error",
                        payload={"error": event["content"]}
                    )
            
            if agent_report:
                agent_reports.append(agent_report)
        
        # Stage 4: Verify
        yield WorkflowEvent(stage="verify", status="running")
        
        verify_start = datetime.now(timezone.utc)
        
        # Collect warnings from all agents
        all_warnings = []
        for report in agent_reports:
            if hasattr(report, 'warnings') and report.warnings:
                all_warnings.extend(report.warnings)
        
        verify_latency = (datetime.now(timezone.utc) - verify_start).total_seconds() * 1000
        
        yield WorkflowEvent(
            stage="verify",
            status="complete",
            payload={"warnings": all_warnings},
            latency_ms=verify_latency
        )
        
        # Stage 5: Synthesize (with streaming)
        yield WorkflowEvent(stage="synthesize", status="running")
        
        synthesize_start = datetime.now(timezone.utc)
        
        from src.qnwis.synthesis.engine import SynthesisEngine
        
        engine = SynthesisEngine(llm_client)
        
        synthesis_tokens = []
        async for token in engine.synthesize_stream(question, agent_reports):
            synthesis_tokens.append(token)
            yield WorkflowEvent(
                stage="synthesize",
                status="streaming",
                payload={"token": token}
            )
        
        synthesis = "".join(synthesis_tokens)
        synthesize_latency = (datetime.now(timezone.utc) - synthesize_start).total_seconds() * 1000
        
        yield WorkflowEvent(
            stage="synthesize",
            status="complete",
            payload={"synthesis": synthesis},
            latency_ms=synthesize_latency
        )
        
        # Stage 6: Done
        total_latency = (datetime.now(timezone.utc) - workflow_start).total_seconds() * 1000
        
        yield WorkflowEvent(
            stage="done",
            status="complete",
            payload={
                "agent_reports": agent_reports,
                "synthesis": synthesis,
                "warnings": all_warnings
            },
            latency_ms=total_latency
        )
    
    except Exception as e:
        logger.error(f"Workflow error: {e}", exc_info=True)
        yield WorkflowEvent(
            stage="error",
            status="error",
            payload={"error": str(e)}
        )
