"""Unit tests for briefing builder."""
from __future__ import annotations

from typing import Any

import pytest

from src.qnwis.briefing.minister import MinisterBriefing, build_briefing
from src.qnwis.verification.rules import RuleIssue
from src.qnwis.verification.triangulation import TriangulationBundle, TriangulationResult


def _stub_findings() -> list[dict[str, Any]]:
    """Create sample findings with evidence and confidence scores."""
    locator = "aggregates/employment_share_by_gender.csv"
    finding = {
        "title": "Employment levels steady",
        "summary": "Synthetic baseline shows minor movement.",
        "metrics": {"employment_total_percent": 99.5},
        "evidence": [
            {"locator": locator, "dataset_id": locator, "fields": ["year", "total_percent"]},
            {"locator": locator, "dataset_id": locator, "fields": ["year", "total_percent"]},
        ],
        "warnings": [],
        "confidence_score": 0.9,
    }
    secondary = {
        "title": "Wage growth",
        "summary": "Synthetic wages are stable.",
        "metrics": {"avg_salary": 12_345.0},
        "evidence": [{"locator": locator, "dataset_id": locator, "fields": ["year", "avg_salary"]}],
        "warnings": ["stale"],
        "confidence_score": 0.85,
    }
    return [finding, secondary]


def _stub_triangulation(issue_count: int = 2) -> TriangulationBundle:
    """Create a triangulation bundle with a configurable number of issues."""
    issues = [
        RuleIssue(code=f"issue_{idx}", detail=f"detail_{idx}", severity="warn")
        for idx in range(issue_count)
    ]
    result = TriangulationResult(check_id="synthetic_check", issues=issues, samples=[{"year": 2024}])
    return TriangulationBundle(
        results=[result],
        warnings=["synthetic_check:1"] if issues else [],
        licenses=["MIT-SYNTHETIC"],
    )


def _patch_briefing_dependencies(
    monkeypatch: pytest.MonkeyPatch,
    *,
    findings: list[dict[str, Any]] | None = None,
    consensus: dict[str, Any] | None = None,
    triangulation: TriangulationBundle | None = None,
) -> None:
    """Patch run_council and run_triangulation with deterministic outputs."""
    if findings is None:
        findings = _stub_findings()
    if consensus is None:
        consensus = {
            "employment_total_percent": 99.5,
            "avg_salary": 12_345.0,
        }
    if triangulation is None:
        triangulation = _stub_triangulation(issue_count=3)

    council_stub = {
        "council": {
            "agents": ["labour_economist"],
            "findings": findings,
            "consensus": consensus,
            "warnings": [],
            "min_confidence": min(f.get("confidence_score", 1.0) for f in findings),
        },
        "verification": {},
        "rate_limit_applied": False,
    }

    def fake_run_council(*_: Any, **__: Any) -> dict[str, Any]:
        return council_stub

    def fake_run_triangulation(*_: Any, **__: Any) -> TriangulationBundle:
        return triangulation

    monkeypatch.setattr("src.qnwis.briefing.minister.run_council", fake_run_council)
    monkeypatch.setattr("src.qnwis.briefing.minister.run_triangulation", fake_run_triangulation)


def test_briefing_contains_markdown_and_sections(monkeypatch: pytest.MonkeyPatch) -> None:
    """Briefing should include markdown, headline, key metrics, and confidence."""
    _patch_briefing_dependencies(monkeypatch)
    briefing = build_briefing(queries_dir="src/qnwis/data/queries", ttl_s=120)
    assert isinstance(briefing, MinisterBriefing)
    assert briefing.title
    assert briefing.markdown
    assert isinstance(briefing.headline, list)
    assert isinstance(briefing.key_metrics, dict)


def test_briefing_structure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Briefing dataclass exposes the expected fields with correct types."""
    _patch_briefing_dependencies(monkeypatch)
    briefing = build_briefing(queries_dir="src/qnwis/data/queries", ttl_s=120)

    assert isinstance(briefing.title, str)
    assert isinstance(briefing.headline, list)
    assert isinstance(briefing.key_metrics, dict)
    assert isinstance(briefing.red_flags, list)
    assert isinstance(briefing.provenance, list)
    assert isinstance(briefing.min_confidence, float)
    assert isinstance(briefing.licenses, list)
    assert isinstance(briefing.markdown, str)


def test_briefing_markdown_sections(monkeypatch: pytest.MonkeyPatch) -> None:
    """Markdown should include headline, key metrics, confidence, and licenses."""
    _patch_briefing_dependencies(monkeypatch)
    briefing = build_briefing(queries_dir="src/qnwis/data/queries", ttl_s=120)

    assert "# Minister Briefing" in briefing.markdown
    assert "## Headline" in briefing.markdown
    assert "## Key Metrics" in briefing.markdown
    assert "## Confidence" in briefing.markdown
    if briefing.licenses:
        assert "## Licenses" in briefing.markdown


def test_briefing_key_metrics_are_numeric(monkeypatch: pytest.MonkeyPatch) -> None:
    """Key metrics should contain only numeric values."""
    _patch_briefing_dependencies(monkeypatch)
    briefing = build_briefing(queries_dir="src/qnwis/data/queries", ttl_s=120)

    for value in briefing.key_metrics.values():
        assert isinstance(value, (int, float))


def test_briefing_provenance_deduped(monkeypatch: pytest.MonkeyPatch) -> None:
    """Provenance entries must be deduplicated."""
    _patch_briefing_dependencies(monkeypatch)
    briefing = build_briefing(queries_dir="src/qnwis/data/queries", ttl_s=120)

    assert len(briefing.provenance) == len(set(briefing.provenance))


def test_briefing_red_flags_limited(monkeypatch: pytest.MonkeyPatch) -> None:
    """Red flags should be capped to eight items."""
    tri_bundle = _stub_triangulation(issue_count=12)
    _patch_briefing_dependencies(monkeypatch, triangulation=tri_bundle)
    briefing = build_briefing(queries_dir="src/qnwis/data/queries", ttl_s=120)

    assert len(briefing.red_flags) <= 8


def test_briefing_handles_empty_consensus(monkeypatch: pytest.MonkeyPatch) -> None:
    """Briefing should provide fallback headline when consensus is empty."""
    tri_bundle = TriangulationBundle(
        results=[TriangulationResult(check_id="test")],
        warnings=[],
        licenses=["MIT-SYNTHETIC"],
    )

    findings = _stub_findings()
    consensus: dict[str, Any] = {}
    _patch_briefing_dependencies(
        monkeypatch,
        findings=findings,
        consensus=consensus,
        triangulation=tri_bundle,
    )

    briefing = build_briefing(queries_dir="src/qnwis/data/queries", ttl_s=120)

    assert any("No consensus metrics available" in item for item in briefing.headline)
    assert pytest.approx(0.85) == pytest.approx(briefing.min_confidence)
    assert "Minimum finding confidence" in briefing.markdown
