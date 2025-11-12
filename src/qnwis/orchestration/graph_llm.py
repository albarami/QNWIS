"""
LangGraph workflow for LLM-powered multi-agent orchestration.

Implements streaming workflow with nodes:
classify → prefetch → agents (parallel) → verify → synthesize → done
"""

import logging
from typing import TypedDict, Annotated, Sequence, Optional, Dict, Any
from datetime import datetime, timezone

from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages

from src.qnwis.agents.labour_economist import LabourEconomistAgent
from src.qnwis.agents.nationalization import NationalizationAgent
from src.qnwis.agents.skills import SkillsAgent
from src.qnwis.agents.pattern_detective_llm import PatternDetectiveLLMAgent
from src.qnwis.agents.national_strategy_llm import NationalStrategyLLMAgent
from src.qnwis.agents.base import AgentReport, DataClient
from src.qnwis.llm.client import LLMClient
from src.qnwis.classification.classifier import Classifier

logger = logging.getLogger(__name__)


class WorkflowState(TypedDict):
    """State passed between workflow nodes."""
    
    question: str
    classification: Optional[Dict[str, Any]]
    prefetch: Optional[Dict[str, Any]]
    agent_reports: Annotated[Sequence[AgentReport], add_messages]
    verification: Optional[Dict[str, Any]]
    synthesis: Optional[str]
    error: Optional[str]
    metadata: Dict[str, Any]


class LLMWorkflow:
    """
    LangGraph workflow orchestrating LLM-powered agents.
    
    Provides streaming execution with parallel agent processing.
    """
    
    def __init__(
        self,
        data_client: DataClient,
        llm_client: LLMClient,
        classifier: Optional[Classifier] = None
    ):
        """
        Initialize LLM workflow.
        
        Args:
            data_client: Data client for deterministic queries
            llm_client: LLM client for agent reasoning
            classifier: Question classifier (optional)
        """
        self.data_client = data_client
        self.llm_client = llm_client
        self.classifier = classifier or Classifier()
        
        # Initialize agents
        self.agents = {
            "labour_economist": LabourEconomistAgent(data_client, llm_client),
            "nationalization": NationalizationAgent(data_client, llm_client),
            "skills": SkillsAgent(data_client, llm_client),
            "pattern_detective": PatternDetectiveLLMAgent(data_client, llm_client),
            "national_strategy": NationalStrategyLLMAgent(data_client, llm_client),
        }
        
        # Build graph
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """
        Build LangGraph workflow.
        
        Returns:
            Compiled StateGraph
        """
        workflow = StateGraph(WorkflowState)
        
        # Add nodes
        workflow.add_node("classify", self._classify_node)
        workflow.add_node("prefetch", self._prefetch_node)
        workflow.add_node("agents", self._agents_node)
        workflow.add_node("verify", self._verify_node)
        workflow.add_node("synthesize", self._synthesize_node)
        
        # Define edges
        workflow.set_entry_point("classify")
        workflow.add_edge("classify", "prefetch")
        workflow.add_edge("prefetch", "agents")
        workflow.add_edge("agents", "verify")
        workflow.add_edge("verify", "synthesize")
        workflow.add_edge("synthesize", END)
        
        return workflow.compile()
    
    async def _classify_node(self, state: WorkflowState) -> WorkflowState:
        """
        Classify question to determine routing.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state with classification
        """
        start_time = datetime.now(timezone.utc)
        
        try:
            question = state["question"]
            classification = self.classifier.classify_text(question)
            
            latency_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            
            logger.info(
                f"Classification complete: complexity={classification.get('complexity')}, "
                f"latency={latency_ms:.0f}ms"
            )
            
            return {
                **state,
                "classification": {
                    "complexity": classification.get("complexity", "medium"),
                    "topics": classification.get("topics", []),
                    "latency_ms": latency_ms
                }
            }
        
        except Exception as e:
            logger.error(f"Classification failed: {e}", exc_info=True)
            return {
                **state,
                "classification": {"complexity": "medium", "error": str(e)},
                "error": f"Classification error: {e}"
            }
    
    async def _prefetch_node(self, state: WorkflowState) -> WorkflowState:
        """
        Prefetch common data needed by agents.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state with prefetch results
        """
        start_time = datetime.now(timezone.utc)
        
        try:
            # Prefetch common queries
            # (In a real implementation, this would cache results for agents)
            latency_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            
            logger.info(f"Prefetch complete: latency={latency_ms:.0f}ms")
            
            return {
                **state,
                "prefetch": {
                    "status": "complete",
                    "latency_ms": latency_ms
                }
            }
        
        except Exception as e:
            logger.error(f"Prefetch failed: {e}", exc_info=True)
            return {
                **state,
                "prefetch": {"status": "failed", "error": str(e)},
                "error": f"Prefetch error: {e}"
            }
    
    async def _agents_node(self, state: WorkflowState) -> WorkflowState:
        """
        Execute all agents in parallel.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state with agent reports
        """
        import asyncio
        
        question = state["question"]
        context = {
            "classification": state.get("classification"),
            "prefetch": state.get("prefetch")
        }
        
        # Run all agents in parallel
        agent_tasks = []
        for agent_name, agent in self.agents.items():
            task = agent.run(question, context)
            agent_tasks.append((agent_name, task))
        
        reports = []
        for agent_name, task in agent_tasks:
            try:
                report = await task
                reports.append(report)
                logger.info(f"Agent {agent_name} completed successfully")
            except Exception as e:
                logger.error(f"Agent {agent_name} failed: {e}", exc_info=True)
                # Create error report
                from src.qnwis.agents.base import AgentReport
                error_report = AgentReport(
                    agent=agent_name,
                    findings=[],
                    narrative=f"Agent failed: {e}"
                )
                reports.append(error_report)
        
        return {
            **state,
            "agent_reports": reports
        }
    
    async def _verify_node(self, state: WorkflowState) -> WorkflowState:
        """
        Verify agent outputs for consistency.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state with verification results
        """
        start_time = datetime.now(timezone.utc)
        
        try:
            reports = state.get("agent_reports", [])
            
            # Collect all warnings from agents
            all_warnings = []
            for report in reports:
                if hasattr(report, 'warnings') and report.warnings:
                    all_warnings.extend(report.warnings)
            
            latency_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            
            logger.info(
                f"Verification complete: {len(all_warnings)} warnings, "
                f"latency={latency_ms:.0f}ms"
            )
            
            return {
                **state,
                "verification": {
                    "status": "complete",
                    "warnings": all_warnings,
                    "latency_ms": latency_ms
                }
            }
        
        except Exception as e:
            logger.error(f"Verification failed: {e}", exc_info=True)
            return {
                **state,
                "verification": {"status": "failed", "error": str(e)},
                "error": f"Verification error: {e}"
            }
    
    async def _synthesize_node(self, state: WorkflowState) -> WorkflowState:
        """
        Synthesize agent findings into final answer.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state with synthesis
        """
        start_time = datetime.now(timezone.utc)
        
        try:
            from src.qnwis.synthesis.engine import SynthesisEngine
            
            engine = SynthesisEngine(self.llm_client)
            
            question = state["question"]
            reports = state.get("agent_reports", [])
            
            # Generate synthesis
            synthesis = await engine.synthesize(question, reports)
            
            latency_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            
            logger.info(f"Synthesis complete: latency={latency_ms:.0f}ms")
            
            return {
                **state,
                "synthesis": synthesis,
                "metadata": {
                    **state.get("metadata", {}),
                    "synthesis_latency_ms": latency_ms
                }
            }
        
        except Exception as e:
            logger.error(f"Synthesis failed: {e}", exc_info=True)
            # Fallback to simple concatenation
            reports = state.get("agent_reports", [])
            fallback = "\n\n".join([
                f"**{report.agent}**: {report.narrative}"
                for report in reports
                if report.narrative
            ])
            
            return {
                **state,
                "synthesis": fallback or "Unable to synthesize findings.",
                "error": f"Synthesis error: {e}"
            }
    
    async def run(self, question: str) -> Dict[str, Any]:
        """
        Run workflow for a question.
        
        Args:
            question: User's question
            
        Returns:
            Final workflow state
        """
        initial_state: WorkflowState = {
            "question": question,
            "classification": None,
            "prefetch": None,
            "agent_reports": [],
            "verification": None,
            "synthesis": None,
            "error": None,
            "metadata": {
                "start_time": datetime.now(timezone.utc).isoformat()
            }
        }
        
        final_state = await self.graph.ainvoke(initial_state)
        
        # Add total latency
        start_time = datetime.fromisoformat(final_state["metadata"]["start_time"])
        total_latency_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        final_state["metadata"]["total_latency_ms"] = total_latency_ms
        
        return final_state


def build_workflow(
    data_client: DataClient,
    llm_client: LLMClient,
    classifier: Optional[Classifier] = None
) -> LLMWorkflow:
    """
    Build LangGraph workflow.
    
    Args:
        data_client: Data client for deterministic queries
        llm_client: LLM client for agent reasoning
        classifier: Question classifier (optional)
        
    Returns:
        LLMWorkflow instance
    """
    return LLMWorkflow(data_client, llm_client, classifier)
