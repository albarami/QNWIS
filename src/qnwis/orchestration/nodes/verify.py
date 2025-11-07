"""
Verify node: Lightweight structural validation of agent output.

This node checks that the agent output has the expected structure with
required fields. It's a post-agent quality gate.

Now includes Layers 2-4 verification via VerificationEngine.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

from ..metrics import MetricsObserver, ensure_observer

from ...agents.base import AgentReport, Evidence
from ...data.deterministic.models import QueryResult
from ...verification.engine import VerificationEngine
from ...verification.schemas import CitationRules, VerificationConfig
from ..schemas import WorkflowState

logger = logging.getLogger(__name__)

# Cache for verification config
_VERIFICATION_CONFIG: VerificationConfig | None = None
_CITATION_RULES: CitationRules | None = None


def _load_verification_config() -> VerificationConfig | None:
    """
    Load verification config from YAML file (cached).

    Returns:
        VerificationConfig if file exists, None otherwise
    """
    global _VERIFICATION_CONFIG

    if _VERIFICATION_CONFIG is not None:
        return _VERIFICATION_CONFIG

    config_path = Path("src/qnwis/config/verification.yml")
    if not config_path.exists():
        logger.warning("Verification config not found at %s", config_path)
        return None

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)
        _VERIFICATION_CONFIG = VerificationConfig.model_validate(config_data)
        logger.info("Loaded verification config from %s", config_path)
        return _VERIFICATION_CONFIG
    except Exception as exc:
        logger.error("Failed to load verification config: %s", exc)
        return None


def _load_citation_rules() -> CitationRules | None:
    """
    Load citation rules from YAML file (cached).

    Returns:
        CitationRules if file exists, None otherwise
    """
    global _CITATION_RULES

    if _CITATION_RULES is not None:
        return _CITATION_RULES

    config_path = Path("src/qnwis/config/citation.yml")
    if not config_path.exists():
        logger.info("Citation config not found at %s, using defaults", config_path)
        return None

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)
        _CITATION_RULES = CitationRules.model_validate(config_data)
        logger.info("Loaded citation rules from %s", config_path)
        return _CITATION_RULES
    except Exception as exc:
        logger.error("Failed to load citation rules: %s", exc)
        return None


def _extract_query_results_from_evidence(
    report: AgentReport,
    prefetch_cache: Mapping[str, Any] | None,
) -> list[QueryResult]:
    """
    Rehydrate QueryResult objects for verification without new data access.

    Args:
        report: Agent report with findings and evidence.
        prefetch_cache: Cache populated by prefetch node (query_id keyed values).

    Returns:
        List of QueryResult objects in the order they appear in evidence.
    """
    if not prefetch_cache:
        return []

    cache_by_qid: dict[str, QueryResult] = {}
    for value in prefetch_cache.values():
        if isinstance(value, QueryResult):
            cache_by_qid.setdefault(value.query_id, value)

    ordered: list[QueryResult] = []
    seen: set[str] = set()

    for finding in report.findings:
        for evidence in finding.evidence:
            qid = evidence.query_id
            if not qid or qid in seen:
                continue
            cached = cache_by_qid.get(qid)
            if cached is None:
                logger.debug("Prefetch cache missing QueryResult for %s", qid)
                continue
            ordered.append(cached.model_copy(deep=True))
            seen.add(qid)

    return ordered


def verify_structure(
    state: dict[str, Any],
    strict: bool = False,
    *,
    require_evidence: bool = True,
    require_freshness: bool = True,
    observer: MetricsObserver | None = None,
) -> dict[str, Any]:
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
            "error": error_msg,  # Always error on missing output
            "logs": workflow_state.logs + [f"ERROR: {error_msg}"],
        }

    output = workflow_state.agent_output
    warnings: list[str] = []
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

        # Only check freshness if there is evidence to check
        if require_freshness and total_evidence > 0 and not freshness_present:
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
        log_entry = f"Structural verification: {len(warnings)} warning(s)"
        logger.warning(log_entry)
    else:
        log_entry = "Structural verification: PASSED"
        logger.info(log_entry)

    metrics.increment(
        "agent.verify.success",
        tags={"has_warnings": str(bool(warnings)).lower()},
    )
    log_messages = [log_entry]

    # Run Layers 2-4 verification if config is available
    verification_summary = None
    verification_metadata = {}
    verification_error = None

    config = _load_verification_config()
    if config is not None:
        try:
            # Extract narrative text from findings
            narrative_parts = []
            for finding in output.findings:
                narrative_parts.append(f"## {finding.title}\n\n{finding.summary}")
            narrative_md = "\n\n".join(narrative_parts)

            query_results = _extract_query_results_from_evidence(
                output, workflow_state.prefetch_cache
            )

            # Run verification engine
            # Get user roles from task params if available
            user_roles = []
            if workflow_state.task and workflow_state.task.params:
                user_roles = workflow_state.task.params.get("user_roles", [])

            # Load citation rules
            citation_rules = _load_citation_rules()

            engine = VerificationEngine(
                config, user_roles=user_roles, citation_rules=citation_rules
            )

            if query_results:
                verification_summary = engine.run_with_agent_report(
                    narrative_md, query_results
                )
                verification_metadata = {
                    "verification_ok": verification_summary.ok,
                    "verification_issues_count": len(verification_summary.issues),
                    "verification_redactions": verification_summary.applied_redactions,
                    "verification_stats": verification_summary.stats,
                    "verification_issues": [
                        issue.model_dump() for issue in verification_summary.issues
                    ],
                    "verification_narrative_redacted": verification_summary.redacted_text,
                    "verification_available": True,
                }
                # Add citation report if available
                if verification_summary.citation_report:
                    verification_metadata["citation_report"] = (
                        verification_summary.citation_report.model_dump()
                    )
                if verification_summary.summary_md:
                    verification_metadata["verification_summary_md"] = verification_summary.summary_md
                if verification_summary.redaction_reason_codes:
                    verification_metadata[
                        "verification_redaction_codes"
                    ] = verification_summary.redaction_reason_codes
                logger.info(
                    "Verification: %d issues, %d redactions, ok=%s",
                    len(verification_summary.issues),
                    verification_summary.applied_redactions,
                    verification_summary.ok,
                )
                log_messages.append(
                    (
                        "Verification summary attached: "
                        f"{len(verification_summary.issues)} issue(s), "
                        f"{verification_summary.applied_redactions} redaction(s)"
                    )
                )

                # CRITICAL: Fail workflow if verification detects errors
                if not verification_summary.ok:
                    error_issues = [
                        i for i in verification_summary.issues if i.severity == "error"
                    ]
                    error_codes = [f"{i.layer}/{i.code}" for i in error_issues]
                    verification_error = (
                        f"Verification failed with {len(error_issues)} error(s): "
                        f"{', '.join(error_codes)}"
                    )
                    logger.error(verification_error)
                    for issue in error_issues:
                        logger.error(
                            "  [%s] %s: %s", issue.layer, issue.code, issue.message
                        )

            else:
                logger.info(
                    "Verification engine skipped: no prefetched QueryResults available"
                )
                verification_metadata = {"verification_available": False}

        except Exception as exc:
            logger.exception("Verification engine failed")
            verification_error = f"Verification engine exception: {type(exc).__name__}: {exc}"
            warnings.append(verification_error)

    # If verification found errors, fail the workflow
    if verification_error:
        metrics.increment("agent.verify.failure", tags={"reason": "verification_errors"})
        return {
            **state,
            "error": verification_error,
            "logs": workflow_state.logs + log_messages + [f"ERROR: {verification_error}"],
            "metadata": {
                **workflow_state.metadata,
                "verification_warnings": warnings,
                **verification_metadata,
            },
        }

    return {
        **state,
        "logs": workflow_state.logs + log_messages,
        "metadata": {
            **workflow_state.metadata,
            "verification_warnings": warnings,
            **verification_metadata,
        },
    }
