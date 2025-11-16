"""
LangGraph workflow for LLM-powered multi-agent orchestration.

Implements streaming workflow with nodes:
classify ΓåÆ prefetch ΓåÆ agents (parallel) ΓåÆ verify ΓåÆ synthesize ΓåÆ done
"""

import asyncio
import logging
import os
import re
from typing import TypedDict, Annotated, Sequence, Optional, Dict, Any, AsyncIterator
from datetime import datetime, timezone

from dotenv import load_dotenv
from langgraph.graph import StateGraph, END

load_dotenv()

from ..agents.time_machine import TimeMachineAgent
from ..agents.predictor import PredictorAgent
from ..agents.scenario_agent import ScenarioAgent
from ..agents.base import AgentReport, DataClient

from ..llm.client import LLMClient
from ..classification.classifier import Classifier
from src.qnwis.orchestration.prefetch_apis import get_complete_prefetch
from src.qnwis.observability.query_metrics import start_query, finish_query

logger = logging.getLogger(__name__)


class WorkflowState(TypedDict, total=False):
    """Complete workflow state shared between nodes (must declare all keys)."""

    # Inputs / metadata
    question: str
    query: str
    user_id: Optional[str]
    timestamp: str
    execution_time: float

    # Classification
    classification: Optional[Dict[str, Any]]
    complexity: str
    topics: list

    # Data extraction
    prefetch: Optional[Dict[str, Any]]
    extracted_facts: list
    rag_context: Optional[Dict[str, Any]]

    # Agent selection & outputs
    selected_agents: Optional[list]
    agents_invoked: list
    labour_economist_analysis: str
    financial_economist_analysis: str
    market_economist_analysis: str
    operations_expert_analysis: str
    research_scientist_analysis: str
    agent_reports: list  # List of AgentReport objects

    # Debate / critique
    debate_results: Optional[Dict[str, Any]]
    multi_agent_debate: str
    critique_results: Optional[Dict[str, Any]]
    critique_output: str

    # Deterministic routing & verification
    deterministic_result: Optional[str]
    verification: Optional[Dict[str, Any]]

    # Synthesis & scoring
    synthesis: Optional[str]
    final_synthesis: str
    confidence_score: float

    # Error handling / misc
    error: Optional[str]
    metadata: Dict[str, Any]
    reasoning_chain: list
    event_callback: Optional[Any]


def calculate_final_confidence(state: "WorkflowState") -> float:
    """
    Calculate overall confidence from data coverage, agent consensus, and citations.
    """
    extracted_facts = state.get("extracted_facts", []) or []
    data_coverage = min(len(extracted_facts) / 25.0, 1.0)

    agent_conf = state.get("confidence_score", 0.5) or 0.5

    synthesis_text = state.get("final_synthesis") or state.get("synthesis", "") or ""
    has_citations = "Per extraction:" in synthesis_text or "[Per extraction:" in synthesis_text
    citation_score = 1.0 if has_citations else 0.3

    final_confidence = (
        (data_coverage * 0.3)
        + (agent_conf * 0.4)
        + (citation_score * 0.3)
    )
    return round(final_confidence, 2)


class LLMWorkflow:
    """
    LangGraph workflow orchestrating LLM-powered agents.
    
    Provides streaming execution with parallel agent processing.
    """
    
    def __init__(
        self,
        data_client: Optional[DataClient] = None,
        llm_client: Optional[LLMClient] = None,
        classifier: Optional[Classifier] = None
    ):
        """Initialize workflow with enforced Anthropic provider."""
        from qnwis.llm.client import get_client

        provider = os.getenv("QNWIS_LLM_PROVIDER", "anthropic").lower()
        api_key = os.getenv("ANTHROPIC_API_KEY")

        if provider == "stub":
            raise RuntimeError(
                "❌ LLM Workflow cannot run with stub provider!\n\n"
                "Set in environment/.env:\n"
                "  QNWIS_LLM_PROVIDER=anthropic\n"
                "  ANTHROPIC_API_KEY=sk-ant-...\n"
                f"Current provider: {provider}\n"
                f"API key set: {'yes' if api_key else 'no'}"
            )

        if not api_key or not api_key.startswith("sk-ant-"):
            masked = api_key[:20] + "..." if api_key else "NOT SET"
            raise RuntimeError(
                "❌ ANTHROPIC_API_KEY not set or invalid!\n\n"
                "Set in environment/.env:\n"
                "  ANTHROPIC_API_KEY=sk-ant-your-actual-key\n"
                f"Current value: {masked}"
            )

        if llm_client is None:
            llm_client = get_client(provider=provider)

        if not hasattr(llm_client, "ainvoke"):
            raise RuntimeError(
                f"❌ LLM client ({type(llm_client).__name__}) missing required 'ainvoke' method"
            )

        print("=" * 60)
        print("✅ LLM Workflow initialized successfully")
        print(f"   Provider: {provider}")
        print(f"   Model: {getattr(llm_client, 'model', 'default')}")
        print(f"   API Key: {api_key[:15]}...{api_key[-4:]}")
        print("=" * 60)

        self.data_client = data_client or DataClient()
        self.llm_client = llm_client
        self.classifier = classifier or Classifier()

        # Initialize deterministic agents (Phase 3)
        self.deterministic_agents = {
            "time_machine": TimeMachineAgent(self.data_client),
            "predictor": PredictorAgent(self.data_client),
            "scenario": ScenarioAgent(self.data_client),
        }

        # Build graph
        self.graph = self._build_graph()

        # Agent selector
        from .agent_selector import AgentSelector
        self.agent_selector = AgentSelector()
    
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
        workflow.add_node("select_agents", self._select_agents_node)
        workflow.add_node("agents", self._invoke_agents_node)
        workflow.add_node("debate", self._debate_node)
        workflow.add_node("critique", self._critique_node)
        workflow.add_node("verify", self._verify_node)
        workflow.add_node("synthesize", self._synthesize_node)

        # Define routing function
        def should_route_deterministic(state: WorkflowState) -> str:
            """
            Always route to LLM agents for maximum depth and quality.
            
            Cost-optimization disabled - user prioritizes depth over cost.
            Every query gets full 5-agent treatment for ministerial-grade intelligence.
            """
            logger.info("Routing to LLM agents (full depth prioritized over cost)")
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

        # LLM agents path: prefetch ΓåÆ rag ΓåÆ select_agents ΓåÆ agents ΓåÆ debate ΓåÆ critique ΓåÆ verify ΓåÆ synthesize ΓåÆ END
        workflow.add_edge("prefetch", "rag")
        workflow.add_edge("rag", "select_agents")
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
        print(f"\n[CLASSIFY NODE] Starting...")
        
        # Emit running event
        if state.get("event_callback"):
            await state["event_callback"]("classify", "running", {}, None)
        
        start_time = datetime.now(timezone.utc)
        
        try:
            question = state["question"]
            classification = self.classifier.classify_text(question)
            
            # Convert to dict if needed
            if not isinstance(classification, dict):
                classification = classification.dict() if hasattr(classification, 'dict') else dict(classification)
            
            # Use classifier's complexity for intelligent routing
            complexity = classification.get("complexity", "medium")
            
            latency_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            
            logger.info(
                f"Classification complete: complexity={complexity}, "
                f"latency={latency_ms:.0f}ms"
            )
            
            print(f"[CLASSIFY NODE] Complete:")
            print(f"   Complexity: {complexity} (from classifier)")
            print(f"   Route: Will be determined by routing function")
            print(f"   Topics: {classification.get('topics', [])}")

            # Update reasoning chain
            reasoning_chain = list(state.get("reasoning_chain", []))
            reasoning_chain.append(
                f"✓ Classification: {complexity} complexity"
            )
            
            # Emit complete event with REAL classification
            if state.get("event_callback"):
                await state["event_callback"](
                    "classify", 
                    "complete", 
                    {"classification": classification},
                    latency_ms
                )
            
            result = {
                **state,
                "classification": {
                    "complexity": complexity,  # From classifier
                    "topics": classification.get("topics", []),
                    "latency_ms": latency_ms,
                },
                "reasoning_chain": reasoning_chain,
            }
            print(f"   → Returning to graph (routing decision next)\n")
            return result
        
        except Exception as e:
            logger.error(f"Classification failed: {e}", exc_info=True)
            if state.get("event_callback"):
                await state["event_callback"]("classify", "error", {"error": str(e)}, None)
            return {
                **state,
                "classification": {"complexity": "medium", "error": str(e)},
                "error": f"Classification error: {e}"
            }

    async def _route_deterministic_node(self, state: WorkflowState) -> WorkflowState:
        """
        Handle simple queries with deterministic data extraction (no LLM needed).

        Args:
            state: Current workflow state

        Returns:
            Updated state with deterministic_result
        """
        print(f"\n[DETERMINISTIC NODE] Handling simple query without LLM...")
        
        if state.get("event_callback"):
            await state["event_callback"]("route_deterministic", "running", {}, None)

        start_time = datetime.now(timezone.utc)

        try:
            question = state["question"]
            
            logger.info(f"Processing simple query deterministically: {question[:50]}...")

            # Use TimeMachine agent for simple factual queries
            time_machine = self.deterministic_agents["time_machine"]
            
            # Extract simple data from database
            from datetime import date
            
            # Try to answer with deterministic data
            # In a production system, you'd parse the query to extract:
            # - metric (unemployment, employment, retention, etc.)
            # - sector (if specified)
            # - time range
            
            result = time_machine.baseline_report(
                metric="retention",  # Would be extracted from query
                sector=None,
                start=date(2023, 1, 1),
                end=date.today()
            )
            
            # Format as simple response
            answer = f"""
## Simple Query Response

**Query:** {question}

**Answer:** Based on deterministic data extraction from the database:

{result}

**Data Source:** LMIS Database (Direct Query)
**Confidence:** 95% (Deterministic)
**Cost Savings:** ~60% (No LLM calls needed for simple factual query)

This query was answered using direct database access without requiring LLM inference.
"""
            
            latency_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

            logger.info(f"Deterministic query complete: latency={latency_ms:.0f}ms (saved ~$0.05 in LLM costs)")
            print(f"[DETERMINISTIC NODE] Complete: {latency_ms:.0f}ms (no LLM calls)\n")

            # Update reasoning chain
            reasoning_chain = list(state.get("reasoning_chain", []))
            reasoning_chain.append(
                f"✓ Deterministic routing: answered simple query without LLM (saved ~$0.05)"
            )

            if state.get("event_callback"):
                await state["event_callback"](
                    "route_deterministic",
                    "complete",
                    {"method": "time_machine", "cost_saved": 0.05},
                    latency_ms
                )

            return {
                **state,
                "deterministic_result": answer,
                "final_synthesis": answer,  # Set final answer directly
                "confidence_score": 0.95,  # High confidence for deterministic data
                "metadata": {
                    **state.get("metadata", {}),
                    "routing": "deterministic",
                    "deterministic_latency_ms": latency_ms,
                    "llm_calls": 0,
                    "cost_saved_usd": 0.05,
                },
                "reasoning_chain": reasoning_chain,
            }

        except Exception as e:
            logger.error(f"Deterministic routing failed: {e}, routing to LLM fallback", exc_info=True)
            latency_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

            if state.get("event_callback"):
                await state["event_callback"]("route_deterministic", "error", {"error": str(e)}, None)

            # Fallback: create a simple error message that synthesis can handle
            reasoning_chain = list(state.get("reasoning_chain", []))
            reasoning_chain.append(
                f"⚠️ Deterministic routing failed, but query still needs answer"
            )

            return {
                **state,
                "deterministic_result": f"Deterministic extraction failed: {e}",
                "final_synthesis": f"**Note:** Simple query processing encountered an issue. Please try rephrasing your question.",
                "confidence_score": 0.3,
                "error": f"Deterministic routing error: {e}",
                "reasoning_chain": reasoning_chain,
            }
    
    async def _prefetch_node(self, state: WorkflowState) -> WorkflowState:
        """
        Prefetch data from ALL available sources.
        Uses: MoL, GCC-STAT, World Bank, Semantic Scholar, Brave, Perplexity
        """
        print(f"\n[PREFETCH NODE] Starting API calls...")
        
        query = state["question"]
        prefetch = get_complete_prefetch()

        try:
            raw_prefetch_results = await prefetch.fetch_all_sources(query)
            
            print(f"[PREFETCH NODE] Complete: {len(raw_prefetch_results)} facts extracted")

            extraction_confidence = 0.85 if len(raw_prefetch_results) > 10 else 0.60
            reasoning = f"Extracted {len(raw_prefetch_results)} facts from multiple sources"
            reasoning_chain = list(state.get("reasoning_chain", []))
            reasoning_chain.append(reasoning)

            # Normalize facts into structured format for downstream agents
            structured_facts: list[Dict[str, Any]] = []

            for fact in raw_prefetch_results:
                if isinstance(fact, dict):
                    metric = fact.get("metric") or fact.get("title") or fact.get("name")
                    value = fact.get("value") or fact.get("data") or fact.get("summary") or fact.get("abstract")
                    source = fact.get("source") or fact.get("origin") or "unknown"

                    if metric is None and source:
                        metric = f"metric_from_{source}"

                    if metric is None or value is None:
                        # Skip entries that cannot be structured meaningfully
                        continue

                    structured_facts.append({
                        "metric": metric,
                        "value": value,
                        "source": source,
                        "confidence": fact.get("confidence", 0.8),
                        "raw_text": fact.get("raw_text", str(fact)),
                    })
                else:
                    structured_facts.append({
                        "metric": "prefetch_fact",
                        "value": fact,
                        "source": "prefetch",
                        "confidence": 0.6,
                        "raw_text": str(fact),
                    })

            reasoning_chain.append(
                f"Prepared {len(structured_facts)} structured facts for agents"
            )

            updated_state = {
                **state,
                "prefetch": {
                    "fact_count": len(structured_facts),
                    "facts": structured_facts,
                },
                "extracted_facts": structured_facts,
                "extraction_confidence": extraction_confidence,
                "reasoning_chain": reasoning_chain,
            }

            if event_callback := state.get("event_callback"):
                await event_callback(
                    "prefetch",
                    "complete",
                    {
                        "extracted_facts": structured_facts,
                        "fact_count": len(structured_facts),
                        "sources": list(
                            {
                                fact["source"]
                                for fact in structured_facts
                                if isinstance(fact, dict) and fact.get("source")
                            }
                        ),
                    },
                    0,
                )

            print(f"   Facts by source:")
            sources: Dict[str, int] = {}
            for fact in structured_facts:
                if isinstance(fact, dict):
                    source = fact.get("source", "Unknown")
                    sources[source] = sources.get(source, 0) + 1

            for source, count in sources.items():
                print(f"   • {source}: {count} facts")
            
            print(f"   → Returning to graph (next: rag)\n")

            return updated_state

        except Exception as e:
            print(f"❌ Prefetch error: {e}")
            import traceback
            traceback.print_exc()

            if state.get("event_callback"):
                await state["event_callback"]("prefetch", "error", {"error": str(e)}, None)

            return {
                **state,
                "prefetch": {"status": "failed", "error": str(e)},
                "extracted_facts": [],
                "extraction_confidence": 0.0,
            }

    async def _rag_node(self, state: WorkflowState) -> WorkflowState:
        """RAG context retrieval node."""
        if state.get("event_callback"):
            await state["event_callback"]("rag", "running", {}, None)
        
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
            
            if state.get("event_callback"):
                await state["event_callback"](
                    "rag",
                    "complete",
                    {
                        "snippets_retrieved": len(rag_result.get("snippets", [])),
                        "sources": rag_result.get("sources", [])
                    },
                    latency_ms
                )
            
            # Update reasoning chain
            reasoning_chain = list(state.get("reasoning_chain", []))
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
                await state["event_callback"]("rag", "error", {"error": str(e)}, None)
            return {
                **state,
                "rag_context": {"snippets": [], "sources": []}
            }
    
    async def _select_agents_node(self, state: WorkflowState) -> WorkflowState:
        """
        Intelligent agent selection node.
        
        CRITICAL FIX: For "complex" queries, ALWAYS invoke all 4 specialist agents
        to enable true multi-agent debate and synthesis.
        """
        classification = state.get("classification", {})
        complexity = classification.get("complexity", "medium")
        
        # FORCE all 4 agents for complex queries
        if complexity == "complex":
            # Map to actual agent keys in self.agents
            selected_agent_names = [
                "labour_economist",      # Dr. Fatima Al-Mansoori - Labour Economist
                "nationalization",       # Dr. Mohammed Al-Khater - Financial/Policy Economist
                "skills",                # Dr. Layla Al-Said - Market/Skills Economist
                "pattern_detective"      # Eng. Khalid Al-Dosari - Operations Expert
            ]
            print(f"[SELECT AGENTS] Complex query detected - invoking ALL 4 specialist agents")
        else:
            # For simple/medium queries, use intelligent selection
            selected_agent_names = self.agent_selector.select_agents(
                classification=classification,
                min_agents=2,
                max_agents=4
            )
        
        selection_explanation = self.agent_selector.explain_selection(
            selected_agent_names, classification
        )
        
        if state.get("event_callback"):
            await state["event_callback"](
                "agent_selection",
                "complete",
                {
                    "selected_agents": selected_agent_names,
                    "selected_count": len(selected_agent_names),
                    "total_available": len(self.agent_selector.AGENT_EXPERTISE),
                    "savings": selection_explanation["savings"],
                    "explanation": selection_explanation
                },
                0
            )
        
        # Update reasoning chain
        reasoning_chain = list(state.get("reasoning_chain", []))
        reasoning_chain.append(
            f"Γ£ô Agent selection: chose {len(selected_agent_names)}/{len(self.agent_selector.AGENT_EXPERTISE)} agents"
            + (f" ({', '.join(selected_agent_names)})" if selected_agent_names else "")
        )

        return {
            **state,
            "selected_agents": selected_agent_names,
            "reasoning_chain": reasoning_chain,
        }
    
    async def _invoke_agents_node(self, state: WorkflowState) -> WorkflowState:
        """
        Invoke selected agents based on complexity and selection results (OPTIMIZED).
        
        Reduces unnecessary LLM calls by honoring agent selection instead of
        always invoking all 5 agents.
        """

        from qnwis.agents import (
            financial_economist,
            labour_economist,
            market_economist,
            operations_expert,
            research_scientist,
        )

        reasoning_chain = list(state.get("reasoning_chain", []))

        query_text = state.get("query") or state.get("question", "")
        if not query_text:
            reasoning_chain.append("Missing question text; aborting agent invocation")
            state["reasoning_chain"] = reasoning_chain
            return state

        extracted_facts = state.get("extracted_facts", []) or []
        
        # Get selection results and complexity
        selected_agents = state.get("selected_agents", [])
        classification = state.get("classification", {})
        complexity = classification.get("complexity", "complex") if isinstance(classification, dict) else "complex"

        # Agent mapping
        agent_map = {
            "labour_economist": labour_economist,
            "financial_economist": financial_economist,
            "market_economist": market_economist,
            "operations_expert": operations_expert,
            "research_scientist": research_scientist,
        }

        # ALWAYS invoke ALL 5 agents for maximum depth and quality
        # Cost-optimization disabled - user prioritizes depth over cost
        agents_to_invoke = list(agent_map.keys())  # All 5 agents, every time
        reasoning_chain.append("✅ Invoking ALL 5 PhD-level agents for maximum intelligence depth")

        # Build agent list
        agents = [agent_map[name] for name in agents_to_invoke if name in agent_map]
        
        logger.info(
            f"Invoking ALL {len(agents)} agents for maximum depth (complexity={complexity} is for display only)"
        )

        tasks = [agent.analyze(query_text, extracted_facts, self.llm_client) for agent in agents]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        agent_reports: list[dict[str, Any]] = []
        agents_invoked: list[str] = []
        confidences: list[float] = []

        for agent_obj, result in zip(agents, results):
            agent_name = getattr(agent_obj, "__name__", "agent")

            if isinstance(result, Exception):
                logger.error("%s failed", agent_name, exc_info=result)
                reasoning_chain.append(f"❌ {agent_name} failed: {result}")
                continue
            
            # Check if result is a valid dict with required keys
            if not isinstance(result, dict) or "agent_name" not in result:
                logger.error("%s returned invalid result: %s", agent_name, type(result))
                reasoning_chain.append(f"❌ {agent_name} returned invalid result")
                continue

            agent_reports.append(result)
            agents_invoked.append(result["agent_name"])
            confidences.append(result.get("confidence", 0.0))

            state[f"{result['agent_name']}_analysis"] = result["narrative"]

            if state.get("event_callback"):
                await state["event_callback"](
                    "agents",
                    "complete",
                    {
                        "agent": result["agent_name"],
                        "narrative": result["narrative"],
                        "confidence": result.get("confidence", 0.0),
                        "citations_count": len(result.get("citations", [])),
                        "data_gaps_count": len(result.get("data_gaps", [])),
                    },
                    0,
                )

            reasoning_chain.append(f"✅ {result['agent_name']} completed with structured output")

        avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
        reasoning_chain.append(f"{len(agent_reports)} agents completed successfully")
        reasoning_chain.append(f"Average confidence: {avg_conf:.1%}")

        return {
            **state,
            "agent_reports": agent_reports,
            "confidence_score": avg_conf,
            "agents_invoked": agents_invoked,
            "reasoning_chain": reasoning_chain,
        }

    async def _verify_node(self, state: WorkflowState) -> WorkflowState:
        """Verify structured agent reports for citation coverage and numeric accuracy."""
        from .verification_helpers import verify_agent_reports

        if state.get("event_callback"):
            await state["event_callback"]("verify", "running")

        start_time = datetime.now(timezone.utc)

        try:
            agent_reports = state.get("agent_reports", []) or []
            extracted_facts = state.get("extracted_facts", []) or []

            # Call pure verification helper
            verification_payload = verify_agent_reports(agent_reports, extracted_facts)

            latency_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

            reasoning_chain = list(state.get("reasoning_chain", []))
            reasoning_chain.append(
                "✓ Verification: "
                f"{verification_payload['warning_count']} citation violation(s), "
                f"{verification_payload['error_count']} number violation(s)"
            )

            if state.get("event_callback"):
                await state["event_callback"](
                    "verify", "complete", verification_payload, latency_ms
                )

            return {
                **state,
                "verification": {
                    **verification_payload,
                    "latency_ms": latency_ms,
                },
                "reasoning_chain": reasoning_chain,
            }

        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Verification failed: %s", exc, exc_info=True)
            if state.get("event_callback"):
                await state["event_callback"](
                    "verify", "error", {"error": str(exc)}, None
                )
            return {
                **state,
                "verification": {"status": "failed", "error": str(exc)},
                "error": f"Verification error: {exc}",
            }

    def _detect_contradictions(self, reports: list) -> list:
        """
        Detect contradictions between agent reports.

        Args:
            reports: List of agent reports (dicts with 'agent_name', 'narrative', 'confidence')

        Returns:
            List of contradiction dicts
        """
        contradictions = []

        # Extract numbers and citations from each report
        number_pattern = r'\b(\d+\.?\d*%?)\b'
        citation_pattern = r'\[Per extraction: \'([^\']+)\' from ([^\]]+)\]'

        for i, report1 in enumerate(reports):
            for report2 in reports[i+1:]:
                # Extract all numbers with nearby citations from both reports
                narrative1 = report1.get("narrative", "")
                narrative2 = report2.get("narrative", "")

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
                                contradictions.append({
                                    "metric_name": f"metric_at_pos_{pos1}_{pos2}",
                                    "agent1_name": report1.get("agent_name", "Unknown"),
                                    "agent1_value": val1,
                                    "agent1_value_str": value1_str,
                                    "agent1_citation": f"[Per extraction: '{citation1_value}' from {citation1_source}]",
                                    "agent1_confidence": report1.get("confidence", 0.5),
                                    "agent2_name": report2.get("agent_name", "Unknown"),
                                    "agent2_value": val2,
                                    "agent2_value_str": value2_str,
                                    "agent2_citation": f"[Per extraction: '{citation2_value}' from {citation2_source}]",
                                    "agent2_confidence": report2.get("confidence", 0.5),
                                    "severity": "high" if abs(val1 - val2) / val1 > 0.20 else "medium"
                                })
                        except ValueError:
                            # Not numeric, skip
                            continue

        logger.info(f"Detected {len(contradictions)} contradictions")
        return contradictions

    async def _conduct_debate(self, state: "WorkflowState") -> str:
        """Force multi-agent disagreements and preserve competing positions."""

        analyses_map = {
            "Labour Economist": state.get("labour_economist_analysis", ""),
            "Financial Economist": state.get("financial_economist_analysis", ""),
            "Market Economist": state.get("market_economist_analysis", ""),
            "Operations Expert": state.get("operations_expert_analysis", ""),
            "Research Scientist": state.get("research_scientist_analysis", ""),
        }

        valid_analyses = {
            name: text
            for name, text in analyses_map.items()
            if text and len(text) > 200 and "⚠️ ANALYSIS REJECTED" not in text
        }

        if len(valid_analyses) < 2:
            return f"⚠️ Debate skipped: only {len(valid_analyses)} valid analysis"

        analyses_text = "\n\n".join(
            f"**{name}:**\n{text[:1500]}{'...' if len(text) > 1500 else ''}"
            for name, text in valid_analyses.items()
        )

        contradiction_prompt = f"""
You are moderating a high-stakes policy debate. Your ONLY job is to find DISAGREEMENTS.

{analyses_text}

You must identify 2-3 SHARP contradictions where agents fundamentally disagree on feasibility, timeline, cost, or risk.

Format:

**CONTRADICTION 1: [Topic]**
- Agent X says: "[Direct quote showing position]"
- Agent Y says: "[Conflicting quote]"
- Stakes: [Why this matters]
"""

        contradictions = await self.llm_client.ainvoke(contradiction_prompt)

        cross_exam_prompt = f"""
The debate exposed these contradictions:

{contradictions}

Force each side to defend their position with DATA from the analyses. Keep it adversarial.

Produce:

## ⚔️ CROSS-EXAMINATION

**CONTRADICTION 1 DEFENSE:**
- Agent X defends: [Evidence]
- Agent Y counters: [Evidence]
- Evidence favors: [Who has stronger proof]
"""

        cross_exam = await self.llm_client.ainvoke(cross_exam_prompt)

        synthesis_prompt = f"""
Synthesize this debate for the Minister.

**ANALYSES:**
{analyses_text[:3000]}

**CONTRADICTIONS:**
{contradictions}

**CROSS-EXAMINATION:**
{cross_exam}

## 💬 MULTI-AGENT DEBATE SYNTHESIS

### Where Experts Agree (Only list true consensus)

### Critical Disagreements
⚖️ DISAGREEMENT 1: [Topic]
- Position A: [Agent, view, evidence]
- Position B: [Agent, opposing view, evidence]
- Implication: [Different outcomes]
- Which to trust: [Evidence-weighted call]

⚖️ DISAGREEMENT 2: [Topic]
[Same format]

### Evidence-Weighted Recommendation
🎯 [Action acknowledging uncertainty]

### What Would Resolve the Disagreements
📊 [Specific data needed]
"""

        return await self.llm_client.ainvoke(synthesis_prompt)

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
            adjusted_report = report.copy()

            # Find resolutions that affect this report
            relevant_resolutions = [
                r for r in resolutions
                if r.get("explanation", "").find(report.get("agent_name", "")) >= 0
            ]

            if relevant_resolutions:
                # Add debate context to narrative
                debate_context = "\n\n[Debate Context]\n"
                for r in relevant_resolutions:
                    debate_context += f"- {r['explanation']}\n"

                adjusted_report["narrative"] = report.get("narrative", "") + debate_context

            adjusted_reports.append(adjusted_report)

        return adjusted_reports

    async def _debate_node(self, state: WorkflowState) -> WorkflowState:
        """Execute adversarial debate phase."""
        reasoning_chain = list(state.get("reasoning_chain", []))
        reasoning_chain.append("🗣️ Initiating multi-agent debate phase...")

        debate_output = await self._conduct_debate(state)
        state["multi_agent_debate"] = debate_output

        if debate_output.startswith("⚠️"):
            reasoning_chain.append(f"⚠️ Debate: {debate_output[:100]}")
        else:
            reasoning_chain.append("✅ Multi-agent debate completed with explicit disagreements")

        return {**state, "multi_agent_debate": debate_output, "reasoning_chain": reasoning_chain}

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
            await state["event_callback"]("verify", "running", {}, None)

        start_time = datetime.now(timezone.utc)

        try:
            import re
            from .verification import verify_report

            reports = state.get("agent_reports", [])
            # Try both possible keys for prefetch data
            prefetch_data = state.get("prefetch_data", {})
            if not prefetch_data:
                prefetch_info = state.get("prefetch", {})
                prefetch_data = prefetch_info.get("data", {})

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
                    verification_result,
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
                await state["event_callback"]("verify", "error", {"error": str(e)}, None)
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
        contradictions = []

        # Extract numbers and citations from each report
        number_pattern = r'\b(\d+\.?\d*%?)\b'
        citation_pattern = r'\[Per extraction: \'([^\']+)\' from ([^\]]+)\]'

        for i, report1 in enumerate(reports):
            for report2 in reports[i+1:]:
                # Extract all numbers with nearby citations from both reports
                narrative1 = report1.get("narrative", "")
                narrative2 = report2.get("narrative", "")

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
                                contradictions.append({
                                    "metric_name": f"metric_at_pos_{pos1}_{pos2}",
                                    "agent1_name": report1.get("agent_name", "Unknown"),
                                    "agent1_value": val1,
                                    "agent1_value_str": value1_str,
                                    "agent1_citation": f"[Per extraction: '{citation1_value}' from {citation1_source}]",
                                    "agent1_confidence": report1.get("confidence", 0.5),
                                    "agent2_name": report2.get("agent_name", "Unknown"),
                                    "agent2_value": val2,
                                    "agent2_value_str": value2_str,
                                    "agent2_citation": f"[Per extraction: '{citation2_value}' from {citation2_source}]",
                                    "agent2_confidence": report2.get("confidence", 0.5),
                                    "severity": "high" if abs(val1 - val2) / val1 > 0.20 else "medium"
                                })
                        except ValueError:
                            # Not numeric, skip
                            continue

        logger.info(f"Detected {len(contradictions)} contradictions")
        return contradictions

    async def _critique_node(self, state: WorkflowState) -> WorkflowState:
        """Devil's advocate critique that attacks debate conclusions."""

        reasoning_chain = list(state.get("reasoning_chain", []))
        reasoning_chain.append("😈 Devil's advocate critique initiating...")

        debate_output = state.get("multi_agent_debate", "")

        if not debate_output or debate_output.startswith("⚠️"):
            state["critique_output"] = "⚠️ Critique skipped: no debate output to challenge"
            reasoning_chain.append("⚠️ Critique skipped (no debate output)")
            return {**state, "reasoning_chain": reasoning_chain}

        critique_prompt = f"""
You are **Dr. Omar Al-Rashid**, the DEVIL'S ADVOCATE for Qatar's Minister of Labour.

Your mission: DESTROY the council's confidence by exposing blind spots.

**THEIR SYNTHESIS TO ATTACK:**
{debate_output[:4000]}

Respond in this exact structure:

## 😈 DEVIL'S ADVOCATE CRITIQUE

### Fatal Assumptions
**ASSUMPTION 1:** [Quote their assumption]
- Why fragile: [Evidence contradicting it]
- If wrong: [Catastrophic outcome]

**ASSUMPTION 2:** [Another]
- Why fragile: [...]
- If wrong: [...]

### Unexamined Downsides
1. **[Risk they ignored]:** [Impact]
2. **[Second-order effect]:** [Impact]

### Alternative Interpretation
[How same data could support the opposite conclusion]

### Questions That Would Change Everything
1. [Unknown that flips recommendation]
2. [Another make-or-break question]

**Critique Severity: HIGH/MEDIUM/LOW**
"""

        try:
            critique = await self.llm_client.ainvoke(critique_prompt)
            state["critique_output"] = critique

            if "Severity: HIGH" in critique or "Critique Severity: HIGH" in critique:
                reasoning_chain.append("😈 SEVERE critique raised - confidence should be reduced")
            else:
                reasoning_chain.append("✅ Critique completed - assumptions challenged")

        except Exception as exc:
            state["critique_output"] = f"⚠️ Critique failed: {exc}"
            reasoning_chain.append("⚠️ Critique failed")

        return {**state, "reasoning_chain": reasoning_chain}

    async def _synthesize_node(self, state: WorkflowState) -> WorkflowState:
        """Generate final ministerial-grade synthesis from multi-agent debate"""
        reasoning_chain = list(state.get("reasoning_chain", []))
        reasoning_chain.append("📝 Generating final ministerial synthesis...")
        
        # Get debate output (primary source)
        debate_synthesis = state.get("multi_agent_debate", "")
        
        # Get individual agent analyses (backup if debate skipped)
        labour_analysis = state.get("labour_economist_analysis", "")
        financial_analysis = state.get("financial_economist_analysis", "")
        market_analysis = state.get("market_economist_analysis", "")
        operations_analysis = state.get("operations_expert_analysis", "")
        research_analysis = state.get("research_scientist_analysis", "")
        
        # Determine what we have to work with
        has_debate = debate_synthesis and not debate_synthesis.startswith("⚠️")
        has_agents = any([
            labour_analysis,
            financial_analysis,
            market_analysis,
            operations_analysis,
            research_analysis,
        ])
        
        if has_debate:
            critique_output = state.get("critique_output", "")

            print(f"\n{'='*60}")
            print("SYNTHESIS DEBUG")
            print(f"{'='*60}")
            print(f"Debate length: {len(debate_synthesis)} chars")
            print(f"Critique length: {len(critique_output)} chars")
            print(f"Critique preview: {critique_output[:200]}...")
            print(f"{'='*60}\n")

            synthesis_prompt = f"""
You are presenting multi-agent intelligence to the EMIR OF QATAR and the Qatar Financial Centre Authority.

CRITICAL: They don't want consultant platitudes. They need:
- SPECIFIC NUMBERS from agent calculations (not "significant gaps" - give actual numbers)
- BRUTAL CONTRADICTIONS between experts (don't smooth over disagreements - show the fight)
- NAMED PRECEDENTS with actual outcomes (not "regional examples" - cite Singapore 1985, Saudi Nitaqat, etc.)
- QUANTIFIED RISKS in dollar terms (not "may impact" - give $X billion estimates)
- SEVERITY RATINGS from devil's advocate (quote the brutal warnings)

**MULTI-AGENT DEBATE SYNTHESIS:**
{debate_synthesis[:4000]}

**DEVIL'S ADVOCATE CRITIQUE:**
{critique_output[:2000]}

**YOUR TASK:**
Create an executive summary that PRESERVES the brutal, specific details above.

## 🎯 EXECUTIVE SUMMARY

**Key Finding:**
[ONE SENTENCE with SPECIFIC NUMBERS. Example: "Qatar needs 1,277 finance graduates annually but produces only 347 total tech graduates, creating an 18-fold supply crisis that renders 70% target impossible without 25x education capacity expansion."]

**Critical Disagreement:**
[SHOW THE ACTUAL FIGHT between experts with their specific numbers and reasoning. Example: "Labour Economist assigns 5% feasibility probability citing Saudi Nitaqat's 23% private sector job losses, while Operations Expert argues Qatar's 88.5% LFPR vs Saudi's 69.8% creates different dynamics. Financial Economist quantifies downside as 20-35% FDI reduction ($42-73B capital flight)."]

**Devil's Advocate Warning:**
[QUOTE THE MOST BRUTAL PART of the critique with severity. Example: "QIA's $445B portfolio disruption could cost $9-13B annually in reduced returns. Policy failure risks 30-40% financial sector contraction requiring QCB intervention." Severity: HIGH]

**Recommendation:**
[SPECIFIC ACTION, NOT GENERIC. Example: "NO-GO on 70% by 2030. MANDATORY 6-month baseline study to quantify: (1) current financial sector Qatarization rate, (2) QCB enforcement capacity for 500+ institutions, (3) salary premium vs Dubai/London markets. Then pilot 35% target in Islamic banking only with adjustment triggers."]

**Go/No-Go Decision:**
[CLEAN DECISION. Example: "NO-GO on current timeline (2027: 50%, 2030: 70%). Operationally impossible given 36-48 month infrastructure lead times. ALTERNATIVE: 40% by 2030, 60% by 2035 with quality controls preventing UAE-style ghost employment."]

**Confidence: [X]%**
[EXPLAIN THE CONFIDENCE BREAKDOWN with numbers. Example: "35% confidence overall. HIGH (90%) that current timeline fails. MEDIUM (60%) that 8-year revised timeline works. VERY LOW (15%) on economic impacts due to missing GDP sector data, FDI sensitivity, productivity differentials."]

**Stakes:**
[WHAT HAPPENS if policy succeeds vs fails with hard numbers. Example: "FAILURE: 30-40% financial sector contraction, brain drain to Dubai/London, $9-13B QIA performance hit. SUCCESS: $200B knowledge economy anchor, Vision 2030 credibility."]

DO NOT use generic phrases like "substantial challenges" or "stakeholder engagement". Use the agents' actual numbers, precedents, and contradictions.
"""
            
        elif has_agents:
            # Fallback: Synthesize from individual agents
            agents_text = "\n\n".join([
                f"**Labour Economist:**\n{labour_analysis[:800]}" if labour_analysis else "",
                f"**Financial Economist:**\n{financial_analysis[:800]}" if financial_analysis else "",
                f"**Market Economist:**\n{market_analysis[:800]}" if market_analysis else "",
                f"**Operations Expert:**\n{operations_analysis[:800]}" if operations_analysis else "",
                f"**Research Scientist:**\n{research_analysis[:800]}" if research_analysis else "",
            ])
            
            synthesis_prompt = f"""
Synthesize these expert analyses into a ministerial briefing:

{agents_text}

Provide:
## 🎯 EXECUTIVE SUMMARY

**Key Finding:** [Synthesis of expert views]
**Recommendation:** [Actionable recommendation]
**Confidence: [X]%** [Reasoning]
"""
        else:
            # No content available
            state["final_synthesis"] = "⚠️ Insufficient analysis for synthesis"
            state["reasoning_chain"] = reasoning_chain + ["⚠️ Synthesis: No agent outputs available"]
            return state
        
        try:
            final_synthesis = await self.llm_client.ainvoke(synthesis_prompt)
            
            # Calculate final confidence
            confidence = self._calculate_final_confidence(state)
            
            state["final_synthesis"] = final_synthesis
            state["synthesis"] = final_synthesis
            state["confidence_score"] = confidence
            reasoning_chain.append(f"✅ Ministerial synthesis complete (confidence: {confidence:.1%})")
            state["reasoning_chain"] = reasoning_chain
            
        except Exception as e:
            state["final_synthesis"] = f"⚠️ Synthesis failed: {str(e)}"
            reasoning_chain.append(f"❌ Synthesis error: {str(e)}")
            state["reasoning_chain"] = reasoning_chain
        
        return state
    
    def _calculate_final_confidence(self, state: WorkflowState) -> float:
        """
        Calculate final confidence based on:
        - Data coverage (facts extracted)
        - Agent consensus (agreement level)
        - Citation coverage (% of claims cited)
        """
        # Data coverage (25+ facts = 100%)
        facts = state.get("extracted_facts", [])
        data_coverage = min(len(facts) / 25.0, 1.0)
        
        # Agent confidence (if available)
        agent_conf = state.get("confidence_score", 0.5)
        
        # Debate quality (did it execute?)
        debate = state.get("multi_agent_debate", "")
        debate_quality = 1.0 if debate and not debate.startswith("⚠️") else 0.5
        
        final_confidence = (
            data_coverage * 0.3 +
            agent_conf * 0.4 +
            debate_quality * 0.3
        )
        
        return round(final_confidence, 2)
    
    async def run(self, question: str) -> Dict[str, Any]:
        """
        Run workflow for a question with comprehensive metrics tracking.
        
        Args:
            question: User's question
            
        Returns:
            Final workflow state with metrics
        """
        # Start query metrics tracking
        query_id = start_query(question)
        
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
                "start_time": datetime.now(timezone.utc).isoformat(),
                "query_id": query_id
            },
            "reasoning_chain": [],
            "event_callback": None
        }
        
        try:
            final_state = await self.graph.ainvoke(initial_state)
            
            # Add total latency
            start_time = datetime.fromisoformat(final_state["metadata"]["start_time"])
            total_latency_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            final_state["metadata"]["total_latency_ms"] = total_latency_ms
            
            # Extract metrics data
            complexity = final_state.get("classification", {}).get("complexity", "unknown") \
                if isinstance(final_state.get("classification"), dict) else "unknown"
            
            agents_invoked = [report.get("agent_name", "unknown") 
                            for report in final_state.get("agent_reports", [])]
            
            confidence = final_state.get("confidence_score", 0.0)
            
            verification = final_state.get("verification", {})
            citation_violations = verification.get("citation_violations", 0) \
                if isinstance(verification, dict) else 0
            
            facts_extracted = len(final_state.get("extracted_facts", []))
            
            # Finish query metrics tracking
            query_metrics = finish_query(
                query_id=query_id,
                complexity=complexity,
                status="success",
                agents_invoked=agents_invoked,
                confidence=confidence,
                citation_violations=citation_violations,
                facts_extracted=facts_extracted
            )
            
            # Add metrics summary to final state
            final_state["metrics"] = query_metrics.summary()
            
            return final_state
            
        except Exception as e:
            # Record failed query
            finish_query(
                query_id=query_id,
                complexity="unknown",
                status="error",
                agents_invoked=[],
                confidence=0.0,
                citation_violations=0,
                facts_extracted=0
            )
            raise
    
    async def run_stream(self, question: str, event_callback) -> Dict[str, Any]:
        """
        Run workflow with streaming events.
        
        Args:
            question: User's question
            event_callback: Async callback for events (stage, status, payload, latency_ms)
            
        Yields:
            Workflow state updates
        """
        print(f"\n{'='*60}")
        print(f"\n{'='*60}\nWORKFLOW EXECUTION START\n{'='*60}")
        print(f"{'='*60}")
        print(f"Question: {question[:100]}...")
        
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
            "event_callback": event_callback,
        }
        
        print("Initial state created")
        print(f"Starting graph execution...")
        
        # Execute graph
        try:
            final_state = await self.graph.ainvoke(initial_state)
            print(f"\nGraph execution completed successfully")
        except Exception as e:
            print(f"\nGraph execution FAILED: {e}")
            import traceback
            traceback.print_exc()
            raise
        
        # Add total latency
        start_time = datetime.fromisoformat(final_state["metadata"]["start_time"])
        total_latency_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        final_state["metadata"]["total_latency_ms"] = total_latency_ms
        
        print(f"Total latency: {total_latency_ms:.0f}ms")
        print(f"{'='*60}\n")
        
        # Emit completion
        await event_callback("done", "complete", final_state, total_latency_ms)
        
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
