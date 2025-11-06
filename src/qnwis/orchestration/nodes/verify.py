"""
Verify node: Lightweight structural validation of agent output.

This node checks that the agent output has the expected structure with
required fields. It's a post-agent quality gate.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from ..metrics import MetricsObserver, ensure_observer

from ...agents.base import AgentReport
from ..schemas import WorkflowState

logger = logging.getLogger(__name__)


def verify_structure(
    state: Dict[str, Any],
    strict: bool = False,
    *,
    require_evidence: bool = True,
    require_freshness: bool = True,
    observer: MetricsObserver | None = None,
) -> Dict[str, Any]:
    """
    Verify the structural integrity of agent output.

    Args:
        state: Current workflow state
        strict: If True, structural failures raise errors; if False, add warnings
        require_evidence: Enforce that findings include evidence
        require_freshness: Enforce that evidence conveys freshness metadata
        observer: Metrics observer for counters

    Returns:
        Updated state with validation results
    """
    metrics = ensure_observer(observer)
    workflow_state = WorkflowState(**state)

    if workflow_state.agent_output is None:
        error_msg = "No agent output to verify"
        logger.error(error_msg)
        return {
            **state,
            "error": error_msg if strict else None,
            "logs": workflow_state.logs + [f"ERROR: {error_msg}"],
        }

    output = workflow_state.agent_output
    warnings = []
    violations = []

    logger.info("Verifying structural integrity (strict=%s)", strict)

    # Check if output is an AgentReport
    if not isinstance(output, AgentReport):
        msg = f"Agent output is not an AgentReport: {type(output).__name__}"
        logger.error(msg)
        metrics.increment(
            "agent.verify.failure",
            tags={"reason": "invalid_type"},
        )
        return {
            **state,
            "error": msg,
            "logs": workflow_state.logs + [f"ERROR: {msg}"],
        }

    # Validate AgentReport structure
    # Check for findings
    if not output.findings:
        msg = "Agent report has no findings"
        logger.error(msg)
        violations.append(msg)
    else:
        total_evidence = 0
        total_citations = 0
        freshness_present = False

        # Check each finding has required fields
        for idx, finding in enumerate(output.findings):
            if not finding.title:
                msg = f"Finding {idx} missing title"
                logger.error(msg)
                violations.append(msg)

            if not finding.summary:
                msg = f"Finding {idx} missing summary"
                logger.error(msg)
                violations.append(msg)

            if not finding.evidence:
                msg = f"Finding {idx} missing evidence/citations"
                logger.error(msg)
                if require_evidence:
                    violations.append(msg)
                else:
                    warnings.append(msg)
            else:
                total_evidence += len(finding.evidence)
                for eid, ev in enumerate(finding.evidence):
                    total_citations += 1
                    if not getattr(ev, "query_id", None):
                        msg = f"Finding {idx}, evidence {eid} missing query_id"
                        logger.error(msg)
                        violations.append(msg)
                    if not getattr(ev, "dataset_id", None):
                        msg = f"Finding {idx}, evidence {eid} missing dataset_id"
                        logger.error(msg)
                        violations.append(msg)
                    if getattr(ev, "freshness_as_of", None):
                        freshness_present = True
                    if not getattr(ev, "fields", None):
                        warnings.append(
                            f"Finding {idx}, evidence {eid} missing field metadata"
                        )

        if require_evidence and total_evidence == 0:
            msg = "Agent report contains no evidence across findings"
            logger.error(msg)
            violations.append(msg)

        if require_freshness and not freshness_present:
            msg = "Agent report evidence lacks freshness metadata"
            logger.error(msg)
            violations.append(msg)

    # Ensure invocation metadata is present for reproducibility
    if "agent" not in workflow_state.metadata or "method" not in workflow_state.metadata:
        msg = "Invocation metadata missing agent or method for reproducibility"
        logger.error(msg)
        violations.append(msg)

    # Check for agent warnings
    if output.warnings:
        logger.info("Agent reported %d warnings", len(output.warnings))

    # Log verification results
    if violations:
        error_msg = f"Verification failed: {', '.join(violations)}"
        logger.error(error_msg)
        metrics.increment("agent.verify.failure", tags={"reason": "violations"})
        return {
            **state,
            "error": error_msg,
            "logs": workflow_state.logs + [f"ERROR: {error_msg}"],
        }

    if warnings:
        log_entry = f"Structural verification: {len(warnings)} warnings"
        logger.warning(log_entry)
    else:
        log_entry = "Structural verification: PASSED"
        logger.info(log_entry)

    metrics.increment(
        "agent.verify.success",
        tags={"has_warnings": str(bool(warnings)).lower()},
    )

    return {
        **state,
        "logs": workflow_state.logs + [log_entry],
        "metadata": {
            **workflow_state.metadata,
            "verification_warnings": warnings,
        },
    }
