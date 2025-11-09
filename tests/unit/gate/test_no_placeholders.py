"""Test that production code has no placeholder patterns."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

SRC_ROOT = Path(__file__).parents[3] / "src" / "qnwis"


def test_no_pass_statements():
    """Assert 0 bare pass statements in production code."""
    pattern = re.compile(r"^\s*pass\s*$", re.MULTILINE)
    violations = []

    for py_file in SRC_ROOT.rglob("*.py"):
        content = py_file.read_text(encoding="utf-8", errors="ignore")
        matches = pattern.findall(content)
        if matches:
            violations.append(str(py_file.relative_to(SRC_ROOT.parent)))

    assert not violations, f"Found bare 'pass' statements in: {violations}"


def test_no_not_implemented_error():
    """Assert 0 NotImplementedError raises in production code."""
    pattern = re.compile(r"raise\s+NotImplementedError", re.IGNORECASE)
    violations = []

    for py_file in SRC_ROOT.rglob("*.py"):
        content = py_file.read_text(encoding="utf-8", errors="ignore")
        if pattern.search(content):
            violations.append(str(py_file.relative_to(SRC_ROOT.parent)))

    assert not violations, f"Found 'raise NotImplementedError' in: {violations}"


def test_no_todo_fixme_comments():
    """Assert 0 TODO/FIXME comments in production code."""
    pattern = re.compile(r"#\s*(TODO|FIXME)\b", re.IGNORECASE)
    violations = []

    for py_file in SRC_ROOT.rglob("*.py"):
        content = py_file.read_text(encoding="utf-8", errors="ignore")
        matches = pattern.findall(content)
        if matches:
            violations.append(str(py_file.relative_to(SRC_ROOT.parent)))

    # Allow TODO/FIXME in test files and scripts, but not in production
    production_violations = [
        v for v in violations
        if not any(x in v for x in ["test_", "scripts/"])
    ]

    assert not production_violations, f"Found TODO/FIXME in production code: {production_violations}"


@pytest.mark.parametrize("pattern,description", [
    (r"^\s*pass\s*$", "bare pass statement"),
    (r"raise\s+NotImplementedError", "NotImplementedError"),
    (r"#\s*HACK\b", "HACK comment"),
    (r"#\s*XXX\b", "XXX comment"),
])
def test_no_placeholder_patterns(pattern, description):
    """Parametrized test for various placeholder patterns."""
    regex = re.compile(pattern, re.MULTILINE | re.IGNORECASE)
    violations = []

    for py_file in SRC_ROOT.rglob("*.py"):
        # Skip __pycache__ and test files
        if "__pycache__" in str(py_file) or "test_" in py_file.name:
            continue

        content = py_file.read_text(encoding="utf-8", errors="ignore")
        if regex.search(content):
            violations.append(str(py_file.relative_to(SRC_ROOT.parent)))

    assert not violations, f"Found {description} in: {violations}"
