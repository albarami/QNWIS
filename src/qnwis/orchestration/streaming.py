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
        
        # Stage 2: Intelligent Prefetch (H1)
        yield WorkflowEvent(stage="prefetch", status="running")
        
        prefetch_start = datetime.now(timezone.utc)
        
        # Use intelligent classification-based prefetching
        from .prefetch import prefetch_queries
        
        try:
            prefetched_data = await prefetch_queries(
                classification=classification,
                data_client=data_client,
                max_concurrent=5,
                timeout_seconds=20.0
            )
            prefetch_success = True
        except Exception as e:
            logger.error(f"Prefetch failed: {e}")
            prefetched_data = {}
            prefetch_success = False
        
        prefetch_latency = (datetime.now(timezone.utc) - prefetch_start).total_seconds() * 1000
        
        yield WorkflowEvent(
            stage="prefetch",
            status="complete",
            payload={
                "queries_fetched": len(prefetched_data),
                "query_ids": list(prefetched_data.keys()),
                "success": prefetch_success
            },
            latency_ms=prefetch_latency
        )
        
        # Initialize context dictionary
        context = {"classification": classification}
        
        # Store prefetched data in context for agents to use
        context["prefetched_data"] = prefetched_data
        
        # Stage 2.5: RAG Context Retrieval (H4)
        yield WorkflowEvent(stage="rag", status="running")
        
        rag_start = datetime.now(timezone.utc)
        
        # Retrieve external context using RAG
        from ..rag.retriever import retrieve_external_context, format_rag_context_for_prompt
        
        try:
            rag_result = await retrieve_external_context(
                query=question,
                max_snippets=3,
                include_api_data=True,
                min_relevance=0.15
            )
            rag_context = format_rag_context_for_prompt(rag_result)
            context["rag_context"] = rag_context
            context["rag_sources"] = rag_result.get("sources", [])
            rag_success = True
        except Exception as e:
            logger.error(f"RAG retrieval failed: {e}")
            context["rag_context"] = ""
            context["rag_sources"] = []
            rag_success = False
        
        rag_latency = (datetime.now(timezone.utc) - rag_start).total_seconds() * 1000
        
        yield WorkflowEvent(
            stage="rag",
            status="complete",
            payload={
                "snippets_retrieved": len(rag_result.get("snippets", [])) if rag_success else 0,
                "sources": context.get("rag_sources", []),
                "success": rag_success
            },
            latency_ms=rag_latency
        )
        
        # Stage 3: Intelligent Agent Selection (H6)
        from src.qnwis.agents.labour_economist import LabourEconomistAgent
        from src.qnwis.agents.nationalization import NationalizationAgent
        from src.qnwis.agents.skills import SkillsAgent
        from src.qnwis.agents.pattern_detective_llm import PatternDetectiveLLMAgent
        from src.qnwis.agents.national_strategy_llm import NationalStrategyLLMAgent
        from ..orchestration.agent_selector import AgentSelector
        
        # Select relevant agents based on classification
        selector = AgentSelector()
        selected_agent_names = selector.select_agents(
            classification=classification,
            min_agents=2,
            max_agents=4
        )
        selection_explanation = selector.explain_selection(selected_agent_names, classification)
        
        # Log selection
        logger.info(
            f"Selected {len(selected_agent_names)}/{len(selector.AGENT_EXPERTISE)} agents: "
            f"{selected_agent_names} (saves {selection_explanation['savings']})"
        )
        
        # Yield agent selection event (H6)
        yield WorkflowEvent(
            stage="agent_selection",
            status="complete",
            payload={
                "selected_agents": selected_agent_names,
                "selected_count": len(selected_agent_names),
                "total_available": len(selector.AGENT_EXPERTISE),
                "savings": selection_explanation['savings'],
                "explanation": selection_explanation
            },
            latency_ms=0  # No latency, instant selection
        )
        
        # Create agent registry
        agent_registry = {
            "LabourEconomist": LabourEconomistAgent(data_client, llm_client),
            "Nationalization": NationalizationAgent(data_client, llm_client),
            "SkillsAgent": SkillsAgent(data_client, llm_client),
            "PatternDetective": PatternDetectiveLLMAgent(data_client, llm_client),
            "NationalStrategy": NationalStrategyLLMAgent(data_client, llm_client),
        }
        
        # Build agents list with only selected agents
        agents = [
            (name, agent_registry[name])
            for name in selected_agent_names
            if name in agent_registry
        ]
        
        # If no agents selected (shouldn't happen), fallback to LabourEconomist
        if not agents:
            logger.warning("No agents selected, falling back to LabourEconomist")
            agents = [("LabourEconomist", agent_registry["LabourEconomist"])]
        
        # Context already initialized earlier with classification and prefetched_data
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
        
        # Stage 4: Verify (H3 - Complete verification with numeric validation & citation checks)
        yield WorkflowEvent(stage="verify", status="running")
        
        verify_start = datetime.now(timezone.utc)
        
        # Comprehensive verification using existing verification infrastructure
        from ..orchestration.verification import verify_report, VerificationIssue
        from ..verification.schemas import NumericClaim
        
        # Collect all verification data
        all_warnings = []
        all_verification_issues = []
        numeric_validation_summary = {
            "total_claims": 0,
            "validated_claims": 0,
            "failed_claims": 0,
            "missing_citations": 0
        }
        
        # Process each agent report
        for agent_name, report in zip([name for name, _ in agents], agent_reports):
            # 1. Numeric verification - validate metrics against bounds
            if hasattr(report, 'findings'):
                verification_result = verify_report(report)
                if verification_result.issues:
                    all_verification_issues.extend(verification_result.issues)
                    for issue in verification_result.issues:
                        all_warnings.append(f"[{agent_name}] {issue.code}: {issue.detail}")
            
            # 2. Citation checks - ensure data sources are referenced
            if hasattr(report, 'findings'):
                for idx, finding in enumerate(report.findings):
                    # Check if finding has data sources cited
                    has_citation = False
                    if hasattr(finding, 'data_sources') and finding.data_sources:
                        has_citation = len(finding.data_sources) > 0
                    elif hasattr(finding, 'query_ids') and finding.query_ids:
                        has_citation = len(finding.query_ids) > 0
                    
                    if not has_citation:
                        numeric_validation_summary["missing_citations"] += 1
                        all_warnings.append(
                            f"[{agent_name}] Finding {idx+1} missing data source citation"
                        )
            
            # 3. Collect report-level warnings
            if hasattr(report, 'warnings') and report.warnings:
                all_warnings.extend([f"[{agent_name}] {w}" for w in report.warnings])
        
        # Calculate verification metrics
        numeric_validation_summary["total_issues"] = len(all_verification_issues)
        numeric_validation_summary["warning_count"] = len([i for i in all_verification_issues if i.level == "warn"])
        numeric_validation_summary["error_count"] = len([i for i in all_verification_issues if i.level == "error"])
        
        verify_latency = (datetime.now(timezone.utc) - verify_start).total_seconds() * 1000
        
        # Yield verification complete with detailed payload
        yield WorkflowEvent(
            stage="verify",
            status="complete",
            payload={
                "warnings": all_warnings,
                "verification_summary": numeric_validation_summary,
                "issues": [
                    {
                        "level": issue.level,
                        "code": issue.code,
                        "detail": issue.detail
                    }
                    for issue in all_verification_issues
                ],
                "total_warnings": len(all_warnings),
                "passed": len(all_verification_issues) == 0
            },
            latency_ms=verify_latency
        )
        
        # Log verification results
        if all_verification_issues:
            logger.warning(
                f"Verification found {len(all_verification_issues)} issues: "
                f"{numeric_validation_summary['warning_count']} warnings, "
                f"{numeric_validation_summary['error_count']} errors"
            )
        else:
            logger.info("Verification passed with no issues")
        
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
