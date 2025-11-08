"""
Confidence Scoring Engine for QNWIS Verification Pipeline.

This module computes a deterministic confidence score (0-100) based on
verification outputs from Layers 2-4, citation enforcement (Step 19),
and result verification (Step 20).

The score is attached to every OrchestrationResult and rendered in reports.
All scoring logic is pure Python, deterministic, and configuration-driven.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

_NEUTRAL_COMPONENT_SCORE = 100.0


def _apply_capped_penalty(
    component: float,
    penalty: float,
    max_fraction: float,
) -> tuple[float, float]:
    """
    Apply a penalty while ensuring it never removes more than the configured fraction.

    Args:
        component: Current component score (0-100).
        penalty: Penalty magnitude to subtract.
        max_fraction: Maximum fraction of the component that a single penalty may remove.

    Returns:
        Tuple of (new_component, applied_penalty).
    """
    if component <= 0.0 or penalty <= 0.0:
        return component, 0.0

    capped_penalty = min(penalty, component * max_fraction)
    new_value = max(0.0, component - capped_penalty)
    return new_value, capped_penalty


def _apply_small_sample_guard(
    component: float,
    sample_size: int,
    threshold: int,
    reasons: list[str],
    label: str,
) -> float:
    """
    Blend the component toward a neutral score when support is below the threshold.

    Args:
        component: Component score before guarding.
        sample_size: Observed count (numbers, claims, etc.).
        threshold: Minimum count required to trust the component fully.
        reasons: Collector for diagnostic reasons (mutated in place).
        label: Human-readable label for the guard reason.

    Returns:
        Guarded component score.
    """
    if threshold <= 0 or sample_size <= 0 or sample_size >= threshold:
        return component

    weight = sample_size / threshold
    guarded = (component * weight) + (_NEUTRAL_COMPONENT_SCORE * (1.0 - weight))
    reasons.append(
        f"Small sample guard: {label}={sample_size} (<{threshold})"
    )
    return guarded


Band = Literal["GREEN", "AMBER", "RED"]


@dataclass
class ConfidenceInputs:
    """
    Inputs for confidence scoring, aggregated from verification layers.

    Attributes:
        total_numbers: Total numeric claims detected (Step 19)
        cited_numbers: Properly cited numeric claims (Step 19)
        citation_errors: Count of citation errors (MALFORMED, UNKNOWN_SOURCE, etc.)
        claims_total: Total claims checked (Step 20)
        claims_matched: Claims that matched source data (Step 20)
        math_checks: Dictionary of math consistency checks {"check_name": passed}
        l2_warnings: Cross-source tolerance violations (Layer 2)
        l3_redactions: PII redactions applied (Layer 3)
        l4_errors: Sanity check errors (negative values, out-of-range) (Layer 4)
        l4_warnings: Sanity warnings (stale data, near-boundary values)
        max_age_hours: Maximum data age across all sources (hours)
        freshness_sla_hours: SLA threshold for freshness warnings
        previous_score: Previous score (for band hysteresis in streaming sessions)
    """

    total_numbers: int = 0
    cited_numbers: int = 0
    citation_errors: int = 0
    claims_total: int = 0
    claims_matched: int = 0
    math_checks: dict[str, bool] | None = None
    l2_warnings: int = 0
    l3_redactions: int = 0
    l4_errors: int = 0
    l4_warnings: int = 0
    max_age_hours: float = 0.0
    freshness_sla_hours: float = 72.0
    previous_score: int | None = None


@dataclass
class ConfidenceRules:
    """
    Configuration-driven rules for confidence scoring.

    Attributes:
        w_citation: Weight for citation component (0.0-1.0)
        w_numbers: Weight for numbers/claims component (0.0-1.0)
        w_cross: Weight for cross-check component (0.0-1.0)
        w_privacy: Weight for privacy component (0.0-1.0)
        w_freshness: Weight for freshness component (0.0-1.0)
        penalty_math_fail: Penalty applied when any math check fails
        penalty_l2_per_item: Penalty per cross-check warning
        penalty_redaction_per_item: Penalty per PII redaction
        penalty_freshness_per_10h: Penalty per 10 hours beyond SLA
        min_score_on_insufficient: Floor score when no evidence available
        bands: Thresholds for GREEN/AMBER/RED bands
        penalty_cap_fraction: Max fraction any penalty may remove
        max_reason_count: Maximum reasons to emit (guard against UI overload)
        enable_hysteresis: Whether to apply band hysteresis
        hysteresis_tolerance: Minimum delta required to change bands when hysteresis
            is enabled
        min_support_numbers: Guard threshold for numeric claims
        min_support_claims: Guard threshold for verified claims
    """

    w_citation: float
    w_numbers: float
    w_cross: float
    w_privacy: float
    w_freshness: float
    penalty_math_fail: float
    penalty_l2_per_item: float
    penalty_redaction_per_item: float
    penalty_freshness_per_10h: float
    min_score_on_insufficient: int
    bands: dict[str, int]
    penalty_cap_fraction: float
    max_reason_count: int
    enable_hysteresis: bool
    hysteresis_tolerance: int
    min_support_numbers: int
    min_support_claims: int


@dataclass
class ConfidenceResult:
    """
    Final confidence scoring result.

    Attributes:
        score: Confidence score (0-100)
        band: Confidence band (GREEN/AMBER/RED)
        components: Per-dimension component scores (0-100)
        reasons: List of human-readable reasons affecting score
        coverage: Coverage ratio for dashboards
        freshness: Freshness score normalized to 0-1
        dashboard_payload: Compact JSON-ready payload for UI hooks
    """

    score: int
    band: Band
    components: dict[str, float]
    reasons: list[str]
    coverage: float
    freshness: float
    dashboard_payload: dict[str, float | str]


def _score_to_band(score: int, bands: dict[str, int]) -> Band:
    """
    Map numeric score to qualitative band.

    Args:
        score: Confidence score
        bands: Threshold configuration

    Returns:
        Band literal
    """
    green = bands.get("GREEN", 90)
    amber = bands.get("AMBER", 75)

    if score >= green:
        return "GREEN"
    if score >= amber:
        return "AMBER"
    return "RED"


def compute_component_citation(
    total_numbers: int,
    cited_numbers: int,
    errors: int,
    *,
    small_sample_threshold: int,
    max_penalty_fraction: float,
) -> tuple[float, list[str]]:
    """
    Compute citation component score (0-100).

    Citation coverage = cited_numbers / total_numbers.
    Any citation errors (malformed, unknown source, etc.) apply a strong penalty.

    Args:
        total_numbers: Total numeric claims detected
        cited_numbers: Properly cited numeric claims
        errors: Count of citation errors

    Returns:
        Tuple of (component_score, reasons)
    """
    reasons: list[str] = []

    if total_numbers == 0:
        reasons.append("No numeric claims detected")
        return 100.0, reasons

    coverage = cited_numbers / max(1, total_numbers)
    component = 100.0 * coverage

    component = _apply_small_sample_guard(
        component=component,
        sample_size=total_numbers,
        threshold=small_sample_threshold,
        reasons=reasons,
        label="numbers",
    )

    if errors > 0:
        # Strong penalty for citation errors (capped by max_penalty_fraction)
        penalty = 100.0
        component, applied = _apply_capped_penalty(
            component=component,
            penalty=penalty,
            max_fraction=max_penalty_fraction,
        )
        reasons.append(f"Citation errors detected: {errors} (-{applied:.1f})")

    if cited_numbers < total_numbers:
        uncited = total_numbers - cited_numbers
        reasons.append(f"Uncited claims: {uncited}/{total_numbers}")

    if cited_numbers == total_numbers and errors == 0:
        reasons.append(f"All {total_numbers} claims properly cited")

    return component, reasons


def compute_component_numbers(
    claims_total: int,
    claims_matched: int,
    math_checks: dict[str, bool] | None,
    penalty_math_fail: float,
    *,
    small_sample_threshold: int,
    max_penalty_fraction: float,
) -> tuple[float, list[str]]:
    """
    Compute numbers/result verification component score (0-100).

    Based on claim matching rate and math consistency checks.

    Args:
        claims_total: Total claims checked
        claims_matched: Claims that matched source data
        math_checks: Dictionary of math consistency checks
        penalty_math_fail: Penalty for failed math checks

    Returns:
        Tuple of (component_score, reasons)
    """
    reasons: list[str] = []

    if claims_total == 0:
        reasons.append("No claims to verify")
        return 100.0, reasons

    match_rate = claims_matched / max(1, claims_total)
    component = 100.0 * match_rate

    component = _apply_small_sample_guard(
        component=component,
        sample_size=claims_total,
        threshold=small_sample_threshold,
        reasons=reasons,
        label="claims",
    )

    # Apply penalty for failed math checks
    if math_checks:
        failed_checks = sorted(name for name, passed in math_checks.items() if not passed)
        if failed_checks:
            component, applied = _apply_capped_penalty(
                component=component,
                penalty=penalty_math_fail,
                max_fraction=max_penalty_fraction,
            )
            reasons.append(
                "Math checks failed ({count}): {names} (-{penalty:.1f})".format(
                    count=len(failed_checks),
                    names=", ".join(failed_checks),
                    penalty=applied,
                )
            )

    if claims_matched < claims_total:
        unmatched = claims_total - claims_matched
        reasons.append(f"Unmatched claims: {unmatched}/{claims_total}")

    if claims_matched == claims_total:
        reasons.append(f"All {claims_total} claims verified")

    return component, reasons


def compute_component_cross(
    l2_warnings: int,
    penalty_per_item: float,
    *,
    max_penalty_fraction: float,
) -> tuple[float, list[str]]:
    """
    Compute cross-check component score (0-100).

    Penalizes cross-source tolerance violations.

    Args:
        l2_warnings: Number of Layer 2 cross-check warnings
        penalty_per_item: Penalty per warning

    Returns:
        Tuple of (component_score, reasons)
    """
    reasons: list[str] = []

    component = 100.0

    if l2_warnings > 0:
        penalty = penalty_per_item * l2_warnings
        component, applied = _apply_capped_penalty(
            component=component,
            penalty=penalty,
            max_fraction=max_penalty_fraction,
        )
        reasons.append(f"Cross-check warnings: {l2_warnings} (-{applied:.1f})")
    else:
        reasons.append("No cross-source discrepancies")

    return component, reasons


def compute_component_privacy(
    redactions: int,
    penalty_per_item: float,
    *,
    max_penalty_fraction: float,
) -> tuple[float, list[str]]:
    """
    Compute privacy component score (0-100).

    Redactions indicate PII was present in narrative. Score scales down gently.

    Args:
        redactions: Number of PII redactions applied
        penalty_per_item: Penalty per redaction

    Returns:
        Tuple of (component_score, reasons)
    """
    reasons: list[str] = []

    component = 100.0

    if redactions > 0:
        penalty = penalty_per_item * redactions
        component, applied = _apply_capped_penalty(
            component=component,
            penalty=penalty,
            max_fraction=max_penalty_fraction,
        )
        reasons.append(f"PII redactions applied: {redactions} (-{applied:.1f})")
    else:
        reasons.append("No PII detected")

    return component, reasons


def compute_component_freshness(
    max_age_hours: float,
    sla_hours: float,
    penalty_per_10h: float,
    *,
    max_penalty_fraction: float,
) -> tuple[float, list[str]]:
    """
    Compute freshness component score (0-100).

    Penalizes data age beyond SLA threshold, per 10-hour bucket.

    Args:
        max_age_hours: Maximum age of data in hours
        sla_hours: SLA threshold in hours
        penalty_per_10h: Penalty per 10 hours beyond SLA

    Returns:
        Tuple of (component_score, reasons)
    """
    reasons: list[str] = []

    if max_age_hours <= 0:
        reasons.append("No freshness metadata reported")
        return 100.0, reasons

    if max_age_hours <= sla_hours:
        reasons.append(f"Data age within SLA: {max_age_hours:.1f}h")
        return 100.0, reasons

    overage_hours = max_age_hours - sla_hours
    buckets = overage_hours / 10.0
    penalty = penalty_per_10h * buckets
    component, applied = _apply_capped_penalty(
        component=100.0,
        penalty=penalty,
        max_fraction=max_penalty_fraction,
    )

    reasons.append(
        f"Data age {max_age_hours:.1f}h exceeds SLA {sla_hours:.1f}h (-{applied:.1f})"
    )

    return component, reasons


def aggregate_confidence(
    ci: ConfidenceInputs,
    rules: ConfidenceRules,
) -> ConfidenceResult:
    """
    Aggregate all component scores into final confidence result.

    Steps:
    1. Compute five components (citation, numbers, cross, privacy, freshness)
    2. Weighted average to get raw score
    3. Handle insufficient evidence case (no numbers & no claims)
    4. Clamp to 0-100, round to int
    5. Map to band via thresholds
    6. Collect and deduplicate reasons

    Args:
        ci: Confidence inputs from verification layers
        rules: Scoring rules from configuration

    Returns:
        ConfidenceResult with score, band, components, and reasons
    """
    # Validate weights sum to ~1.0
    total_weight = (
        rules.w_citation
        + rules.w_numbers
        + rules.w_cross
        + rules.w_privacy
        + rules.w_freshness
    )
    if abs(total_weight - 1.0) > 1e-6:
        raise ValueError(
            f"Weights must sum to 1.0 (got {total_weight:.6f})"
        )

    # Compute components
    citation_score, citation_reasons = compute_component_citation(
        ci.total_numbers,
        ci.cited_numbers,
        ci.citation_errors,
        small_sample_threshold=rules.min_support_numbers,
        max_penalty_fraction=rules.penalty_cap_fraction,
    )

    numbers_score, numbers_reasons = compute_component_numbers(
        ci.claims_total,
        ci.claims_matched,
        ci.math_checks or {},
        rules.penalty_math_fail,
        small_sample_threshold=rules.min_support_claims,
        max_penalty_fraction=rules.penalty_cap_fraction,
    )

    cross_score, cross_reasons = compute_component_cross(
        ci.l2_warnings,
        rules.penalty_l2_per_item,
        max_penalty_fraction=rules.penalty_cap_fraction,
    )

    privacy_score, privacy_reasons = compute_component_privacy(
        ci.l3_redactions,
        rules.penalty_redaction_per_item,
        max_penalty_fraction=rules.penalty_cap_fraction,
    )

    freshness_score, freshness_reasons = compute_component_freshness(
        ci.max_age_hours,
        ci.freshness_sla_hours,
        rules.penalty_freshness_per_10h,
        max_penalty_fraction=rules.penalty_cap_fraction,
    )

    # Build components dict
    components = {
        "citation": citation_score,
        "numbers": numbers_score,
        "cross": cross_score,
        "privacy": privacy_score,
        "freshness": freshness_score,
    }

    # Aggregate reasons
    all_reasons: list[str] = []
    all_reasons.extend(citation_reasons)
    all_reasons.extend(numbers_reasons)
    all_reasons.extend(cross_reasons)
    all_reasons.extend(privacy_reasons)
    all_reasons.extend(freshness_reasons)

    # Check for insufficient evidence
    insufficient_evidence = (ci.total_numbers == 0 and ci.claims_total == 0)

    if insufficient_evidence:
        score = rules.min_score_on_insufficient
        all_reasons.insert(0, "Insufficient evidence: no numeric claims or verifications")
    else:
        # Weighted average
        raw_score = (
            rules.w_citation * citation_score
            + rules.w_numbers * numbers_score
            + rules.w_cross * cross_score
            + rules.w_privacy * privacy_score
            + rules.w_freshness * freshness_score
        )

        # Clamp and round properly
        score = round(max(0.0, min(100.0, raw_score)))

    # Map to band with optional hysteresis
    band: Band = _score_to_band(score, rules.bands)
    if (
        rules.enable_hysteresis
        and ci.previous_score is not None
    ):
        previous_band = _score_to_band(ci.previous_score, rules.bands)
        if previous_band != band:
            delta = abs(ci.previous_score - score)
            if delta < rules.hysteresis_tolerance:
                band = previous_band
                all_reasons.append(
                    f"Band hysteresis applied: delta {delta}<{rules.hysteresis_tolerance}"
                )

    # Deduplicate and sort reasons deterministically
    unique_reasons = sorted({reason for reason in all_reasons if reason})
    max_reasons = max(1, rules.max_reason_count)
    if len(unique_reasons) > max_reasons:
        if max_reasons == 1:
            omitted = len(unique_reasons)
            unique_reasons = [f"... {omitted} factors captured"]
        else:
            omitted = len(unique_reasons) - (max_reasons - 1)
            unique_reasons = unique_reasons[: max_reasons - 1]
            unique_reasons.append(f"... {omitted} additional factor(s)")

    coverage_ratio = (
        1.0
        if ci.total_numbers <= 0
        else max(0.0, min(1.0, ci.cited_numbers / ci.total_numbers))
    )
    freshness_ratio = max(0.0, min(1.0, freshness_score / 100.0))
    dashboard_payload: dict[str, float | str] = {
        "score": float(score),  # Cast int to float for type compatibility
        "band": band,
        "coverage": round(coverage_ratio, 4),
        "freshness": round(freshness_ratio, 4),
    }

    return ConfidenceResult(
        score=score,
        band=band,
        components=components,
        reasons=unique_reasons,
        coverage=coverage_ratio,
        freshness=freshness_ratio,
        dashboard_payload=dashboard_payload,
    )
