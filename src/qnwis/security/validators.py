"""Common input validators for security."""

from __future__ import annotations

import re
from datetime import date
from uuid import UUID


_SAFE_RE = re.compile(r"^[\w\-\.\s,@#:/\(\)\[\]]{1,500}$")


def validate_uuid(value: str) -> UUID:
    """
    Validate and parse UUID string.

    Args:
        value: UUID string

    Returns:
        UUID object

    Raises:
        ValueError: If invalid UUID format
    """
    return UUID(value)


def validate_date_yyyy_mm_dd(value: str) -> date:
    """
    Validate and parse date in YYYY-MM-DD format.

    Args:
        value: Date string in YYYY-MM-DD format

    Returns:
        date object

    Raises:
        ValueError: If invalid date format
    """
    y, m, d = map(int, value.split("-"))
    return date(y, m, d)


def validate_safe_string(value: str) -> str:
    """
    Validate string contains only safe characters.

    Args:
        value: String to validate

    Returns:
        Validated string

    Raises:
        ValueError: If unsafe characters detected
    """
    if not _SAFE_RE.fullmatch(value or ""):
        raise ValueError("Unsafe characters detected")
    return value
