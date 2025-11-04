from __future__ import annotations

import pandas as pd
import pytest

from src.qnwis.data.connectors import world_bank_det
from src.qnwis.data.deterministic.models import QuerySpec


def _make_spec(params: dict[str, object]) -> QuerySpec:
    return QuerySpec(
        id="wb",
        title="World Bank",
        description="test",
        source="world_bank",
        expected_unit="percent",
        params=params,
    )


def test_world_bank_query_success(monkeypatch: pytest.MonkeyPatch) -> None:
    expected_records = [{"country": "QAT", "year": 2023, "value": 1.23, "indicator": "NY.GDP"}]

    class DummyIntegrator:
        def get_indicator(
            self,
            *,
            indicator: str,
            countries: list[str],
            year: int | None,
            start_year: int | None,
            end_year: int | None,
            timeout_s: float | None,
            max_rows: int | None,
        ) -> pd.DataFrame:
            assert indicator == "NY.GDP"
            assert countries == ["QAT"]
            assert timeout_s == pytest.approx(1.5)
            assert max_rows == 10
            return pd.DataFrame(expected_records)

    monkeypatch.setattr(world_bank_det, "UDCGlobalDataIntegrator", DummyIntegrator)
    spec = _make_spec(
        {"indicator": "NY.GDP", "countries": ["QAT"], "timeout_s": 1.5, "max_rows": 10}
    )

    result = world_bank_det.run_world_bank_query(spec)

    assert result.rows[0].data["country"] == "QAT"
    assert result.provenance.license == world_bank_det.WORLD_BANK_LICENSE


def test_world_bank_query_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyIntegrator:
        def get_indicator(self, **_: object) -> pd.DataFrame:
            return pd.DataFrame()

    monkeypatch.setattr(world_bank_det, "UDCGlobalDataIntegrator", DummyIntegrator)
    spec = _make_spec({"indicator": "NY.GDP"})

    with pytest.raises(ValueError, match="returned no data"):
        world_bank_det.run_world_bank_query(spec)


def test_world_bank_query_invalid_country() -> None:
    spec = _make_spec({"indicator": "NY.GDP", "countries": ["QA"]})
    with pytest.raises(ValueError, match="ISO-3"):
        world_bank_det.run_world_bank_query(spec)


def test_world_bank_missing_indicator() -> None:
    spec = _make_spec({})
    with pytest.raises(ValueError, match="indicator"):
        world_bank_det.run_world_bank_query(spec)
