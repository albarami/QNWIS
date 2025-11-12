"""
Basic documentation tests.

Tests:
- Required documentation files exist
- Documentation files have proper headings
- OpenAPI export script works
- Documentation validation passes
"""

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

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


def test_required_docs_exist():
    """Test that all required documentation files exist."""
    missing = []
    for doc_path in REQUIRED_DOCS:
        full_path = ROOT / doc_path
        if not full_path.exists():
            missing.append(doc_path)
    
    assert not missing, f"Missing required documentation files: {missing}"


def test_docs_have_headings():
    """Test that all documentation files have proper H1 headings."""
    missing_headings = []
    
    for doc_path in REQUIRED_DOCS:
        full_path = ROOT / doc_path
        if not full_path.exists():
            continue
        
        content = full_path.read_text(encoding="utf-8", errors="ignore")
        lines = content.splitlines()
        
        # Check first non-empty line is a heading
        has_heading = False
        for line in lines:
            if line.strip():
                if line.strip().startswith("#"):
                    has_heading = True
                break
        
        if not has_heading:
            missing_headings.append(doc_path)
    
    assert not missing_headings, f"Documentation files missing H1 heading: {missing_headings}"


def test_docs_not_empty():
    """Test that all documentation files have substantial content."""
    too_small = []
    min_size = 1000  # At least 1KB
    
    for doc_path in REQUIRED_DOCS:
        full_path = ROOT / doc_path
        if not full_path.exists():
            continue
        
        size = full_path.stat().st_size
        if size < min_size:
            too_small.append((doc_path, size))
    
    assert not too_small, f"Documentation files too small: {too_small}"


def test_docs_no_placeholders():
    """Test that documentation contains no TODO/FIXME placeholders."""
    import re
    
    placeholder_pattern = re.compile(r'\b(TODO|FIXME|XXX|PLACEHOLDER)\b', re.IGNORECASE)
    bad_files = []
    
    for doc_path in REQUIRED_DOCS:
        full_path = ROOT / doc_path
        if not full_path.exists():
            continue
        
        content = full_path.read_text(encoding="utf-8", errors="ignore")
        matches = placeholder_pattern.findall(content)
        if matches:
            bad_files.append((doc_path, matches))
    
    assert not bad_files, f"Documentation contains placeholders: {bad_files}"


@pytest.mark.skipif(
    not (ROOT / "src" / "qnwis" / "api" / "server.py").exists(),
    reason="FastAPI server not found"
)
def test_export_openapi_script():
    """Test that OpenAPI export script runs successfully."""
    script_path = ROOT / "scripts" / "export_openapi.py"
    assert script_path.exists(), "export_openapi.py script not found"
    
    # Run the script
    result = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=30
    )
    
    # Check it succeeded
    if result.returncode != 0:
        pytest.fail(
            f"export_openapi.py failed with code {result.returncode}\n"
            f"STDOUT: {result.stdout}\n"
            f"STDERR: {result.stderr}"
        )
    
    # Check output files exist
    openapi_json = ROOT / "docs" / "api" / "openapi.json"
    openapi_md = ROOT / "docs" / "api" / "openapi.md"
    
    assert openapi_json.exists(), "openapi.json not created"
    assert openapi_md.exists(), "openapi.md not created"
    
    # Check files are not empty
    assert openapi_json.stat().st_size > 100, "openapi.json is too small"
    assert openapi_md.stat().st_size > 100, "openapi.md is too small"
    
    # Check JSON is valid
    import json
    try:
        schema = json.loads(openapi_json.read_text())
        assert "openapi" in schema, "Invalid OpenAPI schema"
        assert "paths" in schema, "OpenAPI schema missing paths"
    except json.JSONDecodeError as e:
        pytest.fail(f"Invalid JSON in openapi.json: {e}")


def test_doc_checks_script():
    """Test that documentation validation script passes."""
    script_path = ROOT / "scripts" / "doc_checks.py"
    assert script_path.exists(), "doc_checks.py script not found"
    
    # Run the script
    result = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=30
    )
    
    # Check it succeeded
    if result.returncode != 0:
        pytest.fail(
            f"doc_checks.py failed with code {result.returncode}\n"
            f"STDOUT: {result.stdout}\n"
            f"STDERR: {result.stderr}"
        )
    
    # Check success message in output
    assert "All documentation checks passed" in result.stdout or "OK" in result.stdout


def test_api_reference_points_to_openapi():
    """Test that API_REFERENCE.md references the OpenAPI files."""
    api_ref = ROOT / "docs" / "API_REFERENCE.md"
    assert api_ref.exists(), "API_REFERENCE.md not found"
    
    content = api_ref.read_text(encoding="utf-8")
    
    # Check it references openapi.json and openapi.md
    assert "openapi.json" in content, "API_REFERENCE.md doesn't reference openapi.json"
    assert "openapi.md" in content, "API_REFERENCE.md doesn't reference openapi.md"


def test_docs_mention_deterministic_data_layer():
    """Test that key docs mention the Deterministic Data Layer."""
    docs_to_check = [
        "docs/USER_GUIDE.md",
        "docs/API_REFERENCE.md",
        "docs/ARCHITECTURE.md",
        "docs/DEVELOPER_ONBOARDING.md",
    ]
    
    missing = []
    for doc_path in docs_to_check:
        full_path = ROOT / doc_path
        if not full_path.exists():
            continue
        
        content = full_path.read_text(encoding="utf-8", errors="ignore").lower()
        if "deterministic data layer" not in content:
            missing.append(doc_path)
    
    assert not missing, f"Docs missing 'Deterministic Data Layer' reference: {missing}"


def test_docs_mention_security_step34():
    """Test that docs reference Step 34 security controls."""
    docs_to_check = [
        "docs/SECURITY.md",
        "docs/ARCHITECTURE.md",
        "docs/RELEASE_NOTES.md",
    ]
    
    missing = []
    for doc_path in docs_to_check:
        full_path = ROOT / doc_path
        if not full_path.exists():
            continue
        
        content = full_path.read_text(encoding="utf-8", errors="ignore").lower()
        # Check for security-related terms
        has_security = any(term in content for term in [
            "step 34", "step34", "csrf", "rate limit", "rbac", "security hardening"
        ])
        if not has_security:
            missing.append(doc_path)
    
    assert not missing, f"Docs missing Step 34 security references: {missing}"


def test_docs_mention_performance_step35():
    """Test that docs reference Step 35 performance optimization."""
    docs_to_check = [
        "docs/PERFORMANCE.md",
        "docs/ARCHITECTURE.md",
        "docs/RELEASE_NOTES.md",
    ]
    
    missing = []
    for doc_path in docs_to_check:
        full_path = ROOT / doc_path
        if not full_path.exists():
            continue
        
        content = full_path.read_text(encoding="utf-8", errors="ignore").lower()
        # Check for performance-related terms
        has_performance = any(term in content for term in [
            "step 35", "step35", "slo", "cache", "performance", "optimization"
        ])
        if not has_performance:
            missing.append(doc_path)
    
    assert not missing, f"Docs missing Step 35 performance references: {missing}"


def test_docs_mention_metrics_endpoint():
    """Test that docs mention /metrics endpoint and its restrictions."""
    docs_to_check = [
        "docs/API_REFERENCE.md",
        "docs/SECURITY.md",
        "docs/PERFORMANCE.md",
    ]
    
    missing = []
    for doc_path in docs_to_check:
        full_path = ROOT / doc_path
        if not full_path.exists():
            continue
        
        content = full_path.read_text(encoding="utf-8", errors="ignore")
        if "/metrics" not in content:
            missing.append(doc_path)
    
    assert not missing, f"Docs missing /metrics endpoint reference: {missing}"


def test_operations_runbook_has_procedures():
    """Test that operations runbook has key procedures."""
    runbook = ROOT / "docs" / "OPERATIONS_RUNBOOK.md"
    assert runbook.exists(), "OPERATIONS_RUNBOOK.md not found"
    
    content = runbook.read_text(encoding="utf-8", errors="ignore").lower()
    
    required_sections = [
        "on-call",
        "incident response",
        "backup",
        "deployment",
        "monitoring",
        "alerts",
    ]
    
    missing = [section for section in required_sections if section not in content]
    assert not missing, f"Operations runbook missing sections: {missing}"


def test_troubleshooting_has_common_issues():
    """Test that troubleshooting guide covers common issues."""
    troubleshooting = ROOT / "docs" / "TROUBLESHOOTING.md"
    assert troubleshooting.exists(), "TROUBLESHOOTING.md not found"
    
    content = troubleshooting.read_text(encoding="utf-8", errors="ignore").lower()
    
    common_issues = [
        "timeout",
        "database",
        "redis",
        "csrf",
        "rate limit",
        "cors",
    ]
    
    missing = [issue for issue in common_issues if issue not in content]
    assert not missing, f"Troubleshooting guide missing issues: {missing}"


def test_security_doc_has_controls():
    """Test that security documentation covers key controls."""
    security = ROOT / "docs" / "SECURITY.md"
    assert security.exists(), "SECURITY.md not found"
    
    content = security.read_text(encoding="utf-8", errors="ignore").lower()
    
    required_controls = [
        "tls",
        "csrf",
        "rate limit",
        "rbac",
        "audit",
        "authentication",
        "authorization",
    ]
    
    missing = [control for control in required_controls if control not in content]
    assert not missing, f"Security doc missing controls: {missing}"


def test_performance_doc_has_slos():
    """Test that performance documentation includes SLOs."""
    performance = ROOT / "docs" / "PERFORMANCE.md"
    assert performance.exists(), "PERFORMANCE.md not found"
    
    content = performance.read_text(encoding="utf-8", errors="ignore")
    
    # Check for SLO targets
    assert "10" in content and "second" in content.lower(), "Missing simple query SLO (10s)"
    assert "30" in content and "second" in content.lower(), "Missing medium query SLO (30s)"
    assert "90" in content and "second" in content.lower(), "Missing complex query SLO (90s)"


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
