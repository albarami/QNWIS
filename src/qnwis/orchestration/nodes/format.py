"""
Format node: Create uniform, PII-safe reports.

This node transforms agent output into a standardized OrchestrationResult
with consistent sections and redacted PII.
"""

from __future__ import annotations

import hashlib
import logging
import re
from datetime import UTC, datetime
from typing import Any

from ...agents.base import AgentReport, Evidence
from ..metrics import MetricsObserver, ensure_observer
from ..schemas import (
    Citation,
    ConfidenceBreakdown,
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
            parsed = parsed.replace(tzinfo=UTC)
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
    all_evidence: list[Evidence] = []
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


def _format_citations(report: AgentReport, max_items: int) -> list[Citation]:
    """
    Extract citations from agent report.

    Deduplicates by query_id to avoid listing the same source multiple times.

    Args:
        report: Agent report
        max_items: Maximum number of citations to return

    Returns:
        List of deduplicated citations
    """
    citations = []
    seen_queries: set[str] = set()

    for finding in report.findings:
        for ev in finding.evidence:
            if not getattr(ev, "query_id", None):
                continue
            # Deduplicate by query_id
            if ev.query_id in seen_queries:
                continue
            seen_queries.add(ev.query_id)

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


def _format_freshness(report: AgentReport) -> dict[str, Freshness]:
    """
    Extract freshness metadata from report warnings.

    Args:
        report: Agent report

    Returns:
        Freshness metadata by source
    """
    now = datetime.now(UTC)
    freshness: dict[str, Freshness] = {}

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
                min_timestamp=last_updated,
                max_timestamp=last_updated,
            )

    return freshness


def _format_citations_summary(citation_report: dict[str, Any]) -> ReportSection:
    """Create citations summary section from citation report."""
    total = citation_report.get("total_numbers", 0)
    cited = citation_report.get("cited_numbers", 0)
    ok = citation_report.get("ok", False)
    runtime_ms = citation_report.get("runtime_ms")

    sources_used = citation_report.get("sources_used", {}) or {}
    uncited = citation_report.get("uncited", []) or []
    malformed = citation_report.get("malformed", []) or []
    missing_qid = citation_report.get("missing_qid", []) or []

    status = "PASS" if ok else "ATTENTION REQUIRED"
    lines: list[str] = [
        f"**Status**: {status}",
        "",
        f"**Coverage**: {cited}/{total} numeric claims properly cited",
    ]
    if runtime_ms is not None:
        lines.append(f"**Runtime**: {runtime_ms:.1f} ms")
    lines.append("")

    if sources_used:
        lines.append("**Sources Used:**")
        for source, count in sorted(sources_used.items()):
            suffix = "s" if count != 1 else ""
            lines.append(f"- {source} ({count} citation{suffix})")
        lines.append("")

    def _add_issue_examples(title: str, issues: list[dict[str, Any]], fallback: str) -> None:
        if not issues:
            return
        lines.append(f"**{title}** ({len(issues)}):")
        for idx, issue in enumerate(issues[:3], 1):
            value = issue.get("value_text", "N/A")
            message = issue.get("message", fallback)
            lines.append(f"{idx}. `{value}` - {message}")
        if len(issues) > 3:
            lines.append(f"*({len(issues) - 3} more {title.lower()})*")
        lines.append("")

    _add_issue_examples("Uncited Claims", uncited, "Missing citation")
    _add_issue_examples("Missing Query IDs", missing_qid, "QID required")
    _add_issue_examples("Unknown Sources", malformed, "Invalid source")

    tips: list[str] = []
    if uncited:
        tips.append("Add a canonical prefix (Per LMIS, According to GCC-STAT, World Bank) before each statistic.")
    if missing_qid:
        tips.append("Append `QID:` or `query_id=` with the originating query id immediately after the cited sentence.")
    if malformed:
        tips.append("Ensure cited datasets map to LMIS, GCC-STAT, or World Bank QueryResults provided to the workflow.")
    if not tips:
        tips.append("All numeric claims are fully cited and mapped to trusted data sources.")

    lines.append("**Remediation Tips:**")
    for tip in tips:
        lines.append(f"- {tip}")

    body = "\n".join(lines)
    return ReportSection(title="Citations Summary", body_md=body.strip())


def _format_result_verification_summary(
    result_report: dict[str, Any]
) -> ReportSection:
    """Create result verification summary section from result verification report."""
    claims_total = result_report.get("claims_total", 0)
    claims_matched = result_report.get("claims_matched", 0)
    ok = result_report.get("ok", False)
    issues = result_report.get("issues", []) or []
    math_checks = result_report.get("math_checks", {}) or {}

    status = "PASS" if ok else "ATTENTION REQUIRED"
    match_pct = (
        (claims_matched / claims_total * 100) if claims_total > 0 else 0
    )

    lines: list[str] = [
        f"**Status**: {status}",
        "",
        f"**Claims Checked**: {claims_total}",
        f"**Claims Matched**: {claims_matched} ({match_pct:.1f}%)",
    ]

    # Math consistency checks
    if math_checks:
        passed = sum(1 for v in math_checks.values() if v)
        failed = len(math_checks) - passed
        lines.append(f"**Math Checks**: {passed} passed, {failed} failed")
    lines.append("")

    # Issue breakdown
    if issues:
        error_issues = [i for i in issues if i.get("severity") == "error"]
        warning_issues = [i for i in issues if i.get("severity") == "warning"]

        if error_issues:
            lines.append(f"**Errors** ({len(error_issues)}):")
            for idx, issue in enumerate(error_issues[:3], 1):
                code = issue.get("code", "UNKNOWN")
                message = issue.get("message", "No message")
                lines.append(f"{idx}. `{code}` - {message[:80]}")
            if len(error_issues) > 3:
                lines.append(f"*({len(error_issues) - 3} more errors)*")
            lines.append("")

        if warning_issues:
            lines.append(f"**Warnings** ({len(warning_issues)}):")
            for idx, issue in enumerate(warning_issues[:2], 1):
                code = issue.get("code", "UNKNOWN")
                message = issue.get("message", "No message")
                lines.append(f"{idx}. `{code}` - {message[:80]}")
            if len(warning_issues) > 2:
                lines.append(f"*({len(warning_issues) - 2} more warnings)*")
            lines.append("")

    # Remediation tips
    tips: list[str] = []
    issue_codes = {i.get("code") for i in issues}
    if "CLAIM_NOT_FOUND" in issue_codes:
        tips.append(
            "Verify claimed values match actual data. Check for rounding differences."
        )
    if "CLAIM_UNCITED" in issue_codes:
        tips.append(
            "Add citation prefixes (Per LMIS:, According to GCC-STAT:) for all numeric claims."
        )
    if "MATH_INCONSISTENT" in issue_codes:
        tips.append(
            "Ensure percentage groups sum to ~100% and table totals match row sums."
        )
    if not tips:
        tips.append("All numeric claims verified successfully against source data.")

    lines.append("**Remediation Tips:**")
    for tip in tips:
        lines.append(f"- {tip}")

    body = "\n".join(lines)
    return ReportSection(title="Result Verification Summary", body_md=body.strip())


def _format_audit_summary(audit_manifest: dict[str, Any]) -> ReportSection:
    """Create audit summary section from audit manifest."""
    audit_id = audit_manifest.get("audit_id", "unknown")
    created_at = audit_manifest.get("created_at", "unknown")
    data_sources = audit_manifest.get("data_sources", [])
    freshness = audit_manifest.get("freshness", {})
    pack_paths = audit_manifest.get("pack_paths", {})
    digest = audit_manifest.get("digest_sha256", "")
    hmac_present = bool(audit_manifest.get("hmac_sha256"))

    top_sources = data_sources[:3]
    source_lines = []
    for source in top_sources:
        source_freshness = freshness.get(source, "unknown") or "unknown"
        source_lines.append(f"- {source} (as of {source_freshness[:10]})")
    if len(data_sources) > len(top_sources):
        remaining = len(data_sources) - len(top_sources)
        source_lines.append(f"*+{remaining} additional source(s)*")

    evidence_count = sum(1 for key in pack_paths if key.startswith("evidence/"))
    source_count = sum(1 for key in pack_paths if key.startswith("sources/"))
    replay_status = "present" if "replay" in pack_paths else "missing"

    lines: list[str] = [
        f"**Audit ID**: `{audit_id}`",
        f"**Created**: {created_at[:19]}",
        "",
        "**Top Sources:**",
        *(source_lines or ["- none recorded"]),
        "",
        "**Integrity:**",
        f"- SHA-256: `{digest[:32]}...`" if digest else "- SHA-256: unavailable",
        f"- HMAC: {'enabled' if hmac_present else 'not configured'}",
        "",
        "**Artifacts:**",
        f"- Evidence files: {evidence_count}",
        f"- Source descriptors: {source_count}",
        f"- Total files: {len(pack_paths)}",
        f"- Replay stub: {replay_status}",
        "",
        "**Reproducibility:**",
        "Run `reproducibility.py` inside the audit pack to refetch QueryResults.",
    ]

    body = "\n".join(line for line in lines if line is not None)
    return ReportSection(title="Audit Summary", body_md=body.strip())


def _format_confidence_summary(confidence: ConfidenceBreakdown) -> ReportSection:
    """
    Create confidence summary section from confidence breakdown.

    Args:
        confidence: Confidence breakdown with score, band, components, reasons

    Returns:
        Formatted confidence section
    """
    score = confidence.score
    band = confidence.band
    components = confidence.components
    reasons = confidence.reasons

    band_badge = {"GREEN": "[G]", "AMBER": "[A]", "RED": "[R]"}
    badge = band_badge.get(band, "[?]")

    lines: list[str] = [
        f"**Overall Score**: {score}/100 - **{band}** {badge}",
        "",
        f"- Citation coverage: {confidence.coverage:.0%}",
        f"- Freshness health: {confidence.freshness:.0%}",
        "",
        "**Component Breakdown:**",
        "",
        "| Component | Score |",
        "|-----------|-------|",
    ]

    component_labels = {
        "citation": "Citation Coverage",
        "numbers": "Result Verification",
        "cross": "Cross-Source Checks",
        "privacy": "Privacy Compliance",
        "freshness": "Data Freshness",
    }

    for key in ["citation", "numbers", "cross", "privacy", "freshness"]:
        if key in components:
            label = component_labels.get(key, key.title())
            comp_score = components[key]
            lines.append(f"| {label} | {comp_score:.1f} |")

    lines.append("")
    lines.append("**Key Factors:**")
    lines.append("")

    for idx, reason in enumerate(reasons[:5], 1):
        lines.append(f"{idx}. {reason}")

    if len(reasons) > 5:
        lines.append(f"*({len(reasons) - 5} additional factors omitted)*")

    lines.append("")
    lines.append("**Interpretation:**")
    if band == "GREEN":
        lines.append("- High confidence: All verification layers passed with minimal issues.")
        lines.append("- Data quality is excellent and suitable for decision-making.")
    elif band == "AMBER":
        lines.append("- Medium confidence: Some verification issues detected.")
        lines.append("- Review key factors above before making critical decisions.")
    else:  # RED
        lines.append("- Low confidence: Significant verification issues present.")
        lines.append("- This report requires remediation before use in decision-making.")

    body = "\n".join(lines)
    return ReportSection(title="Confidence Assessment", body_md=body.strip())


def format_report(
    state: dict[str, Any],
    formatting_config: dict[str, Any] | None = None,
    *,
    observer: MetricsObserver | None = None,
) -> dict[str, Any]:
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

        # Extract verification results if available
        verification_dict = {}
        redactions_count = 0
        issues_summary = {}

        verification_summary_md = workflow_state.metadata.get(
            "verification_summary_md"
        )
        redaction_reason_codes = workflow_state.metadata.get(
            "verification_redaction_codes", []
        )

        if "verification_ok" in workflow_state.metadata:
            verification_dict = {
                "ok": workflow_state.metadata.get("verification_ok", True),
                "issues_count": workflow_state.metadata.get(
                    "verification_issues_count", 0
                ),
                "stats": workflow_state.metadata.get("verification_stats", {}),
            }
            redactions_count = workflow_state.metadata.get(
                "verification_redactions", 0
            )
            issues_summary = workflow_state.metadata.get("verification_stats", {})

            # Apply redactions to sections if available
            redacted_narrative = workflow_state.metadata.get(
                "verification_narrative_redacted"
            )
            # Add a note about redactions to the executive summary
            if redacted_narrative and redactions_count > 0 and sections:
                sections[0].body_md += (
                    f"\n\n*Note: {redactions_count} PII "
                    f"redaction{'s' if redactions_count > 1 else ''} applied.*"
                )

        if verification_summary_md:
            sections.append(
                ReportSection(
                    title="Verification Summary",
                    body_md=verification_summary_md,
                )
            )

        if redactions_count > 0:
            codes = sorted({code for code in redaction_reason_codes if isinstance(code, str)})
            if not codes and redactions_count:
                codes = ["PII_DETECTED"]
            if codes:
                reasons_body = "\n".join(f"- `{code}`" for code in codes)
                sections.append(
                    ReportSection(
                        title="Redaction Reasons",
                        body_md=reasons_body,
                    )
                )

        # Add citations summary if available
        citation_report = workflow_state.metadata.get("citation_report")
        if citation_report:
            sections.append(_format_citations_summary(citation_report))

        # Add result verification summary if available
        result_verification_report = workflow_state.metadata.get(
            "result_verification_report"
        )
        if result_verification_report:
            sections.append(_format_result_verification_summary(result_verification_report))

        # Add audit summary if available
        audit_manifest = workflow_state.metadata.get("audit_manifest")
        audit_id = workflow_state.metadata.get("audit_id")
        if audit_manifest:
            sections.append(_format_audit_summary(audit_manifest))

        # Add confidence summary if available
        confidence_breakdown_dict = workflow_state.metadata.get("confidence_breakdown")
        confidence_breakdown = None
        if confidence_breakdown_dict:
            try:
                confidence_breakdown = ConfidenceBreakdown.model_validate(
                    confidence_breakdown_dict
                )
                sections.append(_format_confidence_summary(confidence_breakdown))
            except Exception as exc:
                logger.warning("Failed to parse confidence breakdown: %s", exc)

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
            verification=verification_dict,
            redactions_applied=redactions_count,
            issues_summary=issues_summary,
            audit_manifest=audit_manifest,
            audit_id=audit_id,
            confidence=confidence_breakdown,
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
