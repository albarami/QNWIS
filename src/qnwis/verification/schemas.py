"""
Verification schemas for Layers 2-4.

Defines Pydantic models for verification rules, issues, and summaries.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

Severity = Literal["info", "warning", "error"]


class Issue(BaseModel):
    """
    A single verification issue found during Layers 2-4 checks.

    Attributes:
        layer: Which verification layer detected this issue
        code: Machine-readable issue code
        message: Human-readable issue description
        severity: Issue severity level
        details: Additional structured context
    """

    layer: Literal["L2", "L3", "L4"]
    code: str
    message: str
    severity: Severity
    details: Dict[str, Any] = Field(default_factory=dict)


class CrossCheckRule(BaseModel):
    """
    Cross-check rule for Layer 2 verification.

    Compares metric values between primary and reference data sources
    to detect inconsistencies.

    Attributes:
        metric: Metric name to cross-check
        tolerance_pct: Allowed percentage difference
        prefer: Which source to prefer when differences are found
    """

    metric: str
    tolerance_pct: float = 2.0
    prefer: Literal["LMIS", "MV", "EXT"] = "LMIS"


class PrivacyRule(BaseModel):
    """
    Privacy rule for Layer 3 verification.

    Defines PII redaction policies and RBAC controls.

    Attributes:
        k_anonymity: Minimum group size for k-anonymity
        redact_email: Whether to redact email addresses
        redact_ids_min_digits: Minimum digit count for ID redaction
        allow_names_when_role: Roles that may see names unredacted
    """

    k_anonymity: int = 15
    redact_email: bool = True
    redact_ids_min_digits: int = 10
    allow_names_when_role: List[str] = Field(default_factory=list)


class SanityRule(BaseModel):
    """
    Sanity check rule for Layer 4 verification.

    Validates metric values against expected ranges and constraints.

    Attributes:
        metric: Metric name to validate
        min_value: Minimum allowed value (if any)
        max_value: Maximum allowed value (if any)
        must_be_non_negative: Whether value must be >= 0
        rate_0_1: Whether value must be in [0, 1] range
    """

    metric: str
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    must_be_non_negative: bool = False
    rate_0_1: bool = False


class VerificationConfig(BaseModel):
    """
    Complete verification configuration for Layers 2-4.

    Attributes:
        crosschecks: List of cross-check rules (Layer 2)
        privacy: Privacy rule configuration (Layer 3)
        sanity: List of sanity check rules (Layer 4)
        freshness_max_hours: Maximum data age in hours
    """

    crosschecks: List[CrossCheckRule] = Field(default_factory=list)
    privacy: PrivacyRule = PrivacyRule()
    sanity: List[SanityRule] = Field(default_factory=list)
    freshness_max_hours: int = 72


class VerificationSummary(BaseModel):
    """
    Summary of verification results from all layers.

    Attributes:
        ok: Whether all checks passed (no error-severity issues)
        issues: List of all detected issues
        redacted_text: Text with PII redactions applied (if any)
        applied_redactions: Count of redactions applied
        stats: Issue counts by layer and severity
        summary_md: Markdown summary describing Layer 2-4 outcomes
        redaction_reason_codes: Codes describing why redactions were applied
    """

    ok: bool
    issues: List[Issue] = Field(default_factory=list)
    redacted_text: Optional[str] = None
    applied_redactions: int = 0
    stats: Dict[str, int] = Field(default_factory=dict)
    summary_md: Optional[str] = None
    redaction_reason_codes: List[str] = Field(default_factory=list)
