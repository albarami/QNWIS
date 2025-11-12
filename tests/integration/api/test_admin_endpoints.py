from __future__ import annotations

import pytest


@pytest.fixture
def llm_stub_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("QNWIS_LLM_PROVIDER", "stub")
    monkeypatch.setenv("QNWIS_STUB_TOKEN_DELAY_MS", "0")
    monkeypatch.delenv("QNWIS_ANTHROPIC_MODEL", raising=False)
    monkeypatch.delenv("QNWIS_OPENAI_MODEL", raising=False)
    return None


def _admin_headers() -> dict[str, str]:
    return {"X-API-Key": "admin-key"}


def test_admin_models_endpoint_returns_config(llm_stub_env, api_client):
    resp = api_client.get("/api/v1/admin/models", headers=_admin_headers())
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["provider"] == "stub"
    assert payload["configured_models"]["stub"] == ["stub-model"]
    assert payload["timeouts"]["seconds"] <= 60



def test_admin_llm_health_flags_missing_keys(api_client, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("QNWIS_LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("QNWIS_ANTHROPIC_MODEL", "claude-test")
    monkeypatch.setenv("QNWIS_ANTHROPIC_MODELS", "claude-test")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(
        "qnwis.llm.client.LLMClient._init_anthropic",
        lambda self: setattr(self, "client", None),
    )
    resp = api_client.get("/api/v1/admin/health/llm", headers=_admin_headers())
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "degraded"
    assert body["missing"] == ["ANTHROPIC_API_KEY"]
    assert body["configured_models"]["anthropic"] == ["claude-test"]
