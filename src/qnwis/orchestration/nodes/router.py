"""
Router node: Validates task intent and resolves routing.

This node performs security checks and ensures the intent is registered
before allowing workflow progression.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from ..registry import AgentRegistry, UnknownIntentError
from ..schemas import WorkflowState

logger = logging.getLogger(__name__)


def route_intent(state: Dict[str, Any], registry: AgentRegistry) -> Dict[str, Any]:
    """
    Validate and route the task intent.

    Args:
        state: Current workflow state
        registry: Agent registry for intent validation

    Returns:
        Updated state with route or error
    """
    workflow_state = WorkflowState(**state)

    if workflow_state.task is None:
        error_msg = "No task provided to router"
        logger.error(error_msg)
        return {
            **state,
            "error": error_msg,
            "logs": workflow_state.logs + [f"ERROR: {error_msg}"],
        }

    task = workflow_state.task
    intent = task.intent

    logger.info("Routing intent=%s request_id=%s", intent, task.request_id)

    try:
        # Validate intent is registered
        if not registry.is_registered(intent):
            raise UnknownIntentError(intent, registry.intents())

        # Log success
        log_entry = f"Routed to intent: {intent}"
        logger.info(log_entry)

        return {
            **state,
            "route": intent,
            "logs": workflow_state.logs + [log_entry],
        }

    except UnknownIntentError as exc:
        logger.error("Unknown intent: %s", exc)
        return {
            **state,
            "error": str(exc),
            "logs": workflow_state.logs + [f"ERROR: {exc}"],
        }
    except Exception as exc:
        logger.exception("Unexpected routing error")
        error_msg = f"Routing failed: {type(exc).__name__}: {exc}"
        return {
            **state,
            "error": error_msg,
            "logs": workflow_state.logs + [f"ERROR: {error_msg}"],
        }
