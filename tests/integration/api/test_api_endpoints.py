from __future__ import annotations

from qnwis.security.ratelimit import RateLimitResult


class ExhaustedLimiter:
    """Simple limiter used to force 429 responses in tests."""

    def __init__(self) -> None:
        self._calls = 0

    def consume(self, principal, cost: int = 1) -> RateLimitResult:  # pragma: no cover - trivial
        self._calls += 1
        if self._calls >= 2:
            return RateLimitResult(
                allowed=False,
                remaining=0,
                reset_after=60.0,
                reason="rps_limit_exceeded",
                daily_remaining=0,
            )
        return RateLimitResult(
            allowed=True,
            remaining=5,
            reset_after=1.0,
            reason=None,
            daily_remaining=100,
        )


def _scenario_spec(name: str, sector: str) -> dict[str, object]:
    return {
        "name": name,
        "description": f"{name} test scenario",
        "metric": "retention",
        "sector": sector,
        "horizon_months": 12,
        "transforms": [
            {"type": "multiplicative", "value": 0.05, "start_month": 0},
        ],
    }


def test_root(api_client):
    response = api_client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "QNWIS Agent API"
    assert "docs_enabled" in body


def test_metrics_endpoint(api_client):
    api_client.get("/")  # ensure at least one request tracked
    response = api_client.get("/metrics")
    assert response.status_code == 200
    assert "qnwis_http_request_duration_seconds_count" in response.text


def test_requires_auth(api_client):
    response = api_client.post(
        "/api/v1/agents/time/baseline",
        json={"intent": "time.baseline", "params": {"metric": "retention"}},
    )
    assert response.status_code == 401


def test_role_mismatch_returns_403(api_client, viewer_headers):
    response = api_client.post(
        "/api/v1/agents/strategy/benchmark",
        json={"intent": "strategy.benchmark", "params": {"min_countries": 3}},
        headers=viewer_headers,
    )
    assert response.status_code == 403


def test_time_baseline_happy_path(api_client, analyst_headers):
    payload = {
        "intent": "time.baseline",
        "params": {"metric": "retention"},
        "options": {"enforce_citations": True, "verify_numbers": True, "audit_pack": True},
    }
    response = api_client.post("/api/v1/agents/time/baseline", json=payload, headers=analyst_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["citations"][0]["qid"] == "LMIS_RETENTION_TS"
    assert body["freshness"]["sources"]["LMIS_RETENTION_TS"] == "2024-12-31"
    assert body["confidence"]["score"] >= 40
    assert body["audit_id"]
    assert "timings_ms" in body


def test_time_intent_mismatch_returns_400(api_client, analyst_headers):
    payload = {"intent": "time.trend", "params": {"metric": "retention"}}
    response = api_client.post("/api/v1/agents/time/baseline", json=payload, headers=analyst_headers)
    assert response.status_code == 400


def test_time_trend_endpoint(api_client, analyst_headers):
    payload = {
        "intent": "time.trend",
        "params": {"metric": "retention"},
        "options": {"enforce_citations": True, "verify_numbers": True, "audit_pack": True},
    }
    response = api_client.post("/api/v1/agents/time/trend", json=payload, headers=analyst_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["result"]["intent"] == "time.trend"
    assert body["citations"]


def test_pattern_anomalies(api_client, analyst_headers):
    payload = {
        "intent": "pattern.anomalies",
        "params": {"z_threshold": 2.0},
        "options": {"enforce_citations": True, "verify_numbers": True, "audit_pack": True},
    }
    response = api_client.post("/api/v1/agents/pattern/anomalies", json=payload, headers=analyst_headers)
    assert response.status_code == 200
    body = response.json()
    assert "findings" in body["result"]
    assert any(c["qid"] == "syn_attrition_by_sector_latest" for c in body["citations"])


def test_pattern_correlations(api_client, analyst_headers):
    payload = {
        "intent": "pattern.correlations",
        "params": {"min_correlation": 0.5},
        "options": {"enforce_citations": True, "verify_numbers": True, "audit_pack": True},
    }
    response = api_client.post("/api/v1/agents/pattern/correlations", json=payload, headers=analyst_headers)
    assert response.status_code == 200
    assert "findings" in response.json()["result"]


def test_predictor_forecast(api_client, analyst_headers):
    payload = {
        "intent": "predictor.forecast",
        "params": {"metric": "retention", "horizon_months": 6},
        "options": {"enforce_citations": True, "verify_numbers": True, "audit_pack": True},
    }
    response = api_client.post("/api/v1/agents/predictor/forecast", json=payload, headers=analyst_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["result"]["intent"] == "predictor.forecast"
    assert body["citations"]


def test_predictor_warnings(api_client, analyst_headers):
    payload = {
        "intent": "predictor.warnings",
        "params": {"metric": "retention", "horizon_months": 3},
    }
    response = api_client.post("/api/v1/agents/predictor/warnings", json=payload, headers=analyst_headers)
    assert response.status_code == 200
    assert "narrative" in response.json()["result"]


def test_scenario_apply(api_client, analyst_headers):
    payload = {
        "intent": "scenario.apply",
        "params": {"spec": _scenario_spec("Retention Boost", "Energy"), "format": "dict"},
        "options": {"audit_pack": True},
    }
    response = api_client.post("/api/v1/agents/scenario/apply", json=payload, headers=analyst_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["result"]["intent"] == "scenario.apply"
    assert body["audit_id"]


def test_scenario_apply_requires_spec(api_client, analyst_headers):
    payload = {"intent": "scenario.apply", "params": {}, "options": {"audit_pack": True}}
    response = api_client.post("/api/v1/agents/scenario/apply", json=payload, headers=analyst_headers)
    assert response.status_code == 400


def test_scenario_compare(api_client, analyst_headers):
    payload = {
        "intent": "scenario.compare",
        "params": {
            "specs": [
                _scenario_spec("Energy Push", "Energy"),
                _scenario_spec("Construction Stabilize", "Construction"),
            ],
            "format": "dict",
        },
    }
    response = api_client.post("/api/v1/agents/scenario/compare", json=payload, headers=analyst_headers)
    assert response.status_code == 200
    assert "narrative" in response.json()["result"]


def test_strategy_benchmark(api_client, analyst_headers):
    payload = {"intent": "strategy.benchmark", "params": {"min_countries": 3}}
    response = api_client.post("/api/v1/agents/strategy/benchmark", json=payload, headers=analyst_headers)
    assert response.status_code == 200
    assert "findings" in response.json()["result"]


def test_strategy_vision(api_client, analyst_headers):
    payload = {"intent": "strategy.vision", "params": {"target_year": 2030}}
    response = api_client.post("/api/v1/agents/strategy/vision", json=payload, headers=analyst_headers)
    assert response.status_code == 200


def test_rate_limit_returns_429(api_client, analyst_headers):
    api_client.app.state.rate_limiter = ExhaustedLimiter()
    ok = api_client.post(
        "/api/v1/agents/time/baseline",
        json={"intent": "time.baseline", "params": {"metric": "retention"}},
        headers=analyst_headers,
    )
    assert ok.status_code == 200
    blocked = api_client.post(
        "/api/v1/agents/time/baseline",
        json={"intent": "time.baseline", "params": {"metric": "retention"}},
        headers=analyst_headers,
    )
    assert blocked.status_code == 429
    assert blocked.json()["reason"] == "rps_limit_exceeded"


def test_internal_error_exposes_error_id(api_client, api_stub_client, analyst_headers):
    original_run = api_stub_client.run

    def _boom(query_id: str):
        raise RuntimeError(f"Boom on {query_id}")

    api_stub_client.run = _boom  # type: ignore[assignment]
    try:
        response = api_client.post(
            "/api/v1/agents/time/baseline",
            json={"intent": "time.baseline", "params": {"metric": "retention"}},
            headers=analyst_headers,
        )
    finally:
        api_stub_client.run = original_run  # type: ignore[assignment]

    assert response.status_code == 500
    assert "error_id" in response.json()
