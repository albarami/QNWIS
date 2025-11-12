from __future__ import annotations

from src.qnwis.validation import metrics


def test_citation_coverage_handles_numbers_without_citations() -> None:
    payload = {"result": [{"value": 42}], "metadata": {}}
    assert metrics.citation_coverage(payload) == 0.0


def test_citation_coverage_is_full_when_numbers_or_citations_absent() -> None:
    payload_no_numbers = {"metadata": {"citations": []}}
    payload_with_citations = {"metadata": {"citations": ["LMIS"]}, "answer": "All good"}
    assert metrics.citation_coverage(payload_no_numbers) == 1.0
    assert metrics.citation_coverage(payload_with_citations) == 1.0


def test_freshness_present_detects_metadata() -> None:
    payload = {"metadata": {"freshness": {"LMIS": "1d"}}}
    assert metrics.freshness_present(payload) is True


def test_verification_passed_accepts_boolean_or_string() -> None:
    assert metrics.verification_passed({"metadata": {"verification": True}}) is True
    assert metrics.verification_passed({"metadata": {"verification": "passed"}}) is True
    assert metrics.verification_passed({"metadata": {"verification": "failed"}}) is False


def test_compute_latency_ms_converts_seconds_to_ms() -> None:
    assert metrics.compute_latency_ms((1.0, 2.0)) == 1000.0


def test_compute_score_enforces_envelopes_and_quality_gates() -> None:
    assert metrics.compute_score(
        latency_ms=5_000,
        tier="simple",
        verified=True,
        cov=0.8,
        fresh=True,
    )
    assert not metrics.compute_score(
        latency_ms=12_000,
        tier="simple",
        verified=True,
        cov=0.8,
        fresh=True,
    )
    assert not metrics.compute_score(
        latency_ms=1_000,
        tier="simple",
        verified=False,
        cov=0.8,
        fresh=True,
    )
