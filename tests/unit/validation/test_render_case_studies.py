from __future__ import annotations

from scripts.validation.render_case_studies import (
    render_case_study,
    resolve_openapi_link,
)


def test_render_case_study_includes_audit_id_and_openapi_link() -> None:
    result = {
        "case": "sample_case",
        "endpoint": "/api/v1/query",
        "tier": "medium",
        "latency_ms": 12.5,
        "pass": True,
        "verification_passed": True,
        "citation_coverage": 1.0,
        "freshness_present": True,
    }
    body = {"metadata": {"audit_id": "AUD-SAMPLE"}}
    rendered = render_case_study("sample_case", result, body)
    assert "AUD-SAMPLE" in rendered
    assert "[Data API - Query]" in rendered
    assert "PASS" in rendered


def test_resolve_openapi_link_handles_non_api_endpoints() -> None:
    assert resolve_openapi_link("/api/v1/query") == (
        "Data API - Query",
        "../api/step27_service_api.md#data-api",
    )
    assert resolve_openapi_link("/health/ready") is None
