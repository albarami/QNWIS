"""
Documentation validation script.

Validates:
- Required documentation files exist
- No TODO/FIXME placeholders
- Intra-repo markdown links resolve
- Required headings present

Usage:
    python scripts/doc_checks.py
"""

from __future__ import annotations
import re
import sys
from pathlib import Path
from typing import List, Tuple


REQUIRED_DOCS = [
    "docs/USER_GUIDE.md",
    "docs/API_REFERENCE.md",
    "docs/OPERATIONS_RUNBOOK.md",
    "docs/TROUBLESHOOTING.md",
    "docs/ARCHITECTURE.md",
    "docs/DEVELOPER_ONBOARDING.md",
    "docs/SECURITY.md",
    "docs/PERFORMANCE.md",
    "docs/DATA_DICTIONARY.md",
    "docs/RELEASE_NOTES.md",
]


def fail(msg: str) -> None:
    """Print error and exit."""
    print(f"❌ [doc-check] {msg}", file=sys.stderr)
    sys.exit(1)


def warn(msg: str) -> None:
    """Print warning."""
    print(f"⚠️  [doc-check] {msg}")


def success(msg: str) -> None:
    """Print success message."""
    print(f"✅ [doc-check] {msg}")


def check_required_files(root: Path) -> None:
    """
    Check that all required documentation files exist.
    
    Args:
        root: Repository root path
    """
    missing = []
    for doc_path in REQUIRED_DOCS:
        full_path = root / doc_path
        if not full_path.exists():
            missing.append(doc_path)
    
    if missing:
        fail(f"Missing required documentation files:\n  " + "\n  ".join(missing))
    
    success(f"All {len(REQUIRED_DOCS)} required documentation files exist")


def check_no_placeholders(root: Path) -> None:
    """
    Check that documentation contains no TODO/FIXME placeholders.
    
    Args:
        root: Repository root path
    """
    placeholder_pattern = re.compile(r'\b(TODO|FIXME|XXX|PLACEHOLDER)\b', re.IGNORECASE)
    bad_files = []
    
    for md_file in root.glob("docs/**/*.md"):
        try:
            content = md_file.read_text(encoding="utf-8", errors="ignore")
            matches = placeholder_pattern.findall(content)
            if matches:
                bad_files.append((str(md_file.relative_to(root)), matches))
        except Exception as e:
            warn(f"Could not read {md_file}: {e}")
    
    if bad_files:
        error_msg = "Documentation contains placeholders:\n"
        for file_path, matches in bad_files:
            error_msg += f"  {file_path}: {', '.join(set(matches))}\n"
        fail(error_msg.rstrip())
    
    success("No placeholders (TODO/FIXME) found in documentation")


def check_headings(root: Path) -> None:
    """
    Check that all documentation files have proper headings.
    
    Args:
        root: Repository root path
    """
    missing_headings = []
    
    for doc_path in REQUIRED_DOCS:
        full_path = root / doc_path
        if not full_path.exists():
            continue
        
        try:
            content = full_path.read_text(encoding="utf-8", errors="ignore")
            lines = content.splitlines()
            
            # Check first non-empty line is a heading
            for line in lines:
                if line.strip():
                    if not line.strip().startswith("#"):
                        missing_headings.append(doc_path)
                    break
        except Exception as e:
            warn(f"Could not read {full_path}: {e}")
    
    if missing_headings:
        fail(f"Documentation files missing H1 heading:\n  " + "\n  ".join(missing_headings))
    
    success("All documentation files have proper headings")


def check_links(root: Path) -> None:
    """
    Check that intra-repo markdown links resolve.
    
    Only validates relative links (not http/https or anchors).
    
    Args:
        root: Repository root path
    """
    link_pattern = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
    broken_links: List[Tuple[str, str, str]] = []
    
    for md_file in root.glob("docs/**/*.md"):
        try:
            content = md_file.read_text(encoding="utf-8", errors="ignore")
            base_dir = md_file.parent
            
            for match in link_pattern.finditer(content):
                link_text = match.group(1)
                link_href = match.group(2).strip()
                
                # Skip external links and anchors
                if link_href.startswith(("http://", "https://", "#", "mailto:")):
                    continue
                
                # Remove anchor from link
                link_path = link_href.split("#")[0]
                if not link_path:  # Pure anchor link
                    continue
                
                # Resolve relative path
                target = (base_dir / link_path).resolve()
                
                # Check if target exists
                if not target.exists():
                    rel_source = str(md_file.relative_to(root))
                    broken_links.append((rel_source, link_href, link_text))
        
        except Exception as e:
            warn(f"Could not check links in {md_file}: {e}")
    
    if broken_links:
        error_msg = "Broken intra-repo links found:\n"
        for source, href, text in broken_links:
            error_msg += f"  {source}: [{text}]({href})\n"
        fail(error_msg.rstrip())
    
    success("All intra-repo markdown links resolve correctly")


def check_api_docs(root: Path) -> None:
    """
    Check that API documentation files exist.
    
    Args:
        root: Repository root path
    """
    api_json = root / "docs" / "api" / "openapi.json"
    api_md = root / "docs" / "api" / "openapi.md"
    
    if not api_json.exists():
        warn(f"OpenAPI JSON not found: {api_json}")
        warn("Run: python scripts/export_openapi.py")
    else:
        # Check file is not empty
        if api_json.stat().st_size < 100:
            fail(f"OpenAPI JSON is too small (< 100 bytes): {api_json}")
        success(f"OpenAPI JSON exists ({api_json.stat().st_size} bytes)")
    
    if not api_md.exists():
        warn(f"OpenAPI Markdown not found: {api_md}")
        warn("Run: python scripts/export_openapi.py")
    else:
        if api_md.stat().st_size < 100:
            fail(f"OpenAPI Markdown is too small (< 100 bytes): {api_md}")
        success(f"OpenAPI Markdown exists ({api_md.stat().st_size} bytes)")


def main() -> None:
    """Main entry point."""
    root = Path(__file__).resolve().parents[1]
    
    print(f"📋 Validating documentation in: {root}\n")
    
    # Run all checks
    check_required_files(root)
    check_headings(root)
    check_no_placeholders(root)
    check_links(root)
    check_api_docs(root)
    
    print(f"\n✅ All documentation checks passed!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
