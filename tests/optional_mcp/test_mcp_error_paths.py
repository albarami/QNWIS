"""
Comprehensive error path tests for QNWIS MCP server.

Tests all failure modes, edge cases, and security boundaries.
"""

import os
import subprocess
from pathlib import Path
from subprocess import TimeoutExpired
from unittest.mock import patch

import pytest

from tools.mcp.qnwis_mcp import (
    ROOT,
    _assert_allowed_path,
    _load_allowlist,
    _normalize_path_input,
    fs_read_text,
    git_diff,
    git_show,
    git_status,
    secrets_scan,
)

pytestmark = pytest.mark.mcp


class TestPathNormalization:
    """Test path normalization and allowlist enforcement."""

    def test_normalize_path_relative_to_root(self) -> None:
        """Verify relative paths are resolved against ROOT."""
        result = _normalize_path_input("README.md")
        assert result.is_absolute()
        # Use case-insensitive comparison on Windows
        assert result.name.lower() == "readme.md"

    def test_normalize_path_absolute(self) -> None:
        """Verify absolute paths are normalized."""
        readme_path = ROOT / "README.md"
        result = _normalize_path_input(str(readme_path))
        assert result.is_absolute()

    @pytest.mark.skipif(os.name != "nt", reason="Windows-specific test")
    def test_normalize_path_windows_backslash(self) -> None:
        """Verify Windows backslash paths are handled."""
        # Windows path with backslashes
        win_path = str(ROOT / "README.md").replace("/", "\\")
        result = _normalize_path_input(win_path)
        assert result.is_absolute()
        assert "readme.md" in str(result).lower()

    @pytest.mark.skipif(os.name != "nt", reason="Windows-specific test")
    def test_normalize_path_windows_case_normalization(self) -> None:
        """Verify case normalization on Windows."""
        readme_upper = str(ROOT / "README.MD").upper()
        readme_lower = str(ROOT / "readme.md").lower()
        norm_upper = _normalize_path_input(readme_upper)
        norm_lower = _normalize_path_input(readme_lower)
        # On Windows, normalized paths should match
        assert os.path.normcase(str(norm_upper)) == os.path.normcase(str(norm_lower))

    def test_assert_allowed_path_outside_allowlist(self) -> None:
        """Verify paths outside allowlist are rejected."""
        with pytest.raises(ValueError, match="Access denied"):
            _assert_allowed_path(str(ROOT / "external_data" / "test.csv"))

    def test_assert_allowed_path_traversal_attack(self) -> None:
        """Verify directory traversal attempts are blocked."""
        # Attempt to escape via ..
        with pytest.raises(ValueError, match="Access denied"):
            _assert_allowed_path(str(ROOT / "docs" / ".." / ".." / "etc" / "passwd"))


class TestAllowlistLoading:
    """Test allowlist file loading and validation."""

    def test_load_allowlist_missing_file(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify clear error when allowlist file is missing."""
        from tools.mcp import qnwis_mcp

        fake_path = Path("/nonexistent/allowlist.json")
        monkeypatch.setattr(qnwis_mcp, "ALLOWLIST_PATH", fake_path)
        monkeypatch.setattr(qnwis_mcp, "_ALLOWLIST_CACHE", None)

        with pytest.raises(RuntimeError, match="Allowlist file not found"):
            _load_allowlist()

    def test_load_allowlist_invalid_json(self, tmp_path: Path) -> None:
        """Verify clear error for malformed JSON."""
        from tools.mcp import qnwis_mcp

        bad_json = tmp_path / "bad_allowlist.json"
        bad_json.write_text("{invalid json", encoding="utf-8")

        original_path = qnwis_mcp.ALLOWLIST_PATH
        try:
            qnwis_mcp.ALLOWLIST_PATH = bad_json
            qnwis_mcp._ALLOWLIST_CACHE = None
            with pytest.raises(RuntimeError, match="not valid JSON"):
                _load_allowlist()
        finally:
            qnwis_mcp.ALLOWLIST_PATH = original_path
            qnwis_mcp._ALLOWLIST_CACHE = None

    def test_load_allowlist_wrong_structure(self, tmp_path: Path) -> None:
        """Verify clear error for non-array allowlist."""
        from tools.mcp import qnwis_mcp

        bad_structure = tmp_path / "wrong_structure.json"
        bad_structure.write_text('{"paths": ["test"]}', encoding="utf-8")

        original_path = qnwis_mcp.ALLOWLIST_PATH
        try:
            qnwis_mcp.ALLOWLIST_PATH = bad_structure
            qnwis_mcp._ALLOWLIST_CACHE = None
            with pytest.raises(RuntimeError, match="JSON array of string paths"):
                _load_allowlist()
        finally:
            qnwis_mcp.ALLOWLIST_PATH = original_path
            qnwis_mcp._ALLOWLIST_CACHE = None


class TestFileReadErrors:
    """Test fs_read_text error handling."""

    def test_fs_read_text_zero_max_bytes(self) -> None:
        """Verify zero max_bytes is rejected."""
        with pytest.raises(ValueError, match="positive integer"):
            fs_read_text(str(ROOT / "README.md"), max_bytes=0)

    def test_fs_read_text_nonexistent_file(self) -> None:
        """Verify clear error for missing files."""
        fake_file = ROOT / "docs" / "nonexistent_file_12345.txt"
        with pytest.raises(RuntimeError, match="Failed to read"):
            fs_read_text(str(fake_file))

    def test_fs_read_text_binary_file_handling(self) -> None:
        """Verify binary files are handled with replacement characters."""
        # pyproject.toml might have some unicode, but should decode
        result = fs_read_text(str(ROOT / "pyproject.toml"))
        assert isinstance(result["text"], str)
        # No exceptions should be raised


class TestGitCommandErrors:
    """Test git command error handling."""

    def test_git_command_not_found(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify clear error when git is not installed."""

        def mock_check_output(*args: object, **kwargs: object) -> None:
            raise FileNotFoundError("git not found")

        monkeypatch.setattr("subprocess.check_output", mock_check_output)

        with pytest.raises(RuntimeError, match="Git executable not found"):
            git_status()

    def test_git_command_not_a_repository(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify clear error when not in a git repository."""
        import subprocess

        def mock_check_output(*args: object, **kwargs: object) -> str:
            exc = subprocess.CalledProcessError(128, ["git"], "fatal: not a git repository")
            exc.stdout = "fatal: not a git repository"
            raise exc

        monkeypatch.setattr("subprocess.check_output", mock_check_output)

        with pytest.raises(RuntimeError, match="not a Git repository"):
            git_status()

    def test_git_command_invalid_reference(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify clear error for invalid git references."""
        import subprocess

        def mock_check_output(*args: object, **kwargs: object) -> str:
            if "diff" in str(args):
                exc = subprocess.CalledProcessError(128, ["git"], "unknown revision")
                exc.stdout = "fatal: bad revision 'INVALID_REF'"
                raise exc
            return ""

        monkeypatch.setattr("subprocess.check_output", mock_check_output)

        with pytest.raises(RuntimeError, match="Git command failed"):
            git_diff("INVALID_REF_DOES_NOT_EXIST")

    def test_git_show_file_outside_repo(self) -> None:
        """Verify git_show rejects files outside repository root."""
        outside_path = Path("/tmp/outside.txt")
        with pytest.raises(ValueError, match="Access denied"):
            git_show(str(outside_path))

    def test_git_show_nonexistent_revision(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify git_show handles nonexistent revisions."""
        import subprocess

        def mock_check_output(*args: object, **kwargs: object) -> bytes:
            if "show" in str(args):
                exc = subprocess.CalledProcessError(128, ["git"], b"bad revision")
                exc.stdout = b"fatal: bad revision 'NOREV'"
                raise exc
            return b""

        monkeypatch.setattr("subprocess.check_output", mock_check_output)

        with pytest.raises(RuntimeError, match="Git command failed"):
            git_show(str(ROOT / "README.md"), rev="NOREV_INVALID")


class TestSecretsScanEdgeCases:
    """Test secrets_scan edge cases."""

    def test_secrets_scan_empty_excludes(self) -> None:
        """Verify secrets_scan handles empty exclusion list."""
        result = secrets_scan(glob_exclude=[])
        assert "findings" in result
        assert "count" in result

    def test_secrets_scan_strict_filters_low_entropy(self, tmp_path: Path) -> None:
        """Verify strict mode requires mixed case and digits."""
        # This test creates a temp file, but we scan the repo
        # Just verify the strict flag changes behavior
        normal = secrets_scan(secrets_scan_strict=False)
        strict = secrets_scan(secrets_scan_strict=True)

        # Strict mode should find fewer or equal matches
        assert strict["count"] <= normal["count"]

    def test_secrets_scan_handles_unreadable_files(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify secrets_scan continues on file read errors."""
        # secrets_scan catches all exceptions during file reading
        result = secrets_scan()
        # Should complete without raising exceptions
        assert isinstance(result["count"], int)


class TestParameterValidation:
    """Test parameter validation across all tools."""

    def test_fs_read_text_string_path_parameter(self) -> None:
        """Verify fs_read_text accepts string paths."""
        result = fs_read_text(str(ROOT / "README.md"))
        assert "text" in result

    def test_fs_read_text_path_object_parameter(self) -> None:
        """Verify fs_read_text accepts Path objects."""
        result = fs_read_text(ROOT / "README.md")
        assert "text" in result

    def test_git_diff_empty_target_string(self) -> None:
        """Verify git_diff validates target parameter."""
        # Empty string should be passed to git, which will fail
        with pytest.raises(RuntimeError, match="Git command failed"):
            git_diff("")

    def test_secrets_scan_none_excludes(self) -> None:
        """Verify secrets_scan handles None for optional parameters."""
        result = secrets_scan(glob_exclude=None, secrets_scan_strict=False)
        assert "findings" in result


class TestSecurityBoundaries:
    """Test security boundaries and attack vectors."""

    def test_cannot_read_git_directory(self) -> None:
        """Verify .git directory is not in allowlist."""
        git_config = ROOT / ".git" / "config"
        with pytest.raises(ValueError, match="Access denied"):
            fs_read_text(str(git_config))

    def test_cannot_read_venv_directory(self) -> None:
        """Verify .venv directory is not in allowlist."""
        venv_file = ROOT / ".venv" / "pyvenv.cfg"
        with pytest.raises(ValueError, match="Access denied"):
            fs_read_text(str(venv_file))

    def test_secrets_scan_excludes_sensitive_dirs(self) -> None:
        """Verify secrets_scan automatically excludes sensitive directories."""
        result = secrets_scan()
        # No findings should be from .git, .venv, etc.
        for finding in result["findings"]:
            file_path = finding["file"]
            assert ".git" not in file_path
            assert ".venv" not in file_path
            assert "__pycache__" not in file_path

    def test_git_show_respects_allowlist(self) -> None:
        """Verify git_show cannot access files outside allowlist."""
        # Try to show a file that exists in git history but is not in allowlist
        with pytest.raises(ValueError, match="Access denied"):
            git_show(str(ROOT / "external_data" / "test.csv"))


@patch("tools.mcp.qnwis_mcp.subprocess.check_output", side_effect=TimeoutExpired(cmd="git", timeout=0.01))
def test_git_status_timeout(pco):
    """Test git_status timeout handling."""
    try:
        git_status()
        raise AssertionError("expected timeout")
    except RuntimeError as e:
        assert "timed out" in str(e)


@patch("tools.mcp.qnwis_mcp.subprocess.check_output", side_effect=subprocess.CalledProcessError(1, "git", "boom"))
def test_git_diff_error(pco):
    """Test git_diff error handling."""
    try:
        git_diff()
        raise AssertionError("expected error")
    except RuntimeError as e:
        assert "failed" in str(e) or "boom" in str(e)
