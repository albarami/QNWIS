"""
Format node: Create uniform, PII-safe reports.

This node transforms agent output into a standardized OrchestrationResult
with consistent sections and redacted PII.
"""

from __future__ import annotations

import hashlib
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List

from ...agents.base import AgentReport, Evidence
from ..metrics import MetricsObserver, ensure_observer
from ..schemas import (
    Citation,
    Freshness,
    OrchestrationResult,
    ReportSection,
    Reproducibility,
    WorkflowState,
)
from ..utils import filter_sensitive_params

logger = logging.getLogger(__name__)

# PII patterns to redact. Rule: replace capitalised first+last names, email addresses,
# and identifiers with 10+ digits. Each match is swapped with a deterministic token.
PII_PATTERNS = [
    (re.compile(r"\b[A-Z][a-z]+ [A-Z][a-z]+\b"), "[REDACTED_NAME]"),
    (re.compile(r"\b\d{10,}\b"), "[REDACTED_ID]"),
    (
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
        "[REDACTED_EMAIL]",
    ),
]


def _redact_pii(text: str) -> str:
    """
    Redact PII from text while preserving hashed IDs.

    Args:
        text: Input text

    Returns:
        Text with PII redacted
    """
    result = text
    for pattern, replacement in PII_PATTERNS:
        result = pattern.sub(replacement, result)
    return result


def _hash_id(value: str) -> str:
    """
    Create a consistent hash for IDs.

    Args:
        value: ID value

    Returns:
        Truncated SHA256 hash
    """
    return hashlib.sha256(value.encode()).hexdigest()[:16]


def _parse_iso(value: str) -> datetime | None:
    """
    Parse ISO-8601 timestamps forgivingly.

    Args:
        value: Timestamp string

    Returns:
        A timezone-aware datetime or None if parsing fails.
    """
    try:
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    except (ValueError, TypeError, AttributeError):
        return None


def _format_executive_summary(report: AgentReport) -> ReportSection:
    """
    Create executive summary section.

    Args:
        report: Agent report

    Returns:
        Formatted section
    """
    finding_count = len(report.findings)
    warning_count = len(report.warnings)

    body = f"**Agent**: {report.agent}\n\n"
    body += f"**Findings**: {finding_count}\n\n"

    if warning_count > 0:
        body += f"**Warnings**: {warning_count}\n\n"

    # Add high-level summary from first finding if available
    if report.findings:
        first_finding = report.findings[0]
        body += f"**Primary Insight**: {_redact_pii(first_finding.title)}\n\n"
        body += f"{_redact_pii(first_finding.summary)}\n"

    return ReportSection(title="Executive Summary", body_md=body)


def _format_key_findings(report: AgentReport, max_findings: int = 10) -> ReportSection:
    """
    Create key findings section with metrics table.

    Args:
        report: Agent report
        max_findings: Maximum findings to include

    Returns:
        Formatted section
    """
    body = ""

    for idx, finding in enumerate(report.findings[:max_findings], 1):
        body += f"### {idx}. {_redact_pii(finding.title)}\n\n"
        body += f"{_redact_pii(finding.summary)}\n\n"

        if finding.metrics:
            body += "**Metrics**:\n\n"
            body += "| Metric | Value |\n"
            body += "|--------|-------|\n"
            for key, value in finding.metrics.items():
                # Redact if key suggests PII
                if any(term in key.lower() for term in ["name", "email", "id", "user"]):
                    display_value = f"[REDACTED] ({_hash_id(str(value))})"
                else:
                    display_value = f"{value:.2f}" if isinstance(value, float) else str(value)
                body += f"| {key} | {display_value} |\n"
            body += "\n"

        if finding.confidence_score < 1.0:
            body += f"*Confidence: {finding.confidence_score:.1%}*\n\n"

    if len(report.findings) > max_findings:
        body += f"\n*({len(report.findings) - max_findings} additional findings omitted)*\n"

    return ReportSection(title="Key Findings", body_md=body.strip())


def _format_evidence(report: AgentReport, top_n: int) -> ReportSection:
    """
    Create evidence section with top N citations.

    Args:
        report: Agent report
        top_n: Number of evidence items to include

    Returns:
        Formatted section
    """
    all_evidence: List[Evidence] = []
    for finding in report.findings:
        all_evidence.extend(finding.evidence)

    ordered = sorted(
        (ev for ev in all_evidence if getattr(ev, "query_id", None)),
        key=lambda ev: (ev.dataset_id or "", ev.query_id, ev.locator),
    )

    deduplicated: list[Evidence] = []
    seen_queries: set[str] = set()
    for ev in ordered:
        if ev.query_id in seen_queries:
            continue
        seen_queries.add(ev.query_id)
        deduplicated.append(ev)

    limited = deduplicated[:top_n]

    body = "| Query ID | Dataset | Source | As Of |\n"
    body += "|----------|---------|--------|-------|\n"

    for ev in limited:
        locator = ev.locator.split("/")[-1] if "/" in ev.locator else ev.locator
        as_of = ev.freshness_as_of or "unknown"
        body += f"| `{ev.query_id}` | {ev.dataset_id} | {locator} | {as_of} |\n"

    omitted = len(deduplicated) - len(limited)
    if omitted > 0:
        body += f"\n*({omitted} additional sources omitted)*\n"

    return ReportSection(title="Evidence (Top Sources)", body_md=body.strip())


def _format_citations(report: AgentReport, max_items: int) -> List[Citation]:
    """
    Extract citations from agent report.

    Args:
        report: Agent report

    Returns:
        List of citations
    """
    citations = []
    for finding in report.findings:
        for ev in finding.evidence:
            if not getattr(ev, "query_id", None):
                continue
            citations.append(
                Citation(
                    query_id=ev.query_id,
                    dataset_id=ev.dataset_id,
                    locator=ev.locator,
                    fields=sorted(ev.fields),
                    timestamp=(ev.freshness_updated_at or datetime.utcnow().isoformat()),
                )
            )

    citations.sort(key=lambda c: (c.dataset_id, c.query_id, c.locator))
    return citations[:max_items]


def _format_freshness(report: AgentReport) -> Dict[str, Freshness]:
    """
    Extract freshness metadata from report warnings.

    Args:
        report: Agent report

    Returns:
        Freshness metadata by source
    """
    now = datetime.now(timezone.utc)
    freshness: Dict[str, Freshness] = {}

    for finding in report.findings:
        for ev in finding.evidence:
            dataset_id = getattr(ev, "dataset_id", None)
            as_of = getattr(ev, "freshness_as_of", None)
            if not dataset_id or not as_of:
                continue

            parsed = _parse_iso(as_of)
            age_days = None
            last_updated = as_of
            if parsed is not None:
                delta = now - parsed
                age_days = round(delta.total_seconds() / 86400, 2)
                last_updated = parsed.isoformat()

            freshness[dataset_id] = Freshness(
                source=dataset_id,
                last_updated=last_updated,
                age_days=age_days,
            )

    return freshness


def format_report(
    state: Dict[str, Any],
    formatting_config: Dict[str, Any] | None = None,
    *,
    observer: MetricsObserver | None = None,
) -> Dict[str, Any]:
    """
    Format agent output into standardized OrchestrationResult.

    Args:
        state: Current workflow state

    Returns:
        Updated state with formatted result
    """
    metrics = ensure_observer(observer)
    config = formatting_config or {}
    max_findings = max(1, int(config.get("max_findings", 10) or 10))
    top_evidence = max(1, int(config.get("top_evidence", 5) or 5))
    max_citations = max(1, int(config.get("max_citations", 20) or 20))

    workflow_state = WorkflowState(**state)

    if workflow_state.agent_output is None:
        error_msg = "No agent output to format"
        logger.error(error_msg)
        metrics.increment("agent.format.failure", tags={"reason": "no_output"})
        return {
            **state,
            "error": error_msg,
            "logs": workflow_state.logs + [f"ERROR: {error_msg}"],
        }

    report = workflow_state.agent_output
    task = workflow_state.task

    if task is None:
        error_msg = "No task available for formatting"
        logger.error(error_msg)
        metrics.increment("agent.format.failure", tags={"reason": "no_task"})
        return {
            **state,
            "error": error_msg,
            "logs": workflow_state.logs + [f"ERROR: {error_msg}"],
        }

    logger.info("Formatting report for intent=%s", task.intent)

    try:
        # Create standardized sections
        sections = [
            _format_executive_summary(report),
            _format_key_findings(report, max_findings=max_findings),
            _format_evidence(report, top_n=top_evidence),
        ]

        # Create citations
        citations = _format_citations(report, max_items=max_citations)

        # Create freshness metadata
        freshness = _format_freshness(report)

        # Create reproducibility metadata
        reproducibility = Reproducibility(
            method=(
                f"{workflow_state.metadata.get('agent', 'Unknown')}."
                f"{workflow_state.metadata.get('method', 'unknown')}"
            ),
            params=filter_sensitive_params(task.params),
            timestamp=datetime.utcnow().isoformat(),
        )

        # Combine all warnings
        all_warnings = list(report.warnings)
        if "verification_warnings" in workflow_state.metadata:
            all_warnings.extend(workflow_state.metadata["verification_warnings"])

        # Create result
        result = OrchestrationResult(
            ok=True,
            intent=task.intent,
            sections=sections,
            citations=citations,
            freshness=freshness,
            reproducibility=reproducibility,
            warnings=all_warnings,
            request_id=task.request_id,
        )

        log_entry = (
            f"Report formatted: {len(sections)} sections, {len(citations)} citations, "
            f"{len(freshness)} freshness entries"
        )
        logger.info(log_entry)
        metrics.increment(
            "agent.format.success",
            tags={"intent": task.intent, "warnings": str(bool(all_warnings)).lower()},
        )

        return {
            **state,
            "agent_output": result,
            "logs": workflow_state.logs + [log_entry],
        }

    except Exception as exc:
        logger.exception("Formatting failed")
        error_msg = f"Formatting error: {type(exc).__name__}: {exc}"
        metrics.increment(
            "agent.format.failure",
            tags={"reason": type(exc).__name__},
        )
        return {
            **state,
            "error": error_msg,
            "logs": workflow_state.logs + [f"ERROR: {error_msg}"],
        }
