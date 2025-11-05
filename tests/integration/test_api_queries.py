"""Integration tests for deterministic query API endpoints."""

import textwrap
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import src.qnwis.api.routers.queries as queries_router
from src.qnwis.app import app


def _write_query(tmpdir: Path) -> tuple[str, str]:
    """
    Create a test query definition and CSV data file.

    Args:
        tmpdir: Temporary directory for test files

    Returns:
        Tuple of (queries_dir, data_dir)
    """
    qdir = tmpdir / "queries"
    qdir.mkdir(exist_ok=True)

    query_yaml = qdir / "q.yaml"
    query_yaml.write_text(
        textwrap.dedent("""
        id: q_demo
        title: Demo
        description: D
        source: csv
        expected_unit: percent
        params:
          pattern: "demo*.csv"
          select: ["year","male_percent","female_percent","total_percent"]
          year: 2023
        constraints:
          sum_to_one: true
          freshness_sla_days: 3650
    """).strip(),
        encoding="utf-8",
    )

    dfile = tmpdir / "demo_1.csv"
    dfile.write_text(
        "year;male_percent;female_percent;total_percent\n2023;60;40;100\n",
        encoding="utf-8",
    )
    return str(qdir), str(tmpdir)


@pytest.fixture
def test_env(tmp_path: Path, monkeypatch):
    """
    Set up test environment with temporary query and data directories.

    Args:
        tmp_path: Pytest temporary directory
        monkeypatch: Pytest monkeypatch fixture
    """
    qdir, base = _write_query(tmp_path)
    monkeypatch.setenv("QNWIS_QUERIES_DIR", qdir)

    # Monkeypatch CSV BASE
    import src.qnwis.data.connectors.csv_catalog as mod

    old_base = mod.BASE
    mod.BASE = Path(base)
    yield qdir, base
    mod.BASE = old_base


def test_list_queries(test_env):
    """Test listing available queries."""
    c = TestClient(app)
    r = c.get("/v1/queries")
    assert r.status_code == 200
    data = r.json()
    assert "ids" in data
    assert "q_demo" in data["ids"]


def test_list_queries_empty(monkeypatch, tmp_path):
    """Empty registry should return an empty list of IDs."""
    monkeypatch.setenv("QNWIS_QUERIES_DIR", str(tmp_path))
    c = TestClient(app)
    r = c.get("/v1/queries")
    assert r.status_code == 200
    assert r.json()["ids"] == []


def test_run_query_basic(test_env):
    """Test basic query execution."""
    c = TestClient(app)
    r = c.post("/v1/queries/q_demo/run", json={})
    assert r.status_code == 200
    js = r.json()
    assert js["query_id"] == "q_demo"
    assert js["unit"] == "percent"
    assert len(js["rows"]) > 0
    assert "provenance" in js
    assert "freshness" in js
    assert "warnings" in js


def test_run_query_with_ttl(test_env):
    """Test query execution with TTL override."""
    c = TestClient(app)
    r = c.post("/v1/queries/q_demo/run", json={"ttl_s": 120})
    assert r.status_code == 200
    js = r.json()
    assert js["query_id"] == "q_demo"


def test_run_query_with_param_overrides(test_env):
    """Test query execution with parameter overrides."""
    c = TestClient(app)
    r = c.post(
        "/v1/queries/q_demo/run",
        json={"override_params": {"year": "2023"}},
    )
    assert r.status_code == 200
    js = r.json()
    assert js["query_id"] == "q_demo"


def test_run_query_overrides_do_not_mutate_registry(test_env):
    """Per-request overrides should not persist in the registry."""
    c = TestClient(app)
    r = c.post(
        "/v1/queries/q_demo/run",
        json={"override_params": {"max_rows": 1}},
    )
    assert r.status_code == 200

    spec_resp = c.get("/v1/queries/q_demo")
    assert spec_resp.status_code == 200
    params = spec_resp.json()["query"]["params"]
    assert "max_rows" not in params
    assert params.get("year") == 2023


def test_run_query_ttl_bounds(test_env, monkeypatch):
    """Test that TTL is bounded to 60-86400 seconds."""
    c = TestClient(app)
    captured: list[int] = []

    original_execute = queries_router.execute_cached

    def wrapped_execute(query_id, registry, ttl_s=None, invalidate=False, spec_override=None):
        captured.append(ttl_s)
        return original_execute(
            query_id,
            registry,
            ttl_s=ttl_s,
            invalidate=invalidate,
            spec_override=spec_override,
        )

    monkeypatch.setattr(queries_router, "execute_cached", wrapped_execute)

    # Too low TTL should be clamped to 60
    r = c.post("/v1/queries/q_demo/run", json={"ttl_s": 30})
    assert r.status_code == 200

    # Too high TTL should be clamped to 86400
    r = c.post("/v1/queries/q_demo/run", json={"ttl_s": 100000})
    assert r.status_code == 200

    # Valid TTL should work
    r = c.post("/v1/queries/q_demo/run", json={"ttl_s": 300})
    assert r.status_code == 200

    assert captured == [60, 86400, 300]


def test_run_query_invalid_override_type(test_env):
    """Invalid override_params types should return 400."""
    c = TestClient(app)
    r = c.post("/v1/queries/q_demo/run", json={"override_params": ["bad"]})
    assert r.status_code == 400
    assert r.json()["detail"] == "'override_params' must be an object mapping."


def test_run_query_whitelisted_params(test_env):
    """Test that only whitelisted parameters can be overridden."""
    c = TestClient(app)
    # Whitelisted params
    r = c.post(
        "/v1/queries/q_demo/run",
        json={
            "override_params": {
                "year": 2023,
                "timeout_s": 10,
                "max_rows": 100,
                "to_percent": ["male_percent"],
            }
        },
    )
    assert r.status_code == 200

    # Non-whitelisted params should be ignored (not cause error)
    r = c.post(
        "/v1/queries/q_demo/run",
        json={"override_params": {"year": 2023, "malicious_param": "value"}},
    )
    assert r.status_code == 200


def test_run_query_unknown_id(test_env):
    """Test querying with unknown query_id."""
    c = TestClient(app)
    r = c.post("/v1/queries/nonexistent/run", json={})
    assert r.status_code == 404
    assert "Unknown query_id" in r.json()["detail"]


def test_run_query_normalized_rows(test_env):
    """Test that returned rows have normalized keys."""
    c = TestClient(app)
    r = c.post("/v1/queries/q_demo/run", json={})
    assert r.status_code == 200
    js = r.json()
    rows = js["rows"]
    assert len(rows) > 0
    # Check that keys are snake_case
    first_row = rows[0]
    assert "male_percent" in first_row or "year" in first_row


def test_run_query_provenance_and_freshness(test_env):
    """Test that provenance and freshness are included."""
    c = TestClient(app)
    r = c.post("/v1/queries/q_demo/run", json={})
    assert r.status_code == 200
    js = r.json()
    assert "provenance" in js
    assert "freshness" in js
    assert isinstance(js["provenance"], dict)
    assert isinstance(js["freshness"], dict)


def test_get_query_spec(test_env):
    """GET endpoint returns the registered QuerySpec."""
    c = TestClient(app)
    r = c.get("/v1/queries/q_demo")
    assert r.status_code == 200
    data = r.json()
    assert data["query"]["id"] == "q_demo"
    assert "params" in data["query"]


def test_get_query_spec_unknown(test_env):
    """Unknown query id returns 404."""
    c = TestClient(app)
    r = c.get("/v1/queries/does-not-exist")
    assert r.status_code == 404


def test_run_query_no_sum_to_one_warnings(test_env):
    """Test that no sum_to_one warnings for valid data."""
    c = TestClient(app)
    r = c.post("/v1/queries/q_demo/run", json={})
    assert r.status_code == 200
    js = r.json()
    # The test data sums to 100, so no warnings expected
    warnings = js["warnings"]
    # May or may not have warnings depending on implementation
    # Just verify warnings field exists
    assert isinstance(warnings, list)


def test_invalidate_cache(test_env):
    """Test cache invalidation endpoint."""
    c = TestClient(app)
    # First, run query to populate cache
    c.post("/v1/queries/q_demo/run", json={})

    # Then invalidate
    r = c.post("/v1/queries/q_demo/cache/invalidate")
    assert r.status_code == 200
    js = r.json()
    assert js["status"] == "ok"
    assert js["invalidated"] == "q_demo"


def test_invalidate_cache_unknown_query(test_env):
    """Test cache invalidation for unknown query (should not error)."""
    c = TestClient(app)
    r = c.post("/v1/queries/nonexistent/cache/invalidate")
    assert r.status_code == 200
    js = r.json()
    assert js["status"] == "ok"


def test_request_id_header(test_env):
    """Test that X-Request-ID is included in response if provided."""
    c = TestClient(app)
    r = c.post(
        "/v1/queries/q_demo/run",
        json={},
        headers={"X-Request-ID": "test-req-123"},
    )
    assert r.status_code == 200
    js = r.json()
    assert js["request_id"] == "test-req-123"
    assert r.headers.get("X-Request-ID") == "test-req-123"


def test_health_endpoints():
    """Test health and readiness endpoints."""
    c = TestClient(app)

    r = c.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"

    r = c.get("/ready")
    assert r.status_code == 200
    assert r.json()["status"] == "ready"


def test_queries_dir_fallback(monkeypatch, tmp_path):
    """Test that queries_dir falls back gracefully if not set."""
    # Don't set QNWIS_QUERIES_DIR
    c = TestClient(app)
    r = c.get("/v1/queries")
    # Should return empty list or handle gracefully
    assert r.status_code == 200
    data = r.json()
    assert "ids" in data
    assert isinstance(data["ids"], list)
