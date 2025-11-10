"""
Citation pattern matching and extraction utilities.

Provides compiled regex patterns for detecting numeric claims, years,
query IDs, and citation source prefixes in agent narratives.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping

DEFAULT_ALLOWED_PREFIXES = [
    "Per LMIS:",
    "According to GCC-STAT:",
    "According to World Bank:",
]

DEFAULT_SOURCE_SYNONYMS: dict[str, list[str]] = {
    "According to GCC-STAT:": [
        "According to GCCSTAT:",
        "According to GCC STAT:",
        "According to GCCStat:",
    ],
}

# Numeric pattern that captures:
# - Optional sign (+ or -)
# - Number with optional thousand separators or decimal points
# - Optional units (%, percent, pts, bp/bps, QR/QAR, pp for percentage points)
NUMBER = re.compile(
    r"""(?x)
    (?P<sign>[-+])?
    (?P<num>(\d{1,3}(,\d{3})+|\d+)(\.\d+)?)
    (?P<unit>\s?(?:%|percent|pts|bp|bps|basis\s+points|(?:QR|QAR)|pp))?
    """,
    re.VERBOSE | re.IGNORECASE,
)

# Year pattern (4-digit years starting with 19 or 20)
YEAR = re.compile(r"\b(19|20)\d{2}\b")

# Query ID patterns (QID:xxx or query_id=xxx)
QID = re.compile(
    r"\b(?:QID[:=]\s*[A-Za-z0-9_-]{8,}|query_id\s*=\s*[A-Za-z0-9_-]{8,})\b",
    re.IGNORECASE,
)

# Source prefix patterns for recognized citation sources
SOURCE_PREFIX = re.compile(
    r"^\s*(Per LMIS:|According to GCC-STAT:|According to World Bank:)",
    re.IGNORECASE | re.MULTILINE,
)

# Pattern to identify common non-claim tokens (codes, identifiers)
# These are typically not numeric "claims" that need citation
IGNORABLE_TOKEN = re.compile(
    r"\b(?:ISO-3166|NOC|PO\s+Box|RFC\s+\d+|ID\s+\d+)\b",
    re.IGNORECASE,
)


def extract_number_value(match: re.Match[str]) -> float:
    """
    Extract numeric value from a NUMBER regex match.

    Args:
        match: Regex match from NUMBER pattern

    Returns:
        Numeric value as float
    """
    sign = match.group("sign") or ""
    num_str = match.group("num").replace(",", "")
    value = float(num_str)
    if sign == "-":
        value = -value
    return value


def is_year(token: str) -> bool:
    """
    Check if token is a year (e.g., 2023).

    Args:
        token: Token to check

    Returns:
        True if token matches year pattern
    """
    return YEAR.fullmatch(token.strip()) is not None


def is_ignorable(token: str, context: str = "") -> bool:
    """
    Check if token is an ignorable identifier (not a numeric claim).

    Args:
        token: Token to check
        context: Surrounding context for additional checks

    Returns:
        True if token should be ignored
    """
    # Check explicit ignorable patterns
    if IGNORABLE_TOKEN.search(token):
        return True

    # Single digit is often not a substantive claim (e.g., "Q3", "T1")
    clean_token = token.strip().strip('%')
    if len(clean_token) == 1 and clean_token.isdigit():
        return True

    # Check if token is part of a QID pattern or code
    # Look for patterns like "lmis_001", "QID: 001", "ISO-3166"
    if context:
        idx = context.find(token)
        if idx >= 0:
            # Check immediately before the number
            if idx > 0:
                char_before = context[idx - 1]
                # Code patterns (letter/underscore/hyphen immediately before)
                if char_before in ('_', '-'):
                    return True
                # Q1-Q4 quarter patterns
                if char_before.upper() == 'Q' and token.strip() in ('1', '2', '3', '4'):
                    return True

            # Check immediately after the number
            end_idx = idx + len(token)
            if end_idx < len(context):
                char_after = context[end_idx]
                # Code patterns (hyphen/underscore immediately after)
                if char_after in ('_', '-'):
                    return True

            # Check broader context for QID keywords and ISO codes
            prefix = context[max(0, idx - 20):idx]
            if "QID" in prefix.upper() or "query_id" in prefix.lower():
                return True
            if "ISO" in prefix.upper():
                return True

    return False


def extract_qid(text: str) -> str | None:
    """
    Extract first query ID from text.

    Args:
        text: Text to search

    Returns:
        Query ID if found, None otherwise
    """
    match = QID.search(text)
    if match:
        # Extract just the ID portion
        matched = match.group(0)
        # Parse out the actual ID
        if ":" in matched:
            return matched.split(":", 1)[1].strip()
        elif "=" in matched:
            return matched.split("=", 1)[1].strip()
    return None


def extract_source_prefix(
    text: str,
    allowed_prefixes: Iterable[str] | None = None,
    synonyms: Mapping[str, Iterable[str]] | None = None,
) -> str | None:
    """
    Extract source prefix from text using allowed prefixes and synonyms.

    Args:
        text: Text to search
        allowed_prefixes: Canonical prefixes (defaults to Step 19 defaults)
        synonyms: Mapping from canonical prefix to acceptable synonyms

    Returns:
        Source prefix if found, None otherwise
    """
    allowed = list(allowed_prefixes or DEFAULT_ALLOWED_PREFIXES)
    match = SOURCE_PREFIX.search(text)
    if match:
        detected = match.group(1)
        for prefix in allowed:
            if detected.lower().startswith(prefix.lower()):
                return prefix
        return detected

    synonym_map = synonyms or DEFAULT_SOURCE_SYNONYMS
    for canonical, alias_list in synonym_map.items():
        for alias in alias_list:
            alias_clean = alias.strip()
            if not alias_clean:
                continue
            pattern = rf"(?mi)^\s*{re.escape(alias_clean)}"
            if re.search(pattern, text):
                return canonical

    return None
