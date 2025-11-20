"""
QNWIS Orchestration Graph using LangGraph.

This module builds and executes the LangGraph workflow for QNWIS agent orchestration.
The graph routes tasks to agents, validates outputs, and formats results consistently.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from typing import Any, Literal, cast

from langgraph.graph import END, StateGraph

from ..agents.base import DataClient
from ..ui.agent_status import display_agent_execution_status
from ..verification.citation_enforcer import verify_agent_output_with_retry
from .metrics import MetricsObserver, ensure_observer
from .nodes import error_handler, format_report, invoke_agent, route_intent, verify_structure
from .prefetch import Prefetcher
from .quality_metrics import calculate_analysis_confidence
from .registry import AgentRegistry
from .schemas import OrchestrationResult, OrchestrationTask, ReportSection, WorkflowState
from .types import PrefetchSpec

logger = logging.getLogger(__name__)


class QNWISGraph:
    """
    LangGraph-based orchestration workflow for QNWIS agents.

    This class builds a state machine that:
    1. Routes tasks to appropriate agents
    2. Invokes agent methods with deterministic parameters
    3. Validates structural integrity of outputs
    4. Formats results into uniform reports
    5. Handles errors gracefully

    The graph never directly accesses data sources - all data access
    happens through agents via DataClient.
    """

    def __init__(
        self,
        registry: AgentRegistry,
        config: dict[str, Any] | None = None,
        observer: MetricsObserver | None = None,
        data_client: DataClient | None = None,
        cache: Any | None = None,
    ) -> None:
        """
        Initialize the QNWIS orchestration graph.

        Args:
            registry: Agent registry with intent mappings
            config: Configuration dict with timeouts, retries, validation settings
            observer: Metrics observer for counters/timers
            data_client: DataClient for prefetch operations (optional)
            cache: Optional DeterministicRedisCache for caching (optional)
        """
        self.registry = registry
        self.config = config or self._default_config()
        self.observer = ensure_observer(observer)
        self.data_client = data_client
        self.cache = cache
        self._graph: StateGraph | None = None

        logger.info(
            "QNWISGraph initialized with %d intents",
            len(registry.intents()),
        )

    @staticmethod
    def _default_config() -> dict[str, Any]:
        """
        Get default configuration.

        Returns:
            Default config dict
        """
        return {
            "timeouts": {
                "agent_call_ms": 30000,
                "prefetch_ms": 25000,
            },
            "retries": {
                "agent_call": 1,
                "transient": ["TimeoutError", "ConnectionError"],
            },
            "validation": {
                "strict": False,
                "require_evidence": True,
                "require_freshness": True,
            },
            "formatting": {
                "max_findings": 10,
                "max_citations": 20,
                "top_evidence": 5,
            },
            "logging": {"level": "INFO"},
            "coordination": {
                "enabled": False,  # Enable for multi-agent flows
            },
        }

    def build(self) -> StateGraph:
        """
        Build the LangGraph state machine.

        Returns:
            Compiled StateGraph ready for execution
        """
        logger.info("Building LangGraph workflow")

        # Create graph with WorkflowState type
        workflow = StateGraph(dict[str, Any])

        # Add nodes
        workflow.add_node("router", self._router_node)
        workflow.add_node("prefetch", self._prefetch_node)
        workflow.add_node("invoke", self._invoke_node)
        workflow.add_node("verify", self._verify_node)
        workflow.add_node("format", self._format_node)
        workflow.add_node("error", self._error_node)

        # Set entry point
        workflow.set_entry_point("router")

        # Add edges with conditional routing
        workflow.add_conditional_edges(
            "router",
            self._should_proceed,
            {
                "prefetch": "prefetch",
                "invoke": "invoke",
                "error": "error",
            },
        )

        workflow.add_conditional_edges(
            "prefetch",
            self._should_proceed,
            {
                "invoke": "invoke",
                "error": "error",
            },
        )

        workflow.add_conditional_edges(
            "invoke",
            self._should_proceed,
            {
                "verify": "verify",
                "error": "error",
            },
        )

        workflow.add_conditional_edges(
            "verify",
            self._should_proceed,
            {
                "format": "format",
                "error": "error",
            },
        )

        # Format and error both end the workflow
        workflow.add_edge("format", END)
        workflow.add_edge("error", END)

        # Compile the graph
        self._graph = workflow.compile()
        logger.info("LangGraph workflow built successfully")

        return self._graph

    def _router_node(self, state: dict[str, Any]) -> dict[str, Any]:
        """Router node wrapper."""
        return route_intent(state, self.registry)

    def _prefetch_node(self, state: dict[str, Any]) -> dict[str, Any]:
        """Prefetch node wrapper - executes declarative prefetch specs."""
        workflow_state = WorkflowState(**state)

        # Skip prefetch if no routing decision or no prefetch specs
        if not workflow_state.routing_decision:
            logger.debug("No routing decision, skipping prefetch")
            return state

        prefetch_specs = workflow_state.routing_decision.prefetch
        if not prefetch_specs:
            logger.debug("No prefetch specs, skipping prefetch")
            return state

        # Skip if data_client not available
        if not self.data_client:
            logger.warning("DataClient not available, skipping prefetch")
            return {
                **state,
                "logs": workflow_state.logs + ["WARNING: Prefetch skipped (no DataClient)"],
            }

        try:
            timeout_ms = int(self.config.get("timeouts", {}).get("prefetch_ms", 25000))
            prefetcher = Prefetcher(
                self.data_client, timeout_ms=timeout_ms, cache=self.cache
            )

            logger.info("Running prefetch with %d specs", len(prefetch_specs))
            # Cast to satisfy type checker - validated by Pydantic
            typed_specs = cast(list[PrefetchSpec], prefetch_specs)
            prefetch_cache = prefetcher.run(typed_specs)

            return {
                **state,
                "prefetch_cache": prefetch_cache,
                "logs": workflow_state.logs
                + [f"Prefetch completed: {len(prefetch_cache)} entries"],
            }

        except Exception as exc:
            logger.exception("Prefetch failed")
            # Continue without prefetch - agents will fetch on demand
            return {
                **state,
                "logs": workflow_state.logs
                + [f"WARNING: Prefetch failed: {exc}", "Continuing without prefetch"],
            }

    def _invoke_node(self, state: dict[str, Any]) -> dict[str, Any]:
        """Invoke node wrapper."""
        timeout_ms = int(self.config.get("timeouts", {}).get("agent_call_ms", 30000))
        retry_cfg = self.config.get("retries", {})
        max_retries = int(retry_cfg.get("agent_call", 1))
        transient: Iterable[str] = retry_cfg.get(
            "transient", ["TimeoutError", "ConnectionError"]
        )
        invoked_state = invoke_agent(
            state,
            self.registry,
            timeout_ms=timeout_ms,
            observer=self.observer,
            max_retries=max_retries,
            transient_exceptions=transient,
        )
        return self._record_agent_status(invoked_state)

    async def _verify_node(self, state: dict[str, Any]) -> dict[str, Any]:
        """Verify node wrapper with strict citation enforcement."""
        validation_cfg = self.config.get("validation", {})
        strict = bool(validation_cfg.get("strict", False))

        verified_state = verify_structure(
            state,
            strict=strict,
            require_evidence=validation_cfg.get("require_evidence", True),
            require_freshness=validation_cfg.get("require_freshness", True),
            observer=self.observer,
        )

        # Bail early if an upstream error already occurred
        if verified_state.get("error"):
            return verified_state

        output_text = self._resolve_output_text(verified_state.get("agent_output"))
        if not output_text:
            return verified_state

        agent_name = verified_state.get("metadata", {}).get("agent", "Unknown")
        extracted_facts = self._collect_prefetched_facts(verified_state.get("prefetch_cache"))

        try:
            verification_result = await verify_agent_output_with_retry(
                agent_name,
                output_text,
                extracted_facts,
                max_retries=3,
            )
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("Strict verification error: %s", exc)
            return verified_state

        metadata = dict(verified_state.get("metadata") or {})
        violations = verification_result.get("violations", [])
        metadata["citation_report"] = {
            "status": verification_result.get("status", "passed"),
            "violations": violations,
            "violation_count": verification_result.get("violation_count", len(violations)),
            "attempts": verification_result.get("attempts", 1),
        }
        verified_state["metadata"] = metadata

        if verification_result["status"] == "rejected":
            reason = verification_result.get("reason", "citation_violations")
            error_msg = f"Strict verification failed: {reason}"
            rejected_agents = list(metadata.get("rejected_agents", []))
            rejected_agents.append(agent_name)
            metadata["rejected_agents"] = rejected_agents
            verified_state["metadata"] = metadata
            verified_state = self._record_agent_status(verified_state, status="failed", reason=error_msg)
            return {
                **verified_state,
                "error": error_msg,
                "verification_details": verification_result,
                "logs": verified_state.get("logs", []) + [f"ERROR: {error_msg}"],
            }

        if verification_result.get("output") and verification_result["output"] != output_text:
            verified_state["agent_output"] = verification_result["output"]

        return verified_state

    def _format_node(self, state: dict[str, Any]) -> dict[str, Any]:
        """Format node wrapper."""
        formatting_cfg = self.config.get("formatting", {})
        enriched_state = self._apply_confidence_metadata(state)
        formatted_state = format_report(
            enriched_state,
            formatting_config=formatting_cfg,
            observer=self.observer,
        )
        return self._append_agent_status_section(formatted_state)

    def _error_node(self, state: dict[str, Any]) -> dict[str, Any]:
        """Error handler node wrapper."""
        return error_handler(state, observer=self.observer)

    def _should_proceed(
        self, state: dict[str, Any]
    ) -> Literal["prefetch", "invoke", "verify", "format", "error"]:
        """
        Conditional edge function to determine next node.

        Args:
            state: Current workflow state

        Returns:
            Next node name
        """
        workflow_state = WorkflowState(**state)

        # Check for errors
        if workflow_state.error is not None:
            return "error"

        # Route based on what's been completed
        if workflow_state.route is None:
            # Router hasn't run yet, this shouldn't happen
            logger.error("Routing decision with no route or error")
            return "error"

        # Check if we need prefetch
        if workflow_state.routing_decision:
            has_prefetch_specs = bool(workflow_state.routing_decision.prefetch)
            prefetch_executed = "prefetch_cache" in state or bool(workflow_state.prefetch_cache)

            if has_prefetch_specs and not prefetch_executed:
                # Need to run prefetch
                return "prefetch"

        if workflow_state.agent_output is None:
            # Agent hasn't been invoked yet
            return "invoke"

        # Check if output is already an OrchestrationResult (formatted)
        if isinstance(workflow_state.agent_output, OrchestrationResult):
            # Already formatted (shouldn't normally happen in this flow)
            return "format"

        # Check if we've verified yet
        if "verification_warnings" not in workflow_state.metadata:
            # Need to verify
            return "verify"

        # Ready to format
        return "format"

    def _record_agent_status(
        self,
        state: dict[str, Any],
        status: str | None = None,
        reason: str | None = None,
    ) -> dict[str, Any]:
        """Append an agent execution record for UI transparency."""
        metadata = dict(state.get("metadata") or {})
        agent_name = metadata.get("agent")
        if not agent_name:
            return state
        elapsed_ms = metadata.get("elapsed_ms")
        entry: dict[str, Any] = {
            "name": agent_name,
            "status": status or ("failed" if state.get("error") else "invoked"),
        }
        if isinstance(elapsed_ms, (int, float)):
            entry["duration"] = elapsed_ms / 1000.0
        if reason:
            entry["reason"] = reason
        agent_status = list(metadata.get("agent_status", []))
        agent_status.append(entry)
        metadata["agent_status"] = agent_status
        state["metadata"] = metadata
        return state

    def _collect_prefetched_facts(self, cache: Any) -> list[dict[str, Any]]:
        """Normalize prefetched QueryResults into lightweight fact dictionaries."""
        facts: list[dict[str, Any]] = []
        if not isinstance(cache, dict):
            return facts
        for cache_key, value in cache.items():
            rows = getattr(value, "rows", None)
            if rows:
                for row in rows[:5]:
                    payload = getattr(row, "data", {}) or {}
                    facts.append(
                        {
                            "metric": cache_key,
                            "data_type": cache_key,
                            "value": payload,
                        }
                    )
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        facts.append(item)
        return facts

    def _resolve_output_text(self, output: Any) -> str | None:
        """Extract narrative text from assorted agent output types."""
        if isinstance(output, str):
            return output
        narrative = getattr(output, "narrative", None)
        if isinstance(narrative, str):
            return narrative
        return None

    def _apply_confidence_metadata(self, state: dict[str, Any]) -> dict[str, Any]:
        """Attach confidence scoring metadata if not already computed."""
        metadata = dict(state.get("metadata") or {})
        if metadata.get("confidence_breakdown"):
            state["metadata"] = metadata
            return state

        facts = self._collect_prefetched_facts(state.get("prefetch_cache"))
        agent_outputs = {}
        if state.get("agent_output") is not None:
            agent_outputs["primary"] = state["agent_output"]
        citation_report = metadata.get("citation_report") or {}
        citation_count = citation_report.get("violation_count") or len(
            citation_report.get("violations", [])
        )

        confidence = calculate_analysis_confidence(
            facts,
            metadata.get("required_data_types", []),
            agent_outputs,
            citation_count,
        )
        band = self._score_to_band(confidence["overall_confidence"])
        metadata["confidence_details"] = confidence
        metadata["confidence_breakdown"] = {
            "score": int(confidence["overall_confidence"] * 100),
            "band": band,
            "components": {
                "citation": confidence["components"]["citation_compliance"] * 100,
                "numbers": confidence["components"]["data_quality"] * 100,
                "cross": confidence["components"]["agent_agreement"] * 100,
            },
            "reasons": [confidence["recommendation"]],
            "coverage": confidence["components"]["data_quality"],
            "freshness": 1.0,
            "dashboard_payload": {
                "score": confidence["overall_confidence"],
                "band": band,
                "facts": confidence["facts_extracted"],
                "violations": confidence["citation_violations"],
            },
        }
        state["metadata"] = metadata
        return state

    def _score_to_band(self, score: float) -> str:
        if score >= 0.85:
            return "GREEN"
        if score >= 0.55:
            return "AMBER"
        return "RED"

    def _append_agent_status_section(self, state: dict[str, Any]) -> dict[str, Any]:
        """Add the agent status summary as a new report section when available."""
        result = state.get("agent_output")
        if not isinstance(result, OrchestrationResult):
            return state
        metadata = state.get("metadata") or {}
        agent_status = metadata.get("agent_status")
        if agent_status:
            status_md = display_agent_execution_status(agent_status)
            result.sections.append(
                ReportSection(title="Agent Execution Status", body_md=status_md)
            )
        return {**state, "agent_output": result}

    def run(self, task: OrchestrationTask) -> OrchestrationResult:
        """
        Execute the workflow for a given task.

        Args:
            task: Orchestration task to execute

        Returns:
            OrchestrationResult with findings or error

        Raises:
            RuntimeError: If graph has not been built
        """
        if self._graph is None:
            self.build()

        self.observer.increment(
            "workflow.run.start",
            tags={"intent": task.intent},
        )

        logger.info(
            "Running workflow: intent=%s request_id=%s params=%s",
            task.intent,
            task.request_id,
            list(task.params.keys()),
        )

        # Initialize state
        initial_state: dict[str, Any] = {
            "task": task,
            "route": None,
            "routing_decision": None,
            "agent_output": None,
            "error": None,
            "logs": [f"Started workflow for intent: {task.intent}"],
            "metadata": {},
            "prefetch_cache": {},
        }

        try:
            # Run the graph
            final_state = self._graph.invoke(initial_state)

            # Extract result
            result = final_state.get("agent_output")

            if result is None:
                logger.error("Workflow completed with no result")
                # Create error result
                return OrchestrationResult(
                    ok=False,
                    intent=task.intent,
                    sections=[],
                    citations=[],
                    freshness={},
                    reproducibility={"method": "unknown", "params": {}, "timestamp": ""},
                    warnings=["Workflow completed with no result"],
                    request_id=task.request_id,
                )

            if not isinstance(result, OrchestrationResult):
                logger.error("Result is not an OrchestrationResult: %s", type(result))
                # Try to convert
                from .nodes.error import error_handler as convert_error

                error_state = {**final_state, "error": "Invalid result type"}
                converted = convert_error(error_state)
                result = converted.get("agent_output")

            logger.info(
                "Workflow completed: ok=%s warnings=%d",
                result.ok,
                len(result.warnings),
            )
            self.observer.increment(
                "workflow.run.success",
                tags={"intent": result.intent, "ok": str(result.ok).lower()},
            )

            return result

        except Exception as exc:
            logger.exception("Workflow execution failed")
            self.observer.increment(
                "workflow.run.failure",
                tags={"intent": task.intent, "reason": type(exc).__name__},
            )

            # Create safe error result
            from .nodes.error import error_handler as convert_error

            error_state = {
                "task": task,
                "error": str(exc),
                "logs": initial_state["logs"] + [f"FATAL: {type(exc).__name__}: {exc}"],
                "metadata": {},
            }

            converted = convert_error(error_state)
            return converted.get("agent_output")


def create_graph(
    registry: AgentRegistry,
    config: dict[str, Any] | None = None,
    observer: MetricsObserver | None = None,
    data_client: DataClient | None = None,
    cache: Any | None = None,
) -> QNWISGraph:
    """
    Factory function to create and build a QNWIS graph.

    Args:
        registry: Agent registry
        config: Optional configuration
        observer: Optional metrics observer
        data_client: Optional DataClient for prefetch operations
        cache: Optional DeterministicRedisCache for caching

    Returns:
        Built QNWISGraph instance
    """
    graph = QNWISGraph(
        registry, config, observer=observer, data_client=data_client, cache=cache
    )
    graph.build()
    return graph
