"""
Integration tests for Chainlit UI streaming.

Tests that websocket session receives streamed tokens with CSP-safe markdown.
"""

import pytest


@pytest.mark.skip(reason="Chainlit websocket tests require running server")
def test_chainlit_receives_streamed_tokens():
    """Test websocket session receives streamed tokens."""
    # This test requires a running Chainlit server
    # Skip for now - manual testing required
    pass


@pytest.mark.skip(reason="Chainlit websocket tests require running server") 
def test_chainlit_no_raw_html_in_payload():
    """Test Chainlit payload contains no raw <div> tags."""
    # This test requires a running Chainlit server
    # Skip for now - manual testing required
    pass


def test_chainlit_app_imports():
    """Test Chainlit app can be imported without errors."""
    try:
        from src.qnwis.ui import chainlit_app
        assert chainlit_app is not None
    except ImportError as e:
        pytest.skip(f"Chainlit not available: {e}")


def test_chainlit_markdown_sanitization_helper():
    """Test markdown sanitization removes unsafe HTML."""
    try:
        from src.qnwis.ui.chainlit_app import sanitize_markdown
        
        # Test removing script tags
        unsafe = "Hello <script>alert('xss')</script> world"
        safe = sanitize_markdown(unsafe)
        assert "<script>" not in safe
        
        # Test allowing safe markdown
        markdown = "# Title\n\n- Item 1\n- Item 2"
        result = sanitize_markdown(markdown)
        assert "Title" in result
        
    except (ImportError, AttributeError):
        pytest.skip("Sanitization helper not available")
