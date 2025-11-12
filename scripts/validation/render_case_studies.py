"""
QNWIS Case Study Renderer.

Generates executive-ready case study documentation from validation results.

Usage:
    python scripts/validation/render_case_studies.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict


def render_case_study(
    case_name: str,
    result: Dict[str, Any],
    body: Dict[str, Any]
) -> str:
    """
    Render a single case study.
    
    Args:
        case_name: Case identifier
        result: Result metrics
        body: Response body
        
    Returns:
        Markdown formatted case study
    """
    lines = [
        f"## {case_name.replace('_', ' ').title()}\n\n",
        f"**Endpoint:** `{result.get('endpoint', 'N/A')}`  \n",
        f"**Tier:** {result.get('tier', 'N/A')}  \n",
        f"**Latency:** {result.get('latency_ms', 0):.2f} ms  \n",
        f"**Status:** {'✓ PASSED' if result.get('pass') else '✗ FAILED'}  \n",
        f"**Verified:** {'Yes' if result.get('verification_passed') else 'No'}  \n",
        f"**Citation Coverage:** {result.get('citation_coverage', 0):.2f}  \n",
        f"**Freshness:** {'Present' if result.get('freshness_present') else 'Missing'}  \n\n",
    ]
    
    # Add audit excerpt
    metadata = body.get("metadata", {})
    if metadata:
        lines.append("### Audit Trail\n\n")
        lines.append("```json\n")
        lines.append(json.dumps(metadata, indent=2))
        lines.append("\n```\n\n")
    
    # Add answer excerpt if available
    answer = body.get("answer") or body.get("data") or body.get("result")
    if answer and isinstance(answer, str):
        excerpt = answer[:500] + "..." if len(answer) > 500 else answer
        lines.append("### Response Excerpt\n\n")
        lines.append(f"> {excerpt}\n\n")
    
    lines.append("---\n\n")
    
    return "".join(lines)


def main() -> None:
    """Main entry point."""
    root = Path(".").resolve()
    results_dir = root / "validation" / "results"
    output_path = root / "docs" / "validation" / "CASE_STUDIES.md"
    
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Load results
    results = sorted(results_dir.glob("*.json"))
    
    if not results:
        print("Error: No results found in validation/results", file=sys.stderr)
        sys.exit(1)
    
    # Render header
    lines = [
        "# QNWIS Real-World Case Studies\n\n",
        "**Generated:** Validation Results  \n",
        "**Purpose:** Executive review of system performance on real Ministry questions  \n\n",
        "---\n\n"
    ]
    
    # Render each case
    for p in results:
        try:
            j = json.loads(p.read_text(encoding="utf-8"))
            result = j.get("result", {})
            body = j.get("body", {})
            case_name = result.get("case", p.stem)
            
            lines.append(render_case_study(case_name, result, body))
        
        except Exception as e:
            print(f"Warning: Failed to render {p}: {e}", file=sys.stderr)
            continue
    
    # Add metrics reference
    lines.extend([
        "## System Metrics\n\n",
        "For detailed system performance metrics, see:\n\n",
        "- **Prometheus Metrics:** `/metrics` endpoint\n",
        "- **Health Status:** `/health/ready` endpoint\n",
        "- **Operations Console:** See Step 30 documentation\n\n",
        "---\n\n",
        "*This document is auto-generated from validation results. ",
        "Do not edit manually.*\n"
    ])
    
    # Write output
    output_path.write_text("".join(lines), encoding="utf-8")
    print(f"[render] Wrote case studies to {output_path}")


if __name__ == "__main__":
    main()
