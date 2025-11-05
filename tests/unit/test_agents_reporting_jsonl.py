"""Tests for JSONL agent report writer."""

from __future__ import annotations

import json

from src.qnwis.agents.base import AgentReport, Evidence, Insight
from src.qnwis.agents.reporting.jsonl import write_report


def _sample_insight() -> Insight:
    """Create a deterministic insight for serialization tests."""
    evidence = Evidence(
        query_id="q_test",
        dataset_id="ds_test",
        locator="data/test.csv",
        fields=["value"],
    )
    return Insight(
        title="Sample insight",
        summary="Example summary",
        metrics={"value": 1.23},
        evidence=[evidence],
        warnings=["warn1", "warn2"],
    )


def test_write_report_appends_entries(tmp_path):
    """Reports are encoded as NDJSON and appended to disk."""
    target = tmp_path / "reports" / "agent.jsonl"
    report = AgentReport(agent="TestAgent", findings=[_sample_insight()])

    write_report(report, target)
    write_report(report, target)

    lines = target.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2

    payload = json.loads(lines[0])
    assert payload["agent"] == "TestAgent"
    assert payload["findings"][0]["confidence_score"] == 0.8
