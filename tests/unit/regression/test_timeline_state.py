"""
Regression tests for the stage timeline renderer.

Ensures the markdown output stays HTML-free and uses clean emoji badges.
"""

from src.qnwis.ui.components import render_stage_timeline_md


def test_timeline_all_stages_complete():
    """All stages completed should show checkmarks and durations."""
    markdown = render_stage_timeline_md([
        ("Classify", "done", 45.0),
        ("Prefetch", "done", 30.0),
        ("Agents", "done", 120.0),
        ("Verify", "done", 15.0),
        ("Synthesize", "done", 60.0),
        ("Done", "done", 300.0),
    ])

    assert markdown.count("✅") == 6
    assert "🔄" not in markdown
    assert "⏳" not in markdown
    assert "45" in markdown and "300" in markdown


def test_timeline_agents_in_progress():
    """When agents are running, they should show the running icon."""
    markdown = render_stage_timeline_md([
        ("Classify", "done", 40.0),
        ("Prefetch", "done", 25.0),
        ("Agents", "running", 10.0),
        ("Verify", "pending", 0.0),
        ("Synthesize", "pending", 0.0),
        ("Done", "pending", 0.0),
    ])

    assert "🔄 **Agents**" in markdown
    assert markdown.count("✅") == 2
    assert markdown.count("⏳") == 3


def test_timeline_agents_complete():
    """After agents finish, they should render as completed."""
    markdown = render_stage_timeline_md([
        ("Classify", "done", 40.0),
        ("Prefetch", "done", 25.0),
        ("Agents", "done", 140.0),
        ("Verify", "running", 5.0),
        ("Synthesize", "pending", 0.0),
        ("Done", "pending", 0.0),
    ])

    assert markdown.count("✅") == 3
    assert "🔄 **Verify**" in markdown


def test_timeline_no_corrupted_labels():
    """Ensure output only uses clean unicode icons."""
    markdown = render_stage_timeline_md([
        ("Classify", "running", 0.0),
        ("Prefetch", "pending", 0.0),
        ("Agents", "pending", 0.0),
    ])

    assert "<div" not in markdown
    assert "dYZ" not in markdown
    assert "🔄 **Classify**" in markdown


def test_timeline_initial_state():
    """Initial state should show classify as running and others pending."""
    markdown = render_stage_timeline_md([
        ("Classify", "running", 0.0),
        ("Prefetch", "pending", 0.0),
        ("Agents", "pending", 0.0),
        ("Verify", "pending", 0.0),
    ])

    assert "🔄 **Classify**" in markdown
    assert markdown.count("⏳") == 3
