"""
UI components for Chainlit application.

Provides reusable components for rendering agent findings, audit trails,
verification results, and timeline widgets.
"""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def render_timeline_widget(stages_completed: List[str], current_stage: str) -> str:
    """
    Render a sticky timeline widget showing workflow progress.

    Args:
        stages_completed: List of completed stage names
        current_stage: Currently executing stage

    Returns:
        HTML/markdown string with timeline visualization
    """
    all_stages = [
        ("classify", "dYZ_ Classify"),
        ("prefetch", 'dY"S Prefetch'),
        ("agents", "dY- Agents"),
        ("verify", 'dY? Verify'),
        ("synthesize", 'dY? Synthesize'),
        ("done", "?o. Done"),
    ]

    rows: List[str] = []
    effective_current = current_stage if not current_stage.startswith("agent:") else "agents"

    for stage_id, stage_label in all_stages:
        if stage_id in stages_completed:
            status_badge = "?o."
            detail = "Complete"
            status_class = "qnwis-stage-complete"
        elif stage_id == effective_current:
            status_badge = "??3"
            detail = "In progress"
            status_class = "qnwis-stage-active"
        else:
            status_badge = "??,?,?"
            detail = "Pending"
            status_class = "qnwis-stage-pending"

        rows.append(
            (
                '<div class="{cls}" style="display:flex;gap:8px;padding:4px 0;">'
                '<span style="font-weight:600;min-width:40px;">{badge}</span>'
                '<div><div style="font-weight:600;">{label}</div>'
                '<div style="font-size:0.8rem;color:#94a3b8;">{detail}</div></div>'
                '</div>'
            ).format(
                cls=status_class,
                badge=status_badge,
                label=stage_label,
                detail=detail,
            )
        )

    container = (
        '<div style="position:sticky;top:16px;right:16px;margin-left:auto;'
        'max-width:320px;padding:16px 18px;border-radius:12px;'
        'border:1px solid #1f2937;background:rgba(6,11,25,0.92);'
        'box-shadow:0 12px 24px rgba(2,6,23,0.45);backdrop-filter:blur(6px);'
        'align-self:flex-end;">'
        '<div style="text-transform:uppercase;font-size:0.75rem;'
        'letter-spacing:0.12em;color:#22d3ee;margin-bottom:8px;">Stage timeline</div>'
        f"{''.join(rows)}"
        '</div>'
    )

    return container


def render_stage_card(stage: str, payload: Dict[str, Any], latency_ms: int) -> str:
    """
    Render a card for a completed workflow stage.
    
    Args:
        stage: Stage identifier
        payload: Stage-specific data
        latency_ms: Stage execution time in milliseconds
        
    Returns:
        Markdown string with stage summary
    """
    if stage == "classify":
        return _render_classify_card(payload, latency_ms)
    elif stage == "prefetch":
        return _render_prefetch_card(payload, latency_ms)
    elif stage.startswith("agent:"):
        return _render_agent_card(stage, payload, latency_ms)
    elif stage == "verify":
        return _render_verify_card(payload, latency_ms)
    elif stage == "synthesize":
        return _render_synthesize_card(payload, latency_ms)
    elif stage == "done":
        return _render_done_card(payload, latency_ms)
    else:
        return f"## {stage}\n\nStatus: {payload.get('status', 'unknown')}"


def _render_classify_card(payload: Dict[str, Any], latency_ms: int) -> str:
    """Render classification stage card."""
    intent = payload.get("intent", "unknown")
    complexity = payload.get("complexity", "unknown")
    confidence = payload.get("confidence", 0)
    entities = payload.get("entities", {})
    
    lines = [
        "## 🎯 Intent Classification",
        "",
        f"**Intent**: `{intent}`",
        f"**Complexity**: {complexity.title()}",
        f"**Confidence**: {confidence:.0%}",
        "",
    ]
    
    if entities.get("sectors"):
        lines.append(f"**Sectors**: {', '.join(entities['sectors'][:3])}")
    if entities.get("metrics"):
        lines.append(f"**Metrics**: {', '.join(entities['metrics'][:3])}")
    if entities.get("horizon_months"):
        lines.append(f"**Time Horizon**: {entities['horizon_months']} months")
    
    lines.append(f"\n*Completed in {latency_ms}ms*")
    
    return "\n".join(lines)


def _render_prefetch_card(payload: Dict[str, Any], latency_ms: int) -> str:
    """Render prefetch stage card."""
    rag_snippets = payload.get("rag_snippets", 0)
    rag_sources = payload.get("rag_sources", [])
    
    lines = [
        "## 📊 Data Prefetch",
        "",
        f"**RAG Context**: {rag_snippets} snippets retrieved",
    ]
    
    if rag_sources:
        lines.append(f"**External Sources**: {', '.join(rag_sources)}")
    
    lines.append(f"\n*Completed in {latency_ms}ms*")
    
    return "\n".join(lines)


def _render_agent_card(stage: str, payload: Dict[str, Any], latency_ms: int) -> str:
    """Render agent execution card."""
    agent_name = payload.get("agent", stage.replace("agent:", ""))
    finding_count = payload.get("finding_count", 0)
    status = payload.get("status", "unknown")
    
    if status == "error":
        error = payload.get("error", "Unknown error")
        return f"## 🤖 {agent_name}\n\n❌ **Error**: {error}\n\n*Failed after {latency_ms}ms*"
    
    lines = [
        f"## 🤖 {agent_name}",
        "",
        f"**Findings**: {finding_count}",
        "**Status**: ✅ Completed",
        f"\n*Execution time: {latency_ms}ms*",
    ]
    
    return "\n".join(lines)


def _render_verify_card(payload: Dict[str, Any], latency_ms: int) -> str:
    """Render verification stage card."""
    citations = payload.get("citations", {})
    numeric = payload.get("numeric_checks", {})
    confidence = payload.get("confidence", {})
    
    lines = [
        "## 🧪 Verification",
        "",
    ]
    
    # Citations
    if citations.get("status") == "pass":
        lines.append("✅ **Citations**: All valid")
    else:
        lines.append("❌ **Citations**: Issues detected")
    
    # Numeric checks
    if numeric.get("status") == "pass":
        lines.append("✅ **Numeric Checks**: All valid")
    elif numeric.get("status") == "warn":
        lines.append("⚠️ **Numeric Checks**: Warnings present")
    else:
        lines.append("❌ **Numeric Checks**: Errors detected")
    
    # Confidence
    if confidence:
        avg = confidence.get("avg", 0)
        lines.append(f"📊 **Avg Confidence**: {avg:.0%}")
    
    lines.append(f"\n*Completed in {latency_ms}ms*")
    
    return "\n".join(lines)


def _render_synthesize_card(payload: Dict[str, Any], latency_ms: int) -> str:
    """Render synthesis stage card."""
    agents = payload.get("agents", [])
    finding_count = payload.get("finding_count", 0)
    
    lines = [
        "## 🧠 Synthesis",
        "",
        f"**Agents Consulted**: {len(agents)}",
        f"**Total Findings**: {finding_count}",
        f"\n*Completed in {latency_ms}ms*",
    ]
    
    return "\n".join(lines)


def _render_done_card(payload: Dict[str, Any], latency_ms: int) -> str:
    """Render final completion card."""
    audit = payload.get("audit", {})
    query_count = len(audit.get("query_ids", []))
    source_count = len(audit.get("sources", []))
    
    lines = [
        "## ✅ Analysis Complete",
        "",
        f"**Queries Executed**: {query_count}",
        f"**Data Sources**: {source_count}",
        f"**Total Time**: {latency_ms}ms ({latency_ms/1000:.2f}s)",
    ]
    
    return "\n".join(lines)


def sanitize_markdown(text: str) -> str:
    """
    Sanitize markdown text to prevent XSS and injection attacks.
    
    This is a basic sanitizer. In production, use a library like bleach
    or markdown-it with proper configuration.
    
    Args:
        text: Raw markdown text
        
    Returns:
        Sanitized markdown text
    """
    # Remove script tags
    import re
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove on* event handlers
    text = re.sub(r'\s*on\w+\s*=\s*["\'][^"\']*["\']', '', text, flags=re.IGNORECASE)
    
    # Remove javascript: URLs
    text = re.sub(r'javascript:', '', text, flags=re.IGNORECASE)
    
    return text


def format_metric_value(key: str, value: Any) -> str:
    """
    Format a metric value for display based on its key and type.
    
    Args:
        key: Metric key name
        value: Metric value
        
    Returns:
        Formatted string representation
    """
    if isinstance(value, float):
        # Percentages
        if "percent" in key.lower() or "rate" in key.lower():
            if abs(value) < 1:
                return f"{value:.2%}"
            else:
                return f"{value:.1f}%"
        # Ratios/scores
        elif "score" in key.lower() or "confidence" in key.lower():
            return f"{value:.2f}"
        # General floats
        else:
            return f"{value:.2f}"
    elif isinstance(value, int):
        # Large numbers with comma separators
        if abs(value) >= 1000:
            return f"{value:,}"
        else:
            return str(value)
    else:
        return str(value)


def truncate_text(text: str, max_length: int = 200, suffix: str = "...") -> str:
    """
    Truncate text to maximum length with suffix.
    
    Args:
        text: Text to truncate
        max_length: Maximum length before truncation
        suffix: Suffix to append if truncated
        
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix
