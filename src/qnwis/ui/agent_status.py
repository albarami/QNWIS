"""
Utilities for presenting agent execution status in the UI.

These helpers accept neutral dictionaries so they can be called from the
orchestration layer without importing UI frameworks.  The rendered strings are
Markdown-safe snippets that can be placed into any section of the final report.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List


AgentStatus = Dict[str, Any]


def _group_agents(statuses: Iterable[AgentStatus]) -> tuple[list[AgentStatus], list[AgentStatus], list[AgentStatus]]:
    """Group agents into invoked/skipped/failed buckets."""
    invoked: list[AgentStatus] = []
    skipped: list[AgentStatus] = []
    failed: list[AgentStatus] = []

    for status in statuses:
        label = (status.get("status") or "").lower()
        if label in {"invoked", "running", "complete"}:
            invoked.append(status)
        elif label == "skipped":
            skipped.append(status)
        elif label == "failed":
            failed.append(status)
    return invoked, skipped, failed


def display_agent_execution_status(agents_status: List[AgentStatus]) -> str:
    """
    Render a Markdown summary of agent execution.

    Args:
        agents_status: List of dictionaries describing each agent.  Supported keys:
            - name: Agent name (required)
            - status: invoked | skipped | failed
            - reason: Optional reason for skip/failure
            - error: Optional error message
            - duration: Optional execution duration in seconds

    Returns:
        Markdown string suitable for embedding inside a report section.
    """
    invoked, skipped, failed = _group_agents(agents_status)

    lines = [
        "## Agent Execution Status",
        "",
        f"- **Invoked:** {len(invoked)}",
        f"- **Skipped:** {len(skipped)}",
        f"- **Failed:** {len(failed)}",
        "",
        "### Active Agents",
        format_active_agents(invoked),
        "",
        "### Skipped Agents",
        format_skipped_agents(skipped),
    ]

    if failed:
        lines.extend(["", "### Failed Agents", format_failed_agents(failed)])

    return "\n".join(lines).strip()


def format_active_agents(invoked: List[AgentStatus]) -> str:
    """Render a list of active agents with execution durations."""
    if not invoked:
        return "None"

    # Split into core debaters and supporting analysts
    core_debaters = []
    supporting_analysts = []
    
    for agent in invoked:
        name = agent.get("name", "Unknown")
        if name in {"MicroEconomist", "MacroEconomist"}:
            core_debaters.append(agent)
        else:
            supporting_analysts.append(agent)
            
    lines: list[str] = []
    
    # Render Core Debaters
    if core_debaters:
        lines.append("#### ⚔️ Core Debaters")
        for agent in core_debaters:
            name = agent.get("name", "Unknown")
            duration = agent.get("duration")
            stage = agent.get("status", "invoked").capitalize()
            
            # Add specific icons
            icon = "🏢" if name == "MicroEconomist" else "🌍"
            
            if isinstance(duration, (int, float)):
                lines.append(f"- {icon} **{name}**: {stage} ({duration:.1f}s)")
            else:
                lines.append(f"- {icon} **{name}**: {stage}")
        lines.append("")  # Spacer

    # Render Supporting Analysts
    if supporting_analysts:
        lines.append("#### 🔍 Supporting Analysts")
        for agent in supporting_analysts:
            name = agent.get("name", "Unknown")
            duration = agent.get("duration")
            stage = agent.get("status", "invoked").capitalize()
            if isinstance(duration, (int, float)):
                lines.append(f"- **{name}**: {stage} ({duration:.1f}s)")
            else:
                lines.append(f"- **{name}**: {stage}")

    return "\n".join(lines)


def format_skipped_agents(skipped: List[AgentStatus]) -> str:
    """Render deterministic agents that chose not to run."""
    if not skipped:
        return "None"

    lines: list[str] = []
    for agent in skipped:
        name = agent.get("name", "Unknown")
        reason = agent.get("reason") or "Data not available for this specialization."
        lines.append(f"- **{name}**: {reason}")

    return "\n".join(lines)


def format_failed_agents(failed: List[AgentStatus]) -> str:
    """Render agents that attempted execution but failed."""
    if not failed:
        return "None"

    lines: list[str] = []
    for agent in failed:
        name = agent.get("name", "Unknown")
        reason = agent.get("reason")
        error = agent.get("error")
        detail = reason or error or "Unknown error"
        lines.append(f"- **{name}**: {detail}")

    return "\n".join(lines)


def create_agent_status_summary(
    total_agents: int,
    invoked_count: int,
    skipped_count: int,
    failed_count: int,
) -> str:
    """
    Produce a compact one-line summary for dashboards.

    Returns:
        String formatted as: "Agent Status: 5/12 invoked, 7 skipped, 0 failed"
    """
    return (
        f"Agent Status: {invoked_count}/{total_agents} invoked, "
        f"{skipped_count} skipped, {failed_count} failed"
    )

