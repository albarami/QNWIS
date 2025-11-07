"""Unit tests for Layer 3 privacy helpers."""

from __future__ import annotations

from src.qnwis.verification.layer3_policy_privacy import (
    check_k_anonymity,
    redact,
)
from src.qnwis.verification.schemas import PrivacyRule


def test_redact_covers_emails_ids_and_names() -> None:
    """Ensure regexes catch emails, numeric IDs, and multi-word names."""
    rule = PrivacyRule(redact_email=True, redact_ids_min_digits=10)
    text = "Contact Ahmed Al Thani via ahmed@example.com, ID 12345678901."

    redacted, count, issues = redact(text, rule)

    assert "[REDACTED_EMAIL]" in redacted
    assert "[REDACTED_ID]" in redacted
    assert "[REDACTED_NAME]" in redacted
    assert count == 3
    codes = {issue.code for issue in issues}
    assert codes == {"PII_EMAIL", "PII_ID", "PII_NAME"}


def test_redact_respects_name_bypass_flag() -> None:
    """Name redaction can be skipped when RBAC allows it."""
    rule = PrivacyRule(redact_email=False, redact_ids_min_digits=0)
    text = "Sara bint Khalid presented the findings."

    redacted, count, issues = redact(text, rule, redact_names=False)

    assert "Sara bint Khalid" in redacted
    assert count == 0
    assert issues == []


def test_k_anonymity_flags_small_groups() -> None:
    """check_k_anonymity emits errors for groups smaller than k."""
    rows = [
        {"sector": "Energy", "gender": "F"},
        {"sector": "Energy", "gender": "M"},
        {"sector": "Health", "gender": "F"},
    ]

    issues = check_k_anonymity(rows, ["sector"], k=3)

    assert len(issues) == 2
    assert all(issue.code == "K_ANONYMITY_VIOLATION" for issue in issues)
