"""
End-to-end integration test for council with real synthetic data.

Tests the complete council execution pipeline using synthetic LMIS data
without mocks, ensuring the full stack works together.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import src.qnwis.data.connectors.csv_catalog as csvcat
from src.qnwis.app import app
from src.qnwis.data.synthetic.seed_lmis import generate_synthetic_lmis


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


def test_council_run_on_synthetic(synthetic_data_env):
    """Test council endpoint with real synthetic data."""
    client = TestClient(app)
    response = client.post("/v1/council/run", json={})

    assert response.status_code == 200

    data = response.json()

    # Verify council structure
    assert "council" in data
    assert "verification" in data

    council = data["council"]

    # Verify agents ran
    assert "agents" in council
    assert isinstance(council["agents"], list)
    assert len(council["agents"]) > 0

    # Verify findings exist
    assert "findings" in council
    assert isinstance(council["findings"], list)
    assert len(council["findings"]) > 0, "Council should produce findings from synthetic data"

    # Verify consensus computed
    assert "consensus" in council
    assert isinstance(council["consensus"], dict)

    # Verify warnings collected
    assert "warnings" in council
    assert isinstance(council["warnings"], list)

    # Verify verification ran
    verification = data["verification"]
    assert isinstance(verification, dict)
    # Verification should have entries for each agent
    for agent in council["agents"]:
        assert agent in verification
        assert isinstance(verification[agent], list)


def test_council_findings_structure(synthetic_data_env):
    """Test that findings have complete structure."""
    client = TestClient(app)
    response = client.post("/v1/council/run", json={})

    data = response.json()
    findings = data["council"]["findings"]

    assert len(findings) > 0

    for finding in findings:
        # Required fields
        assert "title" in finding
        assert "summary" in finding
        assert "metrics" in finding
        assert "evidence" in finding
        assert "warnings" in finding
        assert "confidence_score" in finding

        # Verify types
        assert isinstance(finding["title"], str)
        assert isinstance(finding["summary"], str)
        assert isinstance(finding["metrics"], dict)
        assert isinstance(finding["evidence"], list)
        assert isinstance(finding["warnings"], list)
        assert isinstance(finding["confidence_score"], (int, float))

        # Verify evidence structure
        for evidence in finding["evidence"]:
            assert "query_id" in evidence
            assert "dataset_id" in evidence
            assert "locator" in evidence
            assert "fields" in evidence


def test_council_consensus_numeric(synthetic_data_env):
    """Test that consensus contains numeric values."""
    client = TestClient(app)
    response = client.post("/v1/council/run", json={})

    data = response.json()
    consensus = data["council"]["consensus"]

    # All consensus values should be numeric
    for key, value in consensus.items():
        assert isinstance(value, (int, float)), f"Consensus {key} should be numeric"


def test_council_verification_format(synthetic_data_env):
    """Test verification output format."""
    client = TestClient(app)
    response = client.post("/v1/council/run", json={})

    data = response.json()
    verification = data["verification"]

    for _agent_name, issues in verification.items():
        assert isinstance(issues, list)
        for issue in issues:
            assert "level" in issue
            assert "code" in issue
            assert "detail" in issue
            assert issue["level"] in ["warn", "error"]


def test_council_deterministic(synthetic_data_env):
    """Test that council produces identical results on repeated runs."""
    client = TestClient(app)

    response1 = client.post("/v1/council/run", json={})
    response2 = client.post("/v1/council/run", json={})

    data1 = response1.json()
    data2 = response2.json()

    # Agent list should be identical
    assert data1["council"]["agents"] == data2["council"]["agents"]

    # Number of findings should be identical
    assert len(data1["council"]["findings"]) == len(data2["council"]["findings"])

    # Consensus should be identical
    assert data1["council"]["consensus"] == data2["council"]["consensus"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
