"""Tests for the PowerShell secret scanner script behaviour."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest


def _powershell_executable() -> str | None:
    """Return available PowerShell executable or None."""
    for candidate in ("pwsh", "powershell", "powershell.exe"):
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    return None


def _ensure_tools_available() -> str:
    """Skip tests if required command line tools are missing."""
    if not shutil.which("git"):
        pytest.skip("git executable not available for secret scan tests")
    exe = _powershell_executable()
    if not exe:
        pytest.skip("PowerShell executable not available for secret scan tests")
    return exe


def _stage_and_commit(repo: Path) -> None:
    """Stage and commit all files within the temporary git repo."""
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(
        ["git", "config", "user.email", "ci@example.com"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "CI"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )


def _prepare_repo(tmp_path: Path) -> tuple[Path, Path]:
    """Create temp repo with secret_scan script copied in."""
    repo = tmp_path / "repo"
    repo.mkdir()
    scripts_dir = repo / "scripts"
    scripts_dir.mkdir()
    src_script = Path(__file__).resolve().parents[2] / "scripts" / "secret_scan.ps1"
    dest_script = scripts_dir / "secret_scan.ps1"
    dest_script.write_text(src_script.read_text(encoding="utf-8"), encoding="utf-8")
    return repo, dest_script


def test_secret_scan_allowlist_trims_blank_lines(tmp_path):
    """Allowlist filters ignore comments/blank lines and prevent false flags."""
    pwsh = _ensure_tools_available()
    repo, script_path = _prepare_repo(tmp_path)

    allowlist = repo / "scripts" / "allowlist.txt"
    allowlist.write_text("# comment line\n\n   SKIPME[0-9]+\n", encoding="utf-8")

    data_file = repo / "data.txt"
    data_file.write_text("API_KEY=SKIPME1234567890123456789012345\n", encoding="utf-8")

    _stage_and_commit(repo)

    result = subprocess.run(
        [
            pwsh,
            "-NoLogo",
            "-NoProfile",
            "-File",
            str(script_path),
            "-AllowlistFile",
            "scripts/allowlist.txt",
        ],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "Loaded 1 allowlist patterns" in result.stdout
    assert "Secret scan: CLEAN" in result.stdout


def test_secret_scan_reports_diff_on_findings(tmp_path):
    """Scanner outputs diff-style context for flagged secrets."""
    pwsh = _ensure_tools_available()
    repo, script_path = _prepare_repo(tmp_path)

    allowlist = repo / "scripts" / "allowlist.txt"
    allowlist.write_text("", encoding="utf-8")

    bad_file = repo / "app.py"
    bad_file.write_text("token ABCDEFGHIJKLMNOPQRSTUVWXYZ123456\n", encoding="utf-8")

    _stage_and_commit(repo)

    result = subprocess.run(
        [
            pwsh,
            "-NoLogo",
            "-NoProfile",
            "-File",
            str(script_path),
            "-AllowlistFile",
            "scripts/allowlist.txt",
        ],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Secret scan: ISSUES FOUND" in result.stdout
    assert "@@ app.py:1 @@" in result.stdout
    assert "+ token ABCDEFGHIJKLMNOPQRSTUVWXYZ123456" in result.stdout
