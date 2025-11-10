from __future__ import annotations


def test_health_and_metrics(api_client):
    health = api_client.get("/health/ready")
    assert health.status_code in (200, 503)
    metrics = api_client.get("/metrics")
    assert metrics.status_code == 200


def test_router_smoke(api_client, analyst_headers):
    baseline = api_client.post(
        "/api/v1/agents/time/baseline",
        json={"intent": "time.baseline", "params": {"metric": "retention"}},
        headers=analyst_headers,
    )
    assert baseline.status_code == 200

    pattern = api_client.post(
        "/api/v1/agents/pattern/anomalies",
        json={"intent": "pattern.anomalies", "params": {"z_threshold": 2.0}},
        headers=analyst_headers,
    )
    assert pattern.status_code == 200

    predictor = api_client.post(
        "/api/v1/agents/predictor/forecast",
        json={"intent": "predictor.forecast", "params": {"metric": "retention", "horizon_months": 6}},
        headers=analyst_headers,
    )
    assert predictor.status_code == 200

    scenario = api_client.post(
        "/api/v1/agents/scenario/apply",
        json={
            "intent": "scenario.apply",
            "params": {
                "spec": {
                    "name": "System Scenario",
                    "description": "determinism check",
                    "metric": "retention",
                    "sector": "Energy",
                    "horizon_months": 12,
                    "transforms": [{"type": "multiplicative", "value": 0.02, "start_month": 0}],
                },
                "format": "dict",
            },
        },
        headers=analyst_headers,
    )
    assert scenario.status_code == 200

    strategy = api_client.post(
        "/api/v1/agents/strategy/benchmark",
        json={"intent": "strategy.benchmark", "params": {"min_countries": 3}},
        headers=analyst_headers,
    )
    assert strategy.status_code == 200


def test_deterministic_time_machine(api_client, analyst_headers):
    payload = {"intent": "time.baseline", "params": {"metric": "retention"}}
    first = api_client.post("/api/v1/agents/time/baseline", json=payload, headers=analyst_headers).json()
    second = api_client.post("/api/v1/agents/time/baseline", json=payload, headers=analyst_headers).json()
    assert first["result"]["narrative"] == second["result"]["narrative"]
