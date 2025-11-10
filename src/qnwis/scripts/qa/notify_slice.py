"""Step 29 notify slice runner for pre-commit + CI."""

from __future__ import annotations

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
INCIDENTS_DIR = REPO_ROOT / "src" / "qnwis" / "incidents"


def _run(cmd: list[str]) -> None:
    """Run a single command, streaming output and failing fast."""
    print(f"[step29] Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=REPO_ROOT, check=False)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def main() -> None:
    """Execute the notify hardening slice."""
    notify_dir = "src/qnwis/notify"
    ops_gate_path = "src/qnwis/scripts/qa/ops_notify_gate.py"
    incidents_dir = (
        str(INCIDENTS_DIR.relative_to(REPO_ROOT))
        if INCIDENTS_DIR.exists()
        else None
    )

    lint_targets = [notify_dir, ops_gate_path]
    if incidents_dir:
        lint_targets.insert(1, incidents_dir)

    _run(["python", "-m", "ruff", "check", *lint_targets])
    _run(["python", "-m", "flake8", *lint_targets])
    mypy_targets = [notify_dir, ops_gate_path]
    if incidents_dir:
        mypy_targets.insert(1, incidents_dir)
    _run(["python", "-m", "mypy", "--strict", *mypy_targets])
    _run(["python", "-m", "pytest", "-q", "tests/unit/notify", "tests/integration/notify"])


if __name__ == "__main__":
    main()
