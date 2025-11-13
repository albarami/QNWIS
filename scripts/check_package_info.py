#!/usr/bin/env python3
"""Quick package metadata check."""
from __future__ import annotations

import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    print("Python 3.11+ required", file=sys.stderr)
    sys.exit(1)

root = Path(__file__).resolve().parents[1]
pyproject = root / "pyproject.toml"
data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
project = data["project"]
optional = project["optional-dependencies"]

print(f"📦 Package: {project['name']}")
print(f"📌 Version: {project['version']}")
print(f"🐍 Python: {project['requires-python']}")
print(f"📚 Core dependencies: {len(project['dependencies'])}")
print(f"🛠️  Dev dependencies: {len(optional['dev'])}")
print(f"🚀 Production dependencies: {len(optional['production'])}")
print(f"✅ All extras: {optional['all']}")
