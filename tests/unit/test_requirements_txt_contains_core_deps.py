from __future__ import annotations
from pathlib import Path


def test_requirements_contains_core_packages():
    root = Path(__file__).resolve().parents[2]
    text = (root / "requirements.txt").read_text(encoding="utf-8")
    for pkg in ["anthropic", "openai", "chainlit", "langgraph", "langchain-core", "fastapi"]:
        assert pkg in text, f"{pkg} not listed in requirements.txt"
