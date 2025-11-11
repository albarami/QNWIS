"""
Step 31 SLO slice runner.

Runs lint, type, and targeted SLO tests with an optional fast-path skip.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
PYTHON = sys.executable

LINT_TARGETS = [
    "src/qnwis/slo",
    "src/qnwis/scripts/qa/rg6_resilience_gate.py",
    "src/qnwis/scripts/qa/step31_slo_slice.py",
    "tests/unit/slo",
    "tests/integration/slo",
]
MYPY_TARGETS = [
    "src/qnwis/slo",
    "src/qnwis/scripts/qa/rg6_resilience_gate.py",
]
PYTEST_TARGETS = [
    "tests/unit/slo",
    "tests/integration/slo",
]
FAST_PATH_PREFIXES = (
    "src/qnwis/slo",
    "src/qnwis/scripts/qa/rg6_resilience_gate.py",
    "src/qnwis/scripts/qa/step31_slo_slice.py",
    "src/qnwis/scripts/qa/readiness_gate.py",
    "docs/ops/step31_slo_error_budgets.md",
    "docs/audit/rg6",
    "slo",
    "tests/unit/slo",
    "tests/integration/slo",
    ".github/workflows/ci_readiness.yml",
    ".pre-commit-config.yaml",
    "pyproject.toml",
    ".flake8",
    "mypy.ini",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Step 31 SLO pre-commit slice.")
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
    lowered_prefixes = tuple(_normalize(prefix) for prefix in FAST_PATH_PREFIXES)
    return any(
        _normalize(path).startswith(prefix)
        for path in file_list
        for prefix in lowered_prefixes
    )


def run_step(name: str, command: list[str]) -> None:
    print(f"[step31] {name}: {' '.join(command)}", flush=True)
    result = subprocess.run(command, cwd=REPO_ROOT, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"{name} failed with exit code {result.returncode}")


def main() -> int:
    args = parse_args()
    files = args.files or []
    if args.files is not None and not should_run(files):
        print("[step31] Fast-path: no SLO/RG-6 files changed; skipping slice.")
        return 0

    run_step("ruff", [PYTHON, "-m", "ruff", "check", *LINT_TARGETS])
    run_step("flake8", [PYTHON, "-m", "flake8", *LINT_TARGETS])
    run_step("mypy", [PYTHON, "-m", "mypy", "--strict", *MYPY_TARGETS])
    run_step("pytest", [PYTHON, "-m", "pytest", "-q", *PYTEST_TARGETS])

    print("[step31] Slice completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
