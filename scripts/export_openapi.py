"""
Export OpenAPI schema from FastAPI application.

Generates:
- docs/api/openapi.json: Complete OpenAPI schema
- docs/api/openapi.md: Human-readable endpoint index

Usage:
    python scripts/export_openapi.py
"""

from pathlib import Path
import json
import sys
from typing import Dict, Any


def create_app():
    """
    Import and create FastAPI application.
    
    Returns:
        FastAPI application instance
    """
    try:
        # Add src to path for imports
        src_path = Path(__file__).resolve().parents[1] / "src"
        if str(src_path) not in sys.path:
            sys.path.insert(0, str(src_path))
        
        from qnwis.api.server import create_app as app_factory
        return app_factory()
    except ImportError as e:
        print(f"Error importing application: {e}", file=sys.stderr)
        print("Ensure the application is installed and src/qnwis/api/server.py exists", file=sys.stderr)
        sys.exit(1)


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
    print("Creating FastAPI application...")
    app = create_app()
    
    print("Generating OpenAPI schema...")
    schema = app.openapi()
    
    # Ensure output directories exist
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write JSON schema
    print(f"Writing OpenAPI JSON to {json_path}...")
    json_path.write_text(json.dumps(schema, indent=2), encoding="utf-8")
    
    # Generate Markdown documentation
    print(f"Writing Markdown documentation to {md_path}...")
    lines = [
        "# QNWIS API Reference (OpenAPI)\n\n",
        f"**Version**: {schema.get('info', {}).get('version', '1.0.0')}  \n",
        f"**Title**: {schema.get('info', {}).get('title', 'QNWIS API')}  \n\n",
        "This document is auto-generated from the FastAPI application.\n\n",
        "## Endpoints\n\n"
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
    
    lines.append(f"\n## Summary\n\n")
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
    
    lines.append(f"\n---\n\n")
    lines.append(f"**Generated**: {json_path.stat().st_mtime if json_path.exists() else 'now'}  \n")
    lines.append(f"**Source**: FastAPI application at `src/qnwis/api/server.py`\n")
    
    md_path.write_text("".join(lines), encoding="utf-8")
    
    print(f"\n✅ OpenAPI export complete:")
    print(f"   - JSON: {json_path} ({json_path.stat().st_size} bytes)")
    print(f"   - Markdown: {md_path} ({md_path.stat().st_size} bytes)")
    print(f"   - Endpoints: {endpoint_count}")


def main() -> None:
    """Main entry point."""
    root = Path(__file__).resolve().parents[1]
    json_path = root / "docs" / "api" / "openapi.json"
    md_path = root / "docs" / "api" / "openapi.md"
    
    try:
        write_openapi(json_path, md_path)
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
