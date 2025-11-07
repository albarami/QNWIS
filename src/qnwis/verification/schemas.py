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


class CitationRules(BaseModel):
    """
    Citation enforcement rules configuration.

    Attributes:
        allowed_prefixes: List of valid citation source prefixes
        require_query_id: Whether query IDs are required in citations
        query_id_patterns: Regex patterns for matching query IDs
        ignore_years: Skip year patterns (e.g., 2023) in citation checks
        ignore_numbers_below: Ignore numbers below this threshold
        ignore_tokens: List of tokens to ignore (codes, identifiers)
        source_mapping: Maps citation prefixes to data source patterns
        missing_qid_severity: Severity to use when QID is required but missing
        strict_qid_keywords: Keywords that always require QIDs, even if optional globally
        strict_qid_severity: Severity to use when strict keywords trigger
        source_synonyms: Synonyms that normalize to canonical prefixes
        adjacent_bullet_window: Number of adjacent bullet lines to consider for citations
    """

    allowed_prefixes: List[str] = Field(
        default_factory=lambda: [
            "Per LMIS:",
            "According to GCC-STAT:",
            "According to World Bank:",
        ]
    )
    require_query_id: bool = True
    query_id_patterns: List[str] = Field(
        default_factory=lambda: [
            r"\bQID[:=]\s*[A-Za-z0-9_-]{8,}\b",
            r"\bquery_id\s*=\s*[A-Za-z0-9_-]{8,}\b",
        ]
    )
    ignore_years: bool = True
    ignore_numbers_below: float = 1.0
    ignore_tokens: List[str] = Field(
        default_factory=lambda: ["ISO-3166", "NOC", "PO Box", "RFC", "ID"]
    )
    source_mapping: Dict[str, List[str]] = Field(default_factory=dict)
    missing_qid_severity: Severity = "error"
    strict_qid_keywords: List[str] = Field(default_factory=list)
    strict_qid_severity: Severity = "error"
    source_synonyms: Dict[str, List[str]] = Field(
        default_factory=lambda: {
            "According to GCC-STAT:": ["According to GCCSTAT:", "According to GCC STAT:"]
        }
    )
    adjacent_bullet_window: int = 1


class CitationIssue(BaseModel):
    """
    A single citation issue detected during enforcement.

    Attributes:
        code: Issue type code
        message: Human-readable issue description
        severity: Issue severity level
        value_text: The numeric or text value with the issue
        span: Character span [start, end] in the source text
    """

    code: Literal[
        "UNCITED_NUMBER",
        "MALFORMED_CITATION",
        "UNKNOWN_SOURCE",
        "MISSING_QID",
    ]
    message: str
    severity: Severity = "error"
    value_text: str
    span: List[int] = Field(default_factory=list)


class CitationReport(BaseModel):
    """
    Citation enforcement report summarizing all checks.

    Attributes:
        ok: Whether all citation checks passed (no errors)
        total_numbers: Total numeric claims found
        cited_numbers: Number of properly cited claims
        uncited: List of uncited number issues
        malformed: List of malformed citation issues
        missing_qid: List of missing query ID issues
        sources_used: Count of citations by source prefix
        runtime_ms: Execution time in milliseconds for enforcement
    """

    ok: bool
    total_numbers: int
    cited_numbers: int
    uncited: List[CitationIssue] = Field(default_factory=list)
    malformed: List[CitationIssue] = Field(default_factory=list)
    missing_qid: List[CitationIssue] = Field(default_factory=list)
    sources_used: Dict[str, int] = Field(default_factory=dict)
    runtime_ms: float | None = None


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
        citation_report: Citation enforcement report (if run)
    """

    ok: bool
    issues: List[Issue] = Field(default_factory=list)
    redacted_text: Optional[str] = None
    applied_redactions: int = 0
    stats: Dict[str, int] = Field(default_factory=dict)
    summary_md: Optional[str] = None
    redaction_reason_codes: List[str] = Field(default_factory=list)
    citation_report: Optional[CitationReport] = None
