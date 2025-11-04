"""Unit tests for QNWIS MCP server tools (optional MCP suite)."""

from __future__ import annotations

import json
import os
from unittest.mock import patch

import pytest
from pytest import MonkeyPatch

from tools.mcp.qnwis_mcp import (
    GIT_SHOW_MAX_BYTES,
    GIT_TIMEOUT_S,
    MAX_FS_READ_BYTES,
    ROOT,
    _is_allowed,
    _load_allowlist,
    env_list,
    fs_read_text,
    git_diff,
    git_show,
    git_status,
    secrets_scan,
)

pytestmark = pytest.mark.mcp


class TestAllowlist:
    """Test allowlist functionality."""

    def test_load_allowlist_returns_list(self) -> None:
        """Verify _load_allowlist returns a list."""
        result = _load_allowlist()
        assert isinstance(result, list)
        assert len(result) > 0

    def test_is_allowed_readme(self) -> None:
        """Verify README.md is in the allowlist."""
        assert _is_allowed(str(ROOT / "README.md"))

    def test_is_allowed_src_directory(self) -> None:
        """Verify src directory is allowed."""
        assert _is_allowed(str(ROOT / "src"))

    def test_is_allowed_docs_directory(self) -> None:
        """Verify docs directory is allowed."""
        assert _is_allowed(str(ROOT / "docs"))

    @pytest.mark.skipif(os.name != "nt", reason="Windows path normalization is Windows-specific")
    def test_is_allowed_windows_case_insensitive(self) -> None:
        """Verify Windows-style case-insensitive paths are normalized."""
        lowered = str((ROOT / "README.md").resolve()).lower()
        assert _is_allowed(lowered)

    def test_is_not_allowed_external_data(self) -> None:
        """Verify external_data is NOT in allowlist."""
        assert not _is_allowed(str(ROOT / "external_data" / "some_file.csv"))


class TestFileRead:
    """Test fs_read_text tool."""

    def test_fs_read_text_reads_pyproject(self) -> None:
        """Verify fs_read_text can read pyproject.toml."""
        out = fs_read_text(str(ROOT / "pyproject.toml"))
        assert "pyproject.toml" in out["path"]
        assert isinstance(out["text"], str)
        assert "qnwis" in out["text"]

    def test_fs_read_text_reads_readme(self) -> None:
        """Verify fs_read_text can read README.md."""
        out = fs_read_text(str(ROOT / "README.md"))
        assert "README.md" in out["path"]
        assert isinstance(out["text"], str)
        assert "QNWIS" in out["text"]

    def test_fs_read_text_rejects_disallowed_path(self) -> None:
        """Verify fs_read_text rejects paths outside allowlist."""
        with pytest.raises(ValueError, match="Access denied"):
            fs_read_text(str(ROOT / "external_data" / "test.csv"))

    def test_fs_read_text_respects_max_bytes(self) -> None:
        """Verify fs_read_text respects max_bytes parameter."""
        out = fs_read_text(str(ROOT / "README.md"), max_bytes=100)
        assert len(out["text"]) <= 100

    def test_fs_read_text_rejects_negative_max_bytes(self) -> None:
        """Verify fs_read_text rejects non-positive max_bytes values."""
        with pytest.raises(ValueError, match="positive integer"):
            fs_read_text(str(ROOT / "README.md"), max_bytes=-1)

    def test_fs_read_text_enforces_upper_bound(self) -> None:
        """Verify fs_read_text rejects values above the configured cap."""
        with pytest.raises(ValueError, match="cannot exceed"):
            fs_read_text(str(ROOT / "README.md"), max_bytes=MAX_FS_READ_BYTES + 1)

    def test_fs_read_text_rejects_directory(self) -> None:
        """Verify fs_read_text refuses to read directories."""
        with pytest.raises(ValueError, match="Cannot read directory"):
            fs_read_text(str(ROOT / "src"))

    def test_fs_read_text_blocks_traversal(self) -> None:
        """Verify fs_read_text blocks parent directory traversal attempts."""
        with pytest.raises(ValueError, match="Access denied"):
            fs_read_text("../README.md")


class TestGitOperations:
    """Test git-related tools."""

    def test_git_status_returns_status(self, monkeypatch: MonkeyPatch) -> None:
        """Verify git_status returns status output without invoking real git."""

        def fake_check_output(command: list[str], **kwargs: object) -> str:
            assert "status" in command
            assert kwargs.get("timeout") == GIT_TIMEOUT_S
            return " M docs/README.md\n"

        monkeypatch.setattr("tools.mcp.qnwis_mcp.subprocess.check_output", fake_check_output)

        result = git_status()
        assert "status" in result
        assert isinstance(result["status"], str)
        assert "docs/README.md" in result["status"]

    def test_git_diff_returns_list(self, monkeypatch: MonkeyPatch) -> None:
        """Verify git_diff returns list of files."""

        def fake_check_output(command: list[str], **kwargs: object) -> str:
            assert command[-2:] == ["--name-only", "HEAD"]
            assert kwargs.get("timeout") == GIT_TIMEOUT_S
            return "a.txt\nb.txt\n"

        monkeypatch.setattr("tools.mcp.qnwis_mcp.subprocess.check_output", fake_check_output)

        result = git_diff("HEAD")
        assert "diff_files" in result
        assert isinstance(result["diff_files"], list)
        assert result["diff_files"] == ["a.txt", "b.txt"]

    def test_git_diff_with_custom_target(self, monkeypatch: MonkeyPatch) -> None:
        """Verify git_diff accepts custom target."""
        # Use 'main' to confirm the target is forwarded correctly.

        def fake_check_output(command: list[str], **kwargs: object) -> str:
            assert command[-1] == "main"
            assert kwargs.get("timeout") == GIT_TIMEOUT_S
            return "c.txt\n"

        monkeypatch.setattr("tools.mcp.qnwis_mcp.subprocess.check_output", fake_check_output)

        result = git_diff("main")
        assert "diff_files" in result
        assert isinstance(result["diff_files"], list)
        assert result["diff_files"] == ["c.txt"]

    def test_git_show_returns_file_contents(self, monkeypatch: MonkeyPatch) -> None:
        """Verify git_show returns file contents within the size limit."""

        def fake_run_git_command(*args: str, **kwargs: object) -> bytes:
            assert args[0] == "show"
            return b"sample text"

        monkeypatch.setattr("tools.mcp.qnwis_mcp._run_git_command", fake_run_git_command)

        result = git_show(str(ROOT / "README.md"))
        assert result["path"].endswith("README.md")
        assert result["rev"] == "HEAD"
        assert isinstance(result["text"], str)
        assert isinstance(result["truncated"], bool)
        assert len(result["text"]) <= GIT_SHOW_MAX_BYTES
        assert result["text"] == "sample text"
        assert result["truncated"] is False

    def test_git_show_rejects_disallowed_path(self) -> None:
        """Verify git_show honors the allowlist."""
        with pytest.raises(ValueError, match="Access denied"):
            git_show(str(ROOT / "external_data" / "secret.txt"))


class TestSecretsScan:
    """Test secrets_scan tool."""

    def test_secrets_scan_returns_results(self) -> None:
        """Verify secrets_scan returns findings and count."""
        result = secrets_scan()
        assert "findings" in result
        assert "count" in result
        assert isinstance(result["findings"], list)
        assert isinstance(result["count"], int)
        assert result["count"] == len(result["findings"])

    def test_secrets_scan_excludes_directories(self) -> None:
        """Verify secrets_scan excludes specified directories."""
        result = secrets_scan(glob_exclude=["src/data/apis"])
        assert "count" in result
        assert result["count"] >= 0
        # Verify no results from excluded path
        for finding in result["findings"]:
            assert not finding["file"].startswith("src/data/apis")

    def test_secrets_scan_redacts_matches(self) -> None:
        """Verify secrets_scan redacts matched values."""
        result = secrets_scan()
        for finding in result["findings"]:
            assert "match" in finding
            if finding["match"]:
                assert finding["match"].endswith("...")
            assert finding.get("strict") is False

    def test_secrets_scan_strict_mode_flags_findings(self) -> None:
        """Verify secrets_scan marks findings when strict mode is enabled."""
        result = secrets_scan(secrets_scan_strict=True)
        for finding in result["findings"]:
            assert finding.get("strict") is True


@patch("tools.mcp.qnwis_mcp.subprocess.check_output", return_value="")
def test_git_status_mocked(pco):
    """Test git_status with mocked subprocess."""
    out = git_status()
    assert "status" in out


@patch("tools.mcp.qnwis_mcp.subprocess.check_output", return_value="a.txt\nb.txt\n")
def test_git_diff_mocked(pco):
    """Test git_diff with mocked subprocess."""
    out = git_diff()
    assert out["diff_files"] == ["a.txt", "b.txt"]


class TestEnvList:
    """Test env_list tool."""

    def test_env_list_returns_names_only(self) -> None:
        """Verify env_list returns environment variable names."""
        result = env_list()
        assert "env_vars" in result
        assert isinstance(result["env_vars"], list)

    def test_env_list_prefix_filter(self, monkeypatch: MonkeyPatch) -> None:
        """Verify env_list filters by SAFE_ENV_PREFIXES."""
        monkeypatch.setenv("QNWIS_TEST", "secret_value")
        result = env_list()
        names = result["env_vars"]
        assert "QNWIS_TEST" in names
        # Verify only names are returned, not values
        assert "secret_value" not in str(result)

    def test_env_list_custom_prefix(self, monkeypatch: MonkeyPatch) -> None:
        """Verify env_list accepts custom prefix."""
        monkeypatch.setenv("CUSTOM_VAR", "value")
        result = env_list(prefix="CUSTOM_")
        names = result["env_vars"]
        assert "CUSTOM_VAR" in names

    def test_env_list_no_values_returned(self, monkeypatch: MonkeyPatch) -> None:
        """Verify env_list NEVER returns values."""
        monkeypatch.setenv("QNWIS_SECRET", "super_secret_api_key_12345")
        result = env_list()
        # Convert entire result to string and verify secret is not present
        result_str = json.dumps(result)
        assert "super_secret_api_key_12345" not in result_str
        assert "QNWIS_SECRET" in result["env_vars"]
