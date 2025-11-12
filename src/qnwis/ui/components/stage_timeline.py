"""
Markdown stage timeline component for the Chainlit UI.

Produces sanitizer-safe markdown that shows stage status and durations.
"""

from __future__ import annotations

from typing import List, Tuple

_ICON_MAP = {
    "done": "✅",
    "running": "🔄",
    "pending": "⏳",
}
_NBSP = "\u202f"  # narrow no-break space for "45 ms"


def render_stage_timeline_md(
    stages: List[Tuple[str, str, float]]
) -> str:
    """
    Render the stage timeline as Markdown.

    Args:
        stages: List of (stage_name, state, duration_ms) tuples
            - stage_name: Human-readable name (e.g., "Classify")
            - state: One of {"done", "running", "pending"}
            - duration_ms: Duration in milliseconds (0 when unknown)

    Returns:
        Markdown string suitable for Chainlit messages.
    """
    lines = ["**Stage Timeline**", ""]

    for name, state, duration_ms in stages:
        icon = _ICON_MAP.get(state, "⏳")

        if state == "done" and duration_ms > 0:
            duration_str = f" — {int(duration_ms)}{_NBSP}ms"
        elif state == "running" and duration_ms > 0:
            duration_str = f" — {int(duration_ms)}{_NBSP}ms elapsed"
        else:
            duration_str = ""

        lines.append(f"- {icon} **{name}**{duration_str}")

    return "\n".join(lines)


def render_compact_timeline(stages: List[Tuple[str, str]]) -> str:
    """
    Render a compact, single-line timeline.

    Args:
        stages: List of (stage_name, state) tuples.

    Returns:
        Compact Markdown string (useful for logs/console output).
    """
    parts = []
    for name, state in stages:
        icon = _ICON_MAP.get(state, "⏳")
        parts.append(f"{icon} {name}")
    return " → ".join(parts)


# Backwards compatibility alias used by older imports.
render_stage_timeline_with_durations = render_stage_timeline_md
