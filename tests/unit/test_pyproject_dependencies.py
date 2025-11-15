from __future__ import annotations
import tomllib
from pathlib import Path


def test_pyproject_has_required_dependencies():
    root = Path(__file__).resolve().parents[2]
    data = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    deps = set(data["project"]["dependencies"])
    required = {
        # key packages must appear as prefixes in the list entries:
        "fastapi",
        "anthropic",
        "openai",
        "tiktoken",
        "langgraph",
        "langchain",
        "langchain-core",
        "sqlalchemy",
        "redis",
    }
    # match by startswith to allow version spec
    dep_names = {d.split(">", 1)[0].split("[", 1)[0] for d in deps}
    missing = {r for r in required if not any(n.startswith(r) for n in dep_names)}
    assert not missing, f"Missing deps in pyproject: {sorted(missing)}"


def test_extras_defined():
    root = Path(__file__).resolve().parents[2]
    data = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    extras = data["project"]["optional-dependencies"]
    for k in ("dev", "production", "all"):
        assert k in extras
