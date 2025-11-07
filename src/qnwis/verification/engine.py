"""Verification engine orchestrating Layers 2-4."""

from __future__ import annotations

from collections import Counter

from .layer2_crosschecks import cross_check
from .layer3_policy_privacy import redact
from .layer4_sanity import sanity_checks
from .schemas import Issue, VerificationConfig, VerificationSummary
from ..data.deterministic.models import QueryResult


def _build_summary_md(issues: list[Issue], ok: bool) -> str:
    """Render a compact Markdown summary for Layers 2-4 findings."""
    if not issues:
        return (
            "Status: PASS\n\n"
            "| Layer | Count | Example |\n"
            "| --- | --- | --- |\n"
            "| L2 | 0 | None |\n"
            "| L3 | 0 | None |\n"
            "| L4 | 0 | None |"
        )

    lines = [
        f"Status: {'PASS' if ok else 'ATTENTION REQUIRED'}",
        "",
        "| Layer | Count | Example |",
        "| --- | --- | --- |",
    ]

    for layer in ("L2", "L3", "L4"):
        layer_issues = [issue for issue in issues if issue.layer == layer]
        example = (
            f"{layer_issues[0].code} – {layer_issues[0].message}".replace("|", r"\|")
            if layer_issues
            else "None"
        )
        lines.append(f"| {layer} | {len(layer_issues)} | {example} |")

    return "\n".join(lines)


class VerificationEngine:
    """
    Runs Layers 2-4 verification on top of existing Layer 1 numeric checks.

    Layer 2: Cross-source metric verification
    Layer 3: Privacy/PII redaction and policy enforcement
    Layer 4: Sanity checks (ranges, freshness, consistency)
    """

    def __init__(
        self,
        cfg: VerificationConfig,
        user_roles: list[str] | None = None,
    ) -> None:
        """
        Initialize verification engine.

        Args:
            cfg: Verification configuration
            user_roles: List of user roles for RBAC decisions
        """
        self.cfg = cfg
        self.user_roles = list(user_roles or [])

    def run(
        self,
        narrative_md: str,
        primary: QueryResult,
        references: list[QueryResult],
    ) -> VerificationSummary:
        """
        Execute all verification layers on agent output.

        Args:
            narrative_md: Narrative text (Markdown) from agent
            primary: Primary query result (main data source)
            references: Reference query results (for cross-checking)

        Returns:
            VerificationSummary with all detected issues and redactions
        """
        issues: list[Issue] = []

        # Layer 2: Cross-checks between primary and references
        if self.cfg.crosschecks:
            issues.extend(cross_check(primary, references, self.cfg.crosschecks))

        # Layer 4: Sanity checks on all results (including primary)
        all_results = [primary] + list(references)
        if self.cfg.sanity or self.cfg.freshness_max_hours:
            issues.extend(
                sanity_checks(
                    all_results,
                    self.cfg.sanity,
                    self.cfg.freshness_max_hours,
                )
            )

        # Layer 3: Privacy redaction
        # Skip name redaction if user has appropriate role
        allow_names_roles = set(self.cfg.privacy.allow_names_when_role)
        allow_names = any(role in allow_names_roles for role in self.user_roles)
        redacted_text, applied, pr_issues = redact(
            narrative_md,
            self.cfg.privacy,
            redact_names=not allow_names,
        )
        issues.extend(pr_issues)

        # Summarize issues by layer and severity
        stats: dict[str, int] = Counter(f"{issue.layer}:{issue.severity}" for issue in issues)

        ok = not any(issue.severity == "error" for issue in issues)
        summary_md = _build_summary_md(issues, ok)
        redaction_codes = sorted(
            {issue.code for issue in issues if issue.code.startswith("PII_")}
        )

        return VerificationSummary(
            ok=ok,
            issues=issues,
            redacted_text=redacted_text,
            applied_redactions=applied,
            stats=stats,
            summary_md=summary_md,
            redaction_reason_codes=redaction_codes,
        )

    def run_with_agent_report(
        self,
        narrative_md: str,
        query_results: list[QueryResult],
    ) -> VerificationSummary:
        """
        Alternative entry point when primary/reference distinction is unclear.

        Uses first result as primary, rest as references.

        Args:
            narrative_md: Narrative text from agent
            query_results: All query results (first is primary)

        Returns:
            VerificationSummary with all detected issues
        """
        if not query_results:
            # No data to verify, return empty summary
            return VerificationSummary(
                ok=True,
                issues=[],
                redacted_text=narrative_md,
                applied_redactions=0,
                stats={},
            )

        primary = query_results[0]
        references = query_results[1:] if len(query_results) > 1 else []

        return self.run(narrative_md, primary, references)
