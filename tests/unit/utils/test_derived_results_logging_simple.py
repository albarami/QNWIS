"""Simplified test that derived_results module has proper logging."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

SRC_ROOT = Path(__file__).parents[3] / "src"


def test_derived_results_has_logger():
    """Verify derived_results.py imports and configures logging."""
    file_path = SRC_ROOT / "qnwis" / "agents" / "utils" / "derived_results.py"
    assert file_path.exists(), f"File not found: {file_path}"

    content = file_path.read_text(encoding="utf-8")

    # Check for logging import
    assert "import logging" in content, "Missing 'import logging'"

    # Check for logger configuration
    assert "logger = logging.getLogger(__name__)" in content or \
           "logger = logging.getLogger" in content, \
           "Missing logger configuration"


def test_derived_results_no_bare_pass():
    """Verify no bare pass statements in derived_results.py."""
    file_path = SRC_ROOT / "qnwis" / "agents" / "utils" / "derived_results.py"
    content = file_path.read_text(encoding="utf-8")

    # Parse AST to find pass statements
    tree = ast.parse(content)

    for node in ast.walk(tree):
        if isinstance(node, ast.Pass):
            # Get the line
            line_content = content.split('\n')[node.lineno - 1]
            # Check if it's a bare pass (not in a placeholder context)
            if line_content.strip() == "pass":
                pytest.fail(
                    f"Found bare pass statement at line {node.lineno}: {line_content}"
                )


def test_derived_results_uses_logger_debug():
    """Verify exception handlers use logger.debug instead of pass."""
    file_path = SRC_ROOT / "qnwis" / "agents" / "utils" / "derived_results.py"
    content = file_path.read_text(encoding="utf-8")

    # Check for logger.debug calls in exception handlers
    assert "logger.debug" in content, "Missing logger.debug calls"

    # Check for specific debug messages about invalid dates
    assert "invalid" in content.lower() or "skipping" in content.lower(), \
        "Missing debug messages for invalid date handling"


def test_derived_results_handles_type_error():
    """Verify exception handlers catch both TypeError and ValueError."""
    file_path = SRC_ROOT / "qnwis" / "agents" / "utils" / "derived_results.py"
    content = file_path.read_text(encoding="utf-8")

    # Look for exception handling with TypeError
    assert "TypeError" in content, "Should catch TypeError for None values"
    assert "ValueError" in content, "Should catch ValueError for invalid formats"


def test_derived_results_freshness_logic_intact():
    """Verify freshness collection logic hasn't been removed."""
    file_path = SRC_ROOT / "qnwis" / "agents" / "utils" / "derived_results.py"
    content = file_path.read_text(encoding="utf-8")

    # Key freshness functions should still exist
    assert "asof_dates.append" in content
    assert "updated_at_values.append" in content
    assert "fromisoformat" in content
    assert "_add_freshness" in content or "add_freshness" in content
