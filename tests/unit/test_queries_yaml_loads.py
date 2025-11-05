"""Unit tests for YAML query loading and registry validation."""

from __future__ import annotations

import pytest

from src.qnwis.data.deterministic.registry import QueryRegistry


def test_yaml_queries_load_successfully() -> None:
    """
    Verify all synthetic YAML queries load into registry.

    Checks that QueryRegistry can parse and load the synthetic queries
    required by the DataAPI facade.
    """
    reg = QueryRegistry("src/qnwis/data/queries")
    reg.load_all()

    needed = {
        "syn_employment_share_by_gender_2017_2024",
        "syn_employment_share_by_gender_latest",
        "syn_employment_male_share",
        "syn_employment_female_share",
        "syn_employment_latest_total",
        "syn_unemployment_rate_gcc_latest",
        "syn_unemployment_gcc_latest",
        "syn_qatarization_rate_by_sector",
        "syn_qatarization_by_sector_latest",
        "syn_qatarization_components",
        "syn_avg_salary_by_sector",
        "syn_avg_salary_by_sector_latest",
        "syn_attrition_rate_by_sector",
        "syn_attrition_by_sector_latest",
        "syn_company_size_distribution",
        "syn_company_size_distribution_latest",
        "syn_sector_employment_by_year",
        "syn_sector_employment_latest",
        "syn_sector_employment_2019",
        "syn_ewi_employment_drop",
        "syn_ewi_employment_drop_latest",
    }

    ids = set(reg.all_ids())
    assert needed.issubset(ids), f"Missing queries: {needed - ids}"


def test_query_specs_have_required_fields() -> None:
    """
    Verify each query spec has required fields.

    Checks:
    - id, title, description, source are present
    - params contains pattern and select
    - expected_unit is set
    """
    reg = QueryRegistry("src/qnwis/data/queries")
    reg.load_all()

    synthetic_ids = [
        "syn_employment_share_by_gender_2017_2024",
        "syn_unemployment_rate_gcc_latest",
        "syn_qatarization_rate_by_sector",
    ]

    for qid in synthetic_ids:
        spec = reg.get(qid)

        # Required fields
        assert spec.id == qid
        assert spec.title
        assert spec.description
        assert spec.source == "csv"

        # Params structure
        assert "pattern" in spec.params
        assert "select" in spec.params
        assert isinstance(spec.params["select"], list)

        # Expected unit
        assert spec.expected_unit in ["percent", "count", "qar", "usd", "unknown"]


def test_query_params_have_valid_patterns() -> None:
    """
    Verify CSV patterns in queries are valid glob patterns.

    Checks that pattern parameters point to expected aggregate files.
    """
    reg = QueryRegistry("src/qnwis/data/queries")
    reg.load_all()

    expected_patterns = {
        "syn_employment_share_by_gender_2017_2024": "aggregates/employment_share_by_gender.csv",
        "syn_employment_share_by_gender_latest": "aggregates/employment_share_by_gender.csv",
        "syn_employment_male_share": "aggregates/employment_share_by_gender.csv",
        "syn_employment_female_share": "aggregates/employment_share_by_gender.csv",
        "syn_employment_latest_total": "aggregates/employment_share_by_gender.csv",
        "syn_unemployment_rate_gcc_latest": "aggregates/unemployment_gcc_latest.csv",
        "syn_unemployment_gcc_latest": "aggregates/unemployment_gcc_latest.csv",
        "syn_qatarization_rate_by_sector": "aggregates/qatarization_by_sector.csv",
        "syn_qatarization_by_sector_latest": "aggregates/qatarization_by_sector.csv",
        "syn_qatarization_components": "aggregates/qatarization_by_sector.csv",
        "syn_avg_salary_by_sector": "aggregates/avg_salary_by_sector.csv",
        "syn_avg_salary_by_sector_latest": "aggregates/avg_salary_by_sector.csv",
        "syn_attrition_rate_by_sector": "aggregates/attrition_by_sector.csv",
        "syn_attrition_by_sector_latest": "aggregates/attrition_by_sector.csv",
        "syn_company_size_distribution": "aggregates/company_size_distribution.csv",
        "syn_company_size_distribution_latest": "aggregates/company_size_distribution.csv",
        "syn_sector_employment_by_year": "aggregates/sector_employment_by_year.csv",
        "syn_sector_employment_latest": "aggregates/sector_employment_by_year.csv",
        "syn_sector_employment_2019": "aggregates/sector_employment_by_year.csv",
        "syn_ewi_employment_drop": "aggregates/ewi_employment_drop.csv",
        "syn_ewi_employment_drop_latest": "aggregates/ewi_employment_drop.csv",
    }

    for qid, expected_pattern in expected_patterns.items():
        spec = reg.get(qid)
        actual_pattern = spec.params["pattern"]
        assert actual_pattern == expected_pattern


def test_query_year_filters() -> None:
    """
    Verify year filters in query params are reasonable.

    Checks that year parameters are within expected range (2017-2024).
    """
    reg = QueryRegistry("src/qnwis/data/queries")
    reg.load_all()

    for qid in reg.all_ids():
        if qid.startswith("syn_"):  # Only check synthetic queries
            spec = reg.get(qid)
            if "year" in spec.params:
                year = spec.params["year"]
                assert isinstance(year, int)
                assert 2017 <= year <= 2024


def test_constraints_structure() -> None:
    """
    Verify constraints in query specs are well-formed.

    Checks that constraints dict contains expected keys.
    """
    reg = QueryRegistry("src/qnwis/data/queries")
    reg.load_all()

    # Check employment share query has sum_to_one constraint
    spec = reg.get("syn_employment_share_by_gender_2017_2024")
    assert "sum_to_one" in spec.constraints
    assert spec.constraints["sum_to_one"] is True

    # All synthetic queries should have freshness_sla_days
    for qid in reg.all_ids():
        if qid.startswith("syn_"):
            spec = reg.get(qid)
            if "freshness_sla_days" in spec.constraints:
                sla = spec.constraints["freshness_sla_days"]
                assert isinstance(sla, int)
                assert sla > 0


def test_no_duplicate_query_ids() -> None:
    """
    Verify there are no duplicate query IDs in registry.

    This would cause a ValueError during load_all().
    """
    reg = QueryRegistry("src/qnwis/data/queries")

    # Should not raise ValueError for duplicate IDs
    try:
        reg.load_all()
    except ValueError as e:
        if "Duplicate QuerySpec id" in str(e):
            pytest.fail(f"Duplicate query ID detected: {e}")
        raise


def test_select_fields_not_empty() -> None:
    """
    Verify select fields are not empty in query params.

    Empty select would return all columns, which may not be desired.
    """
    reg = QueryRegistry("src/qnwis/data/queries")
    reg.load_all()

    for qid in reg.all_ids():
        if qid.startswith("syn_"):
            spec = reg.get(qid)
            select_fields = spec.params.get("select", [])
            assert len(select_fields) > 0, f"Query {qid} has empty select"


def test_expected_units_match_data_types() -> None:
    """
    Verify expected_unit matches the type of data being queried.

    For example:
    - Percentages should have unit 'percent'
    - Counts should have unit 'count'
    - Salaries should have unit 'qar'
    """
    reg = QueryRegistry("src/qnwis/data/queries")
    reg.load_all()

    unit_expectations = {
        "syn_employment_share_by_gender_2017_2024": "percent",
        "syn_unemployment_rate_gcc_latest": "percent",
        "syn_qatarization_rate_by_sector": "percent",
        "syn_avg_salary_by_sector": "qar",
        "syn_attrition_rate_by_sector": "percent",
        "syn_company_size_distribution": "count",
        "syn_sector_employment_by_year": "count",
        "syn_ewi_employment_drop": "percent",
    }

    for qid, expected_unit in unit_expectations.items():
        spec = reg.get(qid)
        assert spec.expected_unit == expected_unit
