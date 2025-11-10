"""
Error handler node: Normalize errors into safe OrchestrationResult.

This node catches workflow failures and converts them into structured,
user-safe error responses without exposing stack traces.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from ..metrics import MetricsObserver, ensure_observer
from ..schemas import OrchestrationResult, ReportSection, Reproducibility, WorkflowState
from ..utils import filter_sensitive_params

logger = logging.getLogger(__name__)


def error_handler(
    state: dict[str, Any],
    observer: MetricsObserver | None = None,
) -> dict[str, Any]:
    """
    Convert workflow errors into safe OrchestrationResult.

    Args:
        state: Current workflow state with error

    Returns:
        Updated state with error result
    """
    metrics = ensure_observer(observer)
    workflow_state = WorkflowState(**state)

    error = workflow_state.error or "Unknown error occurred"
    task = workflow_state.task

    logger.error("Handling workflow error: %s", error)

    # Create safe error message (no stack traces)
    safe_error = _sanitize_error(error)

    # Create error report sections
    sections = [
        ReportSection(
            title="Error Summary",
            body_md=f"**Status**: Failed\n\n**Error**: {safe_error}\n",
        ),
        ReportSection(
            title="Execution Log",
            body_md=_format_log(workflow_state.logs),
        ),
    ]

    # Create reproducibility metadata if task available
    reproducibility = Reproducibility(
        method="error_handler",
        params=filter_sensitive_params(task.params) if task else {},
        timestamp=datetime.utcnow().isoformat(),
    )

    # Determine intent (handle None case when using query_text)
    intent_value = "unknown"
    if task and task.intent:
        intent_value = task.intent
    elif workflow_state.route:
        intent_value = workflow_state.route

    # Create error result
    result = OrchestrationResult(
        ok=False,
        intent=intent_value,
        sections=sections,
        citations=[],
        freshness={},
        reproducibility=reproducibility,
        warnings=[safe_error],
        request_id=task.request_id if task else None,
    )

    logger.info("Error result created for request_id=%s", result.request_id)
    metrics.increment(
        "agent.error.handled",
        tags={"intent": result.intent, "has_task": str(task is not None).lower()},
    )

    return {
        **state,
        "agent_output": result,
        "logs": workflow_state.logs + ["Error handled and converted to result"],
    }


def _sanitize_error(error: str) -> str:
    """
    Remove sensitive information from error messages.

    Args:
        error: Raw error message

    Returns:
        Sanitized error message
    """
    # Remove file paths
    import re

    sanitized = re.sub(r"[A-Z]:\\[^\s]+", "[PATH]", error)
    sanitized = re.sub(r"/[^\s]+\.py", "[FILE]", sanitized)

    # Remove line numbers that might expose code structure
    sanitized = re.sub(r"line \d+", "line [N]", sanitized)

    # Truncate if too long
    max_length = 500
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length] + "... (truncated)"

    return sanitized


def _format_log(logs: list[str]) -> str:
    """
    Format execution log for display.

    Args:
        logs: List of log entries

    Returns:
        Formatted log markdown
    """
    if not logs:
        return "*No log entries*"

    body = ""
    for entry in logs[-10:]:  # Show last 10 entries
        body += f"- {entry}\n"

    if len(logs) > 10:
        body = f"*({len(logs) - 10} earlier entries omitted)*\n\n" + body

    return body.strip()
