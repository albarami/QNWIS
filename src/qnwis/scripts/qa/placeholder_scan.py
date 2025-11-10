"""Placeholder scanning utilities shared by readiness gate and CI pre-checks."""

from __future__ import annotations

import argparse
import logging
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

import yaml

logger = logging.getLogger("readiness_gate.placeholders")

ROOT = Path(__file__).parents[4].resolve()
SRC_ROOT = ROOT / "src"
DEFAULT_SEARCH_ROOT = SRC_ROOT / "qnwis"
RULES_PATH = SRC_ROOT / "qnwis" / "scripts" / "qa" / "grep_rules.yml"


@dataclass(frozen=True)
class PlaceholderMatch:
    """Structured placeholder hit used across readiness tooling."""

    file: str
    line: int
    pattern: str
    snippet: str


def load_placeholder_patterns(rules_path: Path) -> list[str]:
    """Load placeholder regex patterns from grep_rules.yml."""
    if not rules_path.exists():
        logger.debug("Rules file %s missing; falling back to defaults", rules_path)
        return [
            r"^\s*(?:#\s*)?TODO\b.*$",
            r"^\s*(?:#\s*)?FIXME\b.*$",
            r"^\s*(?:#\s*)?HACK\b.*$",
            r"^\s*(?:#\s*)?XXX\b.*$",
            r"^\s*pass\s*$",
            r"^\s*NotImplemented\b.*$",
            r"^\s*raise\s+NotImplementedError\b.*$",
        ]

    data = yaml.safe_load(rules_path.read_text(encoding="utf-8")) or {}
    return data.get("disallow", {}).get("placeholders", {}).get("patterns", []) or []


def scan_placeholders(
    search_root: Path | None = None, *, limit: int = 50, rules_path: Path = RULES_PATH
) -> list[PlaceholderMatch]:
    """Return placeholder matches (up to limit) under the provided root."""
    root = (search_root or DEFAULT_SEARCH_ROOT).resolve()
    patterns = load_placeholder_patterns(rules_path)
    compiled = [re.compile(pattern, re.MULTILINE) for pattern in patterns]
    matches: list[PlaceholderMatch] = []

    for file_path in sorted(root.rglob("*.py")):
        text = file_path.read_text(encoding="utf-8", errors="ignore")
        for regex in compiled:
            for match in regex.finditer(text):
                line_no = text.count("\n", 0, match.start()) + 1
                snippet = text.splitlines()[line_no - 1].strip()
                matches.append(
                    PlaceholderMatch(
                        file=file_path.relative_to(ROOT).as_posix(),
                        line=line_no,
                        pattern=regex.pattern,
                        snippet=snippet,
                    )
                )
                if len(matches) >= limit:
                    return matches
    return matches


def as_dict(matches: Iterable[PlaceholderMatch]) -> list[dict[str, str | int]]:
    """Serialize matches for JSON outputs or GateResult payloads."""
    return [
        {"file": item.file, "line": item.line, "pattern": item.pattern, "snippet": item.snippet}
        for item in matches
    ]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Scan for placeholder code using grep_rules.yml.")
    parser.add_argument("--limit", type=int, default=50, help="Maximum violations to report")
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Override source root (defaults to src/qnwis)",
    )
    parser.add_argument(
        "--rules",
        type=Path,
        default=RULES_PATH,
        help="Path to grep_rules.yml (defaults to repo copy)",
    )
    args = parser.parse_args(argv)

    matches = scan_placeholders(args.root, limit=args.limit, rules_path=args.rules)
    if matches:
        for hit in matches:
            logger.error("%s:%d [%s] %s", hit.file, hit.line, hit.pattern, hit.snippet)
        logger.error("Found %d placeholder hits (limit %d).", len(matches), args.limit)
        return 1

    logger.info("No placeholder hits detected across %s", (args.root or DEFAULT_SEARCH_ROOT))
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    raise SystemExit(main())
