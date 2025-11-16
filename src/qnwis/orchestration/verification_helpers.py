"""
Pure verification logic for agent reports.

Extracted for testability and reusability across the system.
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


def verify_agent_reports(
    agent_reports: list[dict[str, Any]],
    extracted_facts: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Verify structured agent reports for citation coverage and numeric accuracy.

    Args:
        agent_reports: List of structured AgentReport dicts with citations
        extracted_facts: List of extracted fact dicts from prefetch layer

    Returns:
        Verification result dict with violations, counts, and rates
    """
    if not agent_reports:
        logger.warning("No agent reports to verify")
        return {
            "citation_violations": [],
            "number_violations": [],
            "warning_count": 0,
            "error_count": 0,
            "total_citations": 0,
            "total_numbers": 0,
            "citation_violation_rate": 0.0,
            "number_violation_rate": 0.0,
        }

    logger.info("Verifying %d agent reports", len(agent_reports))

    citation_violations: list[dict[str, Any]] = []
    number_violations: list[dict[str, Any]] = []

    for report in agent_reports:
        agent_name = report.get("agent_name", "unknown")
        narrative = report.get("narrative", "")
        citations = report.get("citations", [])

        # Extract all numbers from narrative with context
        number_pattern = r"\b(\d+(?:\.\d+)?%?)\b"
        numbers_in_text = []

        for match in re.finditer(number_pattern, narrative):
            number_value = match.group(1)
            number_pos = match.start()
            context_start = max(0, number_pos - 100)
            context_end = min(len(narrative), number_pos + 100)
            context = narrative[context_start:context_end]
            numbers_in_text.append(
                {
                    "value": number_value,
                    "position": number_pos,
                    "context": context,
                }
            )

        # Check each number has a citation within 100 chars
        for num in numbers_in_text:
            if "[Per extraction:" not in num["context"]:
                violation = {
                    "agent": agent_name,
                    "number": num["value"],
                    "context": num["context"],
                    "violation": "No citation within 100 characters",
                }
                citation_violations.append(violation)
                logger.warning(
                    "CITATION VIOLATION: %s - %s", agent_name, num["value"]
                )

        # Validate cited values against extracted facts (2% tolerance)
        for citation in citations:
            cited_value_str = citation.get("value", "")
            metric = citation.get("metric")

            if not metric:
                continue

            fact = next(
                (f for f in extracted_facts if f.get("metric") == metric),
                None,
            )

            if not fact:
                continue

            try:
                cited_num = float(cited_value_str.replace("%", "").strip())
                source_value = float(fact.get("value"))
                tolerance = 0.02 * abs(source_value)

                if abs(cited_num - source_value) > tolerance:
                    violation = {
                        "agent": agent_name,
                        "metric": metric,
                        "cited": cited_num,
                        "actual": source_value,
                        "difference": abs(cited_num - source_value),
                        "tolerance": tolerance,
                        "violation": "Value mismatch beyond 2% tolerance",
                    }
                    number_violations.append(violation)
                    logger.warning(
                        "NUMBER VIOLATION: %s - %s (cited %s vs actual %s)",
                        agent_name,
                        metric,
                        cited_num,
                        source_value,
                    )
            except (ValueError, TypeError):
                continue

    # Calculate summary statistics
    total_citations = sum(len(r.get("citations", [])) for r in agent_reports)
    total_numbers = sum(
        len(list(re.finditer(r"\b(\d+(?:\.\d+)?)", r.get("narrative", ""))))
        for r in agent_reports
    )

    verification_result = {
        "citation_violations": citation_violations,
        "number_violations": number_violations,
        "warning_count": len(citation_violations),
        "error_count": len(number_violations),
        "total_citations": total_citations,
        "total_numbers": total_numbers,
        "citation_violation_rate": len(citation_violations) / max(total_numbers, 1),
        "number_violation_rate": len(number_violations) / max(total_citations, 1),
    }

    logger.info(
        "Verification complete: %d citation violations, %d number violations",
        len(citation_violations),
        len(number_violations),
    )

    return verification_result
