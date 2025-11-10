from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from qnwis.agents.base import DataClient
from qnwis.api.server import create_app
from qnwis.data.deterministic.models import Freshness, Provenance, QueryResult, Row
from qnwis.security.ratelimit import RateLimiter

STUB_UPDATED_AT = "2025-01-02T00:00:00+00:00"


class _StubRegistry:
    def __init__(self, ids: list[str]) -> None:
        self._ids = ids

    def all_ids(self) -> list[str]:
        return list(self._ids)


class StubDataClient(DataClient):
    """In-memory DataClient used for API tests."""

    def __init__(self) -> None:
        self._responses: dict[str, QueryResult] = {}
        self._registry_ids: list[str] = []
        self._registry = _StubRegistry(self._registry_ids)
        self.ttl_s = 0

    def add_result(self, result: QueryResult) -> None:
        self._responses[result.query_id] = result
        if result.query_id not in self._registry_ids:
            self._registry_ids.append(result.query_id)

    def run(self, query_id: str) -> QueryResult:
        if query_id not in self._responses:
            raise KeyError(f"Stub missing query_id '{query_id}'")
        return self._responses[query_id].model_copy(deep=True)

    @property
    def registry(self) -> _StubRegistry:  # type: ignore[override]
        return self._registry


def _freshness() -> Freshness:
    return Freshness(asof_date="2024-12-31", updated_at=STUB_UPDATED_AT)


def _make_result(qid: str, rows: list[dict[str, Any]], unit: str) -> QueryResult:
    if not rows:
        raise ValueError(f"Stub dataset '{qid}' requires at least one row")
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    return QueryResult(
        query_id=qid,
        rows=[Row(data=dict(row)) for row in rows],
        unit=unit,  # type: ignore[arg-type]
        provenance=Provenance(
            source="csv",
            dataset_id=f"stub_{qid}",
            locator=f"/tmp/{qid}.csv",
            fields=fields,
            license="Synthetic Test Pack",
        ),
        freshness=_freshness(),
    )


def _time_series(start: float, delta: float, sector_cycle: tuple[str, str]) -> list[dict[str, Any]]:
    months = (
        [f"2023-{m:02d}" for m in range(1, 13)]
        + [f"2024-{m:02d}" for m in range(1, 13)]
        + [f"2025-{m:02d}" for m in range(1, 7)]
    )
    rows: list[dict[str, Any]] = []
    for idx, month in enumerate(months):
        sector = sector_cycle[idx % len(sector_cycle)]
        rows.append({"period": month, "value": round(start + idx * delta, 2), "sector": sector})
    return rows


def _baseline_series(base: float) -> list[dict[str, Any]]:
    return [{"month": i + 1, "value": round(base + i * 0.75, 2)} for i in range(12)]


def populate_stub_client(client: StubDataClient) -> None:
    retention_rows = _time_series(95.0, 0.6, ("Energy", "Construction"))
    client.add_result(_make_result("LMIS_RETENTION_TS", retention_rows, unit="percent"))
    qatarization_rows = _time_series(30.0, 0.25, ("Energy", "Finance"))
    client.add_result(_make_result("LMIS_QATARIZATION_TS", qatarization_rows, unit="percent"))
    salary_rows = _time_series(12000.0, 150.0, ("Energy", "National"))
    client.add_result(_make_result("LMIS_SALARY_TS", salary_rows, unit="qar"))
    employment_rows = _time_series(50000.0, 800.0, ("Energy", "Construction"))
    client.add_result(_make_result("LMIS_EMPLOYMENT_TS", employment_rows, unit="count"))
    attrition_monthly = [
        {"period": f"2024-{month:02d}", "value": value}
        for month, value in enumerate([7.5, 7.7, 7.9, 8.2, 8.4, 8.8, 9.0, 9.4, 9.6, 9.7, 10.0, 10.5], start=1)
    ]
    client.add_result(_make_result("syn_attrition_monthly", attrition_monthly, unit="percent"))

    attrition_by_sector = [
        {"sector": "Energy", "attrition_percent": 8.5},
        {"sector": "Construction", "attrition_percent": 12.3},
        {"sector": "Finance", "attrition_percent": 6.4},
        {"sector": "ICT", "attrition_percent": 5.9},
        {"sector": "Healthcare", "attrition_percent": 7.1},
    ]
    client.add_result(_make_result("syn_attrition_by_sector_latest", attrition_by_sector, unit="percent"))

    qatarization_by_sector = [
        {"sector": sector, "qatarization_percent": 20.0 + idx * 1.5, "qataris": 400 + idx * 50, "non_qataris": 1500 - idx * 40}
        for idx, sector in enumerate(["Energy", "Construction", "Finance", "ICT", "Healthcare"])
    ]
    client.add_result(_make_result("syn_qatarization_by_sector_latest", qatarization_by_sector, unit="percent"))

    gcc_unemployment = [
        {"country": "Qatar", "unemployment_rate": 1.5},
        {"country": "KSA", "unemployment_rate": 6.1},
        {"country": "UAE", "unemployment_rate": 2.8},
        {"country": "Kuwait", "unemployment_rate": 2.2},
    ]
    client.add_result(_make_result("syn_unemployment_rate_gcc_latest", gcc_unemployment, unit="percent"))

    metric_series = [{"period": row["period"], "value": row["value"], "sector": row["sector"]} for row in retention_rows]
    client.add_result(_make_result("retention", metric_series, unit="percent"))

    for scope, base in [
        ("all", 88.0),
        ("energy", 90.0),
        ("construction", 84.0),
    ]:
        qid = f"forecast_baseline_retention_{scope}_12m"
        client.add_result(_make_result(qid, _baseline_series(base), unit="percent"))


@pytest.fixture
def api_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("QNWIS_JWT_SECRET", "integration-secret")
    monkeypatch.setenv("QNWIS_RATE_LIMIT_RPS", "50")
    monkeypatch.setenv("QNWIS_RATE_LIMIT_DAILY", "5000")
    monkeypatch.setenv("QNWIS_API_KEY_ANALYST", "integration-key:analyst")
    monkeypatch.setenv("QNWIS_API_KEY_VIEWER", "viewer-key:viewer")
    monkeypatch.setenv("QNWIS_API_KEY_ADMIN", "admin-key:admin")
    monkeypatch.setenv("QNWIS_BYPASS_AUTH", "false")
    monkeypatch.setenv("QNWIS_REDIS_URL", "")
    return None


@pytest.fixture
def api_stub_client() -> StubDataClient:
    client = StubDataClient()
    populate_stub_client(client)
    return client


@pytest.fixture
def api_client(api_env, api_stub_client: StubDataClient):
    app = create_app()
    with TestClient(app) as client:
        client.app.state.data_client_factory = lambda: api_stub_client
        client.app.state.rate_limiter = RateLimiter(rps=1000, burst=1000, daily=10000, clock=client.app.state.clock)
        yield client


@pytest.fixture
def analyst_headers() -> dict[str, str]:
    return {"X-API-Key": "integration-key"}


@pytest.fixture
def viewer_headers() -> dict[str, str]:
    return {"X-API-Key": "viewer-key"}
