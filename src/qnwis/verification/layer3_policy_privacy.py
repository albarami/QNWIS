"""Layer 3: Privacy and policy enforcement."""

from __future__ import annotations

import re
from typing import Any

from .schemas import Issue, PrivacyRule

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
ID_RE = re.compile(r"\b\d{10,}\b")
NAME_RE = re.compile(
    r"\b("
    r"[A-Z][a-z]+"
    r"(?:\s+(?:(?i:(?:bin|bint|al|al-))[\s-]+)?[A-Z][a-z]+){1,3}"
    r")\b"
)


def redact(
    text: str,
    rule: PrivacyRule,
    *,
    redact_names: bool = True,
) -> tuple[str, int, list[Issue]]:
    """
    Redact PII from text according to privacy rules.

    Applies pattern-based redactions for:
    - Email addresses (if enabled)
    - Numeric IDs (10+ digits)
    - Capitalized names (pattern-based, configurable)

    Args:
        text: Input text to redact.
        rule: Privacy rule configuration.
        redact_names: Whether to apply the name redaction pattern.

    Returns:
        Tuple of (redacted_text, redaction_count, issues)
    """
    issues: list[Issue] = []
    redactions = 0
    out = text or ""

    # Email redaction
    if rule.redact_email:
        out, n = EMAIL_RE.subn("[REDACTED_EMAIL]", out)
        redactions += n
        if n:
            issues.append(
                Issue(
                    layer="L3",
                    code="PII_EMAIL",
                    message=f"Redacted {n} email address{'es' if n > 1 else ''}",
                    severity="warning",
                    details={"count": n},
                )
            )

    # Numeric ID redaction (configurable minimum digits)
    if rule.redact_ids_min_digits > 0:
        pattern = re.compile(rf"\b\d{{{rule.redact_ids_min_digits},}}\b")
        out, n = pattern.subn("[REDACTED_ID]", out)
        redactions += n
        if n:
            issues.append(
                Issue(
                    layer="L3",
                    code="PII_ID",
                    message=f"Redacted {n} numeric ID{'s' if n > 1 else ''}",
                    severity="warning",
                    details={"count": n, "min_digits": rule.redact_ids_min_digits},
                )
            )

    if redact_names:
        out, n = NAME_RE.subn("[REDACTED_NAME]", out)
        redactions += n
        if n:
            issues.append(
                Issue(
                    layer="L3",
                    code="PII_NAME",
                    message=f"Redacted {n} name{'s' if n > 1 else ''}",
                    severity="warning",
                    details={"count": n},
                )
            )

    return out, redactions, issues


def check_k_anonymity(
    data_rows: list[dict[str, Any]],
    groupby_fields: list[str],
    k: int = 15,
) -> list[Issue]:
    """
    Check k-anonymity constraint on grouped data.

    Ensures that any group defined by groupby_fields has at least k members.

    Args:
        data_rows: List of data rows to check
        groupby_fields: Fields to group by for anonymity check
        k: Minimum group size

    Returns:
        List of k-anonymity violation issues
    """
    issues: list[Issue] = []

    if not data_rows or not groupby_fields:
        return issues

    # Count group sizes
    groups: dict[tuple[Any, ...], int] = {}
    for row in data_rows:
        key = tuple(row.get(field) for field in groupby_fields)
        groups[key] = groups.get(key, 0) + 1

    # Check violations
    violations = {k_: v for k_, v in groups.items() if v < k}

    if violations:
        for group_key, count in violations.items():
            group_desc = ", ".join(
                f"{field}={val}" for field, val in zip(groupby_fields, group_key)
            )
            issues.append(
                Issue(
                    layer="L3",
                    code="K_ANONYMITY_VIOLATION",
                    message=f"Group ({group_desc}) has only {count} members, requires {k}",
                    severity="error",
                    details={
                        "group": dict(zip(groupby_fields, group_key)),
                        "count": count,
                        "required": k,
                    },
                )
            )

    return issues
