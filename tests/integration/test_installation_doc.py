from __future__ import annotations
from pathlib import Path


def test_installation_doc_has_key_commands():
    root = Path(__file__).resolve().parents[2]
    doc = (root / "docs" / "INSTALLATION.md").read_text(encoding="utf-8")
    for phrase in [
        'pip install -e ".[dev]"',
        "pip install -r requirements.txt",
        "verify_runtime_dependencies.py",
        "docker build",
    ]:
        assert phrase in doc
