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
