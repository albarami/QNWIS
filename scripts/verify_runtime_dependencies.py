#!/usr/bin/env python3
"""
Runtime import sanity check for critical libraries.
Run manually after 'pip install -e .[all]'.

Exits non-zero if any import fails.
"""
from __future__ import annotations

import importlib
import sys

REQUIRED = [
    "fastapi",
    "httpx",
    "anthropic",
    "openai",
    "tiktoken",
    "langgraph",
    "langchain",
    "langchain_core",
    "chainlit",
    "sqlalchemy",
    "alembic",
    "redis",
    "numpy",
    "pandas",
    "scipy",
]


def main() -> None:
    """Verify all critical imports succeed."""
    failures = []
    for mod in REQUIRED:
        try:
            importlib.import_module(mod)
        except Exception as exc:  # noqa: BLE001
            failures.append((mod, repr(exc)))
    if failures:
        for mod, err in failures:
            print(f"❌ import {mod} failed: {err}", file=sys.stderr)
        sys.exit(1)
    print("✅ All critical imports succeeded.")


if __name__ == "__main__":
    main()
