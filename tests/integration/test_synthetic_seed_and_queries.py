"""Integration test for synthetic LMIS data generation and query execution."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from src.qnwis.data.connectors import csv_catalog
from src.qnwis.data.deterministic.cache_access import execute_cached
from src.qnwis.data.deterministic.registry import QueryRegistry
from src.qnwis.data.synthetic.seed_lmis import generate_synthetic_lmis


def test_seed_and_execute_queries(tmp_path: pytest.TempPathFactory) -> None:
    """
    End-to-end test: generate synthetic data and execute queries.

    Verifies that:
    - Synthetic data generation succeeds
    - CSV connector can read synthetic files
    - Query registry loads YAML definitions
    - execute_cached returns valid results
    """
    # Generate synthetic data
    info = generate_synthetic_lmis(str(tmp_path))
    assert "companies" in info
    assert "employment_history" in info
    assert "aggregates_dir" in info

    # Point CSV connector BASE to synthetic folder
    base_before = csv_catalog.BASE
    csv_catalog.BASE = tmp_path

    try:
        # Load query registry
        reg = QueryRegistry("src/qnwis/data/queries")
        reg.load_all()

        # Test a selection of queries
        query_ids = [
            "syn_employment_share_by_gender_2017_2024",
            "syn_unemployment_rate_gcc_latest",
            "syn_qatarization_rate_by_sector",
            "syn_avg_salary_by_sector",
        ]

        for qid in query_ids:
            res = execute_cached(qid, reg, ttl_s=60)

            # Verify result structure
            assert res.rows, f"Query {qid} returned no rows"
            assert res.unit, f"Query {qid} missing unit"
            assert res.provenance.dataset_id, f"Query {qid} missing dataset_id"
            assert res.provenance.source == "csv"
            assert (
                res.provenance.license == "MIT-SYNTHETIC"
            ), f"Query {qid} has unexpected license {res.provenance.license}"
            assert len(res.rows) > 0, f"Query {qid} has empty rows"

            # Verify row data structure
            first_row = res.rows[0]
            assert isinstance(first_row.data, dict)
            assert len(first_row.data) > 0

    finally:
        # Restore original BASE
        csv_catalog.BASE = base_before


def test_all_synthetic_queries_executable(tmp_path: pytest.TempPathFactory) -> None:
    """
    Verify all 8 synthetic queries can be executed successfully.

    This ensures complete coverage of the query library.
    """
    # Generate synthetic data
    generate_synthetic_lmis(str(tmp_path))

    # Point CSV connector BASE to synthetic folder
    base_before = csv_catalog.BASE
    csv_catalog.BASE = tmp_path

    try:
        reg = QueryRegistry("src/qnwis/data/queries")
        reg.load_all()

        # All synthetic query IDs
        all_query_ids = [
            "syn_employment_share_by_gender_2017_2024",
            "syn_unemployment_rate_gcc_latest",
            "syn_qatarization_rate_by_sector",
            "syn_avg_salary_by_sector",
            "syn_attrition_rate_by_sector",
            "syn_company_size_distribution",
            "syn_sector_employment_by_year",
            "syn_ewi_employment_drop",
        ]

        for qid in all_query_ids:
            res = execute_cached(qid, reg, ttl_s=0)  # No caching for test
            assert res.rows, f"Query {qid} returned no rows"
            assert res.query_id == qid
            assert res.provenance.license == "MIT-SYNTHETIC"

    finally:
        csv_catalog.BASE = base_before


def test_query_results_have_expected_fields(tmp_path: pytest.TempPathFactory) -> None:
    """
    Verify query results contain expected field names.

    This ensures the YAML select parameters match CSV columns.
    """
    generate_synthetic_lmis(str(tmp_path))

    base_before = csv_catalog.BASE
    csv_catalog.BASE = tmp_path

    try:
        reg = QueryRegistry("src/qnwis/data/queries")
        reg.load_all()

        # Test employment share query
        res = execute_cached(
            "syn_employment_share_by_gender_2017_2024", reg, ttl_s=0
        )
        expected_fields = {"year", "male_percent", "female_percent", "total_percent"}
        actual_fields = set(res.rows[0].data.keys())
        assert expected_fields == actual_fields

        # Test salary query
        res = execute_cached("syn_avg_salary_by_sector", reg, ttl_s=0)
        expected_fields = {"year", "sector", "avg_salary_qr"}
        actual_fields = set(res.rows[0].data.keys())
        assert expected_fields == actual_fields

    finally:
        csv_catalog.BASE = base_before


def test_synthetic_data_determinism(tmp_path: pytest.TempPathFactory) -> None:
    """
    Verify that synthetic data generation is deterministic with same seed.

    Two generations with same seed should produce identical results.
    """
    # Generate first set
    info1 = generate_synthetic_lmis(str(tmp_path / "run1"), seed=42)

    # Generate second set with same seed
    info2 = generate_synthetic_lmis(str(tmp_path / "run2"), seed=42)

    def _hash_file(path: str) -> str:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()

    # Compare primary CSVs
    assert (
        _hash_file(info1["companies"]) == _hash_file(info2["companies"])
    ), "companies.csv differs between runs"
    assert (
        _hash_file(info1["employment_history"])
        == _hash_file(info2["employment_history"])
    ), "employment_history.csv differs between runs"

    # Compare aggregate CSV directory contents
    agg1 = Path(info1["aggregates_dir"])
    agg2 = Path(info2["aggregates_dir"])
    agg1_files = sorted(p.relative_to(agg1) for p in agg1.glob("*.csv"))
    agg2_files = sorted(p.relative_to(agg2) for p in agg2.glob("*.csv"))

    assert agg1_files == agg2_files, "Aggregate file sets differ between runs"

    for rel in agg1_files:
        path1 = agg1 / rel
        path2 = agg2 / rel
        assert (
            _hash_file(str(path1)) == _hash_file(str(path2))
        ), f"Aggregate file {rel} differs between runs"
