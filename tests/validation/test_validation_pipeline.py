"""
Tests for QNWIS validation pipeline.

Covers YAML loading, execution modes, metrics computation, and reporting.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

import pytest


def _write_sample_case(tmpdir: Path) -> None:
    """Write a sample validation case for testing."""
    cases = tmpdir / "validation" / "cases"
    cases.mkdir(parents=True, exist_ok=True)
    
    cases.joinpath("health_echo.yaml").write_text(
        textwrap.dedent("""
            name: health_echo
            endpoint: /health/ready
            method: GET
            mode: echo
            tier: simple
            expected_response:
              metadata:
                verification: true
                freshness:
                  LMIS: "2h"
                citations:
                  - LMIS
        """).strip(),
        encoding="utf-8"
    )


def test_metrics_citation_coverage():
    """Test citation coverage metric."""
    from src.qnwis.validation.metrics import citation_coverage
    
    # No numbers, no citations -> 1.0
    resp = {"data": "text without numbers"}
    assert citation_coverage(resp) == 1.0
    
    # Numbers present, no citations -> 0.0
    resp = {"data": "value is 42", "metadata": {}}
    assert citation_coverage(resp) == 0.0
    
    # Numbers and citations present -> 1.0
    resp = {
        "data": "value is 42",
        "metadata": {"citations": ["LMIS"]}
    }
    assert citation_coverage(resp) == 1.0


def test_metrics_freshness_present():
    """Test freshness indicator detection."""
    from src.qnwis.validation.metrics import freshness_present
    
    # No metadata
    assert not freshness_present({})
    
    # Freshness present
    resp = {"metadata": {"freshness": {"LMIS": "2h"}}}
    assert freshness_present(resp)
    
    # Data sources present
    resp = {"metadata": {"data_sources": ["LMIS"]}}
    assert freshness_present(resp)


def test_metrics_verification_passed():
    """Test verification status detection."""
    from src.qnwis.validation.metrics import verification_passed
    
    # No metadata
    assert not verification_passed({})
    
    # Verification passed (string)
    resp = {"metadata": {"verification": "passed"}}
    assert verification_passed(resp)
    
    # Verification passed (boolean)
    resp = {"metadata": {"verification": True}}
    assert verification_passed(resp)
    
    # Verification failed
    resp = {"metadata": {"verification": "failed"}}
    assert not verification_passed(resp)


def test_metrics_compute_latency():
    """Test latency computation."""
    from src.qnwis.validation.metrics import compute_latency_ms
    
    timing = (1.0, 1.5)
    latency = compute_latency_ms(timing)
    assert latency == 500.0


def test_metrics_compute_score():
    """Test acceptance envelope scoring."""
    from src.qnwis.validation.metrics import compute_score
    
    # Simple tier, all pass
    assert compute_score(5000, "simple", True, 0.8, True)
    
    # Simple tier, latency fail
    assert not compute_score(15000, "simple", True, 0.8, True)
    
    # Medium tier, verification fail
    assert not compute_score(20000, "medium", False, 0.8, True)
    
    # Complex tier, coverage fail
    assert not compute_score(80000, "complex", True, 0.3, True)
    
    # Dashboard tier, freshness fail
    assert not compute_score(2000, "dashboard", True, 0.8, False)


def test_run_validation_echo(tmp_path: Path, monkeypatch):
    """Test validation runner in echo mode."""
    # Set up test environment
    monkeypatch.chdir(tmp_path)
    
    # Create directory structure
    (tmp_path / "validation" / "results").mkdir(parents=True, exist_ok=True)
    _write_sample_case(tmp_path)
    
    # Copy source files to tmp workspace
    root = Path(__file__).resolve().parents[2]
    
    # Copy metrics module
    metrics_src = root / "src" / "qnwis" / "validation" / "metrics.py"
    metrics_dst = tmp_path / "src" / "qnwis" / "validation" / "metrics.py"
    metrics_dst.parent.mkdir(parents=True, exist_ok=True)
    metrics_dst.write_text(metrics_src.read_text(encoding="utf-8"), encoding="utf-8")
    
    # Copy __init__ files
    for init_path in [
        "src/__init__.py",
        "src/qnwis/__init__.py",
        "src/qnwis/validation/__init__.py"
    ]:
        init_dst = tmp_path / init_path
        init_dst.parent.mkdir(parents=True, exist_ok=True)
        init_dst.write_text("", encoding="utf-8")
    
    # Copy runner script
    runner_src = root / "scripts" / "validation" / "run_validation.py"
    runner_dst = tmp_path / "scripts" / "validation" / "run_validation.py"
    runner_dst.parent.mkdir(parents=True, exist_ok=True)
    runner_dst.write_text(runner_src.read_text(encoding="utf-8"), encoding="utf-8")
    
    # Run validation
    cmd = [
        sys.executable,
        str(runner_dst),
        "--cases", "validation/cases",
        "--mode", "echo",
        "--outdir", "validation/results"
    ]
    
    result = subprocess.run(
        cmd,
        cwd=str(tmp_path),
        capture_output=True,
        text=True
    )
    
    # Check success
    assert result.returncode == 0, f"Validation failed: {result.stderr}"
    
    # Check outputs
    summary_path = tmp_path / "validation" / "summary.csv"
    assert summary_path.exists(), "Summary CSV not created"
    
    summary = summary_path.read_text(encoding="utf-8")
    assert "health_echo" in summary
    assert "pass" in summary.lower()
    
    # Check detailed result
    result_path = tmp_path / "validation" / "results" / "health_echo.json"
    assert result_path.exists(), "Detailed result not created"
    
    result_data = json.loads(result_path.read_text(encoding="utf-8"))
    assert result_data["result"]["pass"] is True


def test_render_case_studies(tmp_path: Path, monkeypatch):
    """Test case study renderer."""
    monkeypatch.chdir(tmp_path)
    
    # Create mock result
    results_dir = tmp_path / "validation" / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    
    mock_result = {
        "spec": {
            "name": "test_case",
            "endpoint": "/api/v1/query"
        },
        "result": {
            "case": "test_case",
            "endpoint": "/api/v1/query",
            "tier": "simple",
            "status": 200,
            "latency_ms": 5000,
            "citation_coverage": 0.85,
            "freshness_present": True,
            "verification_passed": True,
            "pass": True
        },
        "body": {
            "answer": "Test answer",
            "metadata": {
                "verification": "passed",
                "citations": ["LMIS"]
            }
        }
    }
    
    (results_dir / "test_case.json").write_text(
        json.dumps(mock_result, indent=2),
        encoding="utf-8"
    )
    
    # Copy renderer script
    root = Path(__file__).resolve().parents[2]
    renderer_src = root / "scripts" / "validation" / "render_case_studies.py"
    renderer_dst = tmp_path / "scripts" / "validation" / "render_case_studies.py"
    renderer_dst.parent.mkdir(parents=True, exist_ok=True)
    renderer_dst.write_text(renderer_src.read_text(encoding="utf-8"), encoding="utf-8")
    
    # Run renderer
    cmd = [sys.executable, str(renderer_dst)]
    result = subprocess.run(
        cmd,
        cwd=str(tmp_path),
        capture_output=True,
        text=True
    )
    
    assert result.returncode == 0, f"Renderer failed: {result.stderr}"
    
    # Check output
    output_path = tmp_path / "docs" / "validation" / "CASE_STUDIES.md"
    assert output_path.exists(), "Case studies not created"
    
    content = output_path.read_text(encoding="utf-8")
    assert "test_case" in content.lower()
    assert "PASSED" in content or "✓" in content


def test_compare_baseline(tmp_path: Path, monkeypatch):
    """Test baseline comparison."""
    monkeypatch.chdir(tmp_path)
    
    # Create mock result
    results_dir = tmp_path / "validation" / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    
    mock_result = {
        "result": {
            "case": "test_case",
            "latency_ms": 5000,
            "verification_passed": True
        }
    }
    
    (results_dir / "test_case.json").write_text(
        json.dumps(mock_result, indent=2),
        encoding="utf-8"
    )
    
    # Create mock baseline
    baselines_dir = tmp_path / "validation" / "baselines"
    baselines_dir.mkdir(parents=True, exist_ok=True)
    
    mock_baseline = {
        "case": "test_case",
        "latency_ms": 15000,
        "verified": False
    }
    
    (baselines_dir / "test_case.json").write_text(
        json.dumps(mock_baseline, indent=2),
        encoding="utf-8"
    )
    
    # Copy comparison script
    root = Path(__file__).resolve().parents[2]
    compare_src = root / "scripts" / "validation" / "compare_baseline.py"
    compare_dst = tmp_path / "scripts" / "validation" / "compare_baseline.py"
    compare_dst.parent.mkdir(parents=True, exist_ok=True)
    compare_dst.write_text(compare_src.read_text(encoding="utf-8"), encoding="utf-8")
    
    # Run comparison
    cmd = [sys.executable, str(compare_dst)]
    result = subprocess.run(
        cmd,
        cwd=str(tmp_path),
        capture_output=True,
        text=True
    )
    
    assert result.returncode == 0, f"Comparison failed: {result.stderr}"
    
    # Parse output
    output = json.loads(result.stdout)
    assert "improvements" in output
    assert len(output["improvements"]) > 0
    
    improvement = output["improvements"][0]
    assert improvement["throughput_gain_x"] == 3.0  # 15000 / 5000


def test_yaml_case_loading():
    """Test YAML case file loading."""
    import yaml
    
    root = Path(__file__).resolve().parents[2]
    cases_dir = root / "validation" / "cases"
    
    # Check that cases exist
    assert cases_dir.exists(), "Cases directory not found"
    
    case_files = list(cases_dir.glob("*.yaml"))
    assert len(case_files) >= 20, f"Expected 20+ cases, found {len(case_files)}"
    
    # Validate each case
    for case_file in case_files:
        with case_file.open("r", encoding="utf-8") as f:
            case = yaml.safe_load(f)
        
        # Required fields
        assert "name" in case, f"{case_file.name}: missing 'name'"
        assert "endpoint" in case, f"{case_file.name}: missing 'endpoint'"
        assert "tier" in case, f"{case_file.name}: missing 'tier'"
        
        # Valid tier
        assert case["tier"] in ["simple", "medium", "complex", "dashboard"], \
            f"{case_file.name}: invalid tier '{case['tier']}'"
        
        # Acceptance criteria
        if "acceptance" in case:
            acc = case["acceptance"]
            assert "max_latency_ms" in acc, f"{case_file.name}: missing max_latency_ms"
            assert "verification_required" in acc, f"{case_file.name}: missing verification_required"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
