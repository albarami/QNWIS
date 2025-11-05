"""Unit tests for triangulation bundle execution."""
from pathlib import Path

import src.qnwis.data.connectors.csv_catalog as csvcat
from src.qnwis.data.deterministic.registry import QueryRegistry
from src.qnwis.data.synthetic.seed_lmis import generate_synthetic_lmis
from src.qnwis.verification.triangulation import run_triangulation


def test_triangulation_runs_on_synthetic(tmp_path):
    """Test that triangulation runs successfully on synthetic data."""
    generate_synthetic_lmis(str(tmp_path))
    old = csvcat.BASE
    csvcat.BASE = Path(tmp_path)
    try:
        reg = QueryRegistry("src/qnwis/data/queries")
        reg.load_all()
        bundle = run_triangulation(reg, ttl_s=60)
        assert bundle.results
        assert isinstance(bundle.warnings, list)
        assert isinstance(bundle.licenses, list)
        if bundle.licenses:
            assert len(bundle.licenses) == len(set(bundle.licenses))
    finally:
        csvcat.BASE = old


def test_triangulation_results_structure(tmp_path):
    """Test that triangulation results have expected structure."""
    generate_synthetic_lmis(str(tmp_path))
    old = csvcat.BASE
    csvcat.BASE = Path(tmp_path)
    try:
        reg = QueryRegistry("src/qnwis/data/queries")
        reg.load_all()
        bundle = run_triangulation(reg, ttl_s=60)

        # Should have results for all checks
        check_ids = [r.check_id for r in bundle.results]
        assert "employment_sum_to_one" in check_ids
        assert "qatarization_formula" in check_ids
        assert "ewi_vs_yoy" in check_ids
        assert "bounds_sanity" in check_ids
    finally:
        csvcat.BASE = old


def test_triangulation_issues_have_structure(tmp_path):
    """Test that any issues found have proper structure."""
    generate_synthetic_lmis(str(tmp_path))
    old = csvcat.BASE
    csvcat.BASE = Path(tmp_path)
    try:
        reg = QueryRegistry("src/qnwis/data/queries")
        reg.load_all()
        bundle = run_triangulation(reg, ttl_s=60)

        for result in bundle.results:
            for issue in result.issues:
                assert hasattr(issue, 'code')
                assert hasattr(issue, 'detail')
                assert hasattr(issue, 'severity')
                assert issue.severity in ('warn', 'error')
    finally:
        csvcat.BASE = old


def test_triangulation_samples_exist(tmp_path):
    """Test that samples are included in results."""
    generate_synthetic_lmis(str(tmp_path))
    old = csvcat.BASE
    csvcat.BASE = Path(tmp_path)
    try:
        reg = QueryRegistry("src/qnwis/data/queries")
        reg.load_all()
        bundle = run_triangulation(reg, ttl_s=60)

        # At least some results should have samples
        has_samples = any(len(r.samples) > 0 for r in bundle.results)
        assert has_samples
    finally:
        csvcat.BASE = old


def test_triangulation_warnings_format(tmp_path):
    """Test that warnings are properly formatted."""
    generate_synthetic_lmis(str(tmp_path))
    old = csvcat.BASE
    csvcat.BASE = Path(tmp_path)
    try:
        reg = QueryRegistry("src/qnwis/data/queries")
        reg.load_all()
        bundle = run_triangulation(reg, ttl_s=60)

        for warning in bundle.warnings:
            assert ":" in warning  # format: check_id:count
    finally:
        csvcat.BASE = old
