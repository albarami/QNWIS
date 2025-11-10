"""
Verification schemas for Layers 2-4.

Defines Pydantic models for verification rules, issues, and summaries.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

Severity = Literal["info", "warning", "error"]
Unit = Literal["count", "percent", "currency"]


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
    details: dict[str, Any] = Field(default_factory=dict)


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
    allow_names_when_role: list[str] = Field(default_factory=list)


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
    min_value: float | None = None
    max_value: float | None = None
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

    crosschecks: list[CrossCheckRule] = Field(default_factory=list)
    privacy: PrivacyRule = PrivacyRule()
    sanity: list[SanityRule] = Field(default_factory=list)
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

    allowed_prefixes: list[str] = Field(
        default_factory=lambda: [
            "Per LMIS:",
            "According to GCC-STAT:",
            "According to World Bank:",
        ]
    )
    require_query_id: bool = True
    query_id_patterns: list[str] = Field(
        default_factory=lambda: [
            r"\bQID[:=]\s*[A-Za-z0-9_-]{8,}\b",
            r"\bquery_id\s*=\s*[A-Za-z0-9_-]{8,}\b",
        ]
    )
    ignore_years: bool = True
    ignore_numbers_below: float = 1.0
    ignore_tokens: list[str] = Field(
        default_factory=lambda: ["ISO-3166", "NOC", "PO Box", "RFC", "ID"]
    )
    source_mapping: dict[str, list[str]] = Field(default_factory=dict)
    missing_qid_severity: Severity = "error"
    strict_qid_keywords: list[str] = Field(default_factory=list)
    strict_qid_severity: Severity = "error"
    source_synonyms: dict[str, list[str]] = Field(
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
    span: list[int] = Field(default_factory=list)


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
    uncited: list[CitationIssue] = Field(default_factory=list)
    malformed: list[CitationIssue] = Field(default_factory=list)
    missing_qid: list[CitationIssue] = Field(default_factory=list)
    sources_used: dict[str, int] = Field(default_factory=dict)
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
        result_verification_report: Result verification report (if run)
    """

    ok: bool
    issues: list[Issue] = Field(default_factory=list)
    redacted_text: str | None = None
    applied_redactions: int = 0
    stats: dict[str, int] = Field(default_factory=dict)
    summary_md: str | None = None
    redaction_reason_codes: list[str] = Field(default_factory=list)
    citation_report: CitationReport | None = None
    result_verification_report: ResultVerificationReport | None = None


class NumericClaim(BaseModel):
    """
    A numeric claim extracted from narrative text.

    Attributes:
        value_text: Raw text of the numeric value (e.g., "1,234.5")
        value: Normalized numeric value as float
        unit: Unit classification (count, percent, currency)
        span: Character position tuple (start, end)
        sentence: Containing sentence for context
        citation_prefix: Detected citation source prefix (if any)
        query_id: Extracted query ID from citation (if any)
        source_family: Mapped source family (LMIS, GCC-STAT, WorldBank)
    """

    value_text: str
    value: float
    unit: Unit
    span: tuple[int, int]
    sentence: str
    citation_prefix: str | None = None
    query_id: str | None = None
    source_family: str | None = None


class ClaimBinding(BaseModel):
    """
    Result of binding a numeric claim to a QueryResult.

    Attributes:
        claim: The original numeric claim
        matched: Whether claim value was found in a QueryResult
        matched_source_qid: Query ID of the matching source
        matched_location: Path/description of where value was found
        candidate_qids: All source QIDs considered for the binding
        ambiguous: True when multiple sources matched equally (requires agent fix)
        nearest_source_qid: Closest matching QID even if outside tolerances
        nearest_location: Location of the closest value
        nearest_value: Suggested numeric value from data (in display units)
        nearest_diff: Difference between claim and suggested value (display units)
        failure_reason: Optional machine-readable reason for failure (e.g., UNIT_MISMATCH)
        derived_consistent: Result of derived recomputation (True/False/None when not applicable)
        derived_recomputed_value: Value produced by derived recomputation (if available)
    """

    claim: NumericClaim
    matched: bool
    matched_source_qid: str | None = None
    matched_location: str | None = None
    candidate_qids: list[str] = Field(default_factory=list)
    ambiguous: bool = False
    nearest_source_qid: str | None = None
    nearest_location: str | None = None
    nearest_value: float | None = None
    nearest_diff: float | None = None
    failure_reason: str | None = None
    derived_consistent: bool | None = None
    derived_recomputed_value: float | None = None


class VerificationIssue(BaseModel):
    """
    Issue detected during result verification.

    Attributes:
        code: Issue type code
        message: Human-readable description
        severity: Issue severity level
        details: Additional structured context
    """

    code: Literal[
        "CLAIM_UNCITED",
        "CLAIM_NOT_FOUND",
        "ROUNDING_MISMATCH",
        "UNIT_MISMATCH",
        "MATH_INCONSISTENT",
        "AMBIGUOUS_SOURCE",
    ]
    message: str
    severity: Severity
    details: dict[str, str] = Field(default_factory=dict)


class ResultVerificationReport(BaseModel):
    """
    Complete result verification report.

    Attributes:
        ok: Whether all verification checks passed (no errors)
        claims_total: Total numeric claims found
        claims_matched: Number of claims successfully matched to data
        issues: List of verification issues detected
        bindings: List of claim-to-source bindings
        math_checks: Results of math consistency checks
        math_check_details: Metadata describing each math check evaluation
        runtime_ms: Execution time for verification (milliseconds)
    """

    ok: bool
    claims_total: int
    claims_matched: int
    issues: list[VerificationIssue] = Field(default_factory=list)
    bindings: list[ClaimBinding] = Field(default_factory=list)
    math_checks: dict[str, bool] = Field(default_factory=dict)
    math_check_details: dict[str, dict[str, Any]] = Field(default_factory=dict)
    runtime_ms: float | None = None
