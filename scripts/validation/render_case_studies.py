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
from typing import Any, Dict, Optional


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
        f"**Case ID:** `{case_name}`  \n",
        f"**Endpoint:** `{result.get('endpoint', 'N/A')}`  \n",
        f"**Tier:** {result.get('tier', 'N/A')}  \n",
        f"**Latency:** {result.get('latency_ms', 0):.2f} ms  \n",
        f"**Status:** {'✓ PASSED' if result.get('pass') else '✗ FAILED'}  \n",
        f"**Verified:** {'Yes' if result.get('verification_passed') else 'No'}  \n",
        f"**Citation Coverage:** {result.get('citation_coverage', 0):.2f}  \n",
        f"**Freshness:** {'Present' if result.get('freshness_present') else 'Missing'}  \n\n",
    ]
    
    metadata = body.get("metadata", {})
    audit_id = metadata.get("audit_id")
    if audit_id:
        lines.append(f"**Audit ID:** `{audit_id}`  \n\n")
    
    link = resolve_openapi_link(result.get("endpoint"))
    if link:
        label, href = link
        lines.append(f"**OpenAPI:** [{label}]({href})  \n\n")
    
    # Add audit excerpt
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


OPENAPI_LINKS = {
    "/api/v1/query": ("Data API - Query", "../api/step27_service_api.md#data-api"),
    "/api/v1/dashboard/kpis": (
        "Data API - Dashboard",
        "../api/step27_service_api.md#dashboard-kpis",
    ),
}
DEFAULT_OPENAPI_LINK = ("Data API", "../api/step27_service_api.md#data-api")


def resolve_openapi_link(endpoint: Optional[str]) -> Optional[tuple[str, str]]:
    """Return an OpenAPI link tuple for supported endpoints."""
    if not endpoint:
        return None
    if endpoint.startswith("/api/"):
        return OPENAPI_LINKS.get(endpoint, DEFAULT_OPENAPI_LINK)
    return None


def main() -> None:
    """Main entry point."""
    root = Path(".").resolve()
    results_dir = root / "validation" / "results"
    output_path = root / "docs" / "validation" / "CASE_STUDIES.md"
    
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Load results
    if not results_dir.exists():
        print(f"Error: Results directory not found: {results_dir}", file=sys.stderr)
        sys.exit(1)

    results = sorted(results_dir.glob("*.json"))

    if not results:
        print(f"Error: No results found in {results_dir}", file=sys.stderr)
        sys.exit(1)
    
    # Render header
    lines = [
        "# QNWIS Real-World Case Studies\n\n",
        "**Generated:** Validation Results  \n",
        "**Purpose:** Executive review of system performance on real Ministry questions  \n\n",
        "---\n\n"
    ]
    
    # Render each case
    rendered_count = 0
    for p in results:
        try:
            j = json.loads(p.read_text(encoding="utf-8"))
            result = j.get("result", {})
            body = j.get("body", {})
            case_name = result.get("case", p.stem)

            case_study = render_case_study(case_name, result, body)
            lines.append(case_study)
            rendered_count += 1
            print(f"[render] Rendered case: {case_name}", file=sys.stderr)

        except Exception as e:
            print(f"Warning: Failed to render {p}: {e}", file=sys.stderr)
            continue

    if rendered_count == 0:
        print("Warning: No cases were rendered", file=sys.stderr)
    
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
