"""Unit tests for agent reporting utilities."""

import json
from pathlib import Path

import pytest

from src.qnwis.agents.base import AgentReport, Evidence, Insight
from src.qnwis.agents.reporting.jsonl import write_report


def test_write_report_creates_directory(tmp_path):
    """Verify write_report creates parent directories."""
    target = tmp_path / "nested" / "dir" / "reports.jsonl"
    report = AgentReport(agent="Test", findings=[])
    write_report(report, target)
    assert target.exists()


def test_write_report_appends_jsonl(tmp_path):
    """Verify reports are appended as NDJSON."""
    target = tmp_path / "reports.jsonl"
    report1 = AgentReport(agent="Agent1", findings=[])
    report2 = AgentReport(agent="Agent2", findings=[])

    write_report(report1, target)
    write_report(report2, target)

    lines = target.read_text().strip().split("\n")
    assert len(lines) == 2

    data1 = json.loads(lines[0])
    data2 = json.loads(lines[1])
    assert data1["agent"] == "Agent1"
    assert data2["agent"] == "Agent2"


def test_write_report_serializes_full_structure(tmp_path):
    """Verify complete AgentReport structure is serialized."""
    target = tmp_path / "report.jsonl"
    ev = Evidence(query_id="q1", dataset_id="ds1", locator="loc1", fields=["f1"])
    insight = Insight(
        title="Test Insight",
        summary="Summary text",
        metrics={"value": 42.0},
        evidence=[ev],
        warnings=["warn1"],
    )
    report = AgentReport(agent="TestAgent", findings=[insight], warnings=["global_warn"])

    write_report(report, target)

    data = json.loads(target.read_text().strip())
    assert data["agent"] == "TestAgent"
    assert len(data["findings"]) == 1
    assert data["findings"][0]["title"] == "Test Insight"
    assert data["findings"][0]["metrics"]["value"] == 42.0
    assert data["findings"][0]["confidence_score"] == 0.9  # 1 - 0.1*1
    assert "warn1" in data["findings"][0]["warnings"]
    assert "global_warn" in data["warnings"]


def test_write_report_handles_string_path(tmp_path):
    """Verify write_report accepts string paths."""
    target = str(tmp_path / "report.jsonl")
    report = AgentReport(agent="Test", findings=[])
    write_report(report, target)
    assert Path(target).exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
