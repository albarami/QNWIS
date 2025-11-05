"""
Integration tests for queries with postprocess transforms.

Tests end-to-end execution of YAML queries with transform pipelines.
"""

from pathlib import Path

import pytest

from src.qnwis.data.connectors import csv_catalog
from src.qnwis.data.deterministic.cache_access import execute_cached
from src.qnwis.data.deterministic.registry import QueryRegistry
from src.qnwis.data.synthetic.seed_lmis import generate_synthetic_lmis


@pytest.fixture(scope="module")
def synthetic_data(tmp_path_factory):
    """Generate synthetic LMIS data once for all tests."""
    data_dir = tmp_path_factory.mktemp("synthetic_data")
    generate_synthetic_lmis(str(data_dir))
    return data_dir


@pytest.fixture(scope="module")
def registry():
    """Load query registry."""
    queries_dir = Path(__file__).resolve().parents[2] / "src" / "qnwis" / "data" / "queries"
    reg = QueryRegistry(str(queries_dir))
    reg.load_all()
    return reg


@pytest.fixture(autouse=True)
def setup_csv_base(synthetic_data):
    """Point CSV connector to synthetic data."""
    original_base = csv_catalog.BASE
    csv_catalog.BASE = Path(synthetic_data)
    yield
    csv_catalog.BASE = original_base


def test_top5_sector_employment_latest(registry):
    """Test syn_sector_employment_latest_top5 query with top_n transform."""
    query_id = "syn_sector_employment_latest_top5"
    res = execute_cached(query_id, registry, ttl_s=60)

    assert res.query_id == query_id
    assert len(res.rows) <= 5
    assert res.unit == "count"

    # Verify sorted descending by employees
    if len(res.rows) > 1:
        employees = [r.data.get("employees", 0) for r in res.rows]
        assert employees == sorted(employees, reverse=True)


def test_sector_employment_energy_yoy(registry):
    """Test syn_sector_employment_energy_yoy with filter and yoy transforms."""
    query_id = "syn_sector_employment_energy_yoy"
    res = execute_cached(query_id, registry, ttl_s=60)

    assert res.query_id == query_id
    # All rows should be Energy sector
    assert all(r.data.get("sector") == "Energy" for r in res.rows)
    # YoY column should exist
    assert any("yoy_percent" in r.data for r in res.rows)


def test_sector_employment_finance_yoy(registry):
    """Test syn_sector_employment_finance_yoy."""
    query_id = "syn_sector_employment_finance_yoy"
    res = execute_cached(query_id, registry, ttl_s=60)

    assert res.query_id == query_id
    assert all(r.data.get("sector") == "Finance" for r in res.rows)
    assert any("yoy_percent" in r.data for r in res.rows)


def test_rolling3_energy(registry):
    """Test syn_sector_employment_rolling3_energy with rolling_avg."""
    query_id = "syn_sector_employment_rolling3_energy"
    res = execute_cached(query_id, registry, ttl_s=60)

    assert res.query_id == query_id
    assert all(r.data.get("sector") == "Energy" for r in res.rows)
    # rolling_avg should appear after window is filled
    rolling_vals = [r.data.get("rolling_avg") for r in res.rows if r.data.get("rolling_avg") is not None]
    assert len(rolling_vals) > 0


def test_rolling3_finance(registry):
    """Test syn_sector_employment_rolling3_finance."""
    query_id = "syn_sector_employment_rolling3_finance"
    res = execute_cached(query_id, registry, ttl_s=60)

    assert res.query_id == query_id
    assert all(r.data.get("sector") == "Finance" for r in res.rows)


def test_salary_latest_top5(registry):
    """Test syn_salary_latest_top5."""
    query_id = "syn_salary_latest_top5"
    res = execute_cached(query_id, registry, ttl_s=60)

    assert res.query_id == query_id
    assert len(res.rows) <= 5
    assert res.unit == "qar"


def test_salary_yoy_ict(registry):
    """Test syn_salary_yoy_ict."""
    query_id = "syn_salary_yoy_ict"
    res = execute_cached(query_id, registry, ttl_s=60)

    assert res.query_id == query_id
    assert all(r.data.get("sector") == "ICT" for r in res.rows)
    assert any("yoy_percent" in r.data for r in res.rows)


def test_attrition_hotspots_latest(registry):
    """Test syn_attrition_hotspots_latest."""
    query_id = "syn_attrition_hotspots_latest"
    res = execute_cached(query_id, registry, ttl_s=60)

    assert res.query_id == query_id
    assert len(res.rows) <= 5
    assert res.unit == "percent"


def test_qatarization_gap_latest(registry):
    """Test syn_qatarization_gap_latest with ascending sort."""
    query_id = "syn_qatarization_gap_latest"
    res = execute_cached(query_id, registry, ttl_s=60)

    assert res.query_id == query_id
    assert len(res.rows) <= 5
    # Should be sorted ascending (lowest Qatarization first)
    if len(res.rows) > 1:
        rates = [r.data.get("qatarization_percent", 0) for r in res.rows]
        assert rates == sorted(rates)


def test_qatarization_energy_time_series(registry):
    """Test syn_qatarization_energy_time_series."""
    query_id = "syn_qatarization_energy_time_series"
    res = execute_cached(query_id, registry, ttl_s=60)

    assert res.query_id == query_id
    assert all(r.data.get("sector") == "Energy" for r in res.rows)


def test_company_sizes_latest_top5(registry):
    """Test syn_company_sizes_latest_top5."""
    query_id = "syn_company_sizes_latest_top5"
    res = execute_cached(query_id, registry, ttl_s=60)

    assert res.query_id == query_id
    assert len(res.rows) <= 5


def test_gcc_unemployment_rank(registry):
    """Test syn_gcc_unemployment_rank."""
    query_id = "syn_gcc_unemployment_rank"
    res = execute_cached(query_id, registry, ttl_s=60)

    assert res.query_id == query_id
    assert len(res.rows) <= 6  # Up to 6 GCC countries


def test_employment_share_latest_renamed(registry):
    """Test syn_employment_share_latest_renamed with rename and share_of_total."""
    query_id = "syn_employment_share_latest_renamed"
    res = execute_cached(query_id, registry, ttl_s=60)

    assert res.query_id == query_id
    # Check renamed columns exist
    assert any("employment_share_pct" in r.data for r in res.rows)
    assert any("total_employees" in r.data for r in res.rows)


def test_employment_share_bounds_check(registry):
    """Test syn_employment_share_bounds_check with sum_to_one constraint."""
    query_id = "syn_employment_share_bounds_check"
    res = execute_cached(query_id, registry, ttl_s=60)

    assert res.query_id == query_id
    # Shares should sum to 100%
    total = sum(r.data.get("share_percent", 0) for r in res.rows)
    assert abs(total - 100.0) < 0.5  # Within tolerance


def test_ewi_hotlist_latest(registry):
    """Test syn_ewi_hotlist_latest."""
    query_id = "syn_ewi_hotlist_latest"
    res = execute_cached(query_id, registry, ttl_s=60)

    assert res.query_id == query_id
    assert len(res.rows) <= 5


def test_sector_employment_2019_vs_2024(registry):
    """Test syn_sector_employment_2019_vs_2024."""
    query_id = "syn_sector_employment_2019_vs_2024"
    res = execute_cached(query_id, registry, ttl_s=60)

    assert res.query_id == query_id
    assert all(r.data.get("year") == 2024 for r in res.rows)


def test_salary_2019_vs_2024_ict(registry):
    """Test syn_salary_2019_vs_2024_ict."""
    query_id = "syn_salary_2019_vs_2024_ict"
    res = execute_cached(query_id, registry, ttl_s=60)

    assert res.query_id == query_id
    assert all(r.data.get("sector") == "ICT" for r in res.rows)


def test_attrition_rolling3_healthcare(registry):
    """Test syn_attrition_rolling3_healthcare."""
    query_id = "syn_attrition_rolling3_healthcare"
    res = execute_cached(query_id, registry, ttl_s=60)

    assert res.query_id == query_id
    assert all(r.data.get("sector") == "Healthcare" for r in res.rows)


def test_qatarization_energy_share_of_total(registry):
    """Test syn_qatarization_energy_share_of_total with share_of_total then filter."""
    query_id = "syn_qatarization_energy_share_of_total"
    res = execute_cached(query_id, registry, ttl_s=60)

    assert res.query_id == query_id
    # After filter, should only have Energy
    assert all(r.data.get("sector") == "Energy" for r in res.rows)
    # Should have share_percent column
    assert any("share_percent" in r.data for r in res.rows)


def test_qatarization_sorted_latest(registry):
    """Test syn_qatarization_sorted_latest."""
    query_id = "syn_qatarization_sorted_latest"
    res = execute_cached(query_id, registry, ttl_s=60)

    assert res.query_id == query_id
    assert len(res.rows) <= 20


def test_cache_key_includes_postprocess(registry):
    """Test that different postprocess steps generate different cache keys."""
    # Query with postprocess
    query_id_1 = "syn_sector_employment_latest_top5"
    res1 = execute_cached(query_id_1, registry, ttl_s=60)

    # Same base query but different postprocess would have different cache key
    # (we can't easily test this directly, but the cache key generation includes postprocess)
    assert res1.query_id == query_id_1

    # Different query with different postprocess
    query_id_2 = "syn_sector_employment_energy_yoy"
    res2 = execute_cached(query_id_2, registry, ttl_s=60)

    assert res2.query_id == query_id_2
    # Results should be different due to different transforms
    assert res1.rows != res2.rows


def test_multiple_transforms_execute_in_order(registry):
    """Test that transforms execute in correct order."""
    query_id = "syn_employment_share_latest_renamed"
    res = execute_cached(query_id, registry, ttl_s=60)

    # share_of_total runs first, then rename_columns
    # So we should see renamed columns
    assert any("employment_share_pct" in r.data for r in res.rows)
    # Original column names should be renamed
    first_row_keys = set(res.rows[0].data.keys()) if res.rows else set()
    assert "employees" not in first_row_keys or "total_employees" in first_row_keys
