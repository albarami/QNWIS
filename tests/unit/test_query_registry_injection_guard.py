"""Unit tests to verify QueryRegistry queries are parameterized and injection-safe."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.qnwis.data.deterministic.registry import QueryRegistry


def test_queries_are_parameterized():
    """
    Test that all queries in registry use parameterized patterns.

    This test ensures the deterministic data layer maintains its guarantee
    of no dynamic SQL concatenation or injection vulnerabilities.
    """
    # Find query directory
    query_dir = Path(__file__).resolve().parents[2] / "src" / "qnwis" / "data" / "queries"
    if not query_dir.exists():
        pytest.skip(f"Query directory not found: {query_dir}")

    registry = QueryRegistry(str(query_dir))
    registry.load_all()

    # Verify all queries use safe patterns
    for qid, spec in registry._items.items():
        # Check that query uses CSV source (deterministic)
        assert spec.source in {"csv", "world_bank"}, (
            f"Query {qid} uses non-deterministic source: {spec.source}"
        )

        # Check params structure (should be dict, not string concatenation)
        assert isinstance(spec.params, dict), (
            f"Query {qid} has non-dict params: {type(spec.params)}"
        )

        # If CSV source, verify pattern is parameterized
        if spec.source == "csv":
            pattern = spec.params.get("pattern", "")
            # Pattern should not contain SQL-like injection attempts
            dangerous_patterns = [";--", "'; DROP", "UNION SELECT", "/*", "*/"]
            for danger in dangerous_patterns:
                assert danger not in pattern, (
                    f"Query {qid} contains dangerous pattern: {danger}"
                )

            # Pattern should use safe file path references
            assert not pattern.startswith("/"), (
                f"Query {qid} uses absolute path: {pattern}"
            )
            assert ".." not in pattern, (
                f"Query {qid} uses path traversal: {pattern}"
            )


def test_query_specs_use_yaml_structure():
    """Test that queries are defined in YAML with structured parameters."""
    query_dir = Path(__file__).resolve().parents[2] / "src" / "qnwis" / "data" / "queries"
    if not query_dir.exists():
        pytest.skip(f"Query directory not found: {query_dir}")

    registry = QueryRegistry(str(query_dir))
    registry.load_all()

    # All queries should have required fields
    for qid, spec in registry._items.items():
        assert spec.id, f"Query {qid} missing id"
        assert spec.title, f"Query {qid} missing title"
        assert spec.description, f"Query {qid} missing description"
        assert spec.source, f"Query {qid} missing source"


def test_no_dynamic_sql_in_queries():
    """Test that queries don't contain dynamic SQL construction patterns."""
    query_dir = Path(__file__).resolve().parents[2] / "src" / "qnwis" / "data" / "queries"
    if not query_dir.exists():
        pytest.skip(f"Query directory not found: {query_dir}")

    # Read all YAML files directly
    yaml_files = list(query_dir.glob("*.yaml"))
    assert len(yaml_files) > 0, "No query YAML files found"

    for yaml_file in yaml_files:
        content = yaml_file.read_text(encoding="utf-8")

        # Check for SQL injection patterns
        dangerous_patterns = [
            "SELECT *",
            "'; DROP",
            "UNION SELECT",
            "-- ",
            "/*",
            "*/",
            "xp_cmdshell",
            "exec(",
            "execute(",
        ]

        for pattern in dangerous_patterns:
            assert pattern not in content, (
                f"Query file {yaml_file.name} contains dangerous pattern: {pattern}"
            )

        # Verify no Python string formatting in YAML
        assert "{" not in content or "{{" in content, (
            f"Query file {yaml_file.name} may contain Python string formatting"
        )


def test_query_registry_version_deterministic():
    """Test that QueryRegistry version is deterministic."""
    query_dir = Path(__file__).resolve().parents[2] / "src" / "qnwis" / "data" / "queries"
    if not query_dir.exists():
        pytest.skip(f"Query directory not found: {query_dir}")

    # Load registry twice
    registry1 = QueryRegistry(str(query_dir))
    registry1.load_all()
    version1 = registry1.version

    registry2 = QueryRegistry(str(query_dir))
    registry2.load_all()
    version2 = registry2.version

    # Versions should be identical (deterministic)
    assert version1 == version2, "QueryRegistry version is not deterministic"
    assert version1 != "unloaded", "QueryRegistry version not computed"


def test_query_params_no_user_input():
    """Test that query params don't accept raw user input."""
    query_dir = Path(__file__).resolve().parents[2] / "src" / "qnwis" / "data" / "queries"
    if not query_dir.exists():
        pytest.skip(f"Query directory not found: {query_dir}")

    registry = QueryRegistry(str(query_dir))
    registry.load_all()

    for qid, spec in registry._items.items():
        # Params should be predefined, not user-supplied
        if "pattern" in spec.params:
            pattern = spec.params["pattern"]
            # Pattern should be a static string, not a template
            assert isinstance(pattern, str), (
                f"Query {qid} pattern is not a string: {type(pattern)}"
            )
            # Should not contain variable substitution markers
            assert "${" not in pattern, (
                f"Query {qid} pattern contains variable substitution"
            )
            assert "$(" not in pattern, (
                f"Query {qid} pattern contains command substitution"
            )
