"""Integration tests for briefing API endpoint."""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

import src.qnwis.data.connectors.csv_catalog as csvcat
from src.qnwis.app import app
from src.qnwis.data.synthetic.seed_lmis import generate_synthetic_lmis


def _seed_catalog(base: Path) -> None:
    """Populate synthetic catalog files required for API tests."""
    generate_synthetic_lmis(str(base))
    employment_csv = base / "employed-persons-15-years-and-above-2023.csv"
    employment_csv.write_text(
        "year,male_percent,female_percent,total_percent\n2023,52.0,48.0,100.0\n",
        encoding="utf-8",
    )


@contextmanager
def synthetic_catalog(tmp_path: Path):
    """Context manager to point csv catalog at synthetic data."""
    _seed_catalog(tmp_path)
    old = csvcat.BASE
    csvcat.BASE = Path(tmp_path)
    try:
        yield
    finally:
        csvcat.BASE = old


def test_minister_briefing_endpoint(tmp_path, monkeypatch):
    """Test POST /v1/briefing/minister endpoint returns complete briefing."""
    # Generate synthetic data
    with synthetic_catalog(Path(tmp_path)):
        monkeypatch.setenv("QNWIS_QUERIES_DIR", "src/qnwis/data/queries")
        c = TestClient(app)
        r = c.post("/v1/briefing/minister")
        assert r.status_code == 200
        js = r.json()
        assert "markdown" in js
        assert isinstance(js["headline"], list)


def test_minister_briefing_response_structure(tmp_path, monkeypatch):
    """Test that briefing response has all required fields."""
    with synthetic_catalog(Path(tmp_path)):
        monkeypatch.setenv("QNWIS_QUERIES_DIR", "src/qnwis/data/queries")
        c = TestClient(app)
        r = c.post("/v1/briefing/minister")
        assert r.status_code == 200
        js = r.json()

        # Check all required fields
        assert "title" in js
        assert "headline" in js
        assert "key_metrics" in js
        assert "red_flags" in js
        assert "provenance" in js
        assert "min_confidence" in js
        assert "licenses" in js
        assert "markdown" in js

        # Check types
        assert isinstance(js["title"], str)
        assert isinstance(js["headline"], list)
        assert isinstance(js["key_metrics"], dict)
        assert isinstance(js["red_flags"], list)
        assert isinstance(js["provenance"], list)
        assert isinstance(js["min_confidence"], (int, float))
        assert isinstance(js["licenses"], list)
        assert isinstance(js["markdown"], str)


def test_minister_briefing_with_custom_ttl(tmp_path, monkeypatch):
    """Test that briefing endpoint accepts custom TTL parameter."""
    with synthetic_catalog(Path(tmp_path)):
        monkeypatch.setenv("QNWIS_QUERIES_DIR", "src/qnwis/data/queries")
        c = TestClient(app)
        r = c.post("/v1/briefing/minister?ttl_s=60")
        assert r.status_code == 200
        js = r.json()
        assert "markdown" in js


def test_minister_briefing_markdown_content(tmp_path, monkeypatch):
    """Test that markdown contains expected content structure."""
    with synthetic_catalog(Path(tmp_path)):
        monkeypatch.setenv("QNWIS_QUERIES_DIR", "src/qnwis/data/queries")
        c = TestClient(app)
        r = c.post("/v1/briefing/minister")
        assert r.status_code == 200
        js = r.json()

        md = js["markdown"]
        # Check for expected sections
        assert "# Minister Briefing" in md
        assert "## Headline" in md
        assert "## Key Metrics" in md
        assert "## Confidence" in md
        if js.get("licenses"):
            assert "## Licenses" in md


def test_minister_briefing_key_metrics_numeric(tmp_path, monkeypatch):
    """Test that key_metrics contains only numeric values."""
    with synthetic_catalog(Path(tmp_path)):
        monkeypatch.setenv("QNWIS_QUERIES_DIR", "src/qnwis/data/queries")
        c = TestClient(app)
        r = c.post("/v1/briefing/minister")
        assert r.status_code == 200
        js = r.json()

        for _, value in js["key_metrics"].items():
            assert isinstance(value, (int, float))


def test_minister_briefing_deterministic(tmp_path, monkeypatch):
    """Test that briefing is deterministic (same data = same result)."""
    with synthetic_catalog(Path(tmp_path)):
        monkeypatch.setenv("QNWIS_QUERIES_DIR", "src/qnwis/data/queries")
        c = TestClient(app)

        # Call twice
        r1 = c.post("/v1/briefing/minister")
        r2 = c.post("/v1/briefing/minister")

        assert r1.status_code == 200
        assert r2.status_code == 200

        js1 = r1.json()
        js2 = r2.json()

        # Results should be identical (deterministic)
        assert js1["title"] == js2["title"]
        assert js1["headline"] == js2["headline"]
        assert js1["key_metrics"] == js2["key_metrics"]


def test_minister_briefing_ttl_clamped(monkeypatch: pytest.MonkeyPatch):
    """TTL should be clamped to the supported bounds before invoking builder."""
    captured: list[int] = []

    class DummyBriefing:
        title = "t"
        headline: list[str] = []
        key_metrics: dict[str, float] = {}
        red_flags: list[str] = []
        provenance: list[str] = []
        min_confidence: float = 1.0
        licenses: list[str] = []
        markdown = "# Dummy"

    def fake_build_briefing(*_: Any, **kwargs: Any) -> DummyBriefing:
        captured.append(kwargs["ttl_s"])
        return DummyBriefing()

    monkeypatch.setattr("src.qnwis.api.routers.briefing.build_briefing", fake_build_briefing)
    client = TestClient(app)

    resp_low = client.post("/v1/briefing/minister?ttl_s=5")
    resp_high = client.post("/v1/briefing/minister?ttl_s=999999")

    assert resp_low.status_code == 200
    assert resp_high.status_code == 200
    assert captured[0] == 60
    assert captured[1] == 86400
