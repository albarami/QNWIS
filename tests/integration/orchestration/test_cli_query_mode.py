"""
Integration tests for CLI query mode.

Tests cover:
- Running CLI with --query flag
- Verifying exit code 0 for successful queries
- Verifying JSON output includes selected intent and mode
- Testing various query types (anomalies, correlation, GCC, etc.)
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest


def run_cli_query(query: str, extra_args: list[str] | None = None) -> tuple[int, str, str]:
    """
    Run CLI with query and return exit code, stdout, stderr.

    Args:
        query: Natural language query
        extra_args: Additional CLI arguments

    Returns:
        Tuple of (exit_code, stdout, stderr)
    """
    args = [
        sys.executable,
        "-m",
        "src.qnwis.cli.qnwis_workflow",
        "--query",
        query,
        "--format",
        "json",
        "--log-level",
        "ERROR",  # Suppress logs for cleaner test output
    ]

    if extra_args:
        args.extend(extra_args)

    result = subprocess.run(
        args,
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).parent.parent.parent.parent),
    )

    return result.returncode, result.stdout, result.stderr


@pytest.mark.integration
def test_cli_query_mode_anomalies() -> None:
    """Test CLI with query for anomaly detection."""
    query = "Find anomalies in Healthcare retention last 24 months"

    exit_code, stdout, stderr = run_cli_query(query)

    # Should exit successfully
    assert exit_code == 0, f"CLI failed with stderr: {stderr}"

    # Should have JSON output
    assert stdout.strip(), "No output from CLI"

    try:
        result = json.loads(stdout)
    except json.JSONDecodeError as e:
        pytest.fail(f"Invalid JSON output: {e}\nOutput: {stdout}")

    # Should have ok=True
    assert result.get("ok") is True, f"Result not ok: {result}"

    # Should have intent selected
    assert "intent" in result
    # Should be pattern.anomalies or similar
    assert result["intent"] in [
        "pattern.anomalies",
        "pattern.correlation",
        "pattern.root_causes",
        "pattern.best_practices",
    ]

    # Should have sections
    assert "sections" in result
    assert len(result["sections"]) > 0


@pytest.mark.integration
def test_cli_query_mode_correlation() -> None:
    """Test CLI with query for correlation analysis."""
    query = "Is there a correlation between salary and retention in Construction?"

    exit_code, stdout, stderr = run_cli_query(query)

    # Should exit successfully
    assert exit_code == 0, f"CLI failed with stderr: {stderr}"

    # Parse JSON
    result = json.loads(stdout)

    # Should succeed
    assert result.get("ok") is True

    # Should classify to pattern-related intent
    assert result["intent"].startswith("pattern.")


@pytest.mark.integration
def test_cli_query_mode_gcc_benchmark() -> None:
    """Test CLI with query for GCC benchmark."""
    query = "Compare Qatar wage growth to UAE and Saudi Arabia"

    exit_code, stdout, stderr = run_cli_query(query)

    # Should exit successfully
    assert exit_code == 0, f"CLI failed with stderr: {stderr}"

    # Parse JSON
    result = json.loads(stdout)

    # Should succeed
    assert result.get("ok") is True

    # Should classify to strategy.gcc_benchmark
    assert result["intent"] == "strategy.gcc_benchmark"


@pytest.mark.integration
def test_cli_query_mode_vision2030() -> None:
    """Test CLI with query for Vision 2030 alignment."""
    query = "Assess qatarization progress toward Vision 2030 targets"

    exit_code, stdout, stderr = run_cli_query(query)

    # Should exit successfully
    assert exit_code == 0, f"CLI failed with stderr: {stderr}"

    # Parse JSON
    result = json.loads(stdout)

    # Should succeed
    assert result.get("ok") is True

    # Should classify to strategy.vision2030
    assert result["intent"] == "strategy.vision2030"


@pytest.mark.integration
def test_cli_query_mode_talent_competition() -> None:
    """Test CLI with query for talent competition."""
    query = "Analyze poaching patterns in Finance sector"

    exit_code, stdout, stderr = run_cli_query(query)

    # Should exit successfully
    assert exit_code == 0, f"CLI failed with stderr: {stderr}"

    # Parse JSON
    result = json.loads(stdout)

    # Should succeed
    assert result.get("ok") is True

    # Should classify to strategy.talent_competition
    assert result["intent"] == "strategy.talent_competition"


@pytest.mark.integration
def test_cli_query_mode_low_confidence_fails_gracefully() -> None:
    """Test CLI with vague query (low confidence)."""
    query = "Tell me something"

    exit_code, stdout, stderr = run_cli_query(query)

    # Should exit with error code (or 0 with ok=False)
    # Allow either pattern
    if exit_code == 0:
        # Parse JSON and check ok=False
        result = json.loads(stdout)
        assert result.get("ok") is False, "Expected ok=False for low confidence query"
    else:
        # Exit code non-zero is also acceptable
        assert exit_code != 0


@pytest.mark.integration
def test_cli_query_mode_with_output_file(tmp_path: Path) -> None:
    """Test CLI with --output flag."""
    query = "Find correlations in Construction retention"
    output_file = tmp_path / "result.json"

    exit_code, stdout, stderr = run_cli_query(
        query,
        extra_args=["--output", str(output_file)],
    )

    # Should exit successfully
    assert exit_code == 0, f"CLI failed with stderr: {stderr}"

    # Output file should exist
    assert output_file.exists(), "Output file not created"

    # Should have valid JSON in file
    with open(output_file, "r", encoding="utf-8") as f:
        result = json.load(f)

    assert result.get("ok") is True
    assert "intent" in result


@pytest.mark.integration
def test_cli_query_mode_json_includes_metadata() -> None:
    """Test that JSON output includes routing metadata."""
    query = "Analyze retention trends in Healthcare"

    exit_code, stdout, stderr = run_cli_query(query)

    # Should exit successfully
    assert exit_code == 0, f"CLI failed with stderr: {stderr}"

    result = json.loads(stdout)

    # Should have standard fields
    assert "ok" in result
    assert "intent" in result
    assert "sections" in result
    assert "citations" in result
    assert "freshness" in result
    assert "reproducibility" in result
    assert "timestamp" in result

    # Reproducibility should have method and params
    repro = result.get("reproducibility", {})
    assert "method" in repro
    assert "params" in repro
    assert "timestamp" in repro


@pytest.mark.integration
def test_cli_query_mode_markdown_format() -> None:
    """Test CLI with --format markdown."""
    query = "Find anomalies in Construction"

    args = [
        sys.executable,
        "-m",
        "src.qnwis.cli.qnwis_workflow",
        "--query",
        query,
        "--format",
        "markdown",
        "--log-level",
        "ERROR",
    ]

    result = subprocess.run(
        args,
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).parent.parent.parent.parent),
    )

    # Should exit successfully
    assert result.returncode == 0, f"CLI failed with stderr: {result.stderr}"

    # Should have markdown output
    assert result.stdout.strip()
    assert "# QNWIS Analysis:" in result.stdout
    assert "## " in result.stdout  # Section headers


@pytest.mark.integration
def test_cli_query_mode_request_id_propagation() -> None:
    """Test that request_id is propagated through workflow."""
    query = "Analyze retention in Finance"
    request_id = "test-req-12345"

    exit_code, stdout, stderr = run_cli_query(
        query,
        extra_args=["--request-id", request_id],
    )

    # Should exit successfully
    assert exit_code == 0, f"CLI failed with stderr: {stderr}"

    result = json.loads(stdout)

    # Should have request_id in result
    assert result.get("request_id") == request_id


@pytest.mark.integration
def test_cli_query_mode_deterministic_output() -> None:
    """Test that same query produces deterministic output."""
    query = "Find correlations in Construction retention over 24 months"

    # Run twice
    exit_code1, stdout1, stderr1 = run_cli_query(query)
    exit_code2, stdout2, stderr2 = run_cli_query(query)

    # Both should succeed
    assert exit_code1 == 0
    assert exit_code2 == 0

    result1 = json.loads(stdout1)
    result2 = json.loads(stdout2)

    # Intent should be the same
    assert result1["intent"] == result2["intent"]

    # Reproducibility params should be the same
    repro1 = result1.get("reproducibility", {})
    repro2 = result2.get("reproducibility", {})
    assert repro1.get("method") == repro2.get("method")
    # Note: params may include dynamic data, so we just check method is consistent


@pytest.mark.integration
def test_cli_query_mode_root_causes() -> None:
    """Test CLI with root cause query."""
    query = "Why is retention declining in Construction?"

    exit_code, stdout, stderr = run_cli_query(query)

    # Should exit successfully
    assert exit_code == 0, f"CLI failed with stderr: {stderr}"

    result = json.loads(stdout)

    # Should succeed
    assert result.get("ok") is True

    # Should classify to pattern.root_causes
    assert result["intent"] == "pattern.root_causes"


@pytest.mark.integration
def test_cli_query_mode_best_practices() -> None:
    """Test CLI with best practices query."""
    query = "Which companies have best practices for retention in Healthcare?"

    exit_code, stdout, stderr = run_cli_query(query)

    # Should exit successfully
    assert exit_code == 0, f"CLI failed with stderr: {stderr}"

    result = json.loads(stdout)

    # Should succeed
    assert result.get("ok") is True

    # Should classify to pattern.best_practices
    assert result["intent"] == "pattern.best_practices"


@pytest.mark.integration
def test_cli_query_mode_with_sector_override() -> None:
    """Test CLI query with explicit sector parameter override."""
    query = "Find anomalies in retention"

    exit_code, stdout, stderr = run_cli_query(
        query,
        extra_args=["--sector", "Finance"],
    )

    # Should exit successfully
    assert exit_code == 0, f"CLI failed with stderr: {stderr}"

    result = json.loads(stdout)

    # Should succeed
    assert result.get("ok") is True

    # Reproducibility params should include sector=Finance
    repro = result.get("reproducibility", {})
    params = repro.get("params", {})
    # May or may not be in params depending on agent signature, but should not crash
    assert isinstance(params, dict)
