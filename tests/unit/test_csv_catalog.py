from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from src.qnwis.data.connectors import csv_catalog
from src.qnwis.data.deterministic.models import QuerySpec


def _override_base(monkeypatch: pytest.MonkeyPatch, path: Path) -> None:
    """Point the CSV catalog base to a temporary directory."""
    monkeypatch.setattr(csv_catalog, "BASE", path)


def build_spec(pattern: str, params: dict[str, object] | None = None) -> QuerySpec:
    """Helper to construct a CSV QuerySpec for tests."""
    merged_params: dict[str, object] = {"pattern": pattern}
    if params:
        merged_params.update(params)
    return QuerySpec(
        id="test",
        title="Test CSV",
        description="d",
        source="csv",
        expected_unit="percent",
        params=merged_params,
    )


def test_csv_reader_semicolon_and_cast(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    csv_path = tmp_path / "employed.csv"
    csv_path.write_text(
        "year;male_percent;female_percent;total_percent\n2023;60.0;40.0;100.0\n",
        encoding="utf-8",
    )
    _override_base(monkeypatch, tmp_path)
    spec = build_spec(
        csv_path.name,
        {"select": ["year", "male_percent", "female_percent", "total_percent"], "year": 2023},
    )

    result = csv_catalog.run_csv_query(spec)

    assert result.rows
    assert result.rows[0].data["male_percent"] == 60.0
    assert result.provenance.license == csv_catalog.QATAR_OPEN_DATA_LICENSE


def test_csv_reader_to_percent_and_max_rows(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    csv_path = tmp_path / "share.csv"
    csv_path.write_text(
        textwrap.dedent(
            """\
            year,value
            2022,0.25
            2023,0.5
            """
        ),
        encoding="utf-8",
    )
    _override_base(monkeypatch, tmp_path)
    spec = build_spec(csv_path.name, {"max_rows": 1, "to_percent": True})

    result = csv_catalog.run_csv_query(spec)

    assert len(result.rows) == 1
    assert result.rows[0].data["value"] == pytest.approx(25.0)


def test_csv_reader_timeout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    csv_path = tmp_path / "slow.csv"
    csv_path.write_text("year,value\n2023,1\n", encoding="utf-8")
    _override_base(monkeypatch, tmp_path)
    spec = build_spec(csv_path.name, {"timeout_s": 0.5})

    call_count = {"count": 0}

    def fake_perf_counter() -> float:
        call_count["count"] += 1
        # Increase rapidly to exceed timeout after first row
        return float(call_count["count"])

    monkeypatch.setattr(csv_catalog.time, "perf_counter", fake_perf_counter)

    with pytest.raises(TimeoutError):
        csv_catalog.run_csv_query(spec)


def test_csv_reader_no_rows(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    csv_path = tmp_path / "empty.csv"
    csv_path.write_text("year,value\n2023,42\n", encoding="utf-8")
    _override_base(monkeypatch, tmp_path)
    spec = build_spec(csv_path.name, {"year": 2022})

    with pytest.raises(ValueError, match="No rows matched CSV query"):
        csv_catalog.run_csv_query(spec)
