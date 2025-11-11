"""
Step 30 Ops Console slice runner.

Runs lint, type, and targeted test suites with an optional fast-path that
skips execution when no Step 30 files are touched.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
PYTHON = sys.executable

LINT_TARGETS = [
    "src/qnwis/ops_console",
    "src/qnwis/scripts/qa/ops_console_gate.py",
    "grafana/dashboards",
]
MYPY_TARGETS = [
    "src/qnwis/ops_console",
    "src/qnwis/scripts/qa/ops_console_gate.py",
]
PYTEST_TARGETS = [
    "tests/unit/ops_console",
    "tests/integration/ops_console",
]

FAST_PATH_PREFIXES = (
    "src/qnwis/ops_console",
    "tests/unit/ops_console",
    "tests/integration/ops_console",
    "src/qnwis/scripts/qa/ops_console_gate.py",
    "src/qnwis/scripts/qa/step30_ops_console_slice.py",
    "src/qnwis/scripts/qa/readiness_gate.py",
    "src/qnwis/docs/audit/ops",
    "grafana/dashboards",
    "docs/runbooks/ops_console_user_guide.md",
    "docs/ops/step30_ops_console.md",
    "STEP30_OPS_CONSOLE_IMPLEMENTATION_COMPLETE.md",
    "OPS_UI_SUMMARY.md",
    ".github/workflows/ci_readiness.yml",
    "pyproject.toml",
    ".flake8",
    "mypy.ini",
    ".pre-commit-config.yaml",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Step 30 Ops Console pre-commit slice.")
    parser.add_argument(
        "--files",
        nargs="*",
        help="Optional list of changed files to enable fast-path skip.",
    )
    return parser.parse_args()


def _normalize(path: str) -> str:
    return str(Path(path).as_posix()).lower()


def should_run(full_list: list[str] | None) -> bool:
    if not full_list:
        return True
    return any(
        _normalize(file_path).startswith(prefix)
        for file_path in full_list
        for prefix in FAST_PATH_PREFIXES
    )


def run_step(name: str, command: list[str]) -> None:
    print(f"[step30] {name}: {' '.join(command)}", flush=True)
    result = subprocess.run(command, cwd=REPO_ROOT, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"{name} failed with exit code {result.returncode}")


def main() -> int:
    args = parse_args()
    files = args.files or []
    if args.files is not None and not should_run(files):
        print("[step30] Fast-path: no relevant files touched; skipping slice.")
        return 0

    run_step("ruff", [PYTHON, "-m", "ruff", "check", *LINT_TARGETS])
    run_step("flake8", [PYTHON, "-m", "flake8", *LINT_TARGETS])
    run_step("mypy", [PYTHON, "-m", "mypy", "--strict", *MYPY_TARGETS])
    run_step("pytest", [PYTHON, "-m", "pytest", "-q", *PYTEST_TARGETS])

    print("[step30] Slice completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
