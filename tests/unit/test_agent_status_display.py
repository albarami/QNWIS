from src.qnwis.ui.agent_status import (
    create_agent_status_summary,
    display_agent_execution_status,
    format_active_agents,
    format_failed_agents,
    format_skipped_agents,
)


def test_display_agent_execution_status():
    agents = [
        {"name": "LabourEconomist", "status": "invoked", "duration": 1.2},
        {"name": "Predictor", "status": "skipped", "reason": "No time-series data"},
        {"name": "Scenario", "status": "failed", "reason": "Input error"},
    ]

    markdown = display_agent_execution_status(agents)

    assert "**Invoked:** 1" in markdown
    assert "**Skipped:** 1" in markdown
    assert "**Failed:** 1" in markdown
    assert "LabourEconomist" in markdown
    assert "No time-series data" in markdown
    assert "Input error" in markdown


def test_formatter_helpers():
    active = format_active_agents([{"name": "AgentA", "status": "invoked", "duration": 2.0}])
    skipped = format_skipped_agents([{"name": "AgentB", "reason": "missing data"}])
    failed = format_failed_agents([{"name": "AgentC", "error": "Timeout"}])

    assert "AgentA" in active
    assert "missing data" in skipped
    assert "Timeout" in failed


def test_agent_status_summary():
    summary = create_agent_status_summary(total_agents=5, invoked_count=3, skipped_count=1, failed_count=1)
    assert summary.startswith("Agent Status")
    assert "3/5" in summary
