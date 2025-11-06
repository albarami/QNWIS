"""
Deterministic merger for OrchestrationResult objects.

Merges multiple partial results into a single uniform report with
stable ordering, deduplication, and PII safety.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Set, Tuple

from ..orchestration.schemas import (
    Citation,
    Freshness,
    OrchestrationResult,
    ReportSection,
    Reproducibility,
)

logger = logging.getLogger(__name__)

# Canonical section order
SECTION_ORDER = [
    "Executive Summary",
    "Key Findings",
    "Evidence",
    "Citations & Freshness",
    "Reproducibility",
    "Warnings",
]

# PII patterns to mask: names, emails, and long numeric identifiers
PII_PATTERNS = [
    re.compile(r"\b[A-Z][a-z]+ [A-Z][a-z]+\b"),
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    re.compile(r"\b\d{10,}\b"),
]


def mask_pii(text: str) -> str:
    """
    Mask potential PII in text.

    Args:
        text: Input text that may contain PII

    Returns:
        Text with PII masked as ***
    """
    masked = text
    for pattern in PII_PATTERNS:
        masked = pattern.sub("***", masked)
    return masked


def _parse_iso8601(timestamp: str | None) -> datetime | None:
    """
    Parse ISO8601 timestamp strings into datetime objects.

    Args:
        timestamp: Timestamp string (may include trailing 'Z')

    Returns:
        Parsed datetime or None if parsing fails
    """
    if not timestamp:
        return None

    normalized = timestamp.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        logger.debug("Unable to parse timestamp '%s'", timestamp)
        return None


def normalize_section_title(title: str) -> str:
    """
    Normalize section title for comparison.

    Args:
        title: Section title

    Returns:
        Normalized title (lowercase, stripped)
    """
    return title.strip().lower()


def dedupe_sections(sections: List[ReportSection]) -> List[ReportSection]:
    """
    Deduplicate sections by (title, first 40 chars of body).

    Args:
        sections: List of ReportSection objects

    Returns:
        Deduplicated list maintaining first occurrence
    """
    seen: Set[Tuple[str, str]] = set()
    unique: List[ReportSection] = []

    for section in sections:
        normalized_title = normalize_section_title(section.title)
        body_prefix = section.body_md[:40] if section.body_md else ""
        key = (normalized_title, body_prefix)

        if key not in seen:
            seen.add(key)
            unique.append(section)
        else:
            logger.debug("Duplicate section skipped: %s", section.title)

    return unique


def sort_sections(sections: List[ReportSection]) -> List[ReportSection]:
    """
    Sort sections according to canonical order.

    Args:
        sections: List of ReportSection objects

    Returns:
        Sorted list following SECTION_ORDER
    """

    def section_sort_key(section: ReportSection) -> int:
        normalized = normalize_section_title(section.title)
        for idx, canonical in enumerate(SECTION_ORDER):
            if canonical.lower() in normalized:
                return idx
        return len(SECTION_ORDER)  # Unknown sections go last

    return sorted(sections, key=section_sort_key)


def merge_citations(results: List[OrchestrationResult]) -> List[Citation]:
    """
    Merge citations with deduplication by (query_id, dataset_id).

    Args:
        results: List of OrchestrationResult objects

    Returns:
        Deduplicated and sorted list of Citation objects
    """
    seen: Set[Tuple[str, str]] = set()
    citations: List[Citation] = []

    for result in results:
        for citation in result.citations:
            key = (citation.query_id, citation.dataset_id)
            if key not in seen:
                seen.add(key)
                citations.append(citation)

    # Sort by dataset_id then query_id for determinism
    citations.sort(key=lambda c: (c.dataset_id, c.query_id))
    return citations


def merge_freshness(results: List[OrchestrationResult]) -> Dict[str, Freshness]:
    """
    Merge freshness metadata, keeping track of minimum and maximum timestamps.

    Args:
        results: List of OrchestrationResult objects

    Returns:
        Dictionary of source -> Freshness with timestamp ranges
    """
    ranges: Dict[str, Dict[str, Any]] = {}

    for result in results:
        for source, fresh in result.freshness.items():
            info = ranges.setdefault(
                source,
                {
                    "min_dt": None,
                    "max_dt": None,
                    "min_str": None,
                    "max_str": None,
                    "fallback": None,
                    "age_days": fresh.age_days,
                },
            )

            candidates = [
                fresh.min_timestamp,
                fresh.last_updated,
                fresh.max_timestamp,
            ]
            for candidate in candidates:
                parsed = _parse_iso8601(candidate)
                if parsed is None:
                    if candidate and info["fallback"] is None:
                        info["fallback"] = candidate
                    continue

                if info["min_dt"] is None or parsed < info["min_dt"]:
                    info["min_dt"] = parsed
                    info["min_str"] = candidate
                if info["max_dt"] is None or parsed > info["max_dt"]:
                    info["max_dt"] = parsed
                    info["max_str"] = candidate
                    info["age_days"] = fresh.age_days

            if info["fallback"] is None and fresh.last_updated:
                info["fallback"] = fresh.last_updated
            if info["age_days"] is None and fresh.age_days is not None:
                info["age_days"] = fresh.age_days

    merged: Dict[str, Freshness] = {}
    for source, info in ranges.items():
        min_ts = info["min_str"] or info["fallback"]
        max_ts = info["max_str"] or info["fallback"]
        last_updated = max_ts or min_ts or ""

        merged[source] = Freshness(
            source=source,
            last_updated=last_updated,
            age_days=info["age_days"],
            min_timestamp=min_ts,
            max_timestamp=max_ts,
        )

    return merged


def merge_reproducibility(results: List[OrchestrationResult]) -> List[Reproducibility]:
    """
    Merge reproducibility metadata from all results.

    Args:
        results: List of OrchestrationResult objects

    Returns:
        List of unique Reproducibility objects
    """
    seen: Set[Tuple[str, str]] = set()
    repro_list: List[Reproducibility] = []

    for result in results:
        repro = result.reproducibility
        # Create key from method and timestamp
        key = (repro.method, repro.timestamp)
        if key not in seen:
            seen.add(key)
            repro_list.append(repro)

    # Sort by timestamp for determinism
    repro_list.sort(key=lambda r: r.timestamp)
    return repro_list


def merge_warnings(results: List[OrchestrationResult]) -> List[str]:
    """
    Merge and deduplicate warnings.

    Args:
        results: List of OrchestrationResult objects

    Returns:
        Deduplicated list of warnings
    """
    seen: Set[str] = set()
    warnings: List[str] = []

    for result in results:
        for warning in result.warnings:
            normalized = mask_pii(warning.strip())
            if normalized and normalized not in seen:
                seen.add(normalized)
                warnings.append(normalized)

    return warnings


def merge_agent_traces(results: List[OrchestrationResult]) -> List[Dict[str, Any]]:
    """
    Merge agent execution traces with deduplication and deterministic ordering.

    Args:
        results: List of OrchestrationResult objects

    Returns:
        Sorted list of unique execution trace dictionaries
    """
    seen: Set[Tuple[str, str, str, int]] = set()
    traces: List[Dict[str, Any]] = []

    for result in results:
        for trace in result.agent_traces:
            intent = str(trace.get("intent", ""))
            agent = str(trace.get("agent", ""))
            method = str(trace.get("method", ""))
            attempt = int(trace.get("attempt", 0))
            key = (intent, agent, method, attempt)
            if key in seen:
                continue
            seen.add(key)
            traces.append(trace)

    traces.sort(
        key=lambda t: (
            str(t.get("intent", "")),
            str(t.get("method", "")),
            int(t.get("attempt", 0)),
            float(t.get("elapsed_ms", 0.0)),
        )
    )
    return traces


def merge_results(results: List[OrchestrationResult]) -> OrchestrationResult:
    """
    Deterministically merge multiple OrchestrationResult objects.

    Merging rules:
    - Sections: dedupe by (title, first 40 chars), stable order
    - Citations: union by (query_id, dataset_id), sorted
    - Freshness: compute min/max timestamp range per source
    - Reproducibility: list union with agent/method/params
    - ok: all(ok) from all results
    - warnings: concat + dedupe with PII masking
    - agent_traces: dedupe with deterministic ordering
    - PII: mask in sections and warnings

    Args:
        results: List of OrchestrationResult objects to merge

    Returns:
        Single merged OrchestrationResult

    Raises:
        ValueError: If results list is empty
    """
    if not results:
        raise ValueError("Cannot merge empty results list")

    logger.info("Merging %d OrchestrationResult objects", len(results))

    # Aggregate sections
    all_sections: List[ReportSection] = []
    for result in results:
        all_sections.extend(result.sections)

    merged_sections = dedupe_sections(all_sections)
    sorted_sections = sort_sections(merged_sections)

    # Mask PII in sections
    for section in sorted_sections:
        section.body_md = mask_pii(section.body_md)

    # Merge other components
    merged_citations = merge_citations(results)
    merged_freshness = merge_freshness(results)
    merged_warnings = merge_warnings(results)
    merged_traces = merge_agent_traces(results)

    # Determine overall ok status
    overall_ok = all(result.ok for result in results)

    # Use first result's metadata as base
    first = results[0]

    # Create merged reproducibility
    # Combine all methods into a single reproducibility record
    combined_methods = ", ".join(r.reproducibility.method for r in results)
    combined_reproducibility = Reproducibility(
        method=combined_methods,
        params={
            "merged_from": [r.reproducibility.method for r in results],
        },
        timestamp=datetime.utcnow().isoformat(),
    )

    merged = OrchestrationResult(
        ok=overall_ok,
        intent=first.intent,
        sections=sorted_sections,
        citations=merged_citations,
        freshness=merged_freshness,
        reproducibility=combined_reproducibility,
        warnings=merged_warnings,
        request_id=first.request_id,
        timestamp=datetime.utcnow().isoformat(),
        agent_traces=merged_traces,
    )

    logger.info(
        "Merge complete: %d sections, %d citations, %d traces, ok=%s",
        len(merged.sections),
        len(merged.citations),
        len(merged.agent_traces),
        merged.ok,
    )

    return merged
