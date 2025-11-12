"""
UI bridge for verification outputs.

Formats verification results (citations, number checks, confidence) into
markdown panels for Chainlit display.
"""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def render_verification_panel(verification_report: Dict[str, Any]) -> str:
    """
    Convert verification outputs into a markdown block for Chainlit.
    
    Args:
        verification_report: Verification results with structure:
            {
                "citations": {"status": "pass|fail", "details": [...]},
                "numeric_checks": {"status": "pass|warn|fail", "issues": [...]},
                "confidence": {"min": 0.78, "avg": 0.85, "max": 0.92},
                "freshness": {"oldest": "2025-10-15", "newest": "2025-11-08"},
                "issues": [{"level": "warn|error", "code": "...", "detail": "..."}]
            }
            
    Returns:
        Formatted markdown string for display
        
    Example:
        >>> report = {
        ...     "citations": {"status": "pass", "details": []},
        ...     "confidence": {"min": 0.78, "avg": 0.85}
        ... }
        >>> print(render_verification_panel(report))
        ## ✅ Verification Results
        ...
    """
    lines = ["## 🧪 Verification Results\n"]
    
    # Citation check
    citations = verification_report.get("citations", {})
    citation_status = citations.get("status", "unknown")
    
    if citation_status == "pass":
        lines.append("✅ **Citations**: All findings have valid QID sources")
    elif citation_status == "fail":
        lines.append("❌ **Citations**: Missing or invalid citations detected")
        for detail in citations.get("details", []):
            lines.append(f"   - {detail}")
    else:
        lines.append("⚠️ **Citations**: Status unknown")
    
    lines.append("")
    
    # Numeric validation
    numeric = verification_report.get("numeric_checks", {})
    numeric_status = numeric.get("status", "unknown")
    
    if numeric_status == "pass":
        lines.append("✅ **Numeric Validation**: All values in valid ranges")
    elif numeric_status == "warn":
        lines.append("⚠️ **Numeric Validation**: Warnings detected")
        for issue in numeric.get("issues", [])[:3]:  # Limit to 3
            lines.append(f"   - {issue.get('detail', issue)}")
    elif numeric_status == "fail":
        lines.append("❌ **Numeric Validation**: Critical errors detected")
        for issue in numeric.get("issues", [])[:3]:
            lines.append(f"   - {issue.get('detail', issue)}")
    
    lines.append("")
    
    # Confidence scores
    confidence = verification_report.get("confidence", {})
    if confidence:
        min_conf = confidence.get("min", 0)
        avg_conf = confidence.get("avg", 0)
        max_conf = confidence.get("max", 0)
        
        # Determine confidence band
        if avg_conf >= 0.85:
            band = "High"
            icon = "🟢"
        elif avg_conf >= 0.70:
            band = "Medium-High"
            icon = "🟡"
        elif avg_conf >= 0.50:
            band = "Medium"
            icon = "🟠"
        else:
            band = "Low"
            icon = "🔴"
        
        lines.append(f"{icon} **Confidence**: {band} (avg: {avg_conf:.0%})")
        lines.append(f"   - Range: {min_conf:.0%} - {max_conf:.0%}")
    
    lines.append("")
    
    # Data freshness
    freshness = verification_report.get("freshness", {})
    if freshness:
        oldest = freshness.get("oldest", "unknown")
        newest = freshness.get("newest", "unknown")
        
        lines.append("📅 **Data Freshness**:")
        lines.append(f"   - Oldest: {oldest}")
        lines.append(f"   - Newest: {newest}")
    
    lines.append("")
    
    # Issues summary
    issues = verification_report.get("issues", [])
    if issues:
        error_count = sum(1 for i in issues if i.get("level") == "error")
        warn_count = sum(1 for i in issues if i.get("level") == "warn")
        
        if error_count > 0:
            lines.append(f"❌ **Issues**: {error_count} errors, {warn_count} warnings")
        elif warn_count > 0:
            lines.append(f"⚠️ **Issues**: {warn_count} warnings")
        
        # Show top issues
        for issue in issues[:3]:
            level_icon = "❌" if issue.get("level") == "error" else "⚠️"
            lines.append(f"{level_icon} {issue.get('code', 'unknown')}: {issue.get('detail', 'No details')}")
    
    return "\n".join(lines)


def render_audit_panel(audit_data: Dict[str, Any]) -> str:
    """
    Render audit trail information as markdown.
    
    Args:
        audit_data: Audit trail with structure:
            {
                "request_id": "req_abc123",
                "query_ids": ["q_demo", "syn_employment_latest"],
                "sources": ["aggregates/employment.csv", "World Bank API"],
                "timestamps": {"start": "...", "end": "..."},
                "cache_stats": {"hits": 2, "misses": 1},
                "latency_ms": 245
            }
            
    Returns:
        Formatted markdown string
    """
    lines = ["## 📋 Audit Trail\n"]
    
    # Request ID
    request_id = audit_data.get("request_id", "unknown")
    lines.append(f"**Request ID**: `{request_id}`\n")
    
    # Query IDs
    query_ids = audit_data.get("query_ids", [])
    if query_ids:
        lines.append(f"**Queries Executed**: {len(query_ids)}")
        for qid in query_ids[:5]:  # Limit display
            lines.append(f"   - `{qid}`")
        if len(query_ids) > 5:
            lines.append(f"   - ... and {len(query_ids) - 5} more")
        lines.append("")
    
    # Data sources
    sources = audit_data.get("sources", [])
    if sources:
        lines.append(f"**Data Sources**: {len(sources)}")
        for source in sources[:5]:
            lines.append(f"   - {source}")
        if len(sources) > 5:
            lines.append(f"   - ... and {len(sources) - 5} more")
        lines.append("")
    
    # Cache statistics
    cache_stats = audit_data.get("cache_stats", {})
    if cache_stats:
        hits = cache_stats.get("hits", 0)
        misses = cache_stats.get("misses", 0)
        total = hits + misses
        hit_rate = (hits / total * 100) if total > 0 else 0
        
        lines.append("**Cache Performance**:")
        lines.append(f"   - Hits: {hits} / Misses: {misses}")
        lines.append(f"   - Hit Rate: {hit_rate:.1f}%")
        lines.append("")
    
    # Latency
    latency_ms = audit_data.get("latency_ms", 0)
    if latency_ms:
        latency_s = latency_ms / 1000
        lines.append(f"**Total Latency**: {latency_s:.2f}s ({latency_ms}ms)")
    
    # Timestamps
    timestamps = audit_data.get("timestamps", {})
    if timestamps:
        lines.append("\n**Timestamps**:")
        if "start" in timestamps:
            lines.append(f"   - Started: {timestamps['start']}")
        if "end" in timestamps:
            lines.append(f"   - Completed: {timestamps['end']}")
    
    return "\n".join(lines)


def render_agent_finding_panel(
    agent_name: str,
    finding: Dict[str, Any],
    show_full_evidence: bool = False
) -> str:
    """
    Render a single agent finding as an expandable panel.
    
    Args:
        agent_name: Name of the agent (e.g., "TimeMachine")
        finding: Finding dictionary with title, summary, metrics, evidence, etc.
        show_full_evidence: Whether to show all evidence or just top N
        
    Returns:
        Formatted markdown string
    """
    lines = [f"### 🤖 {agent_name}\n"]
    
    # Title and summary
    title = finding.get("title", "Untitled Finding")
    summary = finding.get("summary", "No summary available")
    
    lines.append(f"**{title}**")
    lines.append(f"{summary}\n")
    
    # Metrics (structured display)
    metrics = finding.get("metrics", {})
    if metrics:
        lines.append("**Metrics**:")
        for key, value in metrics.items():
            # Format based on type
            if isinstance(value, float):
                if abs(value) < 1:
                    formatted = f"{value:.2%}" if "percent" in key else f"{value:.3f}"
                else:
                    formatted = f"{value:.2f}"
            else:
                formatted = str(value)
            
            # Make key readable
            readable_key = key.replace("_", " ").title()
            lines.append(f"   - {readable_key}: {formatted}")
        lines.append("")
    
    # Evidence
    evidence = finding.get("evidence", [])
    if evidence:
        display_count = len(evidence) if show_full_evidence else min(3, len(evidence))
        lines.append(f"**Evidence** ({len(evidence)} sources):")
        
        for i, evi in enumerate(evidence[:display_count]):
            query_id = evi.get("query_id", "unknown")
            dataset_id = evi.get("dataset_id", "unknown")
            freshness = evi.get("freshness_as_of", "unknown")
            
            lines.append(f"   {i+1}. `{query_id}`")
            lines.append(f"      - Dataset: {dataset_id}")
            lines.append(f"      - Freshness: {freshness}")
        
        if len(evidence) > display_count:
            lines.append(f"   - ... and {len(evidence) - display_count} more sources")
        lines.append("")
    
    # Warnings
    warnings = finding.get("warnings", [])
    if warnings:
        lines.append("**Warnings**:")
        for warning in warnings:
            lines.append(f"   ⚠️ {warning}")
        lines.append("")
    
    # Confidence score
    confidence = finding.get("confidence_score", 1.0)
    confidence_pct = confidence * 100
    
    if confidence >= 0.85:
        conf_icon = "🟢"
        conf_label = "High"
    elif confidence >= 0.70:
        conf_icon = "🟡"
        conf_label = "Medium-High"
    elif confidence >= 0.50:
        conf_icon = "🟠"
        conf_label = "Medium"
    else:
        conf_icon = "🔴"
        conf_label = "Low"
    
    lines.append(f"{conf_icon} **Confidence**: {conf_label} ({confidence_pct:.0f}%)")
    
    return "\n".join(lines)


def render_raw_evidence_panel(
    agent_name: str,
    finding_title: str,
    tables: List[Dict[str, Any]]
) -> str:
    """
    Render deterministic query rows for transparency previews.
    
    Args:
        agent_name: Name of the agent
        finding_title: Title of the finding
        tables: List of table descriptors with rows
        
    Returns:
        Markdown string containing table previews
    """
    lines = [f"## Raw Evidence — {agent_name}", f"**Finding**: {finding_title}\n"]
    
    if not tables:
        lines.append("_No deterministic rows available for this finding._")
        return "\n".join(lines)
    
    for table in tables:
        query_id = table.get("query_id", "unknown")
        dataset = table.get("dataset_id", "unknown")
        freshness = table.get("freshness", "unknown")
        rows = table.get("rows") or []
        
        lines.append(f"### `{query_id}`")
        lines.append(f"- Dataset: `{dataset}`")
        if freshness:
            lines.append(f"- Freshness: {freshness}")
        lines.append("")
        
        if not rows:
            lines.append("_No preview rows available_\n")
            continue
        
        headers = sorted(rows[0].keys())
        lines.append("| " + " | ".join(headers) + " |")
        lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
        for row in rows:
            values = [_escape_table_value(row.get(col, "")) for col in headers]
            lines.append("| " + " | ".join(values) + " |")
        lines.append("")
    
    lines.append("*Preview limited to top rows per deterministic query.*")
    return "\n".join(lines)


def _escape_table_value(value: Any) -> str:
    """Escape markdown table characters for safe rendering."""
    text = str(value)
    return text.replace("|", "\\|")
