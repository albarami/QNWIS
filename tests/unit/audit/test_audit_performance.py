"""
Performance regression tests for audit pack writing.

Ensures typical packs complete well under the 500 ms budget.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from src.qnwis.data.deterministic.models import (
    Freshness,
    Provenance,
    QueryResult,
    Row,
)
from src.qnwis.verification.audit_trail import AuditTrail
from src.qnwis.verification.schemas import CitationReport, VerificationSummary


@pytest.fixture
def perf_query_results() -> list[QueryResult]:
    """Lightweight QueryResult fixtures for perf testing."""
    rows = [Row(data={"value": idx}) for idx in range(10)]
    return [
        QueryResult(
            query_id=f"qid_perf_{i}",
            rows=rows,
            unit="count",
            provenance=Provenance(
                source="csv",
                dataset_id=f"dataset_{i}",
                locator=f"/data/dataset_{i}.csv",
                fields=["value"],
            ),
            freshness=Freshness(
                asof_date="2024-01-01",
                updated_at="2024-01-02T00:00:00Z",
            ),
        )
        for i in range(3)
    ]


@pytest.fixture
def perf_verification() -> VerificationSummary:
    """Minimal verification summary for perf testing."""
    return VerificationSummary(ok=True, issues=[], applied_redactions=0, stats={})


@pytest.fixture
def perf_citations() -> CitationReport:
    """Minimal citation report."""
    return CitationReport(ok=True, total_numbers=3, cited_numbers=3)


@pytest.fixture
def perf_replay_stub() -> dict:
    """Replay stub used for perf test packs."""
    return {"task": {"intent": "pattern.anomalies"}, "routing": {}}


def test_write_pack_under_500ms(
    tmp_path: Path,
    perf_query_results: list[QueryResult],
    perf_verification: VerificationSummary,
    perf_citations: CitationReport,
    perf_replay_stub: dict,
) -> None:
    """Audit pack writes should complete within 500 ms."""
    trail = AuditTrail(pack_dir=str(tmp_path))

    manifest = trail.generate_trail(
        response_md="# Perf Test",
        qresults=perf_query_results,
        verification=perf_verification,
        citations=perf_citations,
        orchestration_meta={},
        code_version="perf",
        registry_version="v_perf",
        request_id="req-perf",
    )

    start = time.perf_counter()
    trail.write_pack(
        manifest=manifest,
        response_md="# Perf Test",
        qresults=perf_query_results,
        citations=perf_citations,
        result_report=None,
        replay_stub=perf_replay_stub,
    )
    duration_ms = (time.perf_counter() - start) * 1000

    assert duration_ms < 500, f"Audit pack write took {duration_ms:.2f} ms"
