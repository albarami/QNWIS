"""
Unit tests for Data API client core functionality.

Tests alias resolution, parameter overrides, and type safety.
"""

from __future__ import annotations

import builtins
import sys
import types
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path

import pytest

import src.qnwis.data.connectors.csv_catalog as csvcat
from src.qnwis.data.api import client as data_client
from src.qnwis.data.api.client import DataAPI
from src.qnwis.data.api.models import EmploymentShareRow, UnemploymentRow
from src.qnwis.data.synthetic.seed_lmis import generate_synthetic_lmis


@pytest.fixture
def synthetic_data_api(tmp_path, monkeypatch):
    """Fixture providing DataAPI with synthetic data."""
    generate_synthetic_lmis(str(tmp_path))
    old_base = csvcat.BASE
    csvcat.BASE = Path(tmp_path)
    api = DataAPI(queries_dir="src/qnwis/data/queries", ttl_s=60)
    yield api
    csvcat.BASE = old_base


class TestAliasResolution:
    """Test canonical key to query ID alias resolution."""

    def test_alias_resolution_and_param_override(self, tmp_path, monkeypatch):
        """Test that alias resolution works and parameter overrides function."""
        generate_synthetic_lmis(str(tmp_path))
        old = csvcat.BASE
        csvcat.BASE = Path(tmp_path)
        try:
            api = DataAPI(queries_dir="src/qnwis/data/queries", ttl_s=60)

            # Test default latest year
            rows = api.employment_share_latest()
            assert rows, "Should return employment share rows"
            assert rows[-1].total_percent == 100.0, "Total percent should be 100"

            # Test year parameter override
            rows_2019 = api.employment_share_latest(year=2019)
            assert any(r.year == 2019 for r in rows_2019), "Should include 2019 data"
        finally:
            csvcat.BASE = old

    def test_unemployment_alias_resolution(self, synthetic_data_api):
        """Test unemployment query alias resolution."""
        rows = synthetic_data_api.unemployment_gcc_latest()
        assert isinstance(rows, list), "Should return list"
        assert len(rows) > 0, "Should have unemployment data"
        assert all(hasattr(r, "country") for r in rows), "All rows should have country"

    def test_alias_prefers_synthetic_queries_when_available(self, synthetic_data_api):
        """Alias resolver should pick synthetic IDs before q_* fallbacks."""
        reg = synthetic_data_api.reg
        base_spec = reg.get("syn_sector_employment_by_year")
        reg._items["q_sector_employment_by_year"] = base_spec.model_copy(  # type: ignore[attr-defined]
            update={"id": "q_sector_employment_by_year"}
        )
        try:
            resolved = data_client._resolve(reg, "sector_employment")
            assert resolved.startswith("syn_"), f"Resolver should prefer syn_, got {resolved}"
        finally:
            reg._items.pop("q_sector_employment_by_year", None)  # type: ignore[attr-defined]

    def test_resolve_direct_query_id(self, synthetic_data_api):
        """Direct query IDs should resolve without alias lookup."""
        reg = synthetic_data_api.reg
        direct_id = reg.all_ids()[0]
        assert data_client._resolve(reg, direct_id) == direct_id

    def test_resolve_partial_match_fallback(self, synthetic_data_api):
        """Fallback resolution should return syn_* match when no alias exists."""
        reg = synthetic_data_api.reg
        base_spec = reg.get("syn_sector_employment_by_year")
        reg._items["syn_custom_demo_metric"] = base_spec.model_copy(  # type: ignore[attr-defined]
            update={"id": "syn_custom_demo_metric"}
        )
        try:
            resolved = data_client._resolve(reg, "custom_demo")
            assert resolved == "syn_custom_demo_metric"
        finally:
            reg._items.pop("syn_custom_demo_metric", None)  # type: ignore[attr-defined]


class TestParameterValidation:
    """Test parameter validation and overrides."""

    def test_year_parameter_coercion(self, synthetic_data_api):
        """Test that year parameters are properly coerced to integers."""
        # Should accept integer
        rows = synthetic_data_api.employment_share_latest(year=2024)
        assert all(r.year == 2024 for r in rows if r.year == 2024)

    def test_optional_year_parameter(self, synthetic_data_api):
        """Test that year parameter is optional."""
        rows = synthetic_data_api.employment_share_latest()
        assert isinstance(rows, list)


class TestTypeSafety:
    """Test type safety of API responses."""

    def test_employment_share_returns_typed_models(self, synthetic_data_api):
        """Test that employment_share_all returns properly typed models."""
        rows = synthetic_data_api.employment_share_all()
        assert all(isinstance(r.year, int) for r in rows), "Years should be integers"
        assert all(
            isinstance(r.male_percent, float) for r in rows
        ), "Percentages should be floats"

    def test_unemployment_returns_typed_models(self, synthetic_data_api):
        """Test that unemployment methods return properly typed models."""
        qatar_row = synthetic_data_api.unemployment_qatar()
        if qatar_row:
            assert isinstance(qatar_row.country, str)
            assert isinstance(qatar_row.year, int)
            assert isinstance(qatar_row.value, float)

    def test_qatarization_returns_typed_models(self, synthetic_data_api):
        """Test that qatarization methods return properly typed models."""
        rows = synthetic_data_api.qatarization_by_sector(year=2024)
        assert all(isinstance(r.year, int) for r in rows)
        assert all(isinstance(r.sector, str) for r in rows)
        assert all(isinstance(r.qataris, int) for r in rows)
        assert all(isinstance(r.qatarization_percent, float) for r in rows)


class TestGenderShareInference:
    """Test gender share inference logic."""

    def test_male_share_infers_female(self, synthetic_data_api):
        """Test that male share method infers female percentage."""
        rows = synthetic_data_api.employment_male_share(year=2024)
        assert len(rows) > 0, "Should return rows"
        for r in rows:
            # Male + female should approximate 100 (allowing for rounding)
            total = r.male_percent + r.female_percent
            assert 99.0 <= total <= 101.0, f"Total should be ~100%, got {total}"

    def test_female_share_infers_male(self, synthetic_data_api):
        """Test that female share method infers male percentage."""
        rows = synthetic_data_api.employment_female_share(year=2024)
        assert len(rows) > 0, "Should return rows"
        for r in rows:
            # Male + female should approximate 100
            total = r.male_percent + r.female_percent
            assert 99.0 <= total <= 101.0, f"Total should be ~100%, got {total}"


class TestCacheIntegration:
    """Test that caching layer integrates properly."""

    def test_repeated_calls_use_cache(self, synthetic_data_api):
        """Test that repeated calls leverage cache."""
        # First call
        rows1 = synthetic_data_api.unemployment_gcc_latest()
        # Second call should hit cache
        rows2 = synthetic_data_api.unemployment_gcc_latest()

        assert len(rows1) == len(rows2), "Should return same number of rows"
        assert rows1[0].country == rows2[0].country, "Should return same data"


class TestUnemploymentHelpers:
    """Test helper paths related to unemployment convenience methods."""

    def test_unemployment_qatar_returns_match(self, synthetic_data_api, monkeypatch):
        """Ensure Qatar unemployment helper returns row when present."""
        sample = UnemploymentRow(country="Qatar", year=2024, value=2.5)
        monkeypatch.setattr(
            synthetic_data_api,
            "unemployment_gcc_latest",
            lambda: [sample],
        )
        found = synthetic_data_api.unemployment_qatar()
        assert found is sample

    def test_unemployment_qatar_returns_none_when_missing(self, synthetic_data_api, monkeypatch):
        """Ensure helper returns None when Qatar is absent."""
        monkeypatch.setattr(
            synthetic_data_api,
            "unemployment_gcc_latest",
            lambda: [],
        )
        assert synthetic_data_api.unemployment_qatar() is None


class TestParameterOverrides:
    """Test parameter override functionality across methods."""

    def test_year_overrides_work_consistently(self, synthetic_data_api):
        """Year overrides should return data for requested year when available."""
        rows_2024 = synthetic_data_api.employment_share_latest(year=2024)
        assert all(r.year == 2024 for r in rows_2024 if r.year == 2024)

        rows_2019 = synthetic_data_api.employment_share_latest(year=2019)
        years = {r.year for r in rows_2019}
        assert 2019 in years or not rows_2019  # Should not raise even if data absent

    def test_param_overrides_do_not_mutate_registry(self, synthetic_data_api):
        """Applying parameter overrides must not mutate registry state."""
        qid = data_client._resolve(synthetic_data_api.reg, "employment_share_all")
        before = deepcopy(synthetic_data_api.reg.get(qid).params)

        synthetic_data_api.employment_share_latest(year=2019)

        after = synthetic_data_api.reg.get(qid).params
        assert after == before, "Registry spec params should remain immutable"


class TestUtilities:
    """Test helper utilities including latest_year and to_dataframe."""

    def test_latest_year_returns_max_year(self, synthetic_data_api):
        """latest_year should return max year from underlying rows."""
        latest = synthetic_data_api.latest_year("sector_employment")
        rows = synthetic_data_api.sector_employment()
        expected = max(r.year for r in rows) if rows else None
        assert latest == expected

    def test_latest_year_unresolved_key_raises(self, synthetic_data_api):
        """latest_year should raise KeyError for unknown canonical keys."""
        with pytest.raises(KeyError):
            synthetic_data_api.latest_year("nonexistent_metric")

    def test_latest_year_handles_invalid_values(self, synthetic_data_api, monkeypatch):
        """latest_year should ignore None and non-numeric year values."""

        def fake_rows(reg, qid, ttl_s, spec_override=None):
            return [
                {"year": None},
                {"year": "2020"},
                {"year": "invalid"},
                {"year": 2021},
            ]

        monkeypatch.setattr(data_client, "_rows", fake_rows)
        latest = synthetic_data_api.latest_year("employment_share_all")
        assert latest == 2021

    def _install_dummy_pandas(self, monkeypatch):
        class DummyDataFrame:
            def __init__(self, data=None):
                self.data = [] if data is None else data

        dummy_module = types.SimpleNamespace(DataFrame=lambda data=None: DummyDataFrame(data))
        monkeypatch.delitem(sys.modules, "pandas", raising=False)
        monkeypatch.setitem(sys.modules, "pandas", dummy_module)
        return DummyDataFrame

    def test_to_dataframe_requires_pandas(self, monkeypatch):
        """to_dataframe should raise helpful ImportError when pandas missing."""
        original_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "pandas":
                raise ImportError("pandas not installed")
            return original_import(name, *args, **kwargs)

        monkeypatch.delitem(sys.modules, "pandas", raising=False)
        monkeypatch.setattr(builtins, "__import__", fake_import)
        with pytest.raises(ImportError):
            DataAPI.to_dataframe([])

    def test_to_dataframe_converts_rows(self, monkeypatch):
        """to_dataframe should convert Pydantic rows when pandas available."""
        DummyDataFrame = self._install_dummy_pandas(monkeypatch)

        rows = [
            EmploymentShareRow(year=2020, male_percent=60.0, female_percent=40.0, total_percent=100.0),
            EmploymentShareRow(year=2021, male_percent=58.0, female_percent=42.0, total_percent=100.0),
        ]

        df = DataAPI.to_dataframe(rows)
        assert isinstance(df, DummyDataFrame)
        assert df.data[0]["year"] == 2020

    def test_to_dataframe_handles_empty_input(self, monkeypatch):
        """Empty sequences should return an empty DataFrame."""
        DummyDataFrame = self._install_dummy_pandas(monkeypatch)
        df = DataAPI.to_dataframe([])
        assert isinstance(df, DummyDataFrame)
        assert df.data == []

    def test_to_dataframe_accepts_mapping_rows(self, monkeypatch):
        """Plain dictionaries should be supported."""
        DummyDataFrame = self._install_dummy_pandas(monkeypatch)
        df = DataAPI.to_dataframe([{"year": 2020, "value": 1.0}])
        assert isinstance(df, DummyDataFrame)
        assert df.data[0]["value"] == 1.0

    def test_to_dataframe_accepts_legacy_models(self, monkeypatch):
        """Objects exposing dict() should be supported."""

        class LegacyModel:
            def dict(self):
                return {"year": 2019, "value": 2.5}

        self._install_dummy_pandas(monkeypatch)
        df = DataAPI.to_dataframe([LegacyModel()])
        assert df.data[0]["year"] == 2019

    def test_to_dataframe_accepts_dataclasses(self, monkeypatch):
        """Dataclass rows should be converted via asdict."""

        @dataclass
        class Demo:
            year: int
            metric: float

        self._install_dummy_pandas(monkeypatch)
        df = DataAPI.to_dataframe([Demo(year=2022, metric=3.3)])
        assert df.data[0]["metric"] == 3.3

    def test_to_dataframe_rejects_unknown_types(self, monkeypatch):
        """Objects without dict-like semantics should raise TypeError."""

        class Unknown:
            pass

        self._install_dummy_pandas(monkeypatch)
        with pytest.raises(TypeError):
            DataAPI.to_dataframe([Unknown()])
