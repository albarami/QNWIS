"""
Step 33 Business Continuity slice runner.

Runs linting, typing, and continuity-specific tests to protect the RG-8 gate.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
PYTHON = sys.executable

LINT_TARGETS = [
    "src/qnwis/continuity",
    "src/qnwis/api/routers/continuity.py",
    "src/qnwis/cli/qnwis_continuity.py",
    "src/qnwis/scripts/qa/rg8_continuity_gate.py",
    "src/qnwis/scripts/qa/step33_continuity_slice.py",
]

MYPY_TARGETS = [
    "src/qnwis/continuity",
    "src/qnwis/api/routers/continuity.py",
    "src/qnwis/cli/qnwis_continuity.py",
    "src/qnwis/scripts/qa/rg8_continuity_gate.py",
    "src/qnwis/scripts/qa/step33_continuity_slice.py",
]

PYTEST_TARGETS = [
    "tests/unit/continuity",
    "tests/integration/continuity",
]

FAST_PATH_PREFIXES = tuple(
    str(Path(prefix).as_posix()).lower()
    for prefix in (
        "src/qnwis/continuity",
        "src/qnwis/api/routers/continuity.py",
        "src/qnwis/cli/qnwis_continuity.py",
        "src/qnwis/scripts/qa/rg8_continuity_gate.py",
        "src/qnwis/scripts/qa/step33_continuity_slice.py",
        "src/qnwis/scripts/qa/readiness_gate.py",
        "docs/ops/step33_continuity_failover.md",
        "RUN_RG8_GATE.md",
        "STEP33_CONTINUITY_IMPLEMENTATION_COMPLETE.md",
        "tests/unit/continuity",
        "tests/integration/continuity",
        ".github/workflows/ci_readiness.yml",
        ".pre-commit-config.yaml",
        "pyproject.toml",
        ".flake8",
        "mypy.ini",
    )
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Step 33 continuity pre-commit slice.")
    parser.add_argument(
        "--files",
        nargs="*",
        help="Optional list of changed files to enable fast-path skip.",
    )
    return parser.parse_args()


def _normalize(path: str) -> str:
    return str(Path(path).as_posix()).lower()


def should_run(file_list: list[str] | None) -> bool:
    if not file_list:
        return True
    return any(
        _normalize(path).startswith(prefix)
        for path in file_list
        for prefix in FAST_PATH_PREFIXES
    )


def run_step(name: str, command: list[str]) -> None:
    print(f"[step33] {name}: {' '.join(command)}", flush=True)
    result = subprocess.run(command, cwd=REPO_ROOT, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"{name} failed with exit code {result.returncode}")


def main() -> int:
    args = parse_args()
    files = args.files or []
    if args.files is not None and not should_run(files):
        print("[step33] Fast-path: no continuity/RG-8 files changed; skipping slice.")
        return 0

    run_step("ruff", [PYTHON, "-m", "ruff", "check", *LINT_TARGETS])
    run_step("flake8", [PYTHON, "-m", "flake8", *LINT_TARGETS])
    run_step("mypy", [PYTHON, "-m", "mypy", "--strict", *MYPY_TARGETS])
    run_step("pytest", [PYTHON, "-m", "pytest", "-q", *PYTEST_TARGETS])

    print("[step33] Slice completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
