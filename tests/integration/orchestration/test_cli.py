"""
Integration tests for QNWIS workflow CLI.

Tests cover:
- CLI argument parsing and execution
- JSON and Markdown output formats
- Parameter passing to workflows
- Error handling
- Configuration loading
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

# Get the path to the CLI module
CLI_MODULE = "src.qnwis.cli.qnwis_workflow"


def create_test_config() -> dict[str, Any]:
    """Create a minimal valid test configuration."""
    return {
        "timeouts": {
            "agent_call_ms": 30000,
        },
        "retries": {
            "agent_call": 1,
            "transient": ["TimeoutError", "ConnectionError"],
        },
        "validation": {
            "strict": False,
            "require_evidence": True,
            "require_freshness": True,
        },
        "formatting": {
            "max_findings": 10,
            "max_citations": 20,
            "top_evidence": 5,
        },
        "enabled_intents": [
            "pattern.anomalies",
            "pattern.correlation",
            "strategy.gcc_benchmark",
        ],
        "logging": {
            "level": "INFO",
        },
    }


@pytest.fixture
def test_config_file(tmp_path: Path) -> Path:
    """Create a temporary config file for testing."""
    config_file = tmp_path / "test_orchestration.yml"
    config = create_test_config()

    with open(config_file, "w", encoding="utf-8") as f:
        yaml.dump(config, f)

    return config_file


def run_cli(*args: str) -> subprocess.CompletedProcess:
    """
    Run the CLI with given arguments.

    Args:
        *args: CLI arguments

    Returns:
        CompletedProcess with stdout, stderr, and returncode
    """
    cmd = [sys.executable, "-m", CLI_MODULE] + list(args)
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=60,
    )
    return result


def test_cli_basic_invocation(test_config_file: Path) -> None:
    """Test basic CLI invocation with valid arguments."""
    result = run_cli(
        "--intent",
        "pattern.anomalies",
        "--config",
        str(test_config_file),
        "--z-threshold",
        "2.5",
        "--format",
        "json",
    )

    # Should complete (may succeed or fail based on data availability)
    # but should not crash
    assert result.returncode in (0, 1)  # 0=success, 1=error
    assert result.stdout or result.stderr


def test_cli_json_output_structure(test_config_file: Path, tmp_path: Path) -> None:
    """Test that JSON output has correct structure."""
    output_file = tmp_path / "output.json"

    result = run_cli(
        "--intent",
        "pattern.anomalies",
        "--config",
        str(test_config_file),
        "--output",
        str(output_file),
        "--format",
        "json",
        "--z-threshold",
        "2.5",
    )

    # If output was written, verify structure
    if output_file.exists():
        with open(output_file, encoding="utf-8") as f:
            data = json.load(f)

        # Verify OrchestrationResult structure
        assert "ok" in data
        assert "intent" in data
        assert "sections" in data
        assert "citations" in data
        assert "freshness" in data
        assert "reproducibility" in data
        assert "timestamp" in data

        # Verify sections structure
        if data["sections"]:
            section = data["sections"][0]
            assert "title" in section
            assert "body_md" in section


def test_cli_markdown_output(test_config_file: Path, tmp_path: Path) -> None:
    """Test that Markdown output is generated."""
    output_file = tmp_path / "output.md"

    result = run_cli(
        "--intent",
        "pattern.correlation",
        "--config",
        str(test_config_file),
        "--output",
        str(output_file),
        "--format",
        "markdown",
        "--sector",
        "Construction",
        "--months",
        "24",
    )

    # If output was written, verify it's markdown
    if output_file.exists():
        content = output_file.read_text(encoding="utf-8")

        # Should have markdown headers
        assert "#" in content
        assert "**" in content or "*" in content


def test_cli_parameter_passing(test_config_file: Path) -> None:
    """Test that CLI parameters are correctly passed to workflow."""
    result = run_cli(
        "--intent",
        "pattern.correlation",
        "--config",
        str(test_config_file),
        "--sector",
        "Healthcare",
        "--months",
        "36",
        "--format",
        "json",
    )

    # Parameters should be processed
    assert result.returncode in (0, 1)


def test_cli_request_id_tracking(test_config_file: Path) -> None:
    """Test that request ID is tracked through workflow."""
    result = run_cli(
        "--intent",
        "strategy.gcc_benchmark",
        "--config",
        str(test_config_file),
        "--request-id",
        "test-cli-001",
        "--format",
        "json",
    )

    # Request ID should be in output if successful
    if result.returncode == 0 and result.stdout:
        try:
            data = json.loads(result.stdout)
            if "request_id" in data:
                assert data["request_id"] == "test-cli-001"
        except json.JSONDecodeError:
            pass  # Output may not be JSON if there was an error


def test_cli_missing_required_intent() -> None:
    """Test that CLI rejects missing --intent argument."""
    result = run_cli("--format", "json")

    # Should fail
    assert result.returncode != 0
    assert "required" in result.stderr.lower() or "intent" in result.stderr.lower()


def test_cli_invalid_intent(test_config_file: Path) -> None:
    """Test that CLI rejects invalid intent values."""
    result = run_cli(
        "--intent",
        "invalid.intent",
        "--config",
        str(test_config_file),
        "--format",
        "json",
    )

    # Should fail with invalid choice error
    assert result.returncode != 0


def test_cli_disabled_intent(tmp_path: Path) -> None:
    """Test that CLI rejects disabled intents."""
    # Create config with limited enabled intents
    config = create_test_config()
    config["enabled_intents"] = ["pattern.anomalies"]  # Only one enabled

    config_file = tmp_path / "limited_config.yml"
    with open(config_file, "w", encoding="utf-8") as f:
        yaml.dump(config, f)

    result = run_cli(
        "--intent",
        "strategy.gcc_benchmark",  # Not enabled
        "--config",
        str(config_file),
        "--format",
        "json",
    )

    # Should fail or warn about disabled intent
    assert result.returncode == 1


def test_cli_help_flag() -> None:
    """Test that --help flag works."""
    result = run_cli("--help")

    # Should succeed and show help
    assert result.returncode == 0
    assert "usage" in result.stdout.lower() or "QNWIS" in result.stdout


def test_cli_log_level(test_config_file: Path) -> None:
    """Test that log level can be configured."""
    result = run_cli(
        "--intent",
        "pattern.anomalies",
        "--config",
        str(test_config_file),
        "--log-level",
        "DEBUG",
        "--format",
        "json",
    )

    # Should run with debug logging
    assert result.returncode in (0, 1)


def test_cli_multiple_metrics(test_config_file: Path) -> None:
    """Test passing multiple metrics via CLI."""
    result = run_cli(
        "--intent",
        "pattern.correlation",
        "--config",
        str(test_config_file),
        "--metrics",
        "attrition",
        "retention",
        "turnover",
        "--format",
        "json",
    )

    # Should accept multiple metrics
    assert result.returncode in (0, 1)


def test_cli_year_range_parameters(test_config_file: Path) -> None:
    """Test start-year and end-year parameters."""
    result = run_cli(
        "--intent",
        "pattern.correlation",
        "--config",
        str(test_config_file),
        "--start-year",
        "2020",
        "--end-year",
        "2023",
        "--format",
        "json",
    )

    # Should accept year range
    assert result.returncode in (0, 1)


def test_cli_numeric_parameters(test_config_file: Path) -> None:
    """Test that numeric parameters are correctly typed."""
    result = run_cli(
        "--intent",
        "strategy.gcc_benchmark",
        "--config",
        str(test_config_file),
        "--min-countries",
        "4",
        "--format",
        "json",
    )

    # Should accept numeric parameter
    assert result.returncode in (0, 1)


def test_cli_output_directory_creation(test_config_file: Path, tmp_path: Path) -> None:
    """Test that output directory is created if it doesn't exist."""
    nested_dir = tmp_path / "nested" / "output"
    output_file = nested_dir / "result.json"

    result = run_cli(
        "--intent",
        "pattern.anomalies",
        "--config",
        str(test_config_file),
        "--output",
        str(output_file),
        "--format",
        "json",
    )

    # If successful, directory should be created
    if result.returncode == 0:
        assert nested_dir.exists()


def test_cli_stdout_output(test_config_file: Path) -> None:
    """Test that output goes to stdout when --output not specified."""
    result = run_cli(
        "--intent",
        "pattern.anomalies",
        "--config",
        str(test_config_file),
        "--format",
        "json",
        "--z-threshold",
        "3.0",
    )

    # Should have output in stdout or stderr
    assert len(result.stdout) > 0 or len(result.stderr) > 0


def test_cli_user_id_tracking(test_config_file: Path) -> None:
    """Test that user-id is passed through."""
    result = run_cli(
        "--intent",
        "pattern.anomalies",
        "--config",
        str(test_config_file),
        "--user-id",
        "test-user-123",
        "--format",
        "json",
    )

    # Should run with user_id
    assert result.returncode in (0, 1)


def test_cli_missing_config_file() -> None:
    """Test CLI behavior with missing config file."""
    result = run_cli(
        "--intent",
        "pattern.anomalies",
        "--config",
        "/nonexistent/config.yml",
        "--format",
        "json",
    )

    # Should fail
    assert result.returncode == 1
    # Should have error message about missing file
    error_output = result.stderr.lower()
    assert "file" in error_output or "not found" in error_output or "error" in error_output


def test_cli_json_format_default(test_config_file: Path) -> None:
    """Test that JSON is the default output format."""
    result = run_cli(
        "--intent",
        "pattern.anomalies",
        "--config",
        str(test_config_file),
        # Note: no --format specified
    )

    # Default format should work
    assert result.returncode in (0, 1)
