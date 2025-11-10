"""Unit tests for qnwis_cache CLI helpers."""

from __future__ import annotations

import json
import sys
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

import pytest

from src.qnwis.cache.warmup import WarmupPackError
from src.qnwis.cli import qnwis_cache


@dataclass
class DummyQueryResult:
    query_id: str
    rows: list[dict[str, Any]]


class StubCache:
    """Minimal cache double that mimics DeterministicRedisCache contract."""

    def __init__(self, *, redis_info: dict[str, Any] | None = None, delete_count: int | None = None) -> None:
        self._redis_info = redis_info or {"status": "ok"}
        self._delete_count = delete_count
        self.deleted_prefixes: list[str] = []
        self.store: dict[str, Any] = {}
        self.last_ttl: int | None = None

    def info(self) -> dict[str, Any]:
        return self._redis_info

    def delete_prefix(self, prefix: str) -> int:
        self.deleted_prefixes.append(prefix)
        return self._delete_count if self._delete_count is not None else len(prefix)

    def get(self, key: str) -> Any:
        return self.store.get(key)

    def set(self, key: str, value: Any, ttl: int) -> None:
        self.store[key] = value
        self.last_ttl = ttl


class StubClient:
    """Client double exposing dynamic callables."""

    def __init__(self, result_factory: Callable[[dict[str, Any]], DummyQueryResult]) -> None:
        self._factory = result_factory

    def __getattr__(self, item: str) -> Callable[..., DummyQueryResult]:
        def _runner(**params: Any) -> DummyQueryResult:
            return self._factory({"fn": item, "params": params})

        return _runner


def _run_cli(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    cache: StubCache,
    *,
    action: str,
    **kwargs: str,
) -> dict[str, Any]:
    argv = ["qnwis-cache", "--action", action]
    for key, value in kwargs.items():
        flag = f"--{key.replace('_', '-')}"
        argv.extend([flag, value])

    monkeypatch.setattr(sys, "argv", argv)
    monkeypatch.setattr(qnwis_cache, "DeterministicRedisCache", lambda: cache)
    qnwis_cache.main()
    output = capsys.readouterr().out.strip()
    assert output, "CLI did not emit any JSON payload"
    return json.loads(output)


def test_warmup_sets_and_hits() -> None:
    """Warmup should populate cache once and count subsequent hits."""

    cache = StubCache()
    qr = DummyQueryResult(query_id="demo.qid", rows=[{"value": 1}])

    client = StubClient(lambda _: qr)
    samples = [{"fn": "get_retention_by_company", "params": {"sector": "Energy"}}]

    first = qnwis_cache.warmup(cache, samples, client)
    assert first == {"sets": 1, "hits": 0}

    second = qnwis_cache.warmup(cache, samples, client)
    assert second == {"sets": 0, "hits": 1}


def test_warmup_uses_negative_ttl_for_empty_rows() -> None:
    """Negative TTL guard should limit empty result caching horizon."""

    cache = StubCache()
    qr = DummyQueryResult(query_id="demo.qid", rows=[])
    client = StubClient(lambda _: qr)
    samples = [{"fn": "get_retention_by_company", "params": {"sector": "ICT"}}]

    result = qnwis_cache.warmup(cache, samples, client)
    assert result == {"sets": 1, "hits": 0}
    assert cache.last_ttl == qnwis_cache.NEGATIVE_CACHE_TTL


def test_cli_info_action_outputs_payload(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """Info action should emit registry metadata and Redis info."""

    cache = StubCache(redis_info={"role": "primary"})
    payload = _run_cli(monkeypatch, capsys, cache, action="info")
    assert payload["redis"] == {"role": "primary"}
    assert payload["registry_version"] == qnwis_cache.REGISTRY_VERSION


def test_cli_invalidate_prefix(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """Invalidate action should report deleted prefix count."""

    cache = StubCache(delete_count=3)
    payload = _run_cli(monkeypatch, capsys, cache, action="invalidate-prefix", prefix="qr:demo")
    assert payload == {"action": "invalidate-prefix", "prefix": "qr:demo", "deleted": 3}


def test_cli_list_packs_success(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """List packs action should include pack metadata."""

    cache = StubCache()
    monkeypatch.setattr(qnwis_cache, "list_warmup_packs", lambda _: ["core_kpis", "engagement"])

    payload = _run_cli(monkeypatch, capsys, cache, action="list-packs", packs_path="dummy.yml")
    assert payload["count"] == 2
    assert payload["packs"] == ["core_kpis", "engagement"]


def test_cli_list_packs_logs_error(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """List packs should log debug context when loader fails."""

    cache = StubCache()

    def _boom(_: Any) -> Iterable[str]:
        raise WarmupPackError("bad packs")

    monkeypatch.setattr(qnwis_cache, "list_warmup_packs", _boom)
    caplog.set_level("DEBUG", logger=qnwis_cache.logger.name)

    payload = _run_cli(monkeypatch, capsys, cache, action="list-packs", packs_path="missing.yml")

    assert payload["error"] == "bad packs"
    assert any("Warmup pack listing failed" in record.getMessage() for record in caplog.records)


def test_cli_show_pack_success(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """Show-pack action should return serialized specs."""

    cache = StubCache()
    monkeypatch.setattr(qnwis_cache, "load_warmup_pack", lambda name, _: [{"fn": "demo", "params": {}}])

    payload = _run_cli(monkeypatch, capsys, cache, action="show-pack", pack="demo", packs_path="packs.yml")
    assert payload["spec_count"] == 1
    assert payload["pack"] == "demo"


def test_cli_show_pack_logs_error(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Show-pack error path should emit debug diagnostics."""

    cache = StubCache()

    def _boom(*_: Any, **__: Any) -> list[dict[str, Any]]:
        raise WarmupPackError("unknown pack")

    monkeypatch.setattr(qnwis_cache, "load_warmup_pack", _boom)
    caplog.set_level("DEBUG", logger=qnwis_cache.logger.name)

    payload = _run_cli(monkeypatch, capsys, cache, action="show-pack", pack="missing", packs_path="packs.yml")

    assert payload["error"] == "unknown pack"
    assert any("Warmup pack load failed" in record.getMessage() for record in caplog.records)
