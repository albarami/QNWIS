"""
Progress panel component for Chainlit UI.

Renders stage transitions and completion status with visual indicators
and timing information during LLM council workflow execution.
"""

from __future__ import annotations

import chainlit as cl

# Stage labels with emoji indicators
STAGE_LABELS = {
    "heartbeat": "💓 Connected",
    "classify": "🔍 Classifying question",
    "prefetch": "📊 Preparing data",
    "verify": "✅ Verifying results",
    "synthesize": "📝 Synthesizing findings",
    "done": "🎉 Complete",
}

# Agent-specific labels
AGENT_LABELS = {
    "time_machine": "⏰ Time Machine",
    "pattern_miner": "🔬 Pattern Miner",
    "predictor": "📈 Predictor",
    "scenario": "🎯 Scenario Analyzer",
    "strategy": "🗺️ Strategy Advisor",
}


async def render_stage(
    stage: str,
    latency_ms: float | None = None,
    status: str = "running",
) -> None:
    """
    Render a stage transition message in the UI.

    Args:
        stage: Stage name (classify, prefetch, agent:<name>, verify, synthesize, done)
        latency_ms: Optional completion latency in milliseconds
        status: Status indicator (running, complete, error)
    """
    # Handle agent stages
    if stage.startswith("agent:"):
        agent_name = stage.split(":", 1)[1] if ":" in stage else "unknown"
        label = AGENT_LABELS.get(agent_name, f"🤖 {agent_name.replace('_', ' ').title()}")
    else:
        label = STAGE_LABELS.get(stage, f"⚙️ {stage.replace('_', ' ').title()}")

    # Format timing if available
    timing = ""
    if latency_ms is not None:
        if latency_ms < 1000:
            timing = f" _(completed in {latency_ms:.0f}ms)_"
        else:
            timing = f" _(completed in {latency_ms/1000:.1f}s)_"

    # Status indicator
    if status == "running":
        indicator = "▶️"
    elif status == "complete":
        indicator = "✓"
    elif status == "error":
        indicator = "⚠️"
        label = f"⚠️ {stage} encountered an issue"
    else:
        indicator = "•"

    content = f"{indicator} **{label}**{timing}"

    # Send as ephemeral message to avoid clutter
    await cl.Message(content=content, author="System").send()


async def render_error(message: str) -> None:
    """
    Render an error message with appropriate styling.

    Args:
        message: Error message to display
    """
    await cl.Message(
        content=f"❌ **Error**: {message}",
        author="System",
    ).send()


async def render_warning(message: str) -> None:
    """
    Render a warning message.

    Args:
        message: Warning message to display
    """
    await cl.Message(
        content=f"⚠️ **Warning**: {message}",
        author="System",
    ).send()


async def render_info(message: str) -> None:
    """
    Render an informational message.

    Args:
        message: Info message to display
    """
    await cl.Message(
        content=f"ℹ️ {message}",
        author="System",
    ).send()
