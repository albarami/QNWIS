"""Ensure SQL text is not built via f-strings (prevents injection)."""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Iterable

SQL_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE | re.DOTALL)
    for pattern in (
        r"\bSELECT\b.+\bFROM\b",
        r"\bINSERT\b.+\bINTO\b",
        r"\bUPDATE\b.+\bSET\b",
        r"\bDELETE\b.+\bFROM\b",
        r"\bCREATE\b.+\b(TABLE|VIEW|INDEX|MATERIALIZED)\b",
        r"\bDROP\b.+\b(TABLE|VIEW|INDEX|MATERIALIZED)\b",
        r"\bALTER\b.+\b(TABLE|VIEW|INDEX|SCHEMA)\b",
    )
)


class FStringSQLVisitor(ast.NodeVisitor):
    """AST visitor that records f-strings containing SQL keywords."""

    def __init__(self, source: str, path: Path) -> None:
        self._source = source
        self._path = path
        self.offenses: list[str] = []

    def visit_JoinedStr(self, node: ast.JoinedStr) -> None:  # noqa: N802 (ast API)
        """Capture any f-string literal that includes SQL keywords."""
        literal_parts = [
            part.value
            for part in node.values
            if isinstance(part, ast.Constant) and isinstance(part.value, str)
        ]
        literal = "".join(literal_parts)
        if literal and _looks_like_sql(literal):
            snippet = ast.get_source_segment(self._source, node) or literal
            self.offenses.append(f"{self._path}:{node.lineno}: {snippet.strip()}")
        self.generic_visit(node)


def _looks_like_sql(value: str) -> bool:
    """Return True if the literal contains an SQL statement signature."""
    normalized = " ".join(value.split())
    return any(pattern.search(normalized) for pattern in SQL_PATTERNS)


def _scan_file(path: Path) -> Iterable[str]:
    """Return an iterable of offenses for a Python source file."""
    try:
        source = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return []
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as exc:  # pragma: no cover - invalid files should fail loudly
        raise AssertionError(f"Failed to parse {path}: {exc}") from exc
    visitor = FStringSQLVisitor(source, path)
    visitor.visit(tree)
    return visitor.offenses


def test_no_fstring_sql_in_source() -> None:
    """Scan source files for actual f-strings containing SQL keywords."""
    offenses: list[str] = []
    for path in Path("src").rglob("*.py"):
        offenses.extend(_scan_file(path))
    assert not offenses, "F-string SQL detected:\n" + "\n".join(offenses)
