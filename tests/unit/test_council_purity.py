"""
Unit tests for council function purity (determinism).

Verifies that run_council produces identical outputs when called with
identical inputs, ensuring deterministic behavior.
"""

from pathlib import Path

import pytest

import src.qnwis.data.connectors.csv_catalog as csvcat
from src.qnwis.data.synthetic.seed_lmis import generate_synthetic_lmis
from src.qnwis.orchestration.council import CouncilConfig, run_council


@pytest.fixture
def synthetic_data_env(tmp_path, monkeypatch):
    """Set up synthetic data environment."""
    # Generate synthetic data
    generate_synthetic_lmis(str(tmp_path))

    # Point catalog to synthetic data
    old_base = csvcat.BASE
    csvcat.BASE = Path(tmp_path)

    # Set queries directory
    monkeypatch.setenv("QNWIS_QUERIES_DIR", "src/qnwis/data/queries")

    yield tmp_path

    # Cleanup
    csvcat.BASE = old_base


def test_run_council_is_pure(synthetic_data_env):
    """Verify run_council produces identical results on repeated calls."""
    # Run council twice with identical config
    config = CouncilConfig(queries_dir="src/qnwis/data/queries", ttl_s=120)
    out1 = run_council(config)
    out2 = run_council(config)

    # Agent list should be identical
    assert out1["council"]["agents"] == out2["council"]["agents"]

    # Number of findings should be identical
    assert len(out1["council"]["findings"]) == len(out2["council"]["findings"])

    # Consensus should be identical
    assert out1["council"]["consensus"] == out2["council"]["consensus"]


def test_run_council_verification_identical(synthetic_data_env):
    """Verify verification results are identical across runs."""
    config = CouncilConfig(queries_dir="src/qnwis/data/queries", ttl_s=120)
    out1 = run_council(config)
    out2 = run_council(config)

    # Verification should be identical
    assert out1["verification"] == out2["verification"]


def test_run_council_warnings_identical(synthetic_data_env):
    """Verify warnings are identical across runs."""
    config = CouncilConfig(queries_dir="src/qnwis/data/queries", ttl_s=120)
    out1 = run_council(config)
    out2 = run_council(config)

    # Warnings should be identical and sorted
    warnings1 = out1["council"]["warnings"]
    warnings2 = out2["council"]["warnings"]

    assert warnings1 == warnings2
    assert warnings1 == sorted(warnings1)


def test_run_council_different_ttl_produces_same_results(synthetic_data_env):
    """Verify different TTL values don't affect determinism."""
    # Different TTL values should produce identical results
    out1 = run_council(CouncilConfig(queries_dir="src/qnwis/data/queries", ttl_s=60))
    out2 = run_council(CouncilConfig(queries_dir="src/qnwis/data/queries", ttl_s=300))

    # Core results should be identical regardless of TTL
    assert out1["council"]["agents"] == out2["council"]["agents"]
    assert len(out1["council"]["findings"]) == len(out2["council"]["findings"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
