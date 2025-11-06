"""
Invoke node: Execute the agent method with deterministic parameters.

This node calls the resolved agent method using only parameters from the task.
Agents are responsible for their own data access via DataClient.
"""

from __future__ import annotations

import inspect
import logging
import time
from typing import Any, Dict, Iterable

from ..registry import AgentRegistry
from ..schemas import WorkflowState
from ..metrics import MetricsObserver, ensure_observer

logger = logging.getLogger(__name__)


def invoke_agent(
    state: Dict[str, Any],
    registry: AgentRegistry,
    timeout_ms: int = 30000,
    *,
    observer: MetricsObserver | None = None,
    max_retries: int = 1,
    transient_exceptions: Iterable[str] | None = None,
) -> Dict[str, Any]:
    """
    Invoke the agent method with task parameters.

    Args:
        state: Current workflow state
        registry: Agent registry for method resolution
        timeout_ms: Timeout in milliseconds (not enforced, for logging only)
        observer: Metrics observer for counters/timers
        max_retries: Maximum retry attempts for transient failures (1 = one retry)
        transient_exceptions: Iterable of exception class names treated as transient

    Returns:
        Updated state with agent_output or error
    """
    metrics = ensure_observer(observer)
    transient_names = {name for name in (transient_exceptions or ())}

    workflow_state = WorkflowState(**state)

    if workflow_state.route is None:
        error_msg = "No route available for invocation"
        logger.error(error_msg)
        return {
            **state,
            "error": error_msg,
            "logs": workflow_state.logs + [f"ERROR: {error_msg}"],
        }

    route = workflow_state.route
    task = workflow_state.task

    if task is None:
        error_msg = "No task available for invocation"
        logger.error(error_msg)
        return {
            **state,
            "error": error_msg,
            "logs": workflow_state.logs + [f"ERROR: {error_msg}"],
        }

    logger.info(
        "Invoking intent=%s params_keys=%s request_id=%s",
        route,
        list(task.params.keys()),
        task.request_id,
    )

    try:
        # Resolve agent and method
        agent, method_name = registry.resolve(route)
        method = getattr(agent, method_name)

        # Extract method signature for safe parameter passing
        sig = inspect.signature(method)
        valid_params = {}

        call_parameters = {
            name
            for name, param in sig.parameters.items()
            if param.kind
            in {
                inspect.Parameter.POSITIONAL_ONLY,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                inspect.Parameter.KEYWORD_ONLY,
            }
        }
        has_var_kwargs = any(
            param.kind == inspect.Parameter.VAR_KEYWORD for param in sig.parameters.values()
        )

        provided_params = set(task.params.keys())
        if not has_var_kwargs:
            extraneous = sorted(provided_params - call_parameters)
            if extraneous:
                error_msg = (
                    f"Unsupported parameters for {type(agent).__name__}.{method_name}: "
                    f"{', '.join(extraneous)}"
                )
                logger.error(error_msg)
                metrics.increment(
                    "agent.invoke.rejected",
                    tags={"intent": route, "agent": type(agent).__name__},
                )
                return {
                    **state,
                    "error": error_msg,
                    "logs": workflow_state.logs + [f"ERROR: {error_msg}"],
                }

        required_params = {
            name
            for name, param in sig.parameters.items()
            if name in call_parameters and param.default is inspect.Parameter.empty
        }
        missing = sorted(required_params - provided_params)
        if missing:
            error_msg = (
                f"Missing required parameters for {type(agent).__name__}.{method_name}: "
                f"{', '.join(missing)}"
            )
            logger.error(error_msg)
            metrics.increment(
                "agent.invoke.rejected",
                tags={"intent": route, "agent": type(agent).__name__},
            )
            return {
                **state,
                "error": error_msg,
                "logs": workflow_state.logs + [f"ERROR: {error_msg}"],
            }

        valid_params = {}
        for param_name, param in sig.parameters.items():
            # Skip 'self' parameter
            if param_name == "self":
                continue
            if param.kind in (
                inspect.Parameter.VAR_POSITIONAL,
                inspect.Parameter.VAR_KEYWORD,
            ):
                continue

            # Use provided value or default
            if param_name in task.params:
                valid_params[param_name] = task.params[param_name]
            elif param.default is not inspect.Parameter.empty:
                # Use method's default value
                continue
            else:
                # Required parameter not provided
                logger.warning(
                    "Missing required parameter: %s for method %s",
                    param_name,
                    method_name,
                )

        if has_var_kwargs:
            for key, value in task.params.items():
                if key not in valid_params:
                    valid_params[key] = value

        logger.debug(
            "Calling %s.%s with params keys: %s",
            type(agent).__name__,
            method_name,
            sorted(valid_params.keys()),
        )

        attempts_allowed = max(1, int(max_retries) + 1)
        attempt_logs: list[str] = []
        last_error: Exception | None = None  # noqa: F841 - Tracked for potential debugging
        elapsed_ms = 0.0

        for attempt in range(1, attempts_allowed + 1):
            attempt_start = time.perf_counter()
            metrics.increment(
                "agent.invoke.attempt",
                tags={"intent": route, "agent": type(agent).__name__, "attempt": str(attempt)},
            )
            try:
                result = method(**valid_params)
                elapsed_ms = (time.perf_counter() - attempt_start) * 1000
                metrics.increment(
                    "agent.invoke.success",
                    tags={"intent": route, "agent": type(agent).__name__},
                )
                metrics.timing(
                    "agent.invoke.ms",
                    elapsed_ms,
                    tags={"intent": route, "agent": type(agent).__name__},
                )
                break
            except TypeError as exc:
                # Parameter mismatch should never be retried.
                logger.exception("Parameter error invoking agent")
                error_msg = f"Parameter error: {exc}"
                metrics.increment(
                    "agent.invoke.failure",
                    tags={
                        "intent": route,
                        "agent": type(agent).__name__,
                        "reason": "TypeError",
                    },
                )
                return {
                    **state,
                    "error": error_msg,
                    "logs": workflow_state.logs + [f"ERROR: {error_msg}"],
                }
            except Exception as exc:  # pylint: disable=broad-except
                elapsed_ms = (time.perf_counter() - attempt_start) * 1000
                last_error = exc
                exc_name = type(exc).__name__
                attempt_logs.append(
                    f"Attempt {attempt}/{attempts_allowed} failed: {exc_name}: {exc}"
                )
                metrics.increment(
                    "agent.invoke.failure",
                    tags={"intent": route, "agent": type(agent).__name__, "reason": exc_name},
                )
                metrics.timing(
                    "agent.invoke.ms",
                    elapsed_ms,
                    tags={
                        "intent": route,
                        "agent": type(agent).__name__,
                        "outcome": "failure",
                    },
                )
                is_transient = exc_name in transient_names
                if not is_transient or attempt == attempts_allowed:
                    logger.exception("Agent invocation failed")
                    error_msg = f"Agent error: {exc_name}: {exc}"
                    return {
                        **state,
                        "error": error_msg,
                        "logs": workflow_state.logs + [f"ERROR: {error_msg}", *attempt_logs],
                    }

                logger.warning(
                    "Transient agent error (%s). Retrying attempt %d/%d.",
                    exc_name,
                    attempt + 1,
                    attempts_allowed,
                )
                continue
        else:  # pragma: no cover - defensive guard
            error_msg = "Agent invocation completed without result"
            logger.error(error_msg)
            return {
                **state,
                "error": error_msg,
                "logs": workflow_state.logs + [f"ERROR: {error_msg}", *attempt_logs],
            }

        log_entry = (
            f"Agent executed: {type(agent).__name__}.{method_name} "
            f"in {elapsed_ms:.0f}ms after {attempt} attempt(s)"
        )
        logger.info(log_entry)

        if elapsed_ms > timeout_ms:
            logger.warning(
                "Agent execution exceeded timeout: %.0f ms > %d ms",
                elapsed_ms,
                timeout_ms,
            )

        return {
            **state,
            "agent_output": result,
            "logs": workflow_state.logs + [*attempt_logs, log_entry],
            "metadata": {
                **workflow_state.metadata,
                "elapsed_ms": elapsed_ms,
                "agent": type(agent).__name__,
                "method": method_name,
                "attempts": attempt,
            },
        }

    except Exception as exc:  # pragma: no cover - registry resolution failure
        logger.exception("Agent invocation setup failed")
        error_msg = f"Agent error: {type(exc).__name__}: {exc}"
        return {
            **state,
            "error": error_msg,
            "logs": workflow_state.logs + [f"ERROR: {error_msg}"],
        }
