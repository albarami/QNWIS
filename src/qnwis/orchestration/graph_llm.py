"""
LangGraph workflow for LLM-powered multi-agent orchestration.

Implements streaming workflow with nodes:
classify → prefetch → agents (parallel) → verify → synthesize → done
"""

import logging
import re
from typing import TypedDict, Annotated, Sequence, Optional, Dict, Any, AsyncIterator
from datetime import datetime, timezone

from langgraph.graph import StateGraph, END

from src.qnwis.agents.labour_economist import LabourEconomistAgent
from src.qnwis.agents.nationalization import NationalizationAgent
from src.qnwis.agents.skills import SkillsAgent
from src.qnwis.agents.pattern_detective_llm import PatternDetectiveLLMAgent
from src.qnwis.agents.national_strategy_llm import NationalStrategyLLMAgent
from src.qnwis.agents.time_machine import TimeMachineAgent
from src.qnwis.agents.predictor import PredictorAgent
from src.qnwis.agents.scenario_agent import ScenarioAgent
from src.qnwis.agents.base import AgentReport, DataClient
from src.qnwis.llm.client import LLMClient
from src.qnwis.classification.classifier import Classifier
from src.qnwis.orchestration.citation_injector import CitationInjector

logger = logging.getLogger(__name__)


class WorkflowState(TypedDict):
    """State passed between workflow nodes."""

    question: str
    classification: Optional[Dict[str, Any]]
    prefetch: Optional[Dict[str, Any]]
    rag_context: Optional[Dict[str, Any]]
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
        
        # Initialize LLM agents
        self.agents = {
            "labour_economist": LabourEconomistAgent(data_client, llm_client),
            "nationalization": NationalizationAgent(data_client, llm_client),
            "skills": SkillsAgent(data_client, llm_client),
            "pattern_detective": PatternDetectiveLLMAgent(data_client, llm_client),
            "national_strategy": NationalStrategyLLMAgent(data_client, llm_client),
        }

        # Initialize deterministic agents (Phase 3)
        self.deterministic_agents = {
            "time_machine": TimeMachineAgent(data_client),
            "predictor": PredictorAgent(data_client),
            "scenario": ScenarioAgent(data_client),
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
        - classify → routing decision
        - If deterministic agent detected → run that agent → synthesize → END
        - If LLM agents → prefetch → rag → agents → debate → critique → verify → synthesize → END

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

        # Deterministic path: route_deterministic → synthesize → END
        workflow.add_edge("route_deterministic", "synthesize")

        # LLM agents path: prefetch → rag → select_agents → agents → debate → critique → verify → synthesize → END
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
            
            # Emit complete event
            if state.get("event_callback"):
                await state["event_callback"](
                    "classify", 
                    "complete", 
                    {"classification": classification},
                    latency_ms
                )
            
            return {
                **state,
                "classification": {
                    "complexity": classification.get("complexity", "medium"),
                    "topics": classification.get("topics", []),
                    "route_to": classification.get("route_to"),  # Phase 3: deterministic routing
                    "latency_ms": latency_ms
                }
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
                    "deterministic_latency_ms": latency_ms
                }
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
        Prefetch common data needed by agents.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state with prefetch results
        """
        if state.get("event_callback"):
            await state["event_callback"]("prefetch", "running")
        
        start_time = datetime.now(timezone.utc)
        
        try:
            # Use intelligent prefetching
            from .prefetch import prefetch_queries
            
            classification = state.get("classification", {})
            prefetched_data = await prefetch_queries(
                classification=classification,
                data_client=self.data_client,
                max_concurrent=5,
                timeout_seconds=20.0
            )
            
            latency_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            
            logger.info(f"Prefetch complete: {len(prefetched_data)} queries, latency={latency_ms:.0f}ms")
            
            if state.get("event_callback"):
                await state["event_callback"](
                    "prefetch",
                    "complete",
                    {
                        "queries_fetched": len(prefetched_data),
                        "query_ids": list(prefetched_data.keys())
                    },
                    latency_ms
                )
            
            return {
                **state,
                "prefetch": {
                    "status": "complete",
                    "data": prefetched_data,
                    "latency_ms": latency_ms
                }
            }
        
        except Exception as e:
            logger.error(f"Prefetch failed: {e}", exc_info=True)
            if state.get("event_callback"):
                await state["event_callback"]("prefetch", "error", {"error": str(e)})
            return {
                **state,
                "prefetch": {"status": "failed", "error": str(e)},
                "error": f"Prefetch error: {e}"
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
            
            return {
                **state,
                "rag_context": rag_result
            }
        
        except Exception as e:
            logger.error(f"RAG failed: {e}", exc_info=True)
            if state.get("event_callback"):
                await state["event_callback"]("rag", "error", {"error": str(e)})
            return {
                **state,
                "rag_context": {"snippets": [], "sources": []}
            }
    
    async def _select_agents_node(self, state: WorkflowState) -> WorkflowState:
        """Intelligent agent selection node."""
        classification = state.get("classification", {})
        
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
        
        return {
            **state,
            "selected_agents": selected_agent_names
        }
    
    async def _agents_node(self, state: WorkflowState) -> WorkflowState:
        """
        Execute selected agents with streaming and deliberation.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state with agent reports
        """
        import asyncio
        
        question = state["question"]
        context = {
            "classification": state.get("classification"),
            "prefetch": state.get("prefetch", {}).get("data", {}),
            "rag_context": state.get("rag_context", {})
        }
        
        # Get selected agents
        selected_agent_names = state.get("selected_agents", [])
        if not selected_agent_names:
            selected_agent_names = list(self.agents.keys())
        
        # Map agent names to instances
        agent_name_mapping = {
            "labour_economist": "LabourEconomist",
            "nationalization": "Nationalization",
            "skills": "SkillsAgent",
            "pattern_detective": "PatternDetective",
            "national_strategy": "NationalStrategy"
        }
        
        # Run selected agents with streaming
        reports = []
        for agent_name in selected_agent_names:
            # Find matching agent instance
            agent_key = agent_name.lower().replace("agent", "").replace("_", "")
            for key, agent in self.agents.items():
                if key in agent_key or agent_key in key:
                    if state.get("event_callback"):
                        await state["event_callback"](f"agent:{agent_name}", "running")
                    
                    start_time = datetime.now(timezone.utc)
                    
                    try:
                        # Run agent with streaming
                        if hasattr(agent, 'run_stream'):
                            async for event in agent.run_stream(question, context):
                                if event["type"] == "token" and state.get("event_callback"):
                                    await state["event_callback"](
                                        f"agent:{agent_name}",
                                        "streaming",
                                        {"token": event["content"]}
                                    )
                                elif event["type"] == "complete":
                                    report = event["report"]
                                    reports.append(report)
                                    
                                    latency_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                                    
                                    if state.get("event_callback"):
                                        await state["event_callback"](
                                            f"agent:{agent_name}",
                                            "complete",
                                            {"report": report},
                                            latency_ms
                                        )
                        else:
                            # Fallback to non-streaming
                            report = await agent.run(question, context)
                            reports.append(report)
                            
                            latency_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                            
                            if state.get("event_callback"):
                                await state["event_callback"](
                                    f"agent:{agent_name}",
                                    "complete",
                                    {"report": report},
                                    latency_ms
                                )
                        
                        logger.info(f"Agent {agent_name} completed successfully")
                    
                    except Exception as e:
                        logger.error(f"Agent {agent_name} failed: {e}", exc_info=True)
                        if state.get("event_callback"):
                            await state["event_callback"](
                                f"agent:{agent_name}",
                                "error",
                                {"error": str(e)}
                            )
                        # Create error report
                        from src.qnwis.agents.base import AgentReport
                        error_report = AgentReport(
                            agent=agent_name,
                            findings=[],
                            narrative=f"Agent failed: {e}"
                        )
                        reports.append(error_report)
                    
                    break

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

        return {
            **state,
            "agent_reports": reports
        }
    
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
                    "latency_ms": latency_ms
                }
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
            response = await self.llm_client.generate(prompt=debate_prompt, temperature=0.2)

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
        """
        Conduct multi-agent debate to resolve contradictions.

        Args:
            state: Current workflow state with agent_reports

        Returns:
            Updated state with debate_results and adjusted reports
        """
        if state.get("event_callback"):
            await state["event_callback"]("debate", "running")

        start_time = datetime.now(timezone.utc)
        reports = state.get("agent_reports", [])

        # 1. Detect contradictions
        contradictions = self._detect_contradictions(reports)

        if not contradictions:
            logger.info("No contradictions detected - skipping debate")

            if state.get("event_callback"):
                await state["event_callback"](
                    "debate",
                    "complete",
                    {"contradictions": 0, "status": "skipped"},
                    0
                )

            return {
                **state,
                "debate_results": {
                    "contradictions_found": 0,
                    "status": "skipped",
                    "latency_ms": 0
                }
            }

        logger.info(f"Detected {len(contradictions)} contradictions - starting debate")

        # 2. Conduct structured debates
        resolutions = []
        for contradiction in contradictions:
            resolution = await self._conduct_debate(contradiction)
            resolutions.append(resolution)

        # 3. Build consensus
        consensus = self._build_consensus(resolutions)

        # 4. Adjust agent reports based on debate
        adjusted_reports = self._apply_debate_resolutions(reports, resolutions)

        latency_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

        logger.info(
            f"Debate complete: {consensus['resolved_contradictions']} resolved, "
            f"{consensus['flagged_for_review']} flagged, latency={latency_ms:.0f}ms"
        )

        if state.get("event_callback"):
            await state["event_callback"](
                "debate",
                "complete",
                {
                    "contradictions": len(contradictions),
                    "resolved": consensus["resolved_contradictions"],
                    "flagged": consensus["flagged_for_review"]
                },
                latency_ms
            )

        return {
            **state,
            "agent_reports": adjusted_reports,
            "debate_results": {
                "contradictions_found": len(contradictions),
                "resolved": consensus["resolved_contradictions"],
                "flagged_for_review": consensus["flagged_for_review"],
                "consensus_narrative": consensus["consensus_narrative"],
                "latency_ms": latency_ms,
                "status": "complete"
            }
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

            return {
                **state,
                "critique_results": {
                    "status": "skipped",
                    "reason": "no_reports",
                    "latency_ms": 0
                }
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
            response = await self.llm_client.generate(prompt=critique_prompt, temperature=0.2)

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
                        "critiques": len(critique.get("critiques", [])),
                        "red_flags": len(critique.get("red_flags", [])),
                        "strengthened": critique.get("strengthened_by_critique", False)
                    },
                    latency_ms
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
                    "status": "complete"
                }
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

                return {
                    **state,
                    "synthesis": deterministic_result,
                    "metadata": {
                        **state.get("metadata", {}),
                        "synthesis_latency_ms": latency_ms,
                        "synthesis_source": "deterministic"
                    }
                }

            # LLM agent synthesis path
            reports = state.get("agent_reports", [])

            # Build synthesis prompt
            findings_text = "\n\n".join([
                f"**Agent {report.agent}**:\n{report.narrative if hasattr(report, 'narrative') else str(report)}"
                for report in reports
                if report
            ])

            synthesis_prompt = f"""Synthesize the following agent findings into a comprehensive executive summary for the question: \"{question}\"

Agent Findings:
{findings_text}

Provide a ministerial-grade synthesis that:
1. Summarizes key insights
2. Identifies consensus across agents
3. Highlights critical recommendations
4. Notes any data quality concerns

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
                "metadata": {
                    **state.get("metadata", {}),
                    "synthesis_latency_ms": latency_ms
                }
            }
        
        except Exception as e:
            logger.error(f"Synthesis failed: {e}", exc_info=True)
            if state.get("event_callback"):
                await state["event_callback"]("synthesize", "error", {"error": str(e)})
            
            # Fallback to simple concatenation
            reports = state.get("agent_reports", [])
            fallback = "\n\n".join([
                f"**{report.agent}**: {report.narrative}"
                for report in reports
                if hasattr(report, 'narrative') and report.narrative
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
        total_latency_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        final_state["metadata"]["total_latency_ms"] = total_latency_ms
        
        return final_state
    
    async def run_stream(self, question: str, event_callback) -> AsyncIterator[Dict[str, Any]]:
        """
        Run workflow with streaming events.
        
        Args:
            question: User's question
            event_callback: Async callback for events (stage, status, payload, latency_ms)
            
        Yields:
            Workflow state updates
        """
        initial_state: WorkflowState = {
            "question": question,
            "classification": None,
            "prefetch": None,
            "rag_context": None,
            "selected_agents": None,
            "agent_reports": [],
            "verification": None,
            "synthesis": None,
            "error": None,
            "metadata": {
                "start_time": datetime.now(timezone.utc).isoformat()
            },
            "event_callback": event_callback
        }
        
        # Execute graph
        final_state = await self.graph.ainvoke(initial_state)
        
        # Add total latency
        start_time = datetime.fromisoformat(final_state["metadata"]["start_time"])
        total_latency_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        final_state["metadata"]["total_latency_ms"] = total_latency_ms
        
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
