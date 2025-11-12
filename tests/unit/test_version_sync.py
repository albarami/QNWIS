from __future__ import annotations
import tomllib
from pathlib import Path
import importlib.util
import types


def load_module(path: Path) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location("qnwis_init", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)  # type: ignore[assignment]
    return mod


def test_version_matches_pyproject():
    root = Path(__file__).resolve().parents[2]
    data = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    expected = data["project"]["version"]
    mod = load_module(root / "src" / "qnwis" / "__init__.py")
    assert getattr(mod, "__version__", None) == expected
