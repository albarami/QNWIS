"""Determinism scan utilities for alert stack hardening."""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from pathlib import Path
from re import Pattern

REPO_ROOT = Path(__file__).resolve().parents[4]

DEFAULT_BANNED_PATTERNS: dict[str, Pattern[str]] = {
    "datetime.now": re.compile(r"datetime\s*\.\s*now\s*\("),
    "time.time": re.compile(r"time\s*\.\s*time\s*\("),
    "random.*": re.compile(r"random\s*\.\s*[A-Za-z_]"),
}

NETWORK_BANNED_PATTERNS: dict[str, Pattern[str]] = {
    "import smtplib": re.compile(r"\bfrom\s+smtplib\b|\bimport\s+smtplib\b"),
    "import socket": re.compile(r"\bfrom\s+socket\b|\bimport\s+socket\b"),
    "import requests": re.compile(r"\bfrom\s+requests\b|\bimport\s+requests\b"),
    "import httpx": re.compile(r"\bfrom\s+httpx\b|\bimport\s+httpx\b"),
    "import urllib": re.compile(r"\bfrom\s+urllib(\.\w+)?\b|\bimport\s+urllib(\.\w+)?\b"),
    "import ssl": re.compile(r"\bfrom\s+ssl\b|\bimport\s+ssl\b"),
    "import webbrowser": re.compile(r"\bfrom\s+webbrowser\b|\bimport\s+webbrowser\b"),
    "import aiohttp": re.compile(r"\bfrom\s+aiohttp\b|\bimport\s+aiohttp\b"),
}

DR_SECURITY_PATTERNS: dict[str, Pattern[str]] = dict(DEFAULT_BANNED_PATTERNS)
DR_SECURITY_PATTERNS.update(
    {
        "subprocess_call": re.compile(
            r"\bsubprocess\.(run|popen|call|check_call|check_output)\s*\("
        ),
    }
)
for pattern_key in ("import smtplib", "import requests", "import httpx", "import aiohttp"):
    DR_SECURITY_PATTERNS[pattern_key] = NETWORK_BANNED_PATTERNS[pattern_key]


def _iter_python_files(target: Path) -> Iterable[Path]:
    if target.is_file() and target.suffix == ".py":
        yield target
        return

    if target.is_dir():
        for file_path in target.rglob("*.py"):
            if file_path.is_file():
                yield file_path


def scan_for_banned_calls(
    targets: Sequence[str | Path],
    patterns: dict[str, Pattern[str]] | None = None,
) -> list[dict[str, object]]:
    """Scan target paths for banned patterns."""
    regexes = patterns or DEFAULT_BANNED_PATTERNS
    violations: list[dict[str, object]] = []

    for target in targets:
        path = Path(target)
        if not path.exists():
            continue

        for file_path in _iter_python_files(path):
            try:
                text = file_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                text = file_path.read_text(encoding="utf-8", errors="ignore")

            for lineno, line in enumerate(text.splitlines(), 1):
                stripped = line.strip()
                if not stripped:
                    continue

                for label, regex in regexes.items():
                    if regex.search(line):
                        try:
                            rel = file_path.relative_to(REPO_ROOT).as_posix()
                        except ValueError:
                            rel = str(file_path)

                        violations.append(
                            {
                                "file": rel,
                                "line": lineno,
                                "pattern": label,
                                "snippet": stripped[:200],
                            }
                        )
                        break

    return violations
