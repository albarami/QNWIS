"""
QNWIS Orchestration Graph using LangGraph.

This module builds and executes the LangGraph workflow for QNWIS agent orchestration.
The graph routes tasks to agents, validates outputs, and formats results consistently.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Iterable, Literal, List, cast

from langgraph.graph import END, StateGraph

from .nodes import error_handler, format_report, invoke_agent, route_intent, verify_structure
from .registry import AgentRegistry
from .schemas import OrchestrationResult, OrchestrationTask, WorkflowState
from .metrics import MetricsObserver, ensure_observer
from .prefetch import Prefetcher
from .coordination import Coordinator
from .policies import get_policy_for_complexity, DEFAULT_POLICY
from .types import PrefetchSpec
from ..agents.base import DataClient

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
        config: Dict[str, Any] | None = None,
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
    def _default_config() -> Dict[str, Any]:
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
        workflow = StateGraph(Dict[str, Any])

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

    def _router_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Router node wrapper."""
        return route_intent(state, self.registry)

    def _prefetch_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
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
            typed_specs = cast(List[PrefetchSpec], prefetch_specs)
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

    def _invoke_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke node wrapper."""
        timeout_ms = int(self.config.get("timeouts", {}).get("agent_call_ms", 30000))
        retry_cfg = self.config.get("retries", {})
        max_retries = int(retry_cfg.get("agent_call", 1))
        transient: Iterable[str] = retry_cfg.get(
            "transient", ["TimeoutError", "ConnectionError"]
        )
        return invoke_agent(
            state,
            self.registry,
            timeout_ms=timeout_ms,
            observer=self.observer,
            max_retries=max_retries,
            transient_exceptions=transient,
        )

    def _verify_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Verify node wrapper."""
        validation_cfg = self.config.get("validation", {})
        strict = bool(validation_cfg.get("strict", False))
        return verify_structure(
            state,
            strict=strict,
            require_evidence=validation_cfg.get("require_evidence", True),
            require_freshness=validation_cfg.get("require_freshness", True),
            observer=self.observer,
        )

    def _format_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Format node wrapper."""
        formatting_cfg = self.config.get("formatting", {})
        return format_report(state, formatting_config=formatting_cfg, observer=self.observer)

    def _error_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Error handler node wrapper."""
        return error_handler(state, observer=self.observer)

    def _should_proceed(
        self, state: Dict[str, Any]
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
        initial_state: Dict[str, Any] = {
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
    config: Dict[str, Any] | None = None,
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
