"""HTML and text sanitization utilities."""

from __future__ import annotations

import bleach

_ALLOWED_TAGS = [
    "b",
    "i",
    "strong",
    "em",
    "ul",
    "ol",
    "li",
    "p",
    "br",
    "span",
    "div",
    "code",
    "pre",
    "blockquote",
]
_ALLOWED_ATTRS = {"*": ["class", "title", "aria-label"]}


def sanitize_html(value: str) -> str:
    """
    Sanitize HTML content, removing dangerous tags and attributes.

    Args:
        value: HTML string to sanitize

    Returns:
        Sanitized HTML string
    """
    return bleach.clean(
        value or "", tags=_ALLOWED_TAGS, attributes=_ALLOWED_ATTRS, strip=True
    )


def sanitize_text(value: str) -> str:
    """
    Remove all HTML tags from text.

    Args:
        value: Text string to sanitize

    Returns:
        Plain text with all tags removed
    """
    # Remove any tags entirely for plain text contexts
    return bleach.clean(value or "", tags=[], attributes={}, strip=True)
