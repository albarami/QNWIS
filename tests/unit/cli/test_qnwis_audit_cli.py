"""
Unit tests for QNWIS audit CLI commands.

Tests show, list, export, verify, and prune commands.
"""

import argparse
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from src.qnwis.cli.qnwis_audit import (
    cmd_export,
    cmd_list,
    cmd_show,
    cmd_verify,
    main,
)
from src.qnwis.verification.audit_store import FileSystemAuditTrailStore
from src.qnwis.verification.audit_trail import AuditManifest, AuditTrail


@pytest.fixture
def sample_manifest() -> AuditManifest:
    """Create a sample audit manifest for CLI testing."""
    return AuditManifest(
        audit_id="cli-test-123",
        created_at="2024-01-15T10:00:00Z",
        request_id="req-cli-001",
        registry_version="v1.0.0",
        code_version="abc123",
        data_sources=["qnwis_labor", "wb_labor"],
        query_ids=["labor_supply", "unemployment_rate"],
        freshness={
            "qnwis_labor": "2023-12-31",
            "wb_labor": "2023-12-31",
        },
        citations={
            "ok": True,
            "total_numbers": 10,
            "cited_numbers": 10,
            "sources_used": {"labor_supply": 6, "unemployment_rate": 4},
        },
        verification={
            "ok": True,
            "issues_count": 0,
            "redactions_applied": 0,
            "stats": {"L2/ok": 5},
        },
        orchestration={
            "routing": "national_strategy",
            "agents": ["pattern_detective"],
        },
        reproducibility={
            "snippet": "# Python code",
            "params_hash": "xyz789",
        },
        digest_sha256="a" * 64,
    )


@pytest.fixture
def temp_pack_dir_with_manifest(sample_manifest: AuditManifest) -> Path:
    """Create temporary pack directory with a sample manifest."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pack_dir = Path(tmpdir)

        # Create pack using FileSystemAuditTrailStore
        store = FileSystemAuditTrailStore(str(pack_dir))
        store.index(sample_manifest)

        yield pack_dir


class TestCmdShow:
    """Tests for cmd_show function."""

    def test_cli_show_and_verify_pack(
        self,
        sample_manifest: AuditManifest,
        temp_pack_dir_with_manifest: Path,
        capsys,
    ) -> None:
        """Test that show command displays manifest details."""
        args = argparse.Namespace(
            audit_id=sample_manifest.audit_id,
            json=False,
        )

        with patch("src.qnwis.cli.qnwis_audit._get_audit_config") as mock_config:
            mock_config.return_value = {
                "pack_dir": str(temp_pack_dir_with_manifest),
                "sqlite_path": None,
                "hmac_env": None,
                "retention_days": 90,
            }

            result = cmd_show(args)

        assert result == 0

        captured = capsys.readouterr()
        assert "Audit Manifest:" in captured.out
        assert sample_manifest.audit_id in captured.out
        assert sample_manifest.request_id in captured.out
        assert "qnwis_labor" in captured.out
        assert "Citations:" in captured.out
        assert "Verification:" in captured.out

    def test_show_json_output(
        self,
        sample_manifest: AuditManifest,
        temp_pack_dir_with_manifest: Path,
        capsys,
    ) -> None:
        """Test that show command outputs valid JSON when --json flag is used."""
        args = argparse.Namespace(
            audit_id=sample_manifest.audit_id,
            json=True,
        )

        with patch("src.qnwis.cli.qnwis_audit._get_audit_config") as mock_config:
            mock_config.return_value = {
                "pack_dir": str(temp_pack_dir_with_manifest),
                "sqlite_path": None,
                "hmac_env": None,
                "retention_days": 90,
            }

            result = cmd_show(args)

        assert result == 0

        captured = capsys.readouterr()
        # Should be valid JSON
        manifest_data = json.loads(captured.out)
        assert manifest_data["audit_id"] == sample_manifest.audit_id

    def test_show_nonexistent_pack(
        self,
        temp_pack_dir_with_manifest: Path,
        capsys,
    ) -> None:
        """Test that show command handles nonexistent audit ID."""
        args = argparse.Namespace(
            audit_id="nonexistent-id",
            json=False,
        )

        with patch("src.qnwis.cli.qnwis_audit._get_audit_config") as mock_config:
            mock_config.return_value = {
                "pack_dir": str(temp_pack_dir_with_manifest),
                "sqlite_path": None,
                "hmac_env": None,
                "retention_days": 90,
            }

            result = cmd_show(args)

        assert result == 1

        captured = capsys.readouterr()
        assert "ERROR" in captured.out
        assert "not found" in captured.out


class TestCmdList:
    """Tests for cmd_list function."""

    def test_cli_list_limits(
        self,
        sample_manifest: AuditManifest,
        temp_pack_dir_with_manifest: Path,
        capsys,
    ) -> None:
        """Test that list command displays audit runs."""
        args = argparse.Namespace(
            limit=20,
        )

        with patch("src.qnwis.cli.qnwis_audit._get_audit_config") as mock_config:
            mock_config.return_value = {
                "pack_dir": str(temp_pack_dir_with_manifest),
                "sqlite_path": None,
                "hmac_env": None,
                "retention_days": 90,
            }

            result = cmd_list(args)

        assert result == 0

        captured = capsys.readouterr()
        assert "Recent Audit Runs" in captured.out
        assert sample_manifest.audit_id in captured.out
        assert "Total: 1 audit pack(s)" in captured.out

    def test_list_empty_directory(
        self,
        capsys,
    ) -> None:
        """Test that list command handles empty pack directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            args = argparse.Namespace(
                limit=20,
            )

            with patch("src.qnwis.cli.qnwis_audit._get_audit_config") as mock_config:
                mock_config.return_value = {
                    "pack_dir": str(tmpdir),
                    "sqlite_path": None,
                    "hmac_env": None,
                    "retention_days": 90,
                }

                result = cmd_list(args)

            assert result == 0

            captured = capsys.readouterr()
            assert "No audit packs found" in captured.out


class TestCmdExport:
    """Tests for cmd_export function."""

    def test_export_as_zip(
        self,
        sample_manifest: AuditManifest,
        temp_pack_dir_with_manifest: Path,
        capsys,
    ) -> None:
        """Test exporting audit pack as zip file."""
        with tempfile.TemporaryDirectory() as output_dir:
            output_path = Path(output_dir) / "export"

            args = argparse.Namespace(
                audit_id=sample_manifest.audit_id,
                out=str(output_path),
                format="zip",
            )

            with patch("src.qnwis.cli.qnwis_audit._get_audit_config") as mock_config:
                mock_config.return_value = {
                    "pack_dir": str(temp_pack_dir_with_manifest),
                    "sqlite_path": None,
                    "hmac_env": None,
                    "retention_days": 90,
                }

                result = cmd_export(args)

            assert result == 0

            captured = capsys.readouterr()
            assert "Exported to:" in captured.out

            # Check that zip file was created
            zip_path = Path(output_dir) / "export.zip"
            assert zip_path.exists()

    def test_export_nonexistent_pack(
        self,
        temp_pack_dir_with_manifest: Path,
        capsys,
    ) -> None:
        """Test that export command handles nonexistent audit ID."""
        with tempfile.TemporaryDirectory() as output_dir:
            args = argparse.Namespace(
                audit_id="nonexistent-id",
                out=str(output_dir),
                format="zip",
            )

            with patch("src.qnwis.cli.qnwis_audit._get_audit_config") as mock_config:
                mock_config.return_value = {
                    "pack_dir": str(temp_pack_dir_with_manifest),
                    "sqlite_path": None,
                    "hmac_env": None,
                    "retention_days": 90,
                }

                result = cmd_export(args)

            assert result == 1

            captured = capsys.readouterr()
            assert "ERROR" in captured.out


class TestCmdVerify:
    """Tests for cmd_verify function."""

    def test_verify_valid_pack(
        self,
        capsys,
    ) -> None:
        """Test verifying a valid audit pack."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pack_dir = Path(tmpdir)

            # Create a valid pack
            from src.qnwis.data.deterministic.models import (
                Freshness,
                Provenance,
                QueryResult,
                Row,
            )
            from src.qnwis.verification.citation_enforcer import CitationReport
            from src.qnwis.verification.schemas import VerificationSummary

            trail = AuditTrail(pack_dir=str(pack_dir))

            qresults = [
                QueryResult(
                    query_id="test_query",
                    rows=[Row(data={"year": 2023, "value": 100})],
                    unit="count",
                    provenance=Provenance(
                        source="csv",
                        dataset_id="test_data",
                        locator="/data/test.csv",
                        fields=["year", "value"],
                    ),
                    freshness=Freshness(asof_date="2023-12-31"),
                )
            ]

            verification = VerificationSummary(ok=True, issues=[])
            citations = CitationReport(
                ok=True,
                total_numbers=5,
                cited_numbers=5,
            )

            manifest = trail.generate_trail(
                response_md="Test response",
                qresults=qresults,
                verification=verification,
                citations=citations,
                orchestration_meta={},
                code_version="abc123",
                registry_version="v1.0.0",
                request_id="req-001",
            )

            final_manifest = trail.write_pack(
                manifest=manifest,
                response_md="Test response",
                qresults=qresults,
                citations=citations,
                result_report=None,
            )

            # Verify the pack
            args = argparse.Namespace(
                audit_id=final_manifest.audit_id,
                path=None,
            )

            with patch("src.qnwis.cli.qnwis_audit._get_audit_config") as mock_config:
                mock_config.return_value = {
                    "pack_dir": str(pack_dir),
                    "sqlite_path": None,
                    "hmac_env": None,
                    "retention_days": 90,
                }

                result = cmd_verify(args)

            assert result == 0

            captured = capsys.readouterr()
            assert "[OK]" in captured.out
            assert final_manifest.audit_id in captured.out


class TestMainFunction:
    """Tests for main() CLI entry point."""

    def test_main_no_command(
        self,
        capsys,
    ) -> None:
        """Test that main prints help when no command is provided."""
        with patch("sys.argv", ["qnwis_audit"]):
            result = main()

        assert result == 1

        captured = capsys.readouterr()
        # Should display help or usage information
        assert "usage:" in captured.out.lower() or "command" in captured.out.lower()
