import pytest

from src.qnwis.data.deterministic.registry import QueryRegistry


def test_registry_load_and_get(tmp_path):
    registry_dir = tmp_path / "q"
    registry_dir.mkdir()
    (registry_dir / "a.yaml").write_text(
        "id: q1\ntitle: T\ndescription: D\nsource: csv\nparams: {pattern: 'x.csv'}\n",
        encoding="utf-8",
    )
    registry = QueryRegistry(str(registry_dir))
    registry.load_all()
    assert registry.get("q1").id == "q1"


def test_registry_missing_directory(tmp_path):
    missing = tmp_path / "missing"
    registry = QueryRegistry(str(missing))
    with pytest.raises(FileNotFoundError):
        registry.load_all()


def test_registry_duplicate_ids(tmp_path):
    registry_dir = tmp_path / "dupe"
    registry_dir.mkdir()
    payload = "id: shared\ntitle: T\ndescription: D\nsource: csv\nparams: {pattern: 'x.csv'}\n"
    (registry_dir / "a.yaml").write_text(payload, encoding="utf-8")
    (registry_dir / "b.yaml").write_text(payload, encoding="utf-8")
    registry = QueryRegistry(str(registry_dir))
    with pytest.raises(ValueError, match="Duplicate QuerySpec"):
        registry.load_all()


def test_registry_all_ids(tmp_path):
    registry_dir = tmp_path / "ids"
    registry_dir.mkdir()
    (registry_dir / "a.yaml").write_text(
        "id: q2\ntitle: T\ndescription: D\nsource: csv\nparams: {pattern: 'x.csv'}\n",
        encoding="utf-8",
    )
    (registry_dir / "b.yaml").write_text(
        "id: q1\ntitle: T\ndescription: D\nsource: csv\nparams: {pattern: 'y.csv'}\n",
        encoding="utf-8",
    )
    registry = QueryRegistry(str(registry_dir))
    registry.load_all()
    assert sorted(registry.all_ids()) == ["q1", "q2"]
