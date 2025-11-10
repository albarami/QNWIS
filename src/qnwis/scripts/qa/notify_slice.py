"""Step 29 notify slice runner for pre-commit + CI."""

from __future__ import annotations

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]


def _run(cmd: list[str]) -> None:
    """Run a single command, streaming output and failing fast."""
    print(f"[step29] Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=REPO_ROOT, check=False)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def main() -> None:
    """Execute the notify hardening slice."""
    lint_targets = [
        "src/qnwis/notify",
        "src/qnwis/api/routers",
        "src/qnwis/scripts/qa/ops_notify_gate.py",
    ]

    _run(["python", "-m", "ruff", "check", *lint_targets])
    _run(["python", "-m", "flake8", *lint_targets])
    _run(["python", "-m", "mypy", "--strict", "src/qnwis/notify", "src/qnwis/scripts/qa/ops_notify_gate.py"])
    _run(["python", "-m", "pytest", "-q", "tests/unit/notify", "tests/integration/notify"])


if __name__ == "__main__":
    main()
