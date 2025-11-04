from src.qnwis.data.deterministic import access as accessmod
from src.qnwis.data.deterministic import models as models_mod


def test_execute_sum_to_one_warning(monkeypatch):
    spec = models_mod.QuerySpec(
        id="q",
        title="t",
        description="d",
        source="csv",
        expected_unit="percent",
        params={"pattern": "x.csv"},
        constraints={"sum_to_one": True},
    )
    registry = type("R", (object,), {"get": lambda self, _: spec})()

    def fake_run_csv_query(s):
        return models_mod.QueryResult(
            query_id=s.id,
            rows=[models_mod.Row(data={"male_percent": 55.0}), models_mod.Row(data={"female_percent": 44.0})],
            unit="percent",
            provenance=models_mod.Provenance(
                source="csv",
                dataset_id="x",
                locator="x",
                fields=["male_percent", "female_percent"],
            ),
            freshness=models_mod.Freshness(asof_date="2024-01-01"),
        )

    monkeypatch.setattr(accessmod, "run_csv_query", fake_run_csv_query)
    result = accessmod.execute("q", registry)
    assert any("sum_to_one_violation" in warning for warning in result.warnings)


def test_execute_unit_mismatch(monkeypatch):
    spec = models_mod.QuerySpec(
        id="q2",
        title="t",
        description="d",
        source="csv",
        expected_unit="percent",
        params={"pattern": "y.csv"},
    )
    registry = type("R", (object,), {"get": lambda self, _: spec})()

    def fake_run_csv_query(s):
        return models_mod.QueryResult(
            query_id=s.id,
            rows=[],
            unit="count",
            provenance=models_mod.Provenance(
                source="csv",
                dataset_id="y",
                locator="y",
                fields=[],
            ),
            freshness=models_mod.Freshness(asof_date="2024-01-01"),
        )

    monkeypatch.setattr(accessmod, "run_csv_query", fake_run_csv_query)
    result = accessmod.execute("q2", registry)
    assert any("unit_mismatch" in warning for warning in result.warnings)
