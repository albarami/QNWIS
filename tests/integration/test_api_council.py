"""
Integration tests for council API endpoint.

Tests the complete HTTP API flow for multi-agent council execution
with FastAPI test client.
"""

import pytest
from fastapi.testclient import TestClient

from src.qnwis.app import app
from src.qnwis.data.deterministic.models import Freshness, Provenance, QueryResult, Row


@pytest.fixture
def client():
    """Create FastAPI test client."""
    return TestClient(app)


def _mock_query_result(query_id: str) -> QueryResult:
    """Generate mock QueryResult for testing."""
    return QueryResult(
        query_id=query_id,
        rows=[
            Row(
                data={
                    "year": 2023,
                    "male_percent": 60.0,
                    "female_percent": 40.0,
                    "total_percent": 100.0,
                }
            )
        ],
        unit="percent",
        provenance=Provenance(
            source="csv",
            dataset_id="test-dataset",
            locator="test.csv",
            fields=["year", "male_percent", "female_percent", "total_percent"],
        ),
        freshness=Freshness(asof_date="2023-12-31"),
    )


def test_council_endpoint_exists(client, monkeypatch):
    """Verify /v1/council/run endpoint is registered."""

    def mock_run(self, query_id: str):
        return _mock_query_result(query_id)

    monkeypatch.setattr("src.qnwis.agents.base.DataClient.run", mock_run)

    response = client.post("/v1/council/run")
    # Should not be 404 (endpoint exists)
    assert response.status_code == 200


def test_council_endpoint_returns_json(client, monkeypatch):
    """Verify endpoint returns JSON response."""

    def mock_run(self, query_id: str):
        return _mock_query_result(query_id)

    monkeypatch.setattr("src.qnwis.agents.base.DataClient.run", mock_run)

    response = client.post("/v1/council/run")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"


def test_council_endpoint_structure(client, monkeypatch):
    """Verify endpoint returns expected JSON structure."""

    def mock_run(self, query_id: str):
        return _mock_query_result(query_id)

    monkeypatch.setattr("src.qnwis.agents.base.DataClient.run", mock_run)

    response = client.post("/v1/council/run")
    data = response.json()

    assert "council" in data
    assert "verification" in data
    assert "agents" in data["council"]
    assert "findings" in data["council"]
    assert "consensus" in data["council"]
    assert "warnings" in data["council"]


def test_council_endpoint_with_params(client, monkeypatch):
    """Verify endpoint accepts query parameters."""

    def mock_run(self, query_id: str):
        return _mock_query_result(query_id)

    monkeypatch.setattr("src.qnwis.agents.base.DataClient.run", mock_run)

    response = client.post("/v1/council/run?ttl_s=600")
    assert response.status_code == 200


def test_council_endpoint_agents_present(client, monkeypatch):
    """Verify all expected agents are in response."""

    def mock_run(self, query_id: str):
        return _mock_query_result(query_id)

    monkeypatch.setattr("src.qnwis.agents.base.DataClient.run", mock_run)

    response = client.post("/v1/council/run")
    data = response.json()

    expected_agents = {
        "LabourEconomist",
        "Nationalization",
        "Skills",
        "PatternDetective",
        "NationalStrategy",
    }
    actual_agents = set(data["council"]["agents"])
    assert actual_agents == expected_agents


def test_council_endpoint_findings_format(client, monkeypatch):
    """Verify findings have correct format."""

    def mock_run(self, query_id: str):
        return _mock_query_result(query_id)

    monkeypatch.setattr("src.qnwis.agents.base.DataClient.run", mock_run)

    response = client.post("/v1/council/run")
    data = response.json()

    findings = data["council"]["findings"]
    assert len(findings) > 0

    for finding in findings:
        assert "title" in finding
        assert "summary" in finding
        assert "metrics" in finding
        assert "evidence" in finding
        assert "warnings" in finding
        assert "confidence_score" in finding
        assert isinstance(finding["metrics"], dict)
        assert isinstance(finding["evidence"], list)
        assert isinstance(finding["warnings"], list)
        assert isinstance(finding["confidence_score"], (int, float))


def test_council_endpoint_verification_format(client, monkeypatch):
    """Verify verification results have correct format."""

    def mock_run(self, query_id: str):
        return _mock_query_result(query_id)

    monkeypatch.setattr("src.qnwis.agents.base.DataClient.run", mock_run)

    response = client.post("/v1/council/run")
    data = response.json()

    verification = data["verification"]
    assert isinstance(verification, dict)

    for _agent_name, issues in verification.items():
        assert isinstance(issues, list)
        for issue in issues:
            assert "level" in issue
            assert "code" in issue
            assert "detail" in issue


def test_council_endpoint_consensus(client, monkeypatch):
    """Verify consensus metrics are computed."""

    def mock_run(self, query_id: str):
        return _mock_query_result(query_id)

    monkeypatch.setattr("src.qnwis.agents.base.DataClient.run", mock_run)

    response = client.post("/v1/council/run")
    data = response.json()

    consensus = data["council"]["consensus"]
    assert isinstance(consensus, dict)
    # Values should be numeric
    for _key, value in consensus.items():
        assert isinstance(value, (int, float))


def test_council_endpoint_warnings(client, monkeypatch):
    """Verify warnings are collected and deduplicated."""

    def mock_run(self, query_id: str):
        result = _mock_query_result(query_id)
        result.warnings = ["test_warning"]
        return result

    monkeypatch.setattr("src.qnwis.agents.base.DataClient.run", mock_run)

    response = client.post("/v1/council/run")
    data = response.json()

    warnings = data["council"]["warnings"]
    assert isinstance(warnings, list)
    # Should be sorted and deduplicated
    assert warnings == sorted(set(warnings))


def test_council_endpoint_idempotent(client, monkeypatch):
    """Verify endpoint is idempotent (deterministic)."""

    def mock_run(self, query_id: str):
        return _mock_query_result(query_id)

    monkeypatch.setattr("src.qnwis.agents.base.DataClient.run", mock_run)

    response1 = client.post("/v1/council/run")
    response2 = client.post("/v1/council/run")

    data1 = response1.json()
    data2 = response2.json()

    # Agent order should be identical
    assert data1["council"]["agents"] == data2["council"]["agents"]

    # Number of findings should be identical
    assert len(data1["council"]["findings"]) == len(data2["council"]["findings"])


def test_council_endpoint_post_method_only(client):
    """Verify endpoint only accepts POST requests."""
    # GET should fail
    response_get = client.get("/v1/council/run")
    assert response_get.status_code == 405  # Method Not Allowed

    # PUT should fail
    response_put = client.put("/v1/council/run")
    assert response_put.status_code == 405

    # DELETE should fail
    response_delete = client.delete("/v1/council/run")
    assert response_delete.status_code == 405


def test_council_endpoint_with_queries_dir(client, monkeypatch):
    """Verify queries_dir parameter is accepted."""

    def mock_run(self, query_id: str):
        return _mock_query_result(query_id)

    monkeypatch.setattr("src.qnwis.agents.base.DataClient.run", mock_run)

    response = client.post("/v1/council/run?queries_dir=custom/path")
    # Should execute without error (even if path doesn't exist due to mocking)
    assert response.status_code == 200


def test_council_endpoint_tags(client):
    """Verify endpoint has correct OpenAPI tags."""
    openapi = app.openapi()
    council_path = openapi["paths"]["/v1/council/run"]
    post_op = council_path["post"]
    assert "council" in post_op["tags"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
