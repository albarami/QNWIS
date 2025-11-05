"""
Unit tests for orchestration synthesis engine.

Tests council report generation, consensus computation, and
warning deduplication from multiple agent reports.
"""

import pytest

from src.qnwis.agents.base import AgentReport, Insight
from src.qnwis.orchestration.synthesis import CouncilReport, synthesize


def _make_report(agent: str, metrics: dict, warnings: list[str] | None = None) -> AgentReport:
    """Helper to create test AgentReport."""
    return AgentReport(
        agent=agent,
        findings=[
            Insight(
                title=f"{agent} Finding",
                summary="Test insight",
                metrics=metrics,
                warnings=warnings or [],
            )
        ],
        warnings=warnings or [],
    )


def test_synthesize_empty_reports():
    """Verify synthesis handles empty report list."""
    result = synthesize([])
    assert isinstance(result, CouncilReport)
    assert result.agents == []
    assert result.findings == []
    assert result.consensus == {}
    assert result.warnings == []


def test_synthesize_single_report():
    """Verify synthesis works with single report."""
    report = _make_report("Agent1", {"male_percent": 60.0})
    result = synthesize([report])
    assert result.agents == ["Agent1"]
    assert len(result.findings) == 1
    # Single value doesn't create consensus (need 2+)
    assert result.consensus == {}


def test_synthesize_two_reports_consensus():
    """Verify consensus computation with two agents."""
    report1 = _make_report("Agent1", {"male_percent": 60.0, "female_percent": 40.0})
    report2 = _make_report("Agent2", {"male_percent": 62.0, "female_percent": 38.0})
    result = synthesize([report1, report2])
    assert result.agents == ["Agent1", "Agent2"]
    assert len(result.findings) == 2
    # Consensus should be average
    assert result.consensus["male_percent"] == 61.0
    assert result.consensus["female_percent"] == 39.0


def test_synthesize_multiple_reports_consensus():
    """Verify consensus with multiple agents."""
    reports = [
        _make_report("Agent1", {"total_percent": 100.0}),
        _make_report("Agent2", {"total_percent": 100.0}),
        _make_report("Agent3", {"total_percent": 100.0}),
    ]
    result = synthesize(reports)
    assert result.consensus["total_percent"] == 100.0


def test_synthesize_mixed_metrics():
    """Verify that only metrics appearing in 2+ reports get consensus."""
    report1 = _make_report("Agent1", {"male_percent": 60.0, "unique1": 10.0})
    report2 = _make_report("Agent2", {"male_percent": 62.0, "unique2": 20.0})
    result = synthesize([report1, report2])
    # male_percent appears in both → consensus
    assert "male_percent" in result.consensus
    # unique1 and unique2 only in one report each → no consensus
    assert "unique1" not in result.consensus
    assert "unique2" not in result.consensus


def test_synthesize_warnings_deduplication():
    """Verify warnings are deduplicated and sorted."""
    report1 = _make_report("Agent1", {}, warnings=["warn_b", "warn_a"])
    report2 = _make_report("Agent2", {}, warnings=["warn_a", "warn_c"])
    result = synthesize([report1, report2])
    # Should be deduplicated and sorted
    assert result.warnings == ["warn_a", "warn_b", "warn_c"]


def test_synthesize_warnings_from_insights():
    """Verify warnings from insights are included."""
    report = AgentReport(
        agent="Agent1",
        findings=[
            Insight(
                title="Finding 1",
                summary="Test",
                metrics={},
                warnings=["insight_warn1"],
            ),
            Insight(
                title="Finding 2",
                summary="Test",
                metrics={},
                warnings=["insight_warn2"],
            ),
        ],
        warnings=["report_warn"],
    )
    result = synthesize([report])
    assert set(result.warnings) == {"report_warn", "insight_warn1", "insight_warn2"}


def test_synthesize_findings_aggregation():
    """Verify all findings from all agents are included."""
    report1 = AgentReport(
        agent="Agent1",
        findings=[
            Insight(title="F1", summary="Test", metrics={"m1": 1.0}),
            Insight(title="F2", summary="Test", metrics={"m2": 2.0}),
        ],
    )
    report2 = AgentReport(
        agent="Agent2",
        findings=[
            Insight(title="F3", summary="Test", metrics={"m3": 3.0}),
        ],
    )
    result = synthesize([report1, report2])
    assert len(result.findings) == 3
    titles = [f.title for f in result.findings]
    assert titles == ["F1", "F2", "F3"]


def test_synthesize_non_numeric_metrics_ignored():
    """Verify that non-numeric metrics don't affect consensus."""
    report1 = _make_report("Agent1", {"male_percent": 60.0, "description": "test"})
    report2 = _make_report("Agent2", {"male_percent": 62.0, "description": "test"})
    result = synthesize([report1, report2])
    # Only numeric values in consensus
    assert "male_percent" in result.consensus
    assert "description" not in result.consensus


def test_synthesize_consensus_precision():
    """Verify consensus computation precision."""
    reports = [
        _make_report("Agent1", {"value": 10.0}),
        _make_report("Agent2", {"value": 20.0}),
        _make_report("Agent3", {"value": 30.0}),
    ]
    result = synthesize(reports)
    # (10 + 20 + 30) / 3 = 20.0
    assert result.consensus["value"] == 20.0


def test_synthesize_agent_order_preserved():
    """Verify agent names maintain insertion order."""
    reports = [
        _make_report("Zulu", {}),
        _make_report("Alpha", {}),
        _make_report("Mike", {}),
    ]
    result = synthesize(reports)
    assert result.agents == ["Zulu", "Alpha", "Mike"]


def test_synthesize_empty_findings():
    """Verify reports with no findings are handled."""
    report1 = AgentReport(agent="Agent1", findings=[])
    report2 = AgentReport(agent="Agent2", findings=[])
    result = synthesize([report1, report2])
    assert result.agents == ["Agent1", "Agent2"]
    assert result.findings == []
    assert result.consensus == {}


def test_synthesize_integer_metrics():
    """Verify integer metrics are converted to float in consensus."""
    report1 = _make_report("Agent1", {"count": 100})
    report2 = _make_report("Agent2", {"count": 200})
    result = synthesize([report1, report2])
    assert result.consensus["count"] == 150.0
    assert isinstance(result.consensus["count"], float)


def test_synthesize_zero_values():
    """Verify zero values are handled correctly."""
    report1 = _make_report("Agent1", {"female_percent": 0.0})
    report2 = _make_report("Agent2", {"female_percent": 0.0})
    result = synthesize([report1, report2])
    assert result.consensus["female_percent"] == 0.0


def test_synthesize_negative_values():
    """Verify negative values in consensus."""
    reports = [
        _make_report("Agent1", {"yoy_percent": -5.0}),
        _make_report("Agent2", {"yoy_percent": -10.0}),
    ]
    result = synthesize(reports)
    assert result.consensus["yoy_percent"] == -7.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
