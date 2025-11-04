"""Tests covering cache_access error handling paths."""

from __future__ import annotations

import pytest

from src.qnwis.data.deterministic import cache_access as cache_module
from src.qnwis.data.deterministic.cache_access import (
    CacheDecodingError,
    QueryResult,
    QuerySpec,
    _decode_cached_result,
)
from src.qnwis.data.deterministic.models import Freshness, Provenance, Row


def _sample_result() -> QueryResult:
    return QueryResult(
        query_id="q",
        rows=[Row(data={"value": 1})],
        unit="count",
        provenance=Provenance(
            source="csv",
            dataset_id="x",
            locator="employed-persons-15-years-and-above.csv",
            fields=["value"],
        ),
        freshness=Freshness(asof_date="auto"),
    )


def test_decode_cached_result_invalid_json():
    with pytest.raises(CacheDecodingError):
        _decode_cached_result("{")


def test_decode_cached_result_missing_meta():
    payload = '{"payload": "data"}'
    with pytest.raises(CacheDecodingError):
        _decode_cached_result(payload)


def test_decode_cached_result_meta_not_mapping():
    payload = '{"_meta": ["encoded"], "payload": "data"}'
    with pytest.raises(CacheDecodingError):
        _decode_cached_result(payload)


def test_decode_cached_result_zlib_requires_string():
    envelope = {"_meta": {"content_encoding": "zlib"}, "payload": {"not": "string"}}
    with pytest.raises(CacheDecodingError):
        _decode_cached_result(cache_module.json.dumps(envelope))


def test_decode_cached_result_zlib_bad_base64():
    envelope = {"_meta": {"content_encoding": "zlib"}, "payload": "%%%"}
    with pytest.raises(CacheDecodingError):
        _decode_cached_result(cache_module.json.dumps(envelope))


def test_decode_cached_result_unsupported_encoding():
    envelope = {"_meta": {"content_encoding": "brotli"}, "payload": "data"}
    with pytest.raises(CacheDecodingError):
        _decode_cached_result(cache_module.json.dumps(envelope))


def test_canonicalize_params_includes_sets():
    spec = QuerySpec(
        id="q",
        title="t",
        description="d",
        source="csv",
        params={"values": {"b", "a"}},
    )
    key1 = cache_module._key_for(spec)
    key2 = cache_module._key_for(
        QuerySpec(
            id="q",
            title="t",
            description="d",
            source="csv",
            params={"values": {"a", "b"}},
        )
    )
    assert key1 == key2


def test_execute_cached_drops_corrupt_entry(monkeypatch):
    spec = QuerySpec(
        id="q",
        title="t",
        description="d",
        source="csv",
        params={"pattern": "x.csv"},
    )
    registry = type("R", (object,), {"get": lambda self, _: spec})()

    class CorruptBackend(cache_module.CacheBackend):
        def __init__(self) -> None:
            self.value: str | None = None
            self.deleted = 0

        def get(self, key: str):
            return self.value

        def set(self, key: str, value: str, ttl_s: int | None = None):
            self.value = value

        def delete(self, key: str):
            self.deleted += 1
            self.value = None

    backend = CorruptBackend()
    backend.value = "{"  # corrupt JSON

    def fake_execute(*_):
        return _sample_result()

    monkeypatch.setattr(cache_module, "execute_uncached", fake_execute)
    monkeypatch.setattr(cache_module, "get_cache_backend", lambda: backend)

    result = cache_module.execute_cached("q", registry, ttl_s=300)
    assert backend.deleted == 1
    assert backend.value is not None  # new cached value stored
    assert result.rows[0].data["value"] == 1
