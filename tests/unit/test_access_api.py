import pytest

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


def test_execute_world_bank_branch(monkeypatch):
    spec = models_mod.QuerySpec(
        id="q3",
        title="t",
        description="d",
        source="world_bank",
        expected_unit="percent",
        params={"indicator_id": "SL.TLF.CACT.FE.ZS"},
    )
    registry = type("R", (object,), {"get": lambda self, _: spec})()

    def fake_world_bank_query(s):
        return models_mod.QueryResult(
            query_id=s.id,
            rows=[models_mod.Row(data={"year": 2024, "value": 55.0})],
            unit="percent",
            provenance=models_mod.Provenance(
                source="world_bank",
                dataset_id="wb",
                locator="wb:SL.TLF.CACT.FE.ZS",
                fields=["year", "value"],
            ),
            freshness=models_mod.Freshness(asof_date="auto"),
        )

    monkeypatch.setattr(accessmod, "run_world_bank_query", fake_world_bank_query)
    monkeypatch.setattr(accessmod, "verify_result", lambda spec, res: ["ok"])

    result = accessmod.execute("q3", registry)
    assert result.rows[0].data["value"] == 55.0
    assert result.warnings == ["ok"]


def test_execute_unknown_source_raises(monkeypatch):
    spec = type(
        "Spec",
        (object,),
        {
            "id": "q4",
            "source": "unknown",
            "constraints": {},
            "expected_unit": "percent",
        },
    )()
    registry = type("R", (object,), {"get": lambda self, _: spec})()
    with pytest.raises(ValueError):
        accessmod.execute("q4", registry)
