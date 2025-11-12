#!/usr/bin/env python3
"""Generate requirements.txt from pyproject.toml dependencies."""
from __future__ import annotations

import sys
from pathlib import Path

try:
    import tomllib  # Py3.11+
except ModuleNotFoundError:  # pragma: no cover
    print("Python 3.11+ required", file=sys.stderr)
    sys.exit(1)


def main() -> None:
    """Generate requirements.txt from pyproject.toml."""
    root = Path(__file__).resolve().parents[1]
    pyproject = root / "pyproject.toml"
    req = root / "requirements.txt"

    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    deps = data.get("project", {}).get("dependencies", [])
    header = [
        "# QNWIS Production Dependencies",
        "# Generated from pyproject.toml",
        "",
    ]
    req.write_text("\n".join(header + deps) + "\n", encoding="utf-8")
    print(f"Wrote {req.relative_to(root)} with {len(deps)} dependencies")


if __name__ == "__main__":
    main()
