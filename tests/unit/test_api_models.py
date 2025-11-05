"""Unit tests for API Pydantic models."""

from src.qnwis.api.models import QueryRunRequest, QueryRunResponse


def test_query_run_request_default() -> None:
    """Test QueryRunRequest with default values."""
    req = QueryRunRequest()
    assert req.ttl_s is None
    assert req.override_params == {}


def test_query_run_request_with_ttl() -> None:
    """Test QueryRunRequest with TTL override."""
    req = QueryRunRequest(ttl_s=120)
    assert req.ttl_s == 120
    assert req.override_params == {}


def test_query_run_request_with_overrides() -> None:
    """Test QueryRunRequest with parameter overrides."""
    req = QueryRunRequest(ttl_s=120, override_params={"year": 2023})
    assert req.ttl_s == 120
    assert "year" in req.override_params
    assert req.override_params["year"] == 2023


def test_query_run_request_serialization() -> None:
    """Test QueryRunRequest serialization to dict."""
    req = QueryRunRequest(ttl_s=120, override_params={"year": 2023, "max_rows": 100})
    data = req.model_dump()
    assert data["ttl_s"] == 120
    assert data["override_params"]["year"] == 2023
    assert data["override_params"]["max_rows"] == 100


def test_query_run_response_basic() -> None:
    """Test QueryRunResponse with minimal fields."""
    resp = QueryRunResponse(
        query_id="q",
        unit="percent",
        rows=[{"year": 2023}],
        provenance={},
        freshness={},
    )
    assert resp.query_id == "q"
    assert resp.unit == "percent"
    assert len(resp.rows) == 1
    assert resp.rows[0]["year"] == 2023
    assert resp.warnings == []
    assert resp.request_id is None


def test_query_run_response_with_warnings() -> None:
    """Test QueryRunResponse with warnings."""
    resp = QueryRunResponse(
        query_id="q",
        unit="percent",
        rows=[],
        provenance={},
        freshness={},
        warnings=["freshness_exceeded"],
    )
    assert len(resp.warnings) == 1
    assert resp.warnings[0] == "freshness_exceeded"


def test_query_run_response_with_request_id() -> None:
    """Test QueryRunResponse with request ID."""
    resp = QueryRunResponse(
        query_id="q",
        unit="percent",
        rows=[],
        provenance={},
        freshness={},
        request_id="req-123",
    )
    assert resp.request_id == "req-123"


def test_query_run_response_serialization() -> None:
    """Test QueryRunResponse serialization to dict."""
    resp = QueryRunResponse(
        query_id="q_demo",
        unit="percent",
        rows=[{"year": 2023, "value": 100}],
        provenance={"source": "csv", "dataset_id": "demo"},
        freshness={"asof_date": "2023-01-01"},
        warnings=["test_warning"],
        request_id="req-456",
    )
    data = resp.model_dump()
    assert data["query_id"] == "q_demo"
    assert data["unit"] == "percent"
    assert len(data["rows"]) == 1
    assert data["rows"][0]["year"] == 2023
    assert data["provenance"]["source"] == "csv"
    assert data["freshness"]["asof_date"] == "2023-01-01"
    assert "test_warning" in data["warnings"]
    assert data["request_id"] == "req-456"


def test_models_roundtrip() -> None:
    """Test full roundtrip of request/response models."""
    req = QueryRunRequest(ttl_s=120, override_params={"year": 2023})
    assert req.ttl_s == 120
    assert "year" in req.override_params

    resp = QueryRunResponse(
        query_id="q",
        unit="percent",
        rows=[{"year": 2023}],
        provenance={},
        freshness={},
    )
    assert resp.query_id == "q"
    assert resp.rows[0]["year"] == 2023
