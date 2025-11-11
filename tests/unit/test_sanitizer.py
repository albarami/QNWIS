"""Unit tests for sanitization utilities."""

from __future__ import annotations

import pytest

from src.qnwis.security.sanitizer import sanitize_html, sanitize_text


def test_sanitize_html_strips_script():
    """Test that script tags are stripped from HTML."""
    dirty = "<p>ok</p><script>alert(1)</script>"
    clean = sanitize_html(dirty)
    assert "<script>" not in clean
    assert "<p>ok</p>" in clean


def test_sanitize_html_allows_safe_tags():
    """Test that safe HTML tags are preserved."""
    safe = "<p>Hello <strong>world</strong></p>"
    clean = sanitize_html(safe)
    assert "<p>" in clean
    assert "<strong>" in clean
    assert "Hello" in clean
    assert "world" in clean


def test_sanitize_html_strips_dangerous_attributes():
    """Test that dangerous attributes are stripped."""
    dirty = '<p onclick="alert(1)">Click me</p>'
    clean = sanitize_html(dirty)
    assert "onclick" not in clean
    assert "<p>" in clean
    assert "Click me" in clean


def test_sanitize_html_allows_safe_attributes():
    """Test that safe attributes are preserved."""
    safe = '<span class="highlight" title="Info">Text</span>'
    clean = sanitize_html(safe)
    assert 'class="highlight"' in clean
    assert 'title="Info"' in clean


def test_sanitize_text_strips_all_tags():
    """Test that all HTML tags are stripped from text."""
    assert sanitize_text("<b>Hi</b>") == "Hi"
    assert sanitize_text("<script>alert(1)</script>") == "alert(1)"
    assert sanitize_text("<p>Hello <strong>world</strong></p>") == "Hello world"


def test_sanitize_text_handles_empty_input():
    """Test that empty input is handled correctly."""
    assert sanitize_text("") == ""
    assert sanitize_text(None) == ""


def test_sanitize_html_handles_empty_input():
    """Test that empty input is handled correctly."""
    assert sanitize_html("") == ""
    assert sanitize_html(None) == ""


def test_sanitize_html_strips_iframe():
    """Test that iframe tags are stripped."""
    dirty = '<iframe src="evil.com"></iframe><p>Safe</p>'
    clean = sanitize_html(dirty)
    assert "<iframe>" not in clean
    assert "evil.com" not in clean
    assert "<p>Safe</p>" in clean


def test_sanitize_html_strips_object_embed():
    """Test that object and embed tags are stripped."""
    dirty = '<object data="evil.swf"></object><embed src="evil.swf">'
    clean = sanitize_html(dirty)
    assert "<object>" not in clean
    assert "<embed>" not in clean
    assert "evil.swf" not in clean


def test_sanitize_text_preserves_plain_text():
    """Test that plain text without tags is preserved."""
    text = "This is plain text with no HTML"
    assert sanitize_text(text) == text


def test_sanitize_html_handles_nested_tags():
    """Test that nested tags are handled correctly."""
    html = "<div><p><strong>Bold</strong> text</p></div>"
    clean = sanitize_html(html)
    assert "<div>" in clean
    assert "<p>" in clean
    assert "<strong>" in clean
    assert "Bold" in clean


def test_sanitize_html_strips_style_tags():
    """Test that style tags are stripped."""
    dirty = "<style>body { background: red; }</style><p>Content</p>"
    clean = sanitize_html(dirty)
    assert "<style>" not in clean
    # Note: bleach strips tags but may keep content, which is safe for display
    assert "<p>Content</p>" in clean


@pytest.mark.parametrize(
    "payload,blocked_tokens",
    [
        ('<img src=x onerror=alert(1)>', ("<img", "onerror", "alert(1)")),
        ('"><svg onload=alert(1)>', ("<svg", "onload")),
        ('<a href="javascript:alert(1)">Click</a>', ("javascript:", "<a")),
        (
            '<div style="background:url(data:text/html;base64,PHNjcmlwdA==)">bad</div>',
            ("data:text/html", "url("),
        ),
    ],
)
def test_sanitize_html_tricky_payloads(payload, blocked_tokens):
    """Ensure tricky payloads are neutralized."""
    clean = sanitize_html(payload)
    for token in blocked_tokens:
        assert token not in clean
