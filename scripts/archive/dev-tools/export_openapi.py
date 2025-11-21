"""
Export OpenAPI schema from the FastAPI application.

Generates:
- docs/api/openapi.json: Complete OpenAPI schema
- docs/api/openapi.md: Human-readable endpoint index

Usage:
    python scripts/export_openapi.py
"""

from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path
from typing import Any, Dict


def _log(msg: str) -> None:
    """Consistent console logging."""
    print(f"[openapi] {msg}")


def create_app():
    """
    Import and create the FastAPI application.

    Returns:
        FastAPI application instance
    """
    try:
        src_path = Path(__file__).resolve().parents[1] / "src"
        if str(src_path) not in sys.path:
            sys.path.insert(0, str(src_path))
        repo_root = src_path.parent
        if str(repo_root) not in sys.path:
            sys.path.insert(0, str(repo_root))

        from qnwis.api.server import create_app as app_factory
    except ImportError as exc:  # pragma: no cover - import guard
        raise RuntimeError(
            "Unable to import qnwis.api.server. Verify src/qnwis/api/server.py exists."
        ) from exc

    try:
        return app_factory()
    except Exception as exc:  # pragma: no cover - FastAPI bootstrap guard
        raise RuntimeError("FastAPI application factory raised an exception") from exc


def format_parameter(param: Dict[str, Any]) -> str:
    """Format parameter for markdown display."""
    name = param.get("name", "unknown")
    required = " (required)" if param.get("required", False) else ""
    param_type = param.get("schema", {}).get("type", "string")
    return f"`{name}` ({param_type}){required}"


def format_response(responses: Dict[str, Any]) -> str:
    """Format response codes for markdown display."""
    codes = []
    for code, details in responses.items():
        desc = details.get("description", "")
        codes.append(f"{code}: {desc}")
    return ", ".join(codes) if codes else "200: Success"


def write_openapi(json_path: Path, md_path: Path) -> None:
    """
    Export OpenAPI schema to JSON and Markdown.
    
    Args:
        json_path: Path to write JSON schema
        md_path: Path to write Markdown documentation
    """
    _log("Bootstrapping FastAPI application")
    app = create_app()

    _log("Generating OpenAPI schema")
    try:
        schema = app.openapi()
    except Exception as exc:  # pragma: no cover - FastAPI guard
        raise RuntimeError("FastAPI .openapi() generation failed") from exc

    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)

    _log(f"Writing OpenAPI JSON to {json_path}")
    try:
        json_path.write_text(json.dumps(schema, indent=2), encoding="utf-8")
    except OSError as exc:  # pragma: no cover - filesystem guard
        raise RuntimeError(f"Failed to write {json_path}") from exc

    _log(f"Writing Markdown documentation to {md_path}")
    lines = [
        "# QNWIS API Reference (OpenAPI)\n\n",
        f"**Version**: {schema.get('info', {}).get('version', '1.0.0')}  \n",
        f"**Title**: {schema.get('info', {}).get('title', 'QNWIS API')}  \n\n",
        "This document is auto-generated from the FastAPI application.\n\n",
        "## Endpoints\n\n",
    ]

    paths = schema.get("paths", {})
    if not paths:
        lines.append("*No endpoints found*\n")
    else:
        # Sort endpoints by path
        for route in sorted(paths.keys()):
            methods = paths[route]
            
            for method in sorted(methods.keys()):
                if method in ["get", "post", "put", "delete", "patch"]:
                    meta = methods[method]
                    
                    # Endpoint header
                    title = meta.get("summary") or meta.get("operationId") or f"{method.upper()} {route}"
                    lines.append(f"### {method.upper()} `{route}`\n\n")
                    lines.append(f"**Summary**: {title}\n\n")
                    
                    # Description
                    if "description" in meta:
                        lines.append(f"{meta['description']}\n\n")
                    
                    # Parameters
                    if "parameters" in meta and meta["parameters"]:
                        lines.append("**Parameters**:\n")
                        for param in meta["parameters"]:
                            lines.append(f"- {format_parameter(param)}\n")
                        lines.append("\n")
                    
                    # Request body
                    if "requestBody" in meta:
                        lines.append("**Request Body**: Required\n\n")
                    
                    # Responses
                    if "responses" in meta:
                        lines.append(f"**Responses**: {format_response(meta['responses'])}\n\n")
                    
                    # Tags
                    if "tags" in meta:
                        tags = ", ".join(meta["tags"])
                        lines.append(f"**Tags**: {tags}\n\n")
                    
                    lines.append("---\n\n")
    
    # Write statistics
    endpoint_count = sum(
        1 for route in paths.values()
        for method in route.keys()
        if method in ["get", "post", "put", "delete", "patch"]
    )

    lines.append("\n## Summary\n\n")
    lines.append(f"- **Total Endpoints**: {endpoint_count}\n")
    lines.append(f"- **Total Paths**: {len(paths)}\n")

    # Write tags summary
    all_tags = set()
    for route in paths.values():
        for method_data in route.values():
            if isinstance(method_data, dict) and "tags" in method_data:
                all_tags.update(method_data["tags"])

    if all_tags:
        lines.append(f"- **Tags**: {', '.join(sorted(all_tags))}\n")

    lines.append("\n---\n\n")
    lines.append("**Generated**: auto-generated via scripts/export_openapi.py  \n")
    lines.append("**Source**: FastAPI application at `src/qnwis/api/server.py`\n")
    
    try:
        md_path.write_text("".join(lines), encoding="utf-8")
    except OSError as exc:  # pragma: no cover - filesystem guard
        raise RuntimeError(f"Failed to write {md_path}") from exc
    
    _log("OpenAPI export complete")
    _log(f" - JSON: {json_path} ({json_path.stat().st_size} bytes)")
    _log(f" - Markdown: {md_path} ({md_path.stat().st_size} bytes)")
    _log(f" - Endpoints: {endpoint_count}")


def main() -> None:
    """Main entry point."""
    root = Path(__file__).resolve().parents[1]
    json_path = root / "docs" / "api" / "openapi.json"
    md_path = root / "docs" / "api" / "openapi.md"
    
    try:
        write_openapi(json_path, md_path)
    except Exception as exc:
        print(f"[openapi] Error: {exc}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
