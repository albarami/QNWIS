"""
Result verification engine for validating numeric claims against QueryResult data.

Enhancements:
- Segment-aware row selection (sector/company context)
- Ambiguity + rounding/unit diagnostics with retry hints
- Derived share recomputation for derived_* QueryResults
- Math checks cover percentage bullet groups and Markdown totals
- Runtime tracking to enforce <5s budget on large narratives
"""

from __future__ import annotations

import logging
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from math import isnan
from time import perf_counter
from typing import Any

from ..data.deterministic.models import QueryResult
from .number_extractors import extract_numeric_claims
from .schemas import (
    ClaimBinding,
    NumericClaim,
    ResultVerificationReport,
    VerificationIssue,
)

logger = logging.getLogger(__name__)

DEFAULT_SEGMENT_FIELDS = [
    "sector",
    "industry",
    "company",
    "employer",
    "segment",
    "country",
]
PERCENT_FIELD_HINTS = ("percent", "share", "rate", "ratio", "pp")
TABLE_LINE_PATTERN = re.compile(r"^\s*\|.*\|\s*$")
TABLE_SEPARATOR_PATTERN = re.compile(r"^\s*\|?\s*:?-{3,}.*$")
TOTAL_ROW_PATTERN = re.compile(r"^\s*(grand\s+)?total\b", re.IGNORECASE)


@dataclass
class NumericCell:
    """
    Represents a numeric cell encountered during binding (match or near miss).
    """

    qresult: QueryResult
    location: str
    row_index: int | None
    field_name: str | None
    row_data: dict[str, Any] | None
    raw_value: float
    display_value: float
    diff: float
    display_diff: float
    abs_epsilon: float


def _has_percent_token(value_text: str) -> bool:
    """Return True when the raw value text explicitly refers to percentages."""
    lowered = value_text.lower()
    return any(token in lowered for token in ["%", "percent", "pp"])


def _resolve_abs_epsilon(unit: str, tolerances: dict[str, float]) -> float:
    """Resolve absolute epsilon per unit type (counts, percent, currency)."""
    base = tolerances.get("abs_epsilon", 0.5)
    if unit == "percent":
        return tolerances.get("epsilon_pct", base)
    if unit == "currency":
        return tolerances.get("epsilon_amount", base)
    return base


def _to_percent_ratio(value: float) -> float:
    """Normalize percent values into [0, 1] ratio for comparisons."""
    if value > 1.0:
        return value / 100.0
    return value


def _values_close(
    claim: NumericClaim,
    candidate_value: float,
    abs_epsilon: float,
    rel_epsilon: float,
) -> tuple[bool, float]:
    """
    Compare claim vs candidate with unit-aware tolerances.

    Returns tuple (matched, diff_in_comparison_units).
    """
    claim_cmp = claim.value
    candidate_cmp = candidate_value
    epsilon_cmp = abs_epsilon

    if claim.unit == "percent":
        claim_cmp = _to_percent_ratio(claim.value)
        candidate_cmp = _to_percent_ratio(candidate_value)
        epsilon_cmp = abs_epsilon / 100.0

    diff = abs(claim_cmp - candidate_cmp)
    if diff <= epsilon_cmp:
        return True, diff

    if abs(claim_cmp) > epsilon_cmp and diff / abs(claim_cmp) <= rel_epsilon:
        return True, diff

    return False, diff


def _to_display_units(
    claim: NumericClaim,
    value: float,
    *,
    from_dataset: bool,
) -> float:
    """
    Convert numeric value into the units the user expects from the claim text.
    """
    if claim.unit != "percent":
        return value

    text = claim.value_text.lower()
    explicit_percent = _has_percent_token(text)

    if explicit_percent:
        if from_dataset and value <= 1.0:
            return value * 100.0
        return value

    # When the claim omitted "%" treat values <= 1 as ratio, >1 as points.
    if from_dataset and value > 1.0 and claim.value <= 1.0:
        return value / 100.0
    return value


def _format_value_for_hint(claim: NumericClaim, value: float) -> str:
    """Format numeric value with contextual units for retry hints."""
    display = value
    if claim.unit == "percent":
        display = round(value, 2)
        return f"{display:.2f}%"

    if claim.unit == "currency":
        text = claim.value_text.lower()
        currency = "QAR" if "qar" in text else "USD" if "usd" in text else ""
        if currency:
            return f"{currency} {display:,.0f}"
        return f"{display:,.0f}"

    if claim.unit == "count":
        return f"{display:,.0f}"

    return f"{display:.3f}"


def _units_compatible(claim_unit: str, result_unit: str | None) -> bool:
    """Best-effort compatibility check using declared result unit metadata."""
    if not result_unit or result_unit == "unknown":
        return True

    normalized = result_unit.lower()
    if claim_unit == "count":
        return normalized in ("count", "rows", "records")
    if claim_unit == "percent":
        return "percent" in normalized or "rate" in normalized or normalized == "%"
    if claim_unit == "currency":
        return any(code in normalized for code in ["qar", "usd", "currency"])
    return True


def _detect_segment_rows(
    sentence: str,
    qresult: QueryResult,
    segment_fields: Sequence[str],
) -> set[int] | None:
    """
    Restrict search to rows whose segment labels (sector/company/etc.)
    appear in the claim sentence.
    """
    if not sentence or not segment_fields:
        return None

    sentence_lower = sentence.lower()
    matched: set[int] = set()
    for idx, row in enumerate(qresult.rows):
        data = getattr(row, "data", {})
        if not isinstance(data, dict):
            continue
        for field in segment_fields:
            value = data.get(field)
            if not isinstance(value, str):
                continue
            value_lower = value.strip().lower()
            if len(value_lower) < 3:
                continue
            if re.search(rf"\b{re.escape(value_lower)}\b", sentence_lower):
                matched.add(idx)
                break

    return matched or None


def _iterate_row_cells(
    qresult: QueryResult,
    claim: NumericClaim,
    abs_epsilon: float,
    rel_epsilon: float,
    allowed_rows: set[int] | None,
    claim_display_value: float,
) -> Iterable[tuple[bool, NumericCell]]:
    """
    Yield tuples (matched, cell) for each numeric cell (row_count + data fields).
    """
    # Row count check for count claims
    if claim.unit == "count":
        row_count = len(qresult.rows)
        matched, diff = _values_close(claim, float(row_count), abs_epsilon, rel_epsilon)
        display_value = _to_display_units(claim, float(row_count), from_dataset=True)
        cell = NumericCell(
            qresult=qresult,
            location="row_count",
            row_index=None,
            field_name=None,
            row_data=None,
            raw_value=float(row_count),
            display_value=display_value,
            diff=diff,
            display_diff=abs(claim_display_value - display_value),
            abs_epsilon=abs_epsilon,
        )
        yield matched, cell

    for idx, row in enumerate(qresult.rows):
        if allowed_rows is not None and idx not in allowed_rows:
            continue

        data = getattr(row, "data", None)
        if not isinstance(data, dict):
            continue

        for field_name, field_value in data.items():
            if not isinstance(field_value, (int, float)):
                continue
            if isinstance(field_value, bool):
                continue
            if isinstance(field_value, float) and isnan(field_value):
                continue

            raw_value = float(field_value)
            matched, diff = _values_close(claim, raw_value, abs_epsilon, rel_epsilon)
            display_value = _to_display_units(
                claim,
                raw_value,
                from_dataset=True,
            )
            cell = NumericCell(
                qresult=qresult,
                location=f"data[{idx}].{field_name}",
                row_index=idx,
                field_name=field_name,
                row_data=data,
                raw_value=raw_value,
                display_value=display_value,
                diff=diff,
                display_diff=abs(claim_display_value - display_value),
                abs_epsilon=abs_epsilon,
            )
            yield matched, cell


def _select_candidate_sources(
    claim: NumericClaim,
    qresults: list[QueryResult],
    prefer_query_id: bool,
) -> tuple[list[QueryResult], bool]:
    """
    Determine which QueryResults should be searched first.

    Returns tuple (candidate_sources, locked_to_query_id).
    """
    if claim.query_id and prefer_query_id:
        exact = [qr for qr in qresults if qr.query_id == claim.query_id]
        if exact:
            return exact, True

    if claim.source_family:
        family = claim.source_family.lower()
        preferred = [
            qr
            for qr in qresults
            if family in qr.provenance.dataset_id.lower()
            or family.replace("-", "") in qr.provenance.dataset_id.lower()
        ]
        if preferred:
            return preferred, False

    return qresults, False


def bind_claim_to_sources(
    claim: NumericClaim,
    qresults: list[QueryResult],
    tolerances: dict[str, float],
) -> ClaimBinding:
    """
    Bind a numeric claim to QueryResult sources with ambiguity + rounding metadata.
    """
    abs_epsilon = _resolve_abs_epsilon(claim.unit, tolerances)
    rel_epsilon = float(tolerances.get("rel_epsilon", 0.01))
    segment_fields_raw = tolerances.get("segment_fields", DEFAULT_SEGMENT_FIELDS)
    segment_fields = (
        segment_fields_raw if isinstance(segment_fields_raw, list) else DEFAULT_SEGMENT_FIELDS
    )
    prefer_query_id_raw = tolerances.get("prefer_query_id", True)
    prefer_query_id = bool(prefer_query_id_raw)

    binding = ClaimBinding(claim=claim, matched=False)
    claim_display_value = _to_display_units(claim, claim.value, from_dataset=False)

    candidate_sources, locked_to_qid = _select_candidate_sources(
        claim, qresults, prefer_query_id
    )

    if locked_to_qid and candidate_sources:
        primary_unit = candidate_sources[0].unit
        if not _units_compatible(claim.unit, primary_unit):
            binding.failure_reason = "UNIT_MISMATCH"
            binding.candidate_qids = [candidate_sources[0].query_id]
            return binding

    matches: list[NumericCell] = []
    near_candidate: NumericCell | None = None

    for qr in candidate_sources:
        allowed_rows = _detect_segment_rows(claim.sentence, qr, segment_fields)
        for matched, cell in _iterate_row_cells(
            qr,
            claim,
            abs_epsilon,
            rel_epsilon,
            allowed_rows,
            claim_display_value,
        ):
            if matched:
                matches.append(cell)
            else:
                if near_candidate is None or cell.display_diff < near_candidate.display_diff:
                    near_candidate = cell

    if near_candidate:
        binding.nearest_source_qid = near_candidate.qresult.query_id
        binding.nearest_location = near_candidate.location
        binding.nearest_value = near_candidate.display_value
        binding.nearest_diff = near_candidate.display_diff

    if not matches:
        if near_candidate:
            rounding_window = max(near_candidate.abs_epsilon * 2.0, 1e-9)
            if near_candidate.display_diff <= rounding_window:
                binding.failure_reason = "ROUNDING_MISMATCH"
                return binding

        if locked_to_qid and candidate_sources:
            binding.candidate_qids = [candidate_sources[0].query_id]
        binding.failure_reason = "CLAIM_NOT_FOUND"
        return binding

    unique_qids = sorted({cell.qresult.query_id for cell in matches})
    binding.candidate_qids = unique_qids
    if len(unique_qids) > 1 and not claim.query_id:
        binding.failure_reason = "AMBIGUOUS_SOURCE"
        binding.ambiguous = True
        return binding

    # Select best candidate (row_count priority, else smallest diff)
    best = next((cell for cell in matches if cell.location == "row_count"), None)
    if not best:
        best = min(matches, key=lambda cell: cell.display_diff)

    binding.matched = True
    binding.matched_source_qid = best.qresult.query_id
    binding.matched_location = best.location

    # Derived consistency: recompute share-of-total when applicable
    if best.qresult.query_id.startswith("derived_"):
        derived_enabled_raw = tolerances.get("derived_share_check_enabled", True)
        derived_enabled = bool(derived_enabled_raw)
        derived_outcome = _verify_derived_share(
            claim, best, derived_enabled, tolerances
        )
        if derived_outcome is not None:
            consistent, recomputed_value = derived_outcome
            binding.derived_consistent = consistent
            binding.derived_recomputed_value = recomputed_value

    return binding


def _looks_like_percent_field(field_name: str) -> bool:
    """Heuristic check for percent/share column names."""
    lower = field_name.lower()
    return any(token in lower for token in PERCENT_FIELD_HINTS)


def _verify_derived_share(
    claim: NumericClaim,
    cell: NumericCell,
    enabled: bool,
    tolerances: dict[str, float],
) -> tuple[bool, float | None] | None:
    """
    Recompute percent/share derived values from row components when possible.

    Returns tuple (consistent, recomputed_value) or None when not applicable.
    """
    if not enabled or not cell.field_name or not cell.row_data:
        return None

    if claim.unit != "percent" and "percent" not in cell.field_name.lower():
        return None

    numeric_components: dict[str, float] = {}
    for key, value in cell.row_data.items():
        if key == cell.field_name:
            continue
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            continue
        numeric_components[key] = float(value)

    base_components = {
        key: val for key, val in numeric_components.items() if not _looks_like_percent_field(key)
    }

    min_components = int(tolerances.get("derived_share_min_components", 2))
    if len(base_components) < min_components:
        return None

    total = sum(base_components.values())
    if total <= 0:
        return None

    epsilon_pct = tolerances.get("epsilon_pct", 0.5)
    claim_percent = (
        claim.value if _has_percent_token(claim.value_text) else claim.value * 100.0
    )

    closest_field = None
    closest_diff = None
    closest_value = None

    for key, value in base_components.items():
        share = (value / total) * 100.0
        diff = abs(share - claim_percent)
        if diff <= epsilon_pct:
            return True, share

        if closest_diff is None or diff < closest_diff:
            closest_diff = diff
            closest_field = key
            closest_value = share

    if closest_field is None:
        return None

    logger.debug(
        "Derived share mismatch: field=%s claim=%s recomputed=%.2f",
        closest_field,
        claim.value_text,
        closest_value,
    )
    return False, closest_value


def _parse_numeric_cell(cell_text: str) -> float | None:
    """Parse numeric value from Markdown table cell."""
    text = cell_text.strip()
    if not text:
        return None

    text = re.sub(r"(QAR|USD|SAR)\s*", "", text, flags=re.IGNORECASE)
    text = text.replace(",", "")
    text = text.replace("%", "")
    text = text.replace("pp", "")

    try:
        return float(text)
    except ValueError:
        return None


def _extract_table_blocks(lines: list[str]) -> list[tuple[int, list[str]]]:
    """
    Identify Markdown table blocks and return list of (start_index, block_lines).
    """
    tables: list[tuple[int, list[str]]] = []
    i = 0
    while i < len(lines) - 1:
        if TABLE_LINE_PATTERN.match(lines[i]) and TABLE_SEPARATOR_PATTERN.match(lines[i + 1]):
            start = i
            block: list[str] = [lines[i], lines[i + 1]]
            i += 2
            while i < len(lines) and TABLE_LINE_PATTERN.match(lines[i]):
                block.append(lines[i])
                i += 1
            if len(block) > 2:
                tables.append((start, block))
        else:
            i += 1
    return tables


def check_math_consistency(
    narrative_md: str,
    tolerances: dict[str, float],
) -> tuple[dict[str, bool], dict[str, dict[str, Any]]]:
    """
    Run math consistency checks on narrative text.

    Returns tuple (check_results, check_details).
    """
    checks: dict[str, bool] = {}
    details: dict[str, dict[str, Any]] = {}
    epsilon_pct = tolerances.get("epsilon_pct", 0.5)
    abs_epsilon = tolerances.get("abs_epsilon", 0.5)
    sum_to_100 = tolerances.get("sum_to_100", True)

    lines = narrative_md.split("\n")
    i = 0
    while sum_to_100 and i < len(lines):
        line = lines[i].strip()
        if line.startswith(("-", "*", "+")) and ("%" in line or "percent" in line.lower()):
            percentages: list[float] = []
            start_idx = i
            while i < len(lines):
                current = lines[i].strip()
                if not current.startswith(("-", "*", "+")):
                    break
                match = re.search(r"([-+]?\d+(?:\.\d+)?)\s*%", current)
                if match:
                    percentages.append(float(match.group(1)))
                i += 1

            if len(percentages) >= 2:
                total = sum(percentages)
                passes = abs(total - 100.0) <= epsilon_pct
                check_name = f"percent_sum_L{start_idx + 1}"
                checks[check_name] = passes
                details[check_name] = {
                    "sum": total,
                    "expected": 100.0,
                    "values": percentages,
                    "tolerance": epsilon_pct,
                }
        else:
            i += 1

    # Markdown table totals
    tables = _extract_table_blocks(lines)
    for start_idx, block in tables:
        parsed_rows = [
            [cell.strip() for cell in row.strip().strip("|").split("|")]
            for row in block
        ]
        header = parsed_rows[0]
        data_rows = parsed_rows[2:]  # skip header + separator
        if not data_rows:
            continue

        total_row_idx = next(
            (idx for idx, row in enumerate(data_rows) if TOTAL_ROW_PATTERN.match(row[0])),
            None,
        )
        if total_row_idx is None:
            continue

        total_row = data_rows[total_row_idx]
        numeric_columns = range(1, len(total_row))

        for col_idx in numeric_columns:
            total_value = _parse_numeric_cell(total_row[col_idx])
            if total_value is None:
                continue

            column_cells = [
                _parse_numeric_cell(row[col_idx])
                for idx, row in enumerate(data_rows)
                if idx != total_row_idx
            ]
            if any(value is None for value in column_cells):
                continue

            sum_value = sum(cell for cell in column_cells if cell is not None)
            column_header = header[col_idx] if col_idx < len(header) else f"col_{col_idx}"
            tolerance = epsilon_pct if "%" in total_row[col_idx] else abs_epsilon
            passes = abs(sum_value - total_value) <= tolerance

            check_name = f"table_total_L{start_idx + total_row_idx + 3}_C{col_idx + 1}"
            checks[check_name] = passes
            details[check_name] = {
                "sum": sum_value,
                "expected": total_value,
                "column": column_header.strip(),
                "tolerance": tolerance,
            }

    return checks, details


def _issue_hint_from_binding(binding: ClaimBinding, claim: NumericClaim) -> str | None:
    """Construct retry hint string based on binding metadata."""
    if binding.nearest_value is not None:
        formatted = _format_value_for_hint(claim, binding.nearest_value)
        qid = binding.nearest_source_qid or binding.matched_source_qid or "unknown"
        return f"Replace {claim.value_text} with {formatted} (QID: {qid})"

    if binding.ambiguous and binding.candidate_qids:
        joined = ", ".join(binding.candidate_qids[:3])
        return f"Specify a query_id (candidates: {joined})"

    return None


def _issue_from_math_detail(check_name: str, detail: dict[str, Any]) -> dict[str, str]:
    """Build issue details (including hint) for math check failures."""
    hint = None
    if "expected" in detail and "sum" in detail:
        hint = f"Adjust values to reach {detail['expected']:.1f} (current {detail['sum']:.1f})"

    detail_dict = {
        "check": check_name,
        "expected": f"{detail.get('expected')}",
        "actual": f"{detail.get('sum')}",
    }
    if hint:
        detail_dict["hint"] = hint
    return detail_dict


def verify_numbers(
    narrative_md: str,
    qresults: list[QueryResult],
    tolerances: dict[str, float],
) -> ResultVerificationReport:
    """
    Verify numeric claims in narrative against QueryResult data.
    """
    start = perf_counter()
    logger.info("Starting result verification on %d QueryResult(s)", len(qresults))

    # Step 1: Extract claims
    require_citation = tolerances.get("require_citation_first", True)
    allowed_prefixes_raw = tolerances.get(
        "allowed_prefixes",
        ["Per LMIS:", "According to GCC-STAT:", "According to World Bank:"],
    )
    allowed_prefixes = (
        allowed_prefixes_raw
        if isinstance(allowed_prefixes_raw, list)
        else ["Per LMIS:", "According to GCC-STAT:", "According to World Bank:"]
    )

    ignore_below_raw = tolerances.get("ignore_numbers_below", 1.0)
    ignore_below = float(ignore_below_raw) if ignore_below_raw is not None else 1.0

    claims = extract_numeric_claims(
        narrative_md,
        allowed_prefixes=allowed_prefixes,
        ignore_years=True,
        ignore_below=ignore_below,
    )
    logger.debug("Extracted %d numeric claims", len(claims))

    bindings: list[ClaimBinding] = []
    issues: list[VerificationIssue] = []

    for claim in claims:
        if require_citation and not claim.citation_prefix:
            issues.append(
                VerificationIssue(
                    code="CLAIM_UNCITED",
                    message=f"Claim '{claim.value_text}' lacks citation source",
                    severity="error",
                    details={
                        "value": str(claim.value),
                        "unit": claim.unit,
                        "sentence": claim.sentence[:120],
                    },
                )
            )
            bindings.append(ClaimBinding(claim=claim, matched=False))
            continue

        binding = bind_claim_to_sources(claim, qresults, tolerances)
        bindings.append(binding)

        if binding.ambiguous:
            hint = _issue_hint_from_binding(binding, claim)
            issues.append(
                VerificationIssue(
                    code="AMBIGUOUS_SOURCE",
                    message=f"Claim '{claim.value_text}' matches multiple sources",
                    severity="warning",
                    details={
                        "citation": claim.citation_prefix or "None",
                        "candidates": ", ".join(binding.candidate_qids),
                        "hint": hint or "Add the intended query_id to disambiguate",
                    },
                )
            )
            continue

        if binding.matched:
            if binding.derived_consistent is False:
                recomputed = binding.derived_recomputed_value
                formatted = (
                    _format_value_for_hint(claim, recomputed)
                    if recomputed is not None
                    else "derived value"
                )
                issues.append(
                    VerificationIssue(
                        code="ROUNDING_MISMATCH",
                        message=(
                            f"Derived claim '{claim.value_text}' disagrees with recomputed value "
                            f"{formatted}"
                        ),
                        severity="error",
                        details={
                            "query_id": binding.matched_source_qid or "derived",
                            "hint": f"Use derived value {formatted}",
                        },
                    )
                )
            continue

        reason = binding.failure_reason or "CLAIM_NOT_FOUND"
        if reason == "UNIT_MISMATCH":
            hint = (
                f"Use {_format_value_for_hint(claim, binding.nearest_value)} "
                if binding.nearest_value is not None
                else "Verify the unit and rerun"
            )
            issues.append(
                VerificationIssue(
                    code="UNIT_MISMATCH",
                    message=(
                        f"Claim '{claim.value_text}' unit does not match source "
                        f"(QID: {claim.query_id or 'N/A'})"
                    ),
                    severity="error",
                    details={
                        "query_id": claim.query_id or "None",
                        "hint": hint,
                    },
                )
            )
            continue

        if reason == "ROUNDING_MISMATCH":
            hint = _issue_hint_from_binding(binding, claim)
            issues.append(
                VerificationIssue(
                    code="ROUNDING_MISMATCH",
                    message=(
                        f"Claim '{claim.value_text}' differs from source "
                        f"beyond allowed rounding tolerance"
                    ),
                    severity="warning",
                    details={
                        "query_id": binding.nearest_source_qid or claim.query_id or "None",
                        "difference": f"{binding.nearest_diff or 0:.3f}",
                        "hint": hint or "Align the narrative with the cited metric",
                    },
                )
            )
            continue

        hint = _issue_hint_from_binding(binding, claim)
        issues.append(
            VerificationIssue(
                code="CLAIM_NOT_FOUND",
                message=(
                    f"Claim '{claim.value_text}' not found in cited sources "
                    f"(QID: {claim.query_id or 'N/A'})"
                ),
                severity="error",
                details={
                    "value": str(claim.value),
                    "unit": claim.unit,
                    "citation": claim.citation_prefix or "None",
                    "query_id": claim.query_id or "None",
                    "hint": hint or "Verify the cited query_id and value",
                },
            )
        )

    math_checks, math_details = check_math_consistency(narrative_md, tolerances)
    for check_name, passed in math_checks.items():
        if not passed:
            detail = math_details.get(check_name, {})
            issues.append(
                VerificationIssue(
                    code="MATH_INCONSISTENT",
                    message=f"Math check '{check_name}' failed",
                    severity="error",
                    details=_issue_from_math_detail(check_name, detail),
                )
            )

    claims_matched = sum(1 for binding in bindings if binding.matched)
    ok = not any(issue.severity == "error" for issue in issues)

    runtime_ms = (perf_counter() - start) * 1000.0
    logger.info(
        "Result verification complete: %d/%d claims matched, ok=%s, runtime=%.2fms",
        claims_matched,
        len(claims),
        ok,
        runtime_ms,
    )

    return ResultVerificationReport(
        ok=ok,
        claims_total=len(claims),
        claims_matched=claims_matched,
        issues=issues,
        bindings=bindings,
        math_checks=math_checks,
        math_check_details=math_details,
        runtime_ms=runtime_ms,
    )
