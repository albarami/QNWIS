"""
Audit trail utility functions for cryptographic digests, canonicalization, and redaction.

Provides deterministic JSON canonicalization, SHA-256 digests, HMAC signatures,
and PII-safe redaction for audit manifests.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import unicodedata
from typing import Any


def canonical_json(obj: Any) -> str:
    """
    Generate deterministic, sorted JSON representation for hashing/signing.

    Ensures consistent serialization regardless of dict insertion order,
    using sorted keys and no whitespace.

    Args:
        obj: Python object to serialize (must be JSON-serializable)

    Returns:
        Canonical JSON string with sorted keys, no whitespace, UTF-8 encoding

    Raises:
        TypeError: If obj contains non-serializable types
    """
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def sha256_digest(text: str) -> str:
    """
    Compute SHA-256 hex digest of text.

    Args:
        text: Input text (will be UTF-8 encoded)

    Returns:
        Lowercase hexadecimal digest string (64 characters)
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def hmac_sha256(text: str, key: bytes) -> str:
    """
    Compute HMAC-SHA256 signature for tamper detection.

    Args:
        text: Input text to sign (will be UTF-8 encoded)
        key: Secret key bytes (must not be empty)

    Returns:
        Lowercase hexadecimal HMAC signature (64 characters)

    Raises:
        ValueError: If key is empty
    """
    if not key:
        raise ValueError("HMAC key must not be empty")

    return hmac.new(
        key,
        text.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


# PII patterns matching format.py redaction rules
_PII_PATTERNS = [
    (re.compile(r"\b[A-Z][a-z]+ [A-Z][a-z]+\b"), "[REDACTED_NAME]"),
    (re.compile(r"\b\d{10,}\b"), "[REDACTED_ID]"),
    (
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
        "[REDACTED_EMAIL]",
    ),
]


def redact_text(s: str) -> str:
    """
    Apply PII redaction rules to text for audit summaries.

    Matches existing redaction patterns in format.py to ensure consistency.
    Redacts:
    - Capitalized first and last names (e.g., "John Smith")
    - Numeric identifiers with 10+ digits
    - Email addresses

    Args:
        s: Text to redact

    Returns:
        Text with PII replaced by placeholder tokens
    """
    result = s
    for pattern, replacement in _PII_PATTERNS:
        result = pattern.sub(replacement, result)
    return result


def slugify_filename(value: str, default: str = "artifact") -> str:
    """
    Produce a filesystem-safe slug for filenames.

    Args:
        value: Source text to slugify.
        default: Fallback value when slug would otherwise be empty.

    Returns:
        Lowercase, ASCII-safe slug suitable for filenames.
    """
    if not value:
        return default

    normalized = unicodedata.normalize("NFKD", value)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    collapsed = re.sub(r"[^A-Za-z0-9._-]+", "_", ascii_only).strip("_")
    slug = collapsed.lower()
    return slug or default


def reproducibility_snippet(
    query_ids: list[str],
    registry_version: str,
) -> str:
    """
    Generate Python code snippet for reproducing QueryResults from Data API.

    Args:
        query_ids: List of query IDs used in the orchestration run
        registry_version: Version/hash of the query registry at execution time

    Returns:
        Python code snippet as a string
    """
    ids_repr = ",\n    ".join(f'"{qid}"' for qid in query_ids)

    snippet = f'''"""
Reproducibility snippet for audit pack.
Registry version: {registry_version}
"""

from qnwis.data.deterministic.api import DataAPI

# Initialize Data API with the same registry version
api = DataAPI(registry_version="{registry_version}")

# Query IDs from original execution
query_ids = [
    {ids_repr}
]

# Fetch all QueryResults
results = []
for qid in query_ids:
    try:
        result = api.fetch(qid)
        results.append(result)
    except Exception as exc:
        print(f"Failed to fetch {{qid}}: {{exc}}")

# Compare results to evidence/*.json in audit pack
print(f"Fetched {{len(results)}} / {{len(query_ids)}} QueryResults")
'''
    return snippet


def compute_params_hash(params: dict[str, Any]) -> str:
    """
    Compute deterministic hash of orchestration parameters.

    Args:
        params: Parameter dictionary (must be JSON-serializable)

    Returns:
        SHA-256 hex digest of canonical JSON representation
    """
    canonical = canonical_json(params)
    return sha256_digest(canonical)
