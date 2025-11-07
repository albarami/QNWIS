"""
Numeric claim extraction utilities for result verification.

Provides unit-aware parsing of numeric claims from narrative Markdown,
classifying claims as counts, percentages, currency values, or ranges.
"""

from __future__ import annotations

import re
from typing import List, Tuple

from .citation_patterns import extract_qid, extract_source_prefix
from .schemas import NumericClaim, Unit

# Extended number pattern with unit detection
NUM_TOKEN = re.compile(
    r"""(?x)
    (?<![\w/])                              # word boundary before
    (?P<sign>[-+])?                          # optional sign
    (?P<num>\d{1,3}(?:,\d{3})+|\d+)          # number with optional commas
    (?P<decimal>\.\d+)?                      # optional decimal
    (?:\s?(?P<unit>%|percent|pp|bps|QAR|USD))? # optional unit
    (?![\w/])                                # word boundary after
    """,
    re.VERBOSE | re.IGNORECASE,
)


def _classify_unit(unit_text: str | None, context: str) -> str:
    """
    Classify unit type from matched unit text and surrounding context.

    Args:
        unit_text: Matched unit string (%, percent, QAR, etc.)
        context: Surrounding text for additional context

    Returns:
        Unit classification: "count", "percent", or "currency"
    """
    if not unit_text:
        # No explicit unit - check context for currency indicators
        ctx_lower = context.lower()
        if any(curr in ctx_lower for curr in ["qar", "usd", "riyal", "dollar"]):
            return "currency"
        # Default to count for integers, could be currency if context suggests it
        return "count"

    unit_lower = unit_text.strip().lower()
    if unit_lower in ("%", "percent", "pp", "bps"):
        return "percent"
    if unit_lower in ("qar", "usd"):
        return "currency"

    return "count"


def _normalize_number(num_str: str, decimal_str: str | None, sign: str | None) -> float:
    """
    Parse and normalize numeric string to float.

    Args:
        num_str: Number portion (may have comma separators)
        decimal_str: Decimal portion (e.g., ".5")
        sign: Sign prefix ("+" or "-")

    Returns:
        Normalized float value
    """
    # Remove comma separators
    clean_num = num_str.replace(",", "")
    if decimal_str:
        clean_num += decimal_str

    value = float(clean_num)
    if sign == "-":
        value = -value

    return value


def _find_sentence_bounds(text: str, start: int) -> Tuple[int, int]:
    """
    Find sentence boundaries around a position.

    Args:
        text: Full text
        start: Position within text

    Returns:
        Tuple of (sentence_start, sentence_end) positions
    """
    # Look backwards for sentence start
    sent_start = 0
    for i in range(start - 1, -1, -1):
        if text[i] in (".", "!", "?", "\n\n"):
            sent_start = i + 1
            break

    # Look forward for sentence end
    sent_end = len(text)
    for i in range(start, len(text)):
        if text[i] in (".", "!", "?"):
            # Check if followed by space or newline (real sentence boundary)
            if i + 1 >= len(text) or text[i + 1] in (" ", "\n", "\t"):
                sent_end = i + 1
                break
        # Double newline is paragraph boundary
        if i < len(text) - 1 and text[i:i + 2] == "\n\n":
            sent_end = i
            break

    return sent_start, sent_end


def extract_numeric_claims(
    text: str,
    allowed_prefixes: List[str] | None = None,
    ignore_years: bool = True,
    ignore_below: float = 1.0,
) -> List[NumericClaim]:
    """
    Scan narrative Markdown and extract numeric claims with unit classification.

    Returns normalized claims with:
    - value: normalized float value
    - unit: "count", "percent", or "currency"
    - citation_prefix: detected citation source (if present)
    - query_id: extracted QID (if present)
    - sentence: containing sentence for context
    - span: character position (start, end)

    Args:
        text: Narrative Markdown text
        allowed_prefixes: List of allowed citation prefixes
        ignore_years: Skip 4-digit years (2023, etc.)
        ignore_below: Skip numbers below this threshold

    Returns:
        List of NumericClaim objects
    """
    if allowed_prefixes is None:
        allowed_prefixes = [
            "Per LMIS:",
            "According to GCC-STAT:",
            "According to World Bank:",
        ]

    claims: List[NumericClaim] = []

    for match in NUM_TOKEN.finditer(text):
        value_text = match.group(0).strip()
        start = match.start()
        end = match.end()

        # Skip years if configured
        if ignore_years and len(value_text) == 4 and value_text.isdigit():
            year_val = int(value_text)
            if 1900 <= year_val <= 2100:
                continue

        # Extract components
        sign = match.group("sign")
        num_str = match.group("num")
        decimal_str = match.group("decimal")
        unit_text = match.group("unit")

        # Normalize value
        try:
            value = _normalize_number(num_str, decimal_str, sign)
        except (ValueError, TypeError):
            continue

        # Skip small numbers if threshold set
        if ignore_below > 0 and abs(value) < ignore_below:
            continue

        # Find sentence bounds for citation context
        sent_start, sent_end = _find_sentence_bounds(text, start)
        sentence = text[sent_start:sent_end].strip()

        # Classify unit
        context_window = text[max(0, start - 50):min(len(text), end + 50)]
        unit_str = _classify_unit(unit_text, context_window)

        # Detect citation prefix in sentence
        citation_prefix = extract_source_prefix(sentence, allowed_prefixes)

        # Detect query ID in sentence
        query_id = extract_qid(sentence)

        # Map citation prefix to source family
        source_family = None
        if citation_prefix:
            if "LMIS" in citation_prefix:
                source_family = "LMIS"
            elif "GCC-STAT" in citation_prefix or "GCCSTAT" in citation_prefix:
                source_family = "GCC-STAT"
            elif "World Bank" in citation_prefix or "WorldBank" in citation_prefix:
                source_family = "WorldBank"

        # Type assertion for unit
        unit: Unit
        if unit_str == "count":
            unit = "count"
        elif unit_str == "percent":
            unit = "percent"
        else:
            unit = "currency"

        claims.append(
            NumericClaim(
                value_text=value_text,
                value=value,
                unit=unit,
                span=(start, end),
                sentence=sentence,
                citation_prefix=citation_prefix,
                query_id=query_id,
                source_family=source_family,
            )
        )

    return claims
