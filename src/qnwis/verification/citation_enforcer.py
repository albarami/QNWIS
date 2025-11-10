"""
Citation enforcement engine for validating numeric claims in agent narratives.

This module provides deterministic, regex-based citation validation to ensure
all numeric claims are properly cited with source prefixes and query IDs.
"""

from __future__ import annotations

import logging
import time
from bisect import bisect_right
from dataclasses import dataclass

from ..data.deterministic.models import QueryResult
from .citation_patterns import (
    NUMBER,
    extract_number_value,
    extract_qid,
    extract_source_prefix,
    is_ignorable,
    is_year,
)
from .schemas import CitationIssue, CitationReport, CitationRules, Severity

logger = logging.getLogger(__name__)
BULLET_MARKERS = ("-", "*", "+")


@dataclass
class CitationContextEvaluation:
    """Result of validating citation context for a numeric claim."""

    has_source: bool
    has_qid: bool
    matched_prefix: str
    qid_required: bool
    missing_qid_severity: Severity
    strict_keyword: str | None = None


def _splitlines_with_positions(text: str) -> tuple[list[str], list[int]]:
    """
    Split text into lines while keeping starting offsets for each line.

    Args:
        text: Source text

    Returns:
        Tuple of (stripped_lines, start_offsets)
    """
    if not text:
        return [""], [0]

    raw_lines = text.splitlines(keepends=True)
    stripped_lines = [line.rstrip("\r\n") for line in raw_lines]
    starts: list[int] = []
    cursor = 0
    for line in raw_lines:
        starts.append(cursor)
        cursor += len(line)
    return stripped_lines, starts


def _line_index_for_offset(starts: list[int], offset: int) -> int:
    """Return line index for a given character offset."""
    if not starts:
        return 0
    idx = bisect_right(starts, offset) - 1
    return max(idx, 0)


def _is_bullet_line(line: str) -> bool:
    """Check if a line begins with a markdown bullet marker."""
    stripped = line.lstrip()
    return bool(stripped) and stripped[0] in BULLET_MARKERS


def _strip_bullet_marker(line: str) -> str:
    """Remove the bullet marker from the start of a line, if present."""
    stripped = line.lstrip()
    if not stripped:
        return stripped
    if stripped[0] in BULLET_MARKERS:
        return stripped[1:].lstrip()
    return stripped


def _maybe_use_adjacent_bullet_context(
    lines: list[str],
    line_idx: int,
    rules: CitationRules,
) -> str | None:
    """
    Build supplemental context when citations live in adjacent bullet lines.

    Args:
        lines: Narrative split into stripped lines
        line_idx: Index of the line containing the numeric claim
        rules: Citation rules configuration

    Returns:
        Combined context string if a nearby bullet contains the citation.
    """
    if (
        rules.adjacent_bullet_window <= 0
        or not lines
        or line_idx < 0
        or line_idx >= len(lines)
        or not _is_bullet_line(lines[line_idx])
    ):
        return None

    max_distance = rules.adjacent_bullet_window
    current_line = _strip_bullet_marker(lines[line_idx])

    for direction in (-1, 1):
        for step in range(1, max_distance + 1):
            neighbor_idx = line_idx + (direction * step)
            if neighbor_idx < 0 or neighbor_idx >= len(lines):
                break
            neighbor_line = lines[neighbor_idx]
            if not _is_bullet_line(neighbor_line):
                continue
            normalized_neighbor = _strip_bullet_marker(neighbor_line)
            prefix = extract_source_prefix(
                normalized_neighbor,
                allowed_prefixes=rules.allowed_prefixes,
                synonyms=rules.source_synonyms,
            )
            if prefix:
                # Bring citation line before numeric line so prefix is detected
                return f"{normalized_neighbor}\n{current_line}"
    return None


def extract_numeric_spans(text: str, rules: CitationRules) -> list[tuple[int, int, str]]:
    """
    Extract spans of candidate numeric claims from text.

    Filters out years and ignorable tokens based on rules.

    Args:
        text: Source text to scan
        rules: Citation rules configuration

    Returns:
        List of (start, end, token) tuples for numeric claims
    """
    spans: list[tuple[int, int, str]] = []

    for match in NUMBER.finditer(text):
        token = match.group(0)
        start = match.start()
        end = match.end()

        # Skip years if configured
        if rules.ignore_years and is_year(token):
            continue

        # Get context for better token classification
        ctx_start = max(0, start - 30)
        ctx_end = min(len(text), end + 30)
        context = text[ctx_start:ctx_end]

        # Skip ignorable tokens (codes, IDs, QID components)
        if is_ignorable(token, context):
            continue

        # Check any configured ignore tokens
        if any(ignore_token in token for ignore_token in rules.ignore_tokens):
            continue

        # Skip small numbers if threshold is set
        if rules.ignore_numbers_below > 0:
            value = None
            try:
                value = extract_number_value(match)
            except (ValueError, AttributeError):
                value = None
            if value is not None and abs(value) < rules.ignore_numbers_below:
                continue

        spans.append((start, end, token))

    return spans


def find_citation_context(text: str, start: int, window: int = 200) -> str:
    """
    Extract context around a numeric claim for citation validation.

    Looks for the sentence or paragraph containing the number.

    Args:
        text: Full text
        start: Start position of the number
        window: Character window to extract (default 200)

    Returns:
        Context string containing the citation area
    """
    # Find the start of the context (look backwards for newlines or sentence starts)
    ctx_start = max(0, start - window)
    ctx_end = min(len(text), start + window)

    # Try to expand to full sentences or paragraphs
    # Look backwards for sentence boundary (but allow single newlines for multi-line sentences)
    for i in range(start - 1, ctx_start, -1):
        if text[i] in (".", "!", "?"):
            ctx_start = i + 1
            break
        # Double newline indicates paragraph break
        if i > 0 and text[i-1:i+1] == "\n\n":
            ctx_start = i + 1
            break

    # Look forward for sentence boundary
    for i in range(start, ctx_end):
        if text[i] in (".", "!", "?") and (i + 1 >= len(text) or text[i + 1] in (" ", "\n")):
            ctx_end = i + 1
            break
        # Double newline indicates paragraph break
        if i < len(text) - 1 and text[i:i+2] == "\n\n":
            ctx_end = i
            break

    return text[ctx_start:ctx_end].strip()


def validate_context_has_source_and_qid(
    ctx: str, rules: CitationRules
) -> CitationContextEvaluation:
    """
    Check if context contains valid source prefix and query ID.

    Args:
        ctx: Citation context string
        rules: Citation rules configuration

    Returns:
        CitationContextEvaluation describing match results
    """
    matched_prefix = ""
    prefix = extract_source_prefix(
        ctx,
        allowed_prefixes=rules.allowed_prefixes,
        synonyms=rules.source_synonyms,
    )
    if prefix:
        matched_prefix = prefix

    ctx_lower = ctx.lower()
    strict_keyword = None
    for keyword in rules.strict_qid_keywords:
        if keyword.lower() in ctx_lower:
            strict_keyword = keyword
            break

    qid_required = rules.require_query_id or strict_keyword is not None
    has_qid = True
    if qid_required:
        has_qid = extract_qid(ctx) is not None

    missing_qid_severity: Severity = (
        rules.strict_qid_severity if strict_keyword else rules.missing_qid_severity
    )

    return CitationContextEvaluation(
        has_source=bool(matched_prefix),
        has_qid=has_qid,
        matched_prefix=matched_prefix,
        qid_required=qid_required,
        missing_qid_severity=missing_qid_severity,
        strict_keyword=strict_keyword,
    )


def map_sources_to_queryresults(
    prefix: str, qresults: list[QueryResult], rules: CitationRules
) -> bool:
    """
    Verify that cited source has corresponding QueryResult data.

    Uses source_mapping from rules to match prefixes to data sources.

    Args:
        prefix: Citation source prefix
        qresults: List of available query results
        rules: Citation rules configuration

    Returns:
        True if source is validated, False otherwise
    """
    if not prefix or not qresults:
        return False

    # Get expected source patterns from mapping
    source_patterns = rules.source_mapping.get(prefix, [])
    if not source_patterns:
        # No mapping defined - accept any source
        return True

    # Check if any QueryResult has a matching data source
    for qr in qresults:
        dataset_id = (qr.provenance.dataset_id or "").lower()
        for pattern in source_patterns:
            if pattern.lower() in dataset_id:
                return True

    return False


def enforce_citations(
    text_md: str, qresults: list[QueryResult], rules: CitationRules
) -> CitationReport:
    """
    Run citation enforcement on agent narrative text.

    Extracts numeric claims, validates citations, and produces a report.

    Args:
        text_md: Agent narrative text (Markdown format)
        qresults: List of query results available for citation
        rules: Citation rules configuration

    Returns:
        CitationReport with validation results
    """
    start_time = time.perf_counter()
    logger.info("Starting citation enforcement on %d characters", len(text_md))

    # Extract all numeric spans
    spans = extract_numeric_spans(text_md, rules)
    total_numbers = len(spans)

    logger.debug("Found %d numeric claims to validate", total_numbers)
    lines, line_starts = _splitlines_with_positions(text_md)

    uncited: list[CitationIssue] = []
    malformed: list[CitationIssue] = []
    missing_qid: list[CitationIssue] = []
    sources_used: dict[str, int] = {}
    cited_count = 0

    for start, end, token in spans:
        # Get context around this number
        ctx = find_citation_context(text_md, start)

        # Validate citation
        ctx_eval = validate_context_has_source_and_qid(ctx, rules)

        if not ctx_eval.has_source and rules.adjacent_bullet_window > 0:
            line_idx = _line_index_for_offset(line_starts, start)
            bullet_ctx = _maybe_use_adjacent_bullet_context(lines, line_idx, rules)
            if bullet_ctx:
                ctx_eval = validate_context_has_source_and_qid(bullet_ctx, rules)

        if not ctx_eval.has_source:
            # No source citation found
            uncited.append(
                CitationIssue(
                    code="UNCITED_NUMBER",
                    message=f"Numeric claim '{token}' lacks required citation source",
                    severity="error",
                    value_text=token,
                    span=[start, end],
                )
            )
        elif not ctx_eval.has_qid:
            # Source present but missing query ID
            strict_suffix = ""
            if ctx_eval.strict_keyword:
                strict_suffix = f" (strict metric: '{ctx_eval.strict_keyword}')"
            missing_qid.append(
                CitationIssue(
                    code="MISSING_QID",
                    message=(
                        f"Citation for '{token}' missing query ID "
                        f"(QID or query_id required){strict_suffix}"
                    ),
                    severity=ctx_eval.missing_qid_severity,
                    value_text=token,
                    span=[start, end],
                )
            )
        else:
            # Validate source against query results
            if not map_sources_to_queryresults(ctx_eval.matched_prefix, qresults, rules):
                malformed.append(
                    CitationIssue(
                        code="UNKNOWN_SOURCE",
                        message=(
                            f"Citation source '{ctx_eval.matched_prefix}' for '{token}' "
                            "not found in available query results"
                        ),
                        severity="error",
                        value_text=token,
                        span=[start, end],
                    )
                )
            else:
                # Valid citation
                cited_count += 1
                prefix_key = ctx_eval.matched_prefix or "Unknown"
                sources_used[prefix_key] = sources_used.get(prefix_key, 0) + 1

    # Determine overall status
    all_issues = uncited + malformed + missing_qid
    ok = not any(issue.severity == "error" for issue in all_issues)

    duration_ms = (time.perf_counter() - start_time) * 1000.0

    logger.info(
        "Citation enforcement complete: %d/%d cited, ok=%s, runtime=%.2fms",
        cited_count,
        total_numbers,
        ok,
        duration_ms,
    )

    return CitationReport(
        ok=ok,
        total_numbers=total_numbers,
        cited_numbers=cited_count,
        uncited=uncited,
        malformed=malformed,
        missing_qid=missing_qid,
        sources_used=sources_used,
        runtime_ms=duration_ms,
    )
