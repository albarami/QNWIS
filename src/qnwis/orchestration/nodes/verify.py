"""
Verify node: Lightweight structural validation of agent output.

This node checks that the agent output has the expected structure with
required fields. It's a post-agent quality gate.

Now includes Layers 2-4 verification via VerificationEngine.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from ..metrics import MetricsObserver, ensure_observer

from ...agents.base import AgentReport, Evidence
from ...data.deterministic.models import QueryResult
from ...verification.engine import VerificationEngine
from ...verification.schemas import CitationRules, CitationReport, VerificationConfig
from ...verification.audit_trail import AuditTrail
from ...verification.audit_utils import redact_text
from ..schemas import WorkflowState
from ..utils import filter_sensitive_params

logger = logging.getLogger(__name__)

# Cache for verification config
_VERIFICATION_CONFIG: VerificationConfig | None = None
_CITATION_RULES: CitationRules | None = None
_RESULT_VERIFICATION_TOLERANCES: dict[str, Any] | None = None
_AUDIT_CONFIG: dict[str, Any] | None = None


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


def _load_result_verification_tolerances() -> dict[str, Any] | None:
    """
    Load result verification tolerances from YAML file (cached).

    Returns:
        Dictionary of tolerances if file exists, None otherwise
    """
    global _RESULT_VERIFICATION_TOLERANCES

    if _RESULT_VERIFICATION_TOLERANCES is not None:
        return _RESULT_VERIFICATION_TOLERANCES

    config_path = Path("src/qnwis/config/result_verification.yml")
    if not config_path.exists():
        logger.info("Result verification config not found at %s", config_path)
        return None

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)
        # Flatten nested config for easier access
        tolerances: dict[str, Any] = {}
        for section, values in config_data.items():
            if isinstance(values, dict):
                tolerances.update(values)
            else:
                tolerances[section] = values
        _RESULT_VERIFICATION_TOLERANCES = tolerances
        logger.info("Loaded result verification tolerances from %s", config_path)
        return _RESULT_VERIFICATION_TOLERANCES
    except Exception as exc:
        logger.error("Failed to load result verification tolerances: %s", exc)
        return None


def _load_audit_config() -> dict[str, Any]:
    """
    Load audit configuration from orchestration.yml (cached).

    Returns:
        Dictionary with audit configuration
    """
    global _AUDIT_CONFIG

    if _AUDIT_CONFIG is not None:
        return _AUDIT_CONFIG

    config_path = Path("src/qnwis/config/orchestration.yml")
    defaults = {
        "persist": True,
        "pack_dir": "./audit_packs",
        "sqlite_path": "./audit/audit.db",
        "hmac_env": "QNWIS_AUDIT_HMAC_KEY",
    }

    if not config_path.exists():
        logger.info("Orchestration config not found, using audit defaults")
        _AUDIT_CONFIG = defaults
        return _AUDIT_CONFIG

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)
        audit_config = config_data.get("audit", {})
        # Merge with defaults
        _AUDIT_CONFIG = {**defaults, **audit_config}
        logger.info("Loaded audit config from %s", config_path)
        return _AUDIT_CONFIG
    except Exception as exc:
        logger.error("Failed to load audit config: %s", exc)
        _AUDIT_CONFIG = defaults
        return _AUDIT_CONFIG


def _build_replay_stub(
    workflow_state: WorkflowState,
    orchestration_meta: dict[str, Any],
    query_results: list[QueryResult],
) -> dict[str, Any]:
    """
    Build replay metadata for offline dry-runs.

    Captures sanitized task parameters, routing decisions, agent call specs,
    and the ordered list of query IDs used in the run.
    """
    task_payload: dict[str, Any] = {}
    if workflow_state.task:
        task = workflow_state.task
        task_payload = {
            "intent": task.intent,
            "query_text": redact_text(task.query_text or "") if task.query_text else None,
            "params": filter_sensitive_params(task.params),
            "request_id": task.request_id,
            "user_id": getattr(task, "user_id", None),
        }

    routing_decision = None
    if workflow_state.routing_decision is not None:
        decision = workflow_state.routing_decision
        if hasattr(decision, "model_dump"):
            routing_decision = decision.model_dump()
        else:
            routing_decision = decision  # type: ignore[assignment]

    agent_calls: list[dict[str, Any]] = []
    agent_output = workflow_state.agent_output
    if isinstance(agent_output, AgentReport):
        evidence_map: list[dict[str, Any]] = []
        for finding in agent_output.findings:
            evidence_qids = sorted(
                {
                    ev.query_id
                    for ev in finding.evidence
                    if isinstance(ev, Evidence) and ev.query_id
                }
            )
            evidence_map.append(
                {
                    "title": redact_text(finding.title),
                    "summary": redact_text(finding.summary),
                    "evidence_query_ids": evidence_qids,
                }
            )

        agent_calls.append(
            {
                "agent": agent_output.agent,
                "findings": evidence_map,
                "warnings": [redact_text(w) for w in agent_output.warnings],
            }
        )

    return {
        "task": task_payload,
        "routing": orchestration_meta.get("routing", {}),
        "routing_decision": routing_decision,
        "agents": orchestration_meta.get("agents", []),
        "agent_calls": agent_calls,
        "cache_stats": orchestration_meta.get("cache_stats", {}),
        "query_ids": [qr.query_id for qr in query_results],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


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

    narrative_parts_raw = [
        f"## {finding.title}\n\n{finding.summary}" for finding in output.findings
    ]
    narrative_md_raw = "\n\n".join(part for part in narrative_parts_raw if part)

    # Run Layers 2-4 verification if config is available
    verification_summary = None
    verification_metadata = {}
    verification_error = None

    query_results = _extract_query_results_from_evidence(
        output, workflow_state.prefetch_cache
    )

    config = _load_verification_config()
    if config is not None:
        try:
            # Run verification engine
            # Get user roles from task params if available
            user_roles = []
            if workflow_state.task and workflow_state.task.params:
                user_roles = workflow_state.task.params.get("user_roles", [])

            # Load citation rules and result verification tolerances
            citation_rules = _load_citation_rules()
            result_tolerances = _load_result_verification_tolerances()

            engine = VerificationEngine(
                config,
                user_roles=user_roles,
                citation_rules=citation_rules,
                result_tolerances=result_tolerances,
            )

            if query_results:
                verification_summary = engine.run_with_agent_report(
                    narrative_md_raw, query_results
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
                # Add result verification report if available
                if verification_summary.result_verification_report:
                    verification_metadata["result_verification_report"] = (
                        verification_summary.result_verification_report.model_dump()
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

    # Generate audit trail (Layer 4) even on WARNING/ERROR to capture provenance
    audit_manifest_dict: dict[str, Any] | None = None
    audit_id: str | None = None

    audit_config = _load_audit_config()
    if audit_config.get("persist") and verification_summary is not None:
        try:
            orchestration_meta = {
                "routing": workflow_state.metadata.get("routing", {}),
                "agents": workflow_state.metadata.get("agents", []),
                "timings": workflow_state.metadata.get("timings", {}),
                "cache_stats": workflow_state.metadata.get("cache_stats", {}),
                "params": filter_sensitive_params(
                    workflow_state.task.params if workflow_state.task else {}
                ),
            }

            code_version = os.environ.get("GIT_COMMIT", "unknown")
            registry_version = os.environ.get("DATA_REGISTRY_VERSION", "v1.0")
            request_id = (
                workflow_state.task.request_id
                if workflow_state.task and workflow_state.task.request_id
                else workflow_state.metadata.get("request_id", "unknown")
            )

            hmac_key = None
            hmac_env = audit_config.get("hmac_env")
            if hmac_env:
                secret = os.environ.get(hmac_env)
                if secret:
                    hmac_key = secret.encode("utf-8")

            audit_trail = AuditTrail(
                pack_dir=audit_config.get("pack_dir", "./audit_packs"),
                sqlite_path=audit_config.get("sqlite_path"),
                hmac_key=hmac_key,
            )

            citation_report = (
                verification_summary.citation_report
                if verification_summary.citation_report
                else CitationReport(ok=True, total_numbers=0, cited_numbers=0)
            )

            manifest = audit_trail.generate_trail(
                response_md=narrative_md_raw,
                qresults=query_results,
                verification=verification_summary,
                citations=citation_report,
                orchestration_meta=orchestration_meta,
                code_version=code_version,
                registry_version=registry_version,
                request_id=request_id,
            )

            replay_stub = _build_replay_stub(
                workflow_state,
                orchestration_meta,
                query_results,
            )

            final_manifest = audit_trail.write_pack(
                manifest=manifest,
                response_md=narrative_md_raw,
                qresults=query_results,
                citations=citation_report,
                result_report=verification_summary.result_verification_report,
                replay_stub=replay_stub,
            )

            audit_manifest_dict = final_manifest.to_dict()
            audit_id = final_manifest.audit_id
            verification_metadata["audit_manifest"] = audit_manifest_dict
            verification_metadata["audit_id"] = audit_id

            logger.info("Generated audit trail: audit_id=%s", audit_id)
            log_messages.append(f"Audit trail generated: {audit_id}")

        except Exception as exc:
            logger.exception("Failed to generate audit trail")
            warnings.append(
                f"Audit trail generation failed: {type(exc).__name__}: {exc}"
            )

    # If verification found errors, fail the workflow but still attach audit metadata
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
