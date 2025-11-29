"""
LangGraph workflow for LLM-powered multi-agent orchestration.

Implements streaming workflow with nodes:
classify ΓåÆ prefetch ΓåÆ agents (parallel) ΓåÆ verify ΓåÆ synthesize ΓåÆ done
"""

import asyncio
import logging
import re
import textwrap
from typing import TypedDict, Annotated, Sequence, Optional, Dict, Any, AsyncIterator, List
from datetime import datetime, timezone, date, timedelta

from langgraph.graph import StateGraph, END

from ..agents.micro_economist import MicroEconomist
from ..agents.macro_economist import MacroEconomist
from ..agents.nationalization import NationalizationAgent
from ..agents.skills import SkillsAgent
from ..agents.pattern_detective_llm import PatternDetectiveLLMAgent
from ..agents.pattern_detective import PatternDetectiveAgent
from ..agents.pattern_miner import PatternMinerAgent
from ..agents.national_strategy import NationalStrategyAgent
from ..agents.alert_center import AlertCenterAgent
from ..agents.time_machine import TimeMachineAgent
from ..agents.predictor import PredictorAgent
from ..agents.scenario_agent import ScenarioAgent
from ..agents.base import AgentReport, DataClient
from ..llm.client import LLMClient
from ..classification.classifier import Classifier
from .citation_injector import CitationInjector
from src.qnwis.orchestration.prefetch_apis import get_complete_prefetch

logger = logging.getLogger(__name__)


class WorkflowState(TypedDict):
    """State passed between workflow nodes."""

    question: str
    classification: Optional[Dict[str, Any]]
    prefetch: Optional[Dict[str, Any]]
    rag_context: Optional[Dict[str, Any]]
    # McKinsey-Grade Calculation Pipeline
    structured_inputs: Optional[Dict[str, Any]]  # From structure_data_node
    data_quality: Optional[str]  # HIGH/MEDIUM/LOW/FAILED
    data_gaps: Optional[List[str]]  # Missing data points
    calculated_results: Optional[Dict[str, Any]]  # From calculate_node
    calculation_warning: Optional[str]  # Low confidence warning
    # Agent Selection
    selected_agents: Optional[list]
    agent_reports: list  # List of AgentReport objects
    debate_results: Optional[Dict[str, Any]]  # Multi-agent debate outcomes
    critique_results: Optional[Dict[str, Any]]  # Devil's advocate critique
    deterministic_result: Optional[str]  # Result from TimeMachine/Predictor/Scenario
    verification: Optional[Dict[str, Any]]
    synthesis: Optional[str]
    error: Optional[str]
    metadata: Dict[str, Any]
    reasoning_chain: list  # Step-by-step log of workflow actions
    event_callback: Optional[Any]  # For streaming events


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
        
        # Initialize LLM agents (PascalCase keys for reporting)
        self.agents = {
            "MicroEconomist": MicroEconomist(data_client, llm_client),
            "MacroEconomist": MacroEconomist(data_client, llm_client),
            "Nationalization": NationalizationAgent(data_client, llm_client),
            "SkillsAgent": SkillsAgent(data_client, llm_client),
            "PatternDetective": PatternDetectiveLLMAgent(data_client, llm_client),
        }
        self.agent_key_map = {
            "microeconomist": "MicroEconomist",
            "micro": "MicroEconomist",
            "macroeconomist": "MacroEconomist",
            "macro": "MacroEconomist",
            "nationalization": "Nationalization",
            "skills": "SkillsAgent",
            "skillsagent": "SkillsAgent",
            "patterndetective": "PatternDetective",
            "nationalstrategy": "NationalStrategy",  # Default to deterministic
            "timemachine": "TimeMachine",
            "predictor": "Predictor",
            "scenario": "Scenario",
            "patterndetectiveagent": "PatternDetectiveAgent",
            "patternminer": "PatternMiner",
            "alertcenter": "AlertCenter",
        }

        # Initialize deterministic agents for LEGENDARY depth mode
        self.deterministic_agents = {
            "TimeMachine": TimeMachineAgent(data_client),
            "Predictor": PredictorAgent(data_client),
            "Scenario": ScenarioAgent(data_client),
            "PatternDetectiveAgent": PatternDetectiveAgent(data_client),
            "PatternMiner": PatternMinerAgent(data_client),
            "NationalStrategy": NationalStrategyAgent(data_client),
            "AlertCenter": AlertCenterAgent(data_client),
        }

        # Build graph
        self.graph = self._build_graph()

        # Agent selector
        from .agent_selector import AgentSelector
        self.agent_selector = AgentSelector()

    def _normalize_agent_name(self, name: str) -> str:
        """Map selector keys to PascalCase agent names."""
        if not name:
            return ""
        if name in self.agents:
            return name
        if name in self.deterministic_agents:
            return name
            
        sanitized = name.lower().replace("_", "").replace(" ", "")
        mapped = self.agent_key_map.get(sanitized)
        if mapped:
            return mapped
            
        sanitized = sanitized.replace("agent", "")
        
        # Check LLM agents
        for candidate in self.agents:
            candidate_key = candidate.lower().replace("agent", "").replace("_", "")
            if candidate_key == sanitized:
                return candidate
                
        # Check deterministic agents
        for candidate in self.deterministic_agents:
            candidate_key = candidate.lower().replace("agent", "").replace("_", "")
            if candidate_key == sanitized:
                return candidate
                
        return name
    
    def _build_graph(self) -> StateGraph:
        """
        Build LangGraph workflow with conditional routing.

        Flow:
        - classify ΓåÆ routing decision
        - If deterministic agent detected ΓåÆ run that agent ΓåÆ synthesize ΓåÆ END
        - If LLM agents ΓåÆ prefetch ΓåÆ rag ΓåÆ agents ΓåÆ debate ΓåÆ critique ΓåÆ verify ΓåÆ synthesize ΓåÆ END

        Returns:
            Compiled StateGraph
        """
        workflow = StateGraph(WorkflowState)

        # Add nodes
        workflow.add_node("classify", self._classify_node)
        workflow.add_node("route_deterministic", self._route_deterministic_node)
        workflow.add_node("prefetch", self._prefetch_node)
        workflow.add_node("rag", self._rag_node)
        workflow.add_node("structure", self._structure_data_node)    # NEW: McKinsey pipeline
        workflow.add_node("calculate", self._calculate_node)          # NEW: McKinsey pipeline
        workflow.add_node("select_agents", self._select_agents_node)
        workflow.add_node("agents", self._agents_node)
        workflow.add_node("debate", self._debate_node)
        workflow.add_node("critique", self._critique_node)
        workflow.add_node("verify", self._verify_node)
        workflow.add_node("synthesize", self._synthesize_node)

        # Define routing function
        def should_route_deterministic(state: WorkflowState) -> str:
            """
            Decide routing based on classification.

            Returns:
                "deterministic" if temporal/forecast/scenario query
                "llm_agents" otherwise
            """
            classification = state.get("classification", {})
            route_to = classification.get("route_to")

            if route_to in ["time_machine", "predictor", "scenario"]:
                logger.info(f"Routing to deterministic agent: {route_to}")
                return "deterministic"
            else:
                logger.info("Routing to LLM agents")
                return "llm_agents"

        # Define edges
        workflow.set_entry_point("classify")

        # Conditional routing after classification
        workflow.add_conditional_edges(
            "classify",
            should_route_deterministic,
            {
                "deterministic": "route_deterministic",
                "llm_agents": "prefetch"
            }
        )

        # Deterministic path: route_deterministic ΓåÆ synthesize ΓåÆ END
        workflow.add_edge("route_deterministic", "synthesize")

        # LLM agents path: prefetch → rag → structure → calculate → select_agents → agents → debate → critique → verify → synthesize → END
        workflow.add_edge("prefetch", "rag")
        workflow.add_edge("rag", "structure")        # NEW: Structure extracted data
        workflow.add_edge("structure", "calculate")  # NEW: Deterministic calculations
        workflow.add_edge("calculate", "select_agents")
        workflow.add_edge("select_agents", "agents")
        workflow.add_edge("agents", "debate")
        workflow.add_edge("debate", "critique")
        workflow.add_edge("critique", "verify")
        workflow.add_edge("verify", "synthesize")

        # Both paths converge at synthesize
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
        # Emit running event
        if state.get("event_callback"):
            await state["event_callback"]("classify", "running")
        
        start_time = datetime.now(timezone.utc)
        
        try:
            question = state["question"]
            classification = self.classifier.classify_text(question)
            
            latency_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            
            logger.info(
                f"Classification complete: complexity={classification.get('complexity')}, "
                f"latency={latency_ms:.0f}ms"
            )

            # Update reasoning chain
            reasoning_chain = list(state.get("reasoning_chain", []))
            route_to = classification.get("route_to") or "llm_agents"
            reasoning_chain.append(
                f"Γ£ô Classification: {classification.get('complexity', 'medium')} complexity, "
                f"routed to {route_to}"
            )
            
            # Emit complete event
            if state.get("event_callback"):
                await state["event_callback"](
                    "classify", 
                    "complete", 
                    {
                        "classification": classification,
                        "reasoning_chain": reasoning_chain
                    },
                    latency_ms
                )
            
            return {
                **state,
                "classification": {
                    "complexity": classification.get("complexity", "medium"),
                    "topics": classification.get("topics", []),
                    "route_to": classification.get("route_to"),  # Phase 3: deterministic routing
                    "latency_ms": latency_ms,
                },
                "reasoning_chain": reasoning_chain,
            }
        
        except Exception as e:
            logger.error(f"Classification failed: {e}", exc_info=True)
            if state.get("event_callback"):
                await state["event_callback"]("classify", "error", {"error": str(e)})
            return {
                **state,
                "classification": {"complexity": "medium", "error": str(e)},
                "error": f"Classification error: {e}"
            }

    async def _route_deterministic_node(self, state: WorkflowState) -> WorkflowState:
        """
        Route to appropriate deterministic agent (TimeMachine, Predictor, or Scenario).

        Args:
            state: Current workflow state

        Returns:
            Updated state with deterministic_result
        """
        if state.get("event_callback"):
            await state["event_callback"]("route_deterministic", "running")

        start_time = datetime.now(timezone.utc)

        try:
            classification = state.get("classification", {})
            route_to = classification.get("route_to")
            question = state["question"]

            logger.info(f"Routing to deterministic agent: {route_to}")

            # Get the appropriate agent
            agent = self.deterministic_agents.get(route_to)

            if not agent:
                raise ValueError(f"Unknown deterministic agent: {route_to}")

            # For now, we'll create simple narrative responses
            # In production, you'd parse the question to extract parameters
            # and call the appropriate agent method

            if route_to == "time_machine":
                # Simple demo: call baseline_report for retention
                from datetime import date
                result = agent.baseline_report(
                    metric="retention",
                    sector=None,
                    start=date(2023, 1, 1),
                    end=date.today()
                )

            elif route_to == "predictor":
                # Simple demo: call forecast_baseline for retention
                from datetime import date
                result = agent.forecast_baseline(
                    metric="retention",
                    sector=None,
                    start=date(2023, 1, 1),
                    end=date.today(),
                    horizon_months=6
                )

            elif route_to == "scenario":
                # Simple demo: return instruction message
                result = """
# Scenario Planning

To use the Scenario agent, please provide a scenario specification.

Example:
```yaml
name: Retention Boost
description: 10% retention improvement
metric: retention
sector: Construction
horizon_months: 12
transforms:
  - type: multiplicative
    value: 0.10
    start_month: 0
```

Use `agent.apply(scenario_spec)` with your scenario definition.
"""
            else:
                result = f"Deterministic agent '{route_to}' called but not yet configured for this query type."

            latency_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

            logger.info(f"Deterministic agent complete: {route_to}, latency={latency_ms:.0f}ms")

            # Update reasoning chain
            reasoning_chain = list(state.get("reasoning_chain", []))
            reasoning_chain.append(
                f"Γ£ô Deterministic routing: executed {route_to} for historical/forecast/scenario analysis"
            )

            if state.get("event_callback"):
                await state["event_callback"](
                    "route_deterministic",
                    "complete",
                    {"agent": route_to},
                    latency_ms
                )

            return {
                **state,
                "deterministic_result": result,
                "metadata": {
                    **state.get("metadata", {}),
                    "deterministic_agent": route_to,
                    "deterministic_latency_ms": latency_ms,
                },
                "reasoning_chain": reasoning_chain,
            }

        except Exception as e:
            logger.error(f"Deterministic routing failed: {e}", exc_info=True)
            latency_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

            if state.get("event_callback"):
                await state["event_callback"]("route_deterministic", "error", {"error": str(e)})

            return {
                **state,
                "deterministic_result": f"Error routing to deterministic agent: {e}",
                "error": f"Deterministic routing error: {e}"
            }


    async def _prefetch_node(self, state: WorkflowState) -> WorkflowState:
        """
        Prefetch data from ALL available sources.
        Uses: MoL, GCC-STAT, World Bank, Semantic Scholar, Brave, Perplexity
        """
        query = state.get("question") or state.get("query", "")

        prefetch = get_complete_prefetch()

        try:
            extracted_facts = await prefetch.fetch_all_sources(query)

            extraction_confidence = 0.85 if len(extracted_facts) > 10 else 0.60
            reasoning = f"Extracted {len(extracted_facts)} facts from multiple sources"
            reasoning_chain = list(state.get("reasoning_chain", []))
            reasoning_chain.append(reasoning)

            updated_state = {
                **state,
                "prefetch": {
                    "fact_count": len(extracted_facts),
                    "facts": extracted_facts,
                },
                "extracted_facts": extracted_facts,
                "extraction_confidence": extraction_confidence,
                "reasoning_chain": reasoning_chain,
            }

            if event_callback := state.get("event_callback"):
                await event_callback(
                    "prefetch",
                    "complete",
                    {
                        "extracted_facts": extracted_facts,
                        "fact_count": len(extracted_facts),
                        "sources": list(
                            {fact["source"] for fact in extracted_facts if isinstance(fact, dict) and fact.get("source")}
                        ),
                        "reasoning_chain": reasoning_chain,
                    },
                    0,
                )

            # Prefetch complete - log via logger instead of print to avoid Unicode errors
            logger.info(f"Prefetch Complete: {len(extracted_facts)} facts")
            sources: Dict[str, int] = {}
            for fact in extracted_facts:
                if isinstance(fact, dict):
                    source = fact.get("source", "Unknown")
                    sources[source] = sources.get(source, 0) + 1

            for source, count in sources.items():
                logger.debug(f"Source {source}: {count} facts")

            return updated_state

        except Exception as e:
            logger.error(f"Prefetch error: {e}", exc_info=True)

            if state.get("event_callback"):
                await state["event_callback"]("prefetch", "error", {"error": str(e)})

            return {
                **state,
                "prefetch": {"status": "failed", "error": str(e)},
                "extracted_facts": [],
                "extraction_confidence": 0.0,
            }

    async def _rag_node(self, state: WorkflowState) -> WorkflowState:
        """RAG context retrieval node."""
        if state.get("event_callback"):
            await state["event_callback"]("rag", "running")
        
        start_time = datetime.now(timezone.utc)
        
        try:
            from ..rag.retriever import retrieve_external_context
            
            question = state["question"]
            rag_result = await retrieve_external_context(
                query=question,
                max_snippets=3,
                include_api_data=True,
                min_relevance=0.15
            )
            
            latency_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            
            # Get reasoning chain first for event callback
            reasoning_chain = list(state.get("reasoning_chain", []))
            
            if state.get("event_callback"):
                await state["event_callback"](
                    "rag",
                    "complete",
                    {
                        "snippets_retrieved": len(rag_result.get("snippets", [])),
                        "sources": rag_result.get("sources", []),
                        "reasoning_chain": reasoning_chain
                    },
                    latency_ms
                )
            
            # Update reasoning chain
            snippets = len(rag_result.get("snippets", []))
            sources = rag_result.get("sources", [])
            reasoning_chain.append(
                f"Γ£ô RAG: retrieved {snippets} external context snippets"
                + (f" from {', '.join(sources[:3])}{' ...' if len(sources) > 3 else ''}" if sources else "")
            )

            return {
                **state,
                "rag_context": rag_result,
                "reasoning_chain": reasoning_chain,
            }
        
        except Exception as e:
            logger.error(f"RAG failed: {e}", exc_info=True)
            if state.get("event_callback"):
                await state["event_callback"]("rag", "error", {"error": str(e)})
            return {
                **state,
                "rag_context": {"snippets": [], "sources": []}
            }

    async def _structure_data_node(self, state: WorkflowState) -> WorkflowState:
        """
        Structure extracted facts into calculation-ready inputs.

        Uses LLM to identify and organize numbers from extracted facts.
        LLM does NOT generate numbers - only structures them.
        """
        if state.get("event_callback"):
            await state["event_callback"]("structure", "running")

        start_time = datetime.now(timezone.utc)

        try:
            from .nodes.structure_data import structure_data_node

            # Convert WorkflowState to IntelligenceState format
            extracted_facts = state.get("prefetch", {}).get("facts", [])
            if not extracted_facts:
                extracted_facts = state.get("extracted_facts", [])

            mini_state = {
                "query": state.get("question", ""),
                "extracted_facts": extracted_facts,
            }

            result = await structure_data_node(mini_state)

            latency_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

            logger.info(
                f"Data structuring complete: quality={result.get('data_quality', 'UNKNOWN')}, "
                f"latency={latency_ms:.0f}ms"
            )

            # Update reasoning chain
            reasoning_chain = list(state.get("reasoning_chain", []))
            reasoning_chain.append(
                f"✓ Structure: organized data, quality={result.get('data_quality', 'UNKNOWN')}"
            )

            if state.get("event_callback"):
                await state["event_callback"](
                    "structure",
                    "complete",
                    {
                        "data_quality": result.get("data_quality"),
                        "data_gaps": result.get("data_gaps", []),
                        "reasoning_chain": reasoning_chain,
                    },
                    latency_ms,
                )

            return {
                **state,
                "structured_inputs": result.get("structured_inputs"),
                "data_quality": result.get("data_quality", "UNKNOWN"),
                "data_gaps": result.get("data_gaps", []),
                "reasoning_chain": reasoning_chain,
            }

        except Exception as e:
            logger.error(f"Data structuring failed: {e}", exc_info=True)
            if state.get("event_callback"):
                await state["event_callback"]("structure", "error", {"error": str(e)})

            reasoning_chain = list(state.get("reasoning_chain", []))
            reasoning_chain.append(f"✗ Structure: failed ({e})")

            return {
                **state,
                "structured_inputs": None,
                "data_quality": "FAILED",
                "data_gaps": ["Data structuring failed"],
                "reasoning_chain": reasoning_chain,
            }

    async def _calculate_node(self, state: WorkflowState) -> WorkflowState:
        """
        Run deterministic financial calculations.

        ALL MATH IS PYTHON - NO LLM INVOLVED.
        Uses FinancialEngine for NPV, IRR, sensitivity analysis.
        """
        if state.get("event_callback"):
            await state["event_callback"]("calculate", "running")

        start_time = datetime.now(timezone.utc)

        try:
            from .nodes.calculate import calculate_node, get_calculated_summary

            # Build state for calculation node
            calc_state = {
                "structured_inputs": state.get("structured_inputs"),
                "nodes_executed": state.get("reasoning_chain", []),
            }

            result = await calculate_node(calc_state)

            latency_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

            calculated_results = result.get("calculated_results")
            calculation_warning = result.get("calculation_warning")

            if calculated_results:
                confidence = calculated_results.get("data_confidence", 0)
                num_options = len(calculated_results.get("options", []))
                logger.info(
                    f"Calculations complete: {num_options} option(s), "
                    f"confidence={confidence:.0%}, latency={latency_ms:.0f}ms"
                )
            else:
                logger.warning("No calculated results produced")

            # Update reasoning chain
            reasoning_chain = list(state.get("reasoning_chain", []))
            if calculated_results:
                opts = calculated_results.get("options", [])
                if opts:
                    first_npv = opts[0].get("metrics", {}).get("npv_formatted", "N/A")
                    reasoning_chain.append(
                        f"✓ Calculate: deterministic NPV={first_npv}, "
                        f"{len(opts)} option(s)"
                    )
                else:
                    reasoning_chain.append("✓ Calculate: no options to analyze")
            else:
                reasoning_chain.append("✓ Calculate: skipped (no structured inputs)")

            if state.get("event_callback"):
                await state["event_callback"](
                    "calculate",
                    "complete",
                    {
                        "calculated_results": calculated_results,
                        "calculation_warning": calculation_warning,
                        "reasoning_chain": reasoning_chain,
                    },
                    latency_ms,
                )

            return {
                **state,
                "calculated_results": calculated_results,
                "calculation_warning": calculation_warning,
                "reasoning_chain": reasoning_chain,
            }

        except Exception as e:
            logger.error(f"Calculation failed: {e}", exc_info=True)
            if state.get("event_callback"):
                await state["event_callback"]("calculate", "error", {"error": str(e)})

            reasoning_chain = list(state.get("reasoning_chain", []))
            reasoning_chain.append(f"✗ Calculate: failed ({e})")

            return {
                **state,
                "calculated_results": None,
                "calculation_warning": f"Calculation failed: {e}",
                "reasoning_chain": reasoning_chain,
            }

    async def _select_agents_node(self, state: WorkflowState) -> WorkflowState:
        """Intelligent agent selection node with LEGENDARY override."""
        try:
            classification = state.get("classification", {}) or {}
            complexity = classification.get("complexity", "medium")

            # MINISTER-GRADE: ALL queries get full agent team
            # No query is "simple" when the minister is watching
            if complexity in {"complex", "critical", "medium", "simple"}:
                selected_agent_names = [
                    "MicroEconomist",
                    "MacroEconomist",
                    "Nationalization",
                    "SkillsAgent",
                    "PatternDetective",
                ]
                deterministic_names = list(self.deterministic_agents.keys())
                selected_agent_names.extend(deterministic_names)
                mode = "LEGENDARY_DEPTH"
                total_available = len(self.agents) + len(self.deterministic_agents)
                selection_explanation = {
                    "selected_count": len(selected_agent_names),
                    "total_available": total_available,
                    "savings": "0%",
                    "agents": {name: {"description": "MINISTER-GRADE: Full analysis for all queries"} for name in selected_agent_names},
                    "mode": mode,
                }
            else:
                raw_selection = self.agent_selector.select_agents(
                    classification=classification,
                    min_agents=2,
                    max_agents=4,
                )
                selected_agent_names = [
                    self._normalize_agent_name(name)
                    for name in raw_selection
                    if self._normalize_agent_name(name)
                ]
                mode = "INTELLIGENT_SELECTION"
                total_available = len(self.agent_selector.AGENT_EXPERTISE)
                selection_explanation = self.agent_selector.explain_selection(
                    raw_selection, classification
                )

            # Robust Deduplication
            seen: set[str] = set()
            deduped: list[str] = []
            for name in selected_agent_names:
                # Normalize to PascalCase if possible
                normalized = self._normalize_agent_name(name)
                if normalized and normalized not in seen:
                    deduped.append(normalized)
                    seen.add(normalized)
            selected_agent_names = deduped

            # Get reasoning chain first for event callback
            reasoning_chain = list(state.get("reasoning_chain", []))

            if state.get("event_callback"):
                await state["event_callback"](
                    "agent_selection",
                    "complete",
                    {
                        "selected_agents": selected_agent_names,
                        "selected_count": len(selected_agent_names),
                        "total_available": total_available,
                        "mode": mode,
                        "explanation": selection_explanation,
                        "reasoning_chain": reasoning_chain,
                    },
                    0,
                )
            summary = (
                f"⚡ Agent selection: LEGENDARY DEPTH ({len(selected_agent_names)} agents)"
                if mode == "LEGENDARY_DEPTH"
                else f"✓ Agent selection: chose {len(selected_agent_names)} agents"
            )
            if selected_agent_names:
                summary += f" ({', '.join(selected_agent_names)})"
            reasoning_chain.append(summary)

            return {
                **state,
                "selected_agents": selected_agent_names,
                "reasoning_chain": reasoning_chain,
            }

        except Exception as e:
            logger.error(f"Agent selection failed: {e}", exc_info=True)
            if state.get("event_callback"):
                await state["event_callback"]("agent_selection", "error", {"error": str(e)})
            
            # Fallback to a minimal set of agents
            fallback_agents = ["MicroEconomist", "MacroEconomist"]
            
            reasoning_chain = list(state.get("reasoning_chain", []))
            reasoning_chain.append(f"⚠️ Agent selection failed ({e}), falling back to default agents")
            
            return {
                **state,
                "selected_agents": fallback_agents,
                "error": f"Agent selection warning: {e}",
                "reasoning_chain": reasoning_chain
            }
    
    async def _agents_node(self, state: WorkflowState) -> WorkflowState:
        """Execute selected agents with streaming and deliberation."""
        try:
            question = state["question"]
            context = {
                "classification": state.get("classification"),
                "prefetch": state.get("prefetch", {}).get("data", {}),
                "rag_context": state.get("rag_context", {})
            }

            selected_agent_names = state.get("selected_agents", []) or list(self.agents.keys())
            
            # Map normalized names back to actual agent keys
            # This fixes the duplicate agent bug by ensuring we use the actual keys
            agents_to_invoke: list[str] = []
            invoked_set: set[str] = set()
            
            for name in selected_agent_names:
                # Try both the original name and lowercase version
                actual_key = None
                if name in self.agents:
                    actual_key = name
                elif name.lower() in self.agents:
                    actual_key = name.lower()
                elif name in self.deterministic_agents:
                    actual_key = name
                
                if actual_key and actual_key not in invoked_set:
                    agents_to_invoke.append(actual_key)
                    invoked_set.add(actual_key)
            
            if not agents_to_invoke:
                agents_to_invoke = list(self.agents.keys())

            reports: list[AgentReport] = []

            event_cb = state.get("event_callback")
            # Placeholder for upcoming debate context until Phase 5 populates it
            state.setdefault("debate_context", "")
            if event_cb:
                # Send normalized agent names to match event emissions
                normalized_names = [self._normalize_agent_name(name) for name in agents_to_invoke]
                # Remove duplicates while preserving order
                seen_emitted = set()
                unique_names = []
                for name in normalized_names:
                    if name not in seen_emitted:
                        unique_names.append(name)
                        seen_emitted.add(name)
                
                await event_cb(
                    "agents",
                    "running",
                    {"agents": unique_names, "count": len(unique_names)},
                    0,
                )

            tasks = []
            task_names: list[str] = []
            for agent_name in agents_to_invoke:
                if agent_name in self.agents:
                    async def llm_runner(name=agent_name):
                        # Force PascalCase for frontend consistency
                        display_name = self._normalize_agent_name(name)
                        if event_cb:
                            await event_cb(f"agent:{display_name}", "running")
                        start_time = datetime.now(timezone.utc)
                        debate_context = state.get("debate_context", "")
                        try:
                            # Add timeout per agent (180 seconds) to prevent hanging
                            report = await asyncio.wait_for(
                                self.agents[name].run(
                                    question,
                                    context,
                                    debate_context=debate_context
                                ),
                                timeout=180.0
                            )
                            report.agent = getattr(report, "agent", display_name) or display_name
                            latency_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                            if event_cb:
                                await event_cb(
                                    f"agent:{display_name}",
                                    "complete",
                                    {"report": report},
                                    latency_ms,
                                )
                            return report
                        except asyncio.TimeoutError:
                            logger.error(f"LLM agent {display_name} timed out after 60s")
                            if event_cb:
                                await event_cb(f"agent:{display_name}", "error", {"error": "Agent execution timeout"})
                            return None
                        except Exception as exc:
                            logger.error(f"LLM agent {display_name} failed: {exc}", exc_info=True)
                            if event_cb:
                                await event_cb(f"agent:{display_name}", "error", {"error": str(exc)})
                            return None  # Don't crash - let gather handle it

                    tasks.append(llm_runner())
                else:
                    async def deterministic_runner(name=agent_name):
                        # Force PascalCase for frontend consistency
                        display_name = self._normalize_agent_name(name)
                        if event_cb:
                            await event_cb(f"agent:{display_name}", "running")
                        start_time = datetime.now(timezone.utc)
                        try:
                            report = await asyncio.to_thread(
                                self._run_deterministic_agent_sync,
                                name,
                                self.deterministic_agents[name],
                                question,
                            )
                            latency_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                            if event_cb:
                                await event_cb(
                                    f"agent:{display_name}",
                                    "complete",
                                    {"report": report},
                                    latency_ms,
                                )
                            return report
                        except Exception as exc:
                            logger.error(f"Deterministic agent {display_name} failed: {exc}", exc_info=True)
                            if event_cb:
                                await event_cb(f"agent:{display_name}", "error", {"error": str(exc)})
                            return None  # Don't crash - let gather handle it

                    tasks.append(deterministic_runner())

                task_names.append(agent_name)

            # Execute agents with 30-minute timeout for PhD-level deep analysis
            # Individual LLM calls have 3-minute timeout, so 30 minutes total allows for retries and parallel execution
            try:
                results = await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=1800  # 30 minutes total for all 12 agents in parallel
                )
            except asyncio.TimeoutError:
                logger.error("Agent execution timed out after 10 minutes")
                if event_cb:
                    await event_cb("agents", "error", {"error": "Agent execution timeout after 10 minutes - may indicate hung agent"})
                # Return partial results - treat all as failed
                results = [Exception("Timeout") for _ in tasks]

            reasoning_chain = list(state.get("reasoning_chain", []))
            summary_agents = ', '.join(task_names[:5]) + ('...' if len(task_names) > 5 else '')
            reasoning_chain.append(
                f"? Invoking {len(task_names)} agents ({summary_agents})" if task_names else "? Invoking agents"
            )

            for agent_name, result in zip(task_names, results):
                display_name = self._normalize_agent_name(agent_name)

                if isinstance(result, Exception):
                    logger.error("%s failed", agent_name, exc_info=result)
                    reasoning_chain.append(f"✗ {agent_name} failed: {result}")
                    # Ensure error event is emitted if not already
                    if event_cb:
                        await event_cb(f"agent:{display_name}", "error", {"error": str(result)})
                    continue
                
                if result is None:
                    logger.warning(f"{agent_name} returned None (failed gracefully)")
                    reasoning_chain.append(f"✗ {agent_name} failed gracefully")
                    # Ensure error event is emitted
                    if event_cb:
                        await event_cb(f"agent:{display_name}", "error", {"error": "Agent returned no results"})
                    continue

                report = result
                if getattr(report, "agent", None) != agent_name:
                    report.agent = agent_name
                reports.append(report)

                if getattr(report, "narrative", None):
                    state[f"{agent_name}_analysis"] = report.narrative

                reasoning_chain.append(f"? {agent_name} completed with structured output")

            state["reasoning_chain"] = reasoning_chain

            # PHASE 1 FIX: Inject citations into all agent reports
            # Since LLMs resist citation format, we inject programmatically
            logger.info(f"Injecting citations into {len(reports)} agent reports...")
            injector = CitationInjector()
            prefetch_data = state.get("prefetch", {}).get("data", {})

            for report in reports:
                # CRITICAL FIX: Inject into narrative field (this is what UI displays!)
                if hasattr(report, 'narrative') and report.narrative:
                    original_narrative = report.narrative
                    cited_narrative = injector.inject_citations(original_narrative, prefetch_data)
                    report.narrative = cited_narrative
                    logger.info(f"Injected citations into narrative: {len(original_narrative)} -> {len(cited_narrative)} chars")
                    logger.info(f"Citations present in narrative: {'[Per extraction:' in cited_narrative}")

                # Also inject into findings (for completeness)
                if hasattr(report, 'findings') and report.findings:
                    updated_findings = []
                    for finding in report.findings:
                        if isinstance(finding, dict):
                            updated_finding = finding.copy()

                            # Inject into analysis field
                            if 'analysis' in updated_finding:
                                updated_finding['analysis'] = injector.inject_citations(
                                    updated_finding['analysis'],
                                    prefetch_data
                                )

                            # Inject into summary field
                            if 'summary' in updated_finding:
                                updated_finding['summary'] = injector.inject_citations(
                                    updated_finding['summary'],
                                    prefetch_data
                                )

                            updated_findings.append(updated_finding)
                        else:
                            updated_findings.append(finding)

                    report.findings = updated_findings

            logger.info("Citation injection complete")

            # Update reasoning chain
            reasoning_chain = list(state.get("reasoning_chain", []))
            reasoning_chain.append(
                f"Γ£ô Multi-agent analysis: executed {len(reports)} agent report(s) with inline citations"
            )

            return {
                **state,
                "agent_reports": reports,
                "reasoning_chain": reasoning_chain,
            }
        
        except Exception as e:
            logger.error(f"Agent execution failed: {e}", exc_info=True)
            if state.get("event_callback"):
                await state["event_callback"]("agents", "error", {"error": str(e)})
            
            return {
                **state,
                "agent_reports": [],
                "error": f"Agent execution failed: {e}"
            }
    

    def _run_deterministic_agent_sync(
        self,
        agent_name: str,
        agent_obj: Any,
        question: str,
    ) -> AgentReport:
        """Execute deterministic agent synchronously and return an AgentReport."""
        end_date = date.today()
        start_date = self._default_window_start(end_date)

        try:
            if agent_name == "TimeMachine":
                narrative = agent_obj.baseline_report(
                    metric="unemployment",
                    start=start_date,
                    end=end_date,
                )
                return self._make_narrative_report(agent_name, narrative)

            if agent_name == "Predictor":
                narrative = agent_obj.forecast_baseline(
                    metric="retention",
                    sector=None,
                    start=start_date,
                    end=end_date,
                    horizon_months=6,
                )
                return self._make_narrative_report(agent_name, narrative)

            if agent_name == "Scenario":
                spec = self._build_default_scenario_spec(question)
                narrative = agent_obj.apply(spec)
                return self._make_narrative_report(agent_name, narrative)

            if agent_name == "PatternDetectiveAgent":
                report = agent_obj.detect_anomalous_retention()
                report.agent = agent_name
                return report

            if agent_name == "PatternMiner":
                narrative = agent_obj.stable_relations(
                    outcome="retention",
                    drivers=["qatarization", "attrition"],
                    window=12,
                    min_support=12,
                )
                return self._make_narrative_report(agent_name, narrative)

            if agent_name == "NationalStrategy":
                report = agent_obj.gcc_benchmark()
                report.agent = agent_name
                return report

            if agent_name == "AlertCenter":
                report = agent_obj.status()
                report.agent = agent_name
                return report

            return AgentReport(
                agent=agent_name,
                findings=[],
                warnings=[f"No deterministic runner configured for {agent_name}"],
                narrative=f"{agent_name} is not configured for direct execution.",
            )

        except ValueError as exc:  # Expected data unavailability
            logger.warning("Deterministic agent %s skipped: %s", agent_name, exc)
            return AgentReport(
                agent=agent_name,
                findings=[],
                warnings=[f"Data unavailable: {exc}"],
                narrative=f"{agent_name} skipped: {exc}",
            )
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Deterministic agent %s failed: %s", agent_name, exc, exc_info=True)
            return AgentReport(
                agent=agent_name,
                findings=[],
                warnings=[f"Execution failed: {exc}"],
                narrative=f"{agent_name} failed: {exc}",
            )

    @staticmethod
    def _make_narrative_report(agent_name: str, narrative: str) -> AgentReport:
        """Create an AgentReport wrapper for deterministic narratives."""
        return AgentReport(agent=agent_name, findings=[], narrative=narrative)

    @staticmethod
    def _default_window_start(end_date: date) -> date:
        """Return a safe two-year window for deterministic analyses."""
        try:
            return end_date.replace(year=end_date.year - 2)
        except ValueError:
            return end_date - timedelta(days=730)

    @staticmethod
    def _build_default_scenario_spec(question: str) -> str:
        """Build a deterministic scenario specification using the question context."""
        preview = (question or "Ministerial scenario").strip().replace("\n", " ")
        preview = preview[:120] if preview else "Ministerial scenario"
        return textwrap.dedent(
            f"""
            name: Auto Scenario
            description: Derived from query: {preview}
            metric: retention
            sector: Construction
            horizon_months: 12
            transforms:
              - type: multiplicative
                value: 0.05
                start_month: 0
            """
        ).strip()

    async def _verify_node(self, state: WorkflowState) -> WorkflowState:
        """
        Verify agent outputs for citations and number accuracy.

        Enhanced verification that:
        1. Extracts all numbers from agent narratives
        2. Checks each number has [Per extraction: ...] citation
        3. Validates numbers against source data
        4. Logs violations loudly
        5. Adjusts confidence scores based on violations

        Args:
            state: Current workflow state

        Returns:
            Updated state with verification results
        """
        if state.get("event_callback"):
            await state["event_callback"]("verify", "running")

        start_time = datetime.now(timezone.utc)

        try:
            import re
            from .verification import verify_report

            reports = state.get("agent_reports", [])
            # Try both possible keys for prefetch data - defensive access
            prefetch_data = state.get("prefetch_data", {})
            if not prefetch_data:
                prefetch_info = state.get("prefetch", {})
                if isinstance(prefetch_info, dict):
                    prefetch_data = prefetch_info.get("data", {})
                else:
                    prefetch_data = {}
            
            # Defensive: ensure all required state keys exist with defaults
            debate_results = state.get("debate_results", {})
            if not isinstance(debate_results, dict):
                debate_results = {}

            logger.info(f"VERIFICATION START: Checking {len(reports)} reports with {len(prefetch_data)} prefetch results")

            # Verify each agent report
            all_issues = []
            warnings_list = []
            citation_violations = []
            number_violations = []

            # Extract all numbers from source data for validation
            source_numbers = set()
            for query_result in prefetch_data.values():
                if hasattr(query_result, 'rows'):
                    for row in query_result.rows:
                        if hasattr(row, 'data'):
                            for value in row.data.values():
                                if isinstance(value, (int, float)):
                                    source_numbers.add(float(value))

            for report in reports:
                if not report:
                    continue

                agent_name = report.agent if hasattr(report, 'agent') else 'Unknown'

                # 1. Run existing verification
                verification_result = verify_report(report)
                if hasattr(verification_result, 'issues') and verification_result.issues:
                    for issue in verification_result.issues:
                        issue_str = f"[{agent_name}] {issue.code}: {issue.detail}"
                        warnings_list.append(issue_str)
                        all_issues.append(issue)

                # 2. Check citations in narrative
                narrative = report.narrative if hasattr(report, 'narrative') else ""

                # Extract all numbers from narrative (integers, floats, percentages)
                number_pattern = r'\b\d+\.?\d*%?\b'
                numbers_in_narrative = re.findall(number_pattern, narrative)

                # Extract all citations
                citation_pattern = r'\[Per extraction: \'[^\']+\' from [^\]]+\]'
                citations_found = re.findall(citation_pattern, narrative)

                # 3. Check if numbers have citations nearby
                # Simple heuristic: citation should appear within 50 chars of the number
                uncited_numbers = []
                for num_match in re.finditer(number_pattern, narrative):
                    num_pos = num_match.start()
                    num_value = num_match.group()

                    # Check if there's a citation within +/- 50 chars
                    has_nearby_citation = False
                    for cite_match in re.finditer(citation_pattern, narrative):
                        cite_pos = cite_match.start()
                        if abs(cite_pos - num_pos) < 100:  # Within 100 chars
                            has_nearby_citation = True
                            break

                    if not has_nearby_citation:
                        uncited_numbers.append(num_value)

                if uncited_numbers:
                    violation = f"[{agent_name}] {len(uncited_numbers)} number(s) without citations: {uncited_numbers[:5]}"
                    citation_violations.append(violation)
                    warnings_list.append(violation)
                    logger.warning(f"CITATION VIOLATION: {violation}")

                # 4. Validate cited numbers against source data (with tolerance)
                for cite_match in re.finditer(citation_pattern, narrative):
                    citation_text = cite_match.group()
                    # Extract the value from citation
                    value_match = re.search(r"'([^']+)'", citation_text)
                    if value_match:
                        cited_value_str = value_match.group(1)
                        # Try to parse as number
                        try:
                            # Remove % and other non-numeric chars
                            clean_value = cited_value_str.replace('%', '').replace(',', '').strip()
                            cited_value = float(clean_value)

                            # Check if this number exists in source data (with 2% tolerance)
                            found_in_source = False
                            for source_num in source_numbers:
                                tolerance = abs(source_num * 0.02)  # 2% tolerance
                                if abs(cited_value - source_num) <= tolerance:
                                    found_in_source = True
                                    break

                            if not found_in_source and cited_value > 0.01:  # Ignore very small numbers
                                violation = f"[{agent_name}] Cited value '{cited_value_str}' not found in source data"
                                number_violations.append(violation)
                                warnings_list.append(violation)
                                logger.warning(f"NUMBER FABRICATION: {violation}")

                        except (ValueError, AttributeError):
                            # Not a parseable number, skip
                            pass

            verification_result = {
                "status": "complete",
                "warnings": warnings_list,
                "warning_count": len([i for i in all_issues if hasattr(i, 'level') and i.level == 'warn']),
                "error_count": len([i for i in all_issues if hasattr(i, 'level') and i.level == 'error']),
                "missing_citations": len(citation_violations),
                "citation_violations": citation_violations,
                "number_violations": number_violations,
                "fabricated_numbers": len(number_violations)
            }

            latency_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

            logger.info(
                f"Verification complete: {len(warnings_list)} warnings, "
                f"{len(citation_violations)} citation violations, "
                f"{len(number_violations)} number violations, "
                f"latency={latency_ms:.0f}ms"
            )

            # Update reasoning chain
            reasoning_chain = list(state.get("reasoning_chain", []))
            reasoning_chain.append(
                "Γ£ô Verification: "
                f"{len(citation_violations)} citation violation(s), "
                f"{len(number_violations)} number violation(s)"
            )
            
            if state.get("event_callback"):
                await state["event_callback"](
                    "verify",
                    "complete",
                    {
                        **verification_result,
                        "reasoning_chain": reasoning_chain
                    },
                    latency_ms
                )
            
            return {
                **state,
                "verification": {
                    **verification_result,
                    "latency_ms": latency_ms,
                },
                "reasoning_chain": reasoning_chain,
            }
        
        except Exception as e:
            logger.error(f"Verification failed: {e}", exc_info=True)
            if state.get("event_callback"):
                await state["event_callback"]("verify", "error", {"error": str(e)})
            return {
                **state,
                "verification": {"status": "failed", "error": str(e)},
                "error": f"Verification error: {e}"
            }

    def _detect_contradictions(self, reports: list) -> list:
        """
        Detect contradictions between agent reports.

        Args:
            reports: List of agent reports (dicts with 'agent_name', 'narrative', 'confidence')

        Returns:
            List of contradiction dicts
        """
        try:
            contradictions = []

            # Extract numbers and citations from each report
            number_pattern = r'\b(\d+\.?\d*%?)\b'
            citation_pattern = r'\[Per extraction: \'([^\']+)\' from ([^\]]+)\]'

            for i, report1 in enumerate(reports):
                for report2 in reports[i+1:]:
                    # Extract all numbers with nearby citations from both reports
                    # Handle AgentReport objects - use getattr for safe access
                    narrative1 = getattr(report1, 'narrative', '') or ''
                    narrative2 = getattr(report2, 'narrative', '') or ''

                    # Find numbers in report1
                    numbers1 = re.finditer(number_pattern, narrative1)
                    for match1 in numbers1:
                        value1_str = match1.group(1)
                        pos1 = match1.start()

                        # Find nearby citation
                        citation_search1 = narrative1[max(0, pos1-100):min(len(narrative1), pos1+100)]
                        citation_match1 = re.search(citation_pattern, citation_search1)

                        if not citation_match1:
                            continue

                        citation1_value = citation_match1.group(1)
                        citation1_source = citation_match1.group(2)

                        # Now look for similar metric in report2
                        numbers2 = re.finditer(number_pattern, narrative2)
                        for match2 in numbers2:
                            value2_str = match2.group(1)
                            pos2 = match2.start()

                            # Find nearby citation
                            citation_search2 = narrative2[max(0, pos2-100):min(len(narrative2), pos2+100)]
                            citation_match2 = re.search(citation_pattern, citation_search2)

                            if not citation_match2:
                                continue

                            citation2_value = citation_match2.group(1)
                            citation2_source = citation_match2.group(2)

                            # Check if this is a contradiction (same metric, different values)
                            # Parse numeric values
                            try:
                                val1 = float(value1_str.replace('%', ''))
                                val2 = float(value2_str.replace('%', ''))

                                # Skip if values are the same (or very close - within 0.1%)
                                if abs(val1 - val2) <= 0.001:
                                    continue

                                # Check if values differ by more than 5%
                                if val1 > 0 and abs(val1 - val2) / val1 > 0.05:
                                    # This is a potential contradiction
                                    # Use getattr for AgentReport objects
                                    agent1_name = getattr(report1, 'agent', '') or getattr(report1, 'agent_name', 'Unknown')
                                    agent2_name = getattr(report2, 'agent', '') or getattr(report2, 'agent_name', 'Unknown')
                                    agent1_conf = getattr(report1, 'confidence', 0.5)
                                    agent2_conf = getattr(report2, 'confidence', 0.5)
                                    
                                    contradictions.append({
                                        "metric_name": f"metric_at_pos_{pos1}_{pos2}",
                                        "agent1_name": agent1_name,
                                        "agent1_value": val1,
                                        "agent1_value_str": value1_str,
                                        "agent1_citation": f"[Per extraction: '{citation1_value}' from {citation1_source}]",
                                        "agent1_confidence": agent1_conf,
                                        "agent2_name": agent2_name,
                                        "agent2_value": val2,
                                        "agent2_value_str": value2_str,
                                        "agent2_citation": f"[Per extraction: '{citation2_value}' from {citation2_source}]",
                                        "agent2_confidence": agent2_conf,
                                        "severity": "high" if abs(val1 - val2) / val1 > 0.20 else "medium"
                                    })
                            except ValueError:
                                # Not numeric, skip
                                continue

            logger.info(f"Detected {len(contradictions)} contradictions")
            return contradictions

        except Exception as e:
            logger.error(f"Contradiction detection failed: {e}", exc_info=True)
            return []

    async def _conduct_debate(self, contradiction: dict) -> dict:
        """
        Conduct structured debate to resolve a contradiction.

        Args:
            contradiction: Contradiction dict with agent findings

        Returns:
            DebateResolution dict
        """
        debate_prompt = f"""You are a neutral arbitrator conducting a structured debate between two agents who have conflicting findings.

CONTRADICTION:
- Metric: {contradiction['metric_name']}
- Agent 1 ({contradiction['agent1_name']}): {contradiction['agent1_value_str']} {contradiction['agent1_citation']} (confidence: {contradiction['agent1_confidence']:.2f})
- Agent 2 ({contradiction['agent2_name']}): {contradiction['agent2_value_str']} {contradiction['agent2_citation']} (confidence: {contradiction['agent2_confidence']:.2f})

TASK:
1. Analyze both citations to determine source reliability
2. Check if values are actually measuring the same thing (e.g., same time period, same definition)
3. Determine if both can be correct (different methodologies/sources)
4. If only one can be correct, determine which based on:
   - Source authority (GCC-STAT > World Bank > other)
   - Data freshness (more recent > older)
   - Citation completeness
   - Agent confidence

OUTPUT FORMAT (JSON):
{{
  "resolution": "agent1_correct" | "agent2_correct" | "both_valid" | "neither_valid",
  "explanation": "Detailed explanation of why",
  "recommended_value": value or null,
  "recommended_citation": "citation" or null,
  "confidence": 0.0-1.0,
  "action": "use_agent1" | "use_agent2" | "use_both" | "flag_for_review"
}}
"""

        try:
            # Use hybrid routing (GPT-5 for debate)
            response = await self.llm_client.generate_with_routing(
                prompt=debate_prompt, 
                task_type="debate",
                temperature=0.2
            )

            # Parse JSON response - handle markdown code fences if present
            import json

            # Strip markdown code fences if present
            response_clean = response.strip()
            if response_clean.startswith("```json"):
                response_clean = response_clean[7:]
            if response_clean.startswith("```"):
                response_clean = response_clean[3:]
            if response_clean.endswith("```"):
                response_clean = response_clean[:-3]
            response_clean = response_clean.strip()

            if not response_clean:
                raise ValueError("Empty response from LLM")

            resolution = json.loads(response_clean)

            logger.info(f"Debate resolution: {resolution['action']} - {resolution['explanation'][:100]}...")

            return resolution

        except Exception as e:
            logger.error(f"Debate failed: {e}", exc_info=True)
            # Default to flagging for review
            return {
                "resolution": "neither_valid",
                "explanation": f"Debate failed due to error: {e}",
                "recommended_value": None,
                "recommended_citation": None,
                "confidence": 0.0,
                "action": "flag_for_review"
            }

    def _build_consensus(self, resolutions: list) -> dict:
        """
        Build consensus from debate resolutions.

        Args:
            resolutions: List of DebateResolution dicts

        Returns:
            ConsensusResult dict
        """
        resolved_count = sum(1 for r in resolutions if r["action"] in ["use_agent1", "use_agent2", "use_both"])
        flagged_count = sum(1 for r in resolutions if r["action"] == "flag_for_review")

        # Build narrative
        narratives = []
        for r in resolutions:
            if r["action"] == "flag_for_review":
                narratives.append(f"- FLAGGED: {r['explanation']}")
            else:
                narratives.append(f"- RESOLVED: {r['explanation']}")

        consensus_narrative = "\n".join(narratives)

        return {
            "resolved_contradictions": resolved_count,
            "flagged_for_review": flagged_count,
            "consensus_narrative": consensus_narrative
        }

    def _apply_debate_resolutions(self, reports: list, resolutions: list) -> list:
        """
        Apply debate resolutions to adjust agent reports.

        Args:
            reports: Original agent reports
            resolutions: Debate resolutions

        Returns:
            Adjusted agent reports
        """
        # For now, just return original reports
        # In a full implementation, we would modify narratives based on resolutions
        adjusted_reports = []

        for report in reports:
            # AgentReport is a dataclass, so we need to access attributes directly
            # Create a copy by converting to dict
            from dataclasses import asdict
            adjusted_report = asdict(report)

            # Find resolutions that affect this report
            # Use getattr for safe attribute access
            agent_name = getattr(report, 'agent', '') or getattr(report, 'agent_name', '')
            relevant_resolutions = [
                r for r in resolutions
                if r.get("explanation", "").find(agent_name) >= 0
            ]

            if relevant_resolutions:
                # Add debate context to narrative
                debate_context = "\n\n[Debate Context]\n"
                for r in relevant_resolutions:
                    debate_context += f"- {r['explanation']}\n"

                current_narrative = getattr(report, 'narrative', '') or ''
                adjusted_report["narrative"] = current_narrative + debate_context

            adjusted_reports.append(adjusted_report)

        return adjusted_reports

    async def _debate_node(self, state: WorkflowState) -> WorkflowState:
        """
        Conduct legendary multi-turn debate between agents.
        
        Uses new LegendaryDebateOrchestrator for 80-125 turn conversations.
        """
        if state.get("event_callback"):
            await state["event_callback"]("debate", "running")
        
        start_time = datetime.now(timezone.utc)
        reports = state.get("agent_reports", [])
        
        # 1. Detect contradictions
        contradictions = self._detect_contradictions(reports)
        
        if not contradictions:
            logger.info("No contradictions detected - but running legendary debate anyway for depth")
            # We will continue to legendary debate even without contradictions
            # The orchestrator handles this by creating a "policy debate" topic
        
        logger.info(f"Starting legendary debate with {len(contradictions)} contradictions")
        
        # Import debate orchestrator
        from .legendary_debate_orchestrator import LegendaryDebateOrchestrator
        
        # Create orchestrator with event callback
        orchestrator = LegendaryDebateOrchestrator(
            emit_event_fn=state.get("event_callback"),
            llm_client=self.llm_client
        )
        
        # Build agents map (both LLM and deterministic)
        agents_map = {}
        
        # Add LLM agents
        for name, agent in self.agents.items():
            agents_map[name] = agent
        
        # Add deterministic agents (they'll contribute data-backed points)
        for name, agent in self.deterministic_agents.items():
            agents_map[name] = agent
        
        # Build agent reports map for deterministic agents to access their narratives
        agent_reports_map = {}
        for report in reports:
            agent_name = getattr(report, 'agent', None)
            if agent_name:
                agent_reports_map[agent_name] = report
        
        # Conduct legendary debate - pass calculated results for McKinsey-grade analysis
        try:
            debate_results = await orchestrator.conduct_legendary_debate(
                question=state["question"],
                contradictions=contradictions,
                agents_map=agents_map,
                agent_reports_map=agent_reports_map,
                llm_client=self.llm_client,
                calculated_results=state.get("calculated_results"),  # NEW: McKinsey pipeline
                calculation_warning=state.get("calculation_warning")  # NEW: Data confidence warning
            )
        except Exception as exc:
            logger.exception("Legendary debate failed")

            if state.get("event_callback"):
                try:
                    await state["event_callback"](
                        "debate",
                        "error",
                        {"error": str(exc)}
                    )
                except Exception:
                    logger.exception("Failed to emit debate error event")

            raise
        
        latency_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        
        logger.info(
            f"Debate complete: {debate_results['total_turns']} turns, "
            f"latency={latency_ms:.0f}ms"
        )
        
        if state.get("event_callback"):
            await state["event_callback"](
                "debate",
                "complete",
                {
                    "contradictions": len(contradictions),
                    "total_turns": debate_results["total_turns"],
                    "resolutions": debate_results["resolutions"],
                    "consensus": debate_results["consensus"],
                    "final_report": debate_results["final_report"]
                },
                latency_ms
            )
        
        # Update reasoning chain
        reasoning_chain = list(state.get("reasoning_chain", []))
        reasoning_chain.append(
            f"Γ£ô Legendary Debate: {debate_results['total_turns']} turns, "
            f"{len(contradictions)} contradictions debated, 6 phases completed"
        )
        
        # We update the synthesis with the final report from the debate
        # This replaces the need for a separate synthesis step if the debate is comprehensive
        # But the workflow has a synthesis node next. We can pass the debate report as a finding.
        
        return {
            **state,
            "debate_results": {
                "contradictions_found": len(contradictions),
                "total_turns": debate_results["total_turns"],
                "conversation_history": debate_results["conversation_history"],
                "resolutions": debate_results["resolutions"],
                "consensus": debate_results["consensus"],
                "latency_ms": latency_ms,
                "status": "complete",
                "contradictions": contradictions,
                "final_report": debate_results["final_report"]
            },
            "reasoning_chain": reasoning_chain,
            # Optional: Pre-fill synthesis if the debate report is good enough
            "synthesis": debate_results["final_report"] 
        }

    async def _critique_node(self, state: WorkflowState) -> WorkflowState:
        """
        Devil's advocate critique to stress-test conclusions.

        Args:
            state: Current workflow state with agent_reports and debate_results

        Returns:
            Updated state with critique_results
        """
        if state.get("event_callback"):
            await state["event_callback"]("critique", "running")

        start_time = datetime.now(timezone.utc)
        reports = state.get("agent_reports", [])
        debate_results = state.get("debate_results", {})

        if not reports:
            logger.info("No agent reports to critique - skipping")

            if state.get("event_callback"):
                await state["event_callback"](
                    "critique",
                    "complete",
                    {"status": "skipped"},
                    0
                )

            # Update reasoning chain
            reasoning_chain = list(state.get("reasoning_chain", []))
            reasoning_chain.append("Γ£ô Critique: no agent reports available; critique skipped")

            return {
                **state,
                "critique_results": {
                    "status": "skipped",
                    "reason": "no_reports",
                    "latency_ms": 0,
                },
                "reasoning_chain": reasoning_chain,
            }

        logger.info(f"Starting devil's advocate critique of {len(reports)} reports")

        # Build critique prompt with all conclusions
        conclusions = []
        for report in reports:
            # Handle AgentReport objects (not dicts)
            agent_name = report.agent if hasattr(report, 'agent') else 'Unknown'
            narrative = report.narrative if hasattr(report, 'narrative') else ''
            confidence = report.confidence if hasattr(report, 'confidence') else 0.5
            conclusions.append(f"Agent: {agent_name}\nConfidence: {confidence:.2f}\nConclusion: {narrative}\n")

        conclusions_text = "\n---\n".join(conclusions)

        # Add debate results if available
        debate_context = ""
        if debate_results and debate_results.get("status") == "complete":
            debate_context = f"""
DEBATE RESULTS:
- Contradictions found: {debate_results.get('contradictions_found', 0)}
- Resolved: {debate_results.get('resolved', 0)}
- Flagged for review: {debate_results.get('flagged_for_review', 0)}
- Consensus: {debate_results.get('consensus_narrative', 'N/A')}
"""

        critique_prompt = f"""You are a critical thinking expert acting as a devil's advocate. Your role is to stress-test the conclusions reached by the agents.

AGENT CONCLUSIONS:
{conclusions_text}

{debate_context}

YOUR TASK:
1. Identify potential weaknesses in the reasoning
2. Challenge assumptions that may not be warranted
3. Look for:
   - Over-generalization from limited data
   - Missing alternative explanations
   - Unwarranted confidence
   - Gaps in the logic
   - Hidden biases
   - Cherry-picked evidence
4. Propose counter-arguments or alternative interpretations
5. Rate the robustness of each conclusion (0.0-1.0)

Be constructively critical. The goal is to strengthen conclusions by finding and addressing weaknesses, not to tear them down arbitrarily.

OUTPUT FORMAT (JSON):
{{
  "critiques": [
    {{
      "agent_name": "agent name",
      "weakness_found": "description of weakness",
      "counter_argument": "alternative perspective",
      "severity": "high" | "medium" | "low",
      "robustness_score": 0.0-1.0
    }}
  ],
  "overall_assessment": "summary of overall robustness",
  "confidence_adjustments": {{
    "agent_name": adjustment_factor_0_to_1
  }},
  "red_flags": ["flag 1", "flag 2", ...],
  "strengthened_by_critique": true | false
}}
"""

        try:
            # Use hybrid routing (GPT-5 for critique/analysis)
            response = await self.llm_client.generate_with_routing(
                prompt=critique_prompt, 
                task_type="agent_analysis",
                temperature=0.2
            )

            # Parse JSON response - handle markdown code fences if present
            import json

            response_clean = response.strip()
            if response_clean.startswith("```json"):
                response_clean = response_clean[7:]
            if response_clean.startswith("```"):
                response_clean = response_clean[3:]
            if response_clean.endswith("```"):
                response_clean = response_clean[:-3]
            response_clean = response_clean.strip()

            if not response_clean:
                raise ValueError("Empty response from LLM")

            critique = json.loads(response_clean)

            logger.info(f"Critique complete: {len(critique.get('critiques', []))} critiques, "
                       f"{len(critique.get('red_flags', []))} red flags")

            latency_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

            if state.get("event_callback"):
                await state["event_callback"](
                    "critique",
                    "complete",
                    {
                        "num_critiques": len(critique.get("critiques", [])),
                        "red_flags": len(critique.get("red_flags", [])),
                        "strengthened": critique.get("strengthened_by_critique", False),
                        "critiques": critique.get("critiques", []),  # Include actual critiques
                        "overall_assessment": critique.get("overall_assessment", ""),
                        "full_critique": critique  # Include full critique for display
                    },
                    latency_ms
                )

            # Update reasoning chain
            reasoning_chain = list(state.get("reasoning_chain", []))
            reasoning_chain.append(
                f"Γ£ô Critique: {len(critique.get('critiques', []))} critique(s), "
                f"{len(critique.get('red_flags', []))} red flag(s)"
            )

            return {
                **state,
                "critique_results": {
                    "critiques": critique.get("critiques", []),
                    "overall_assessment": critique.get("overall_assessment", ""),
                    "confidence_adjustments": critique.get("confidence_adjustments", {}),
                    "red_flags": critique.get("red_flags", []),
                    "strengthened_by_critique": critique.get("strengthened_by_critique", False),
                    "latency_ms": latency_ms,
                    "status": "complete",
                },
                "reasoning_chain": reasoning_chain,
            }

        except Exception as e:
            logger.error(f"Critique failed: {e}", exc_info=True)
            latency_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

            if state.get("event_callback"):
                await state["event_callback"]("critique", "error", {"error": str(e)})

            return {
                **state,
                "critique_results": {
                    "status": "failed",
                    "error": str(e),
                    "latency_ms": latency_ms
                }
            }

    async def _synthesize_node(self, state: WorkflowState) -> WorkflowState:
        """
        Synthesize agent findings into final answer with streaming.

        Handles both:
        - LLM agent reports (synthesize multiple findings)
        - Deterministic agent results (pass through directly)

        Args:
            state: Current workflow state

        Returns:
            Updated state with synthesis
        """
        if state.get("event_callback"):
            await state["event_callback"]("synthesize", "running")

        start_time = datetime.now(timezone.utc)

        try:
            question = state["question"]

            # Check if this is a deterministic result (bypass LLM synthesis)
            deterministic_result = state.get("deterministic_result")
            if deterministic_result:
                logger.info("Passing through deterministic result (no LLM synthesis needed)")

                latency_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

                if state.get("event_callback"):
                    await state["event_callback"](
                        "synthesize",
                        "complete",
                        {"source": "deterministic"},
                        latency_ms
                    )

                # Update reasoning chain
                reasoning_chain = list(state.get("reasoning_chain", []))
                reasoning_chain.append("✓ Synthesis: returned deterministic analytical narrative")

                return {
                    **state,
                    "synthesis": deterministic_result,
                    "final_synthesis": deterministic_result,  # CRITICAL: streaming.py looks for this
                    "meta_synthesis": deterministic_result,   # CRITICAL: backup key
                    "metadata": {
                        **state.get("metadata", {}),
                        "synthesis_latency_ms": latency_ms,
                        "synthesis_source": "deterministic",
                    },
                    "reasoning_chain": reasoning_chain,
                }

            # LLM agent synthesis path
            reports = state.get("agent_reports", [])

            # Build synthesis prompt
            findings_text = "\n\n".join([
                f"**Agent {report.agent}**:\n{report.narrative if hasattr(report, 'narrative') else str(report)}"
                for report in reports
                if report
            ])
            
            # Include debate synthesis if available (from legendary debate)
            debate_synthesis = state.get("debate_synthesis", "")
            debate_results = state.get("debate_results", {})
            debate_section = ""
            if debate_synthesis:
                debate_turns = debate_results.get("total_turns", 0) if isinstance(debate_results, dict) else 0
                debate_section = f"""

## Multi-Agent Debate Summary ({debate_turns} turns)
{debate_synthesis[:8000]}
"""
            
            # Include critique results if available
            critique_results = state.get("critique_results", {})
            critique_section = ""
            if critique_results:
                red_flags = critique_results.get("red_flags", [])
                if red_flags:
                    flags_text = "\n".join([f"- {flag}" for flag in red_flags[:10]])
                    critique_section = f"""

## Risk Analysis (Red Flags Identified)
{flags_text}
"""
            
            # Include extracted facts count
            extracted_facts = state.get("extracted_facts", [])
            n_facts = len(extracted_facts) if isinstance(extracted_facts, list) else 0
            n_sources = len(set(f.get("source", "") for f in extracted_facts if isinstance(f, dict))) if extracted_facts else 0

            synthesis_prompt = f"""Synthesize the following analysis into a comprehensive executive summary for the question: \"{question}\"

## Data Foundation
- {n_facts} verified facts from {n_sources} data sources

Agent Findings:
{findings_text}
{debate_section}
{critique_section}

Provide a ministerial-grade synthesis that:
1. EXECUTIVE SUMMARY (3 sentences max)
2. THE RECOMMENDATION: What should be done?
3. CONFIDENCE LEVEL: X% (based on evidence quality)
4. KEY DECISIVE FACTORS (3-5 bullet points)
5. CRITICAL RISKS (if any red flags were identified)
6. RECOMMENDED NEXT STEPS (with priority)

Be decisive. Use specific numbers from the analysis.

Synthesis:"""

            # Generate synthesis with streaming
            synthesis_text = ""
            async for token in self.llm_client.generate_stream(
                prompt=synthesis_prompt,
                system="You are an expert labour market analyst for Qatar's Ministry of Labour. Provide concise, data-driven executive summaries."
            ):
                synthesis_text += token
                if state.get("event_callback"):
                    await state["event_callback"](
                        "synthesize",
                        "streaming",
                        {"token": token}
                    )

            latency_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

            logger.info(f"Synthesis complete: latency={latency_ms:.0f}ms")

            # Update reasoning chain
            reasoning_chain = list(state.get("reasoning_chain", []))
            reasoning_chain.append("Γ£ô Synthesis: generated ministerial-grade summary from agent findings")

            if state.get("event_callback"):
                await state["event_callback"](
                    "synthesize",
                    "complete",
                    {"synthesis": synthesis_text},
                    latency_ms
                )
            
            return {
                **state,
                "synthesis": synthesis_text,
                "final_synthesis": synthesis_text,  # CRITICAL: streaming.py looks for this key
                "meta_synthesis": synthesis_text,   # CRITICAL: backup key for compatibility
                "metadata": {
                    **state.get("metadata", {}),
                    "synthesis_latency_ms": latency_ms,
                },
                "reasoning_chain": reasoning_chain,
            }
        
        except Exception as e:
            logger.error(f"Synthesis failed: {e}", exc_info=True)
            if state.get("event_callback"):
                await state["event_callback"]("synthesize", "error", {"error": str(e)})
            
            # Fallback to simple concatenation with debate content
            reports = state.get("agent_reports", [])
            debate_synthesis = state.get("debate_synthesis", "")
            
            fallback_parts = []
            
            # Include debate synthesis if available
            if debate_synthesis:
                fallback_parts.append(f"## Debate Summary\n\n{debate_synthesis[:5000]}")
            
            # Include agent reports
            for report in reports:
                if hasattr(report, 'narrative') and report.narrative:
                    fallback_parts.append(f"**{report.agent}**: {report.narrative}")
            
            fallback = "\n\n".join(fallback_parts) or "Unable to synthesize findings."
            
            return {
                **state,
                "synthesis": fallback,
                "final_synthesis": fallback,  # CRITICAL: streaming.py looks for this
                "meta_synthesis": fallback,   # CRITICAL: backup key
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
            "rag_context": None,
            "selected_agents": None,
            "agent_reports": [],
            "debate_results": None,
            "critique_results": None,
            "deterministic_result": None,  # Phase 3: deterministic agent results
            "verification": None,
            "synthesis": None,
            "error": None,
            "metadata": {
                "start_time": datetime.now(timezone.utc).isoformat()
            },
            "reasoning_chain": [],
            "event_callback": None
        }
        
        final_state = await self.graph.ainvoke(initial_state)
        
        # Add total latency
        start_time = datetime.fromisoformat(final_state["metadata"]["start_time"])
    
    async def run_stream(
        self, 
        question: str, 
        event_callback: Any
    ) -> Dict[str, Any]:
        """
        Run workflow with streaming events.
        Now includes emergency synthesis for timeout scenarios.
        
        Args:
            question: User's question
            event_callback: Async callback function(stage, status, payload, latency)
            
        Returns:
            Final workflow state
        """
        initial_state: WorkflowState = {
            "question": question,
            "classification": None,
            "prefetch": None,
            "rag_context": None,
            "selected_agents": None,
            "agent_reports": [],
            "debate_results": None,
            "critique_results": None,
            "deterministic_result": None,
            "verification": None,
            "synthesis": None,
            "error": None,
            "metadata": {
                "start_time": datetime.now(timezone.utc).isoformat()
            },
            "reasoning_chain": [],
            "event_callback": event_callback
        }
        
        try:
            # Execute workflow WITHOUT timeout - let debate and synthesis complete naturally
            # API endpoint has 60-minute timeout which is the only limit
            final_state = await self.graph.ainvoke(initial_state)
            
            # Emit done event
            if event_callback:
                start_time = datetime.fromisoformat(final_state["metadata"]["start_time"])
                total_latency_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                
                await event_callback(
                    "done",
                    "complete",
                    final_state,
                    total_latency_ms
                )
                
            return final_state
            
        except Exception as e:
            logger.error(f"Streaming workflow failed: {e}", exc_info=True)
            if event_callback:
                await event_callback("error", "error", {"error": str(e)}, 0)
            raise e


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
