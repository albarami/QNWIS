"""
Integration test for end-to-end audit trail generation.

Tests complete flow: orchestration -> verify node -> audit pack -> format node -> result.
"""

import json
import tempfile
from pathlib import Path

import pytest

from src.qnwis.data.deterministic.models import (
    Freshness,
    Provenance,
    QueryResult,
    Row,
)
from src.qnwis.orchestration.nodes.verify import verify_structure
from src.qnwis.orchestration.nodes.format import format_report
from src.qnwis.orchestration.schemas import OrchestrationTask, WorkflowState
from src.qnwis.agents.base import AgentReport, Evidence, Insight
from src.qnwis.verification.audit_store import (
    FileSystemAuditTrailStore,
    SQLiteAuditTrailStore,
)


@pytest.fixture
def temp_audit_dir(tmp_path):
    """Create temporary audit directory."""
    audit_dir = tmp_path / "audit_packs"
    audit_dir.mkdir()
    return audit_dir


@pytest.fixture
def temp_sqlite_db(tmp_path):
    """Create temporary SQLite database."""
    db_path = tmp_path / "audit.db"
    return str(db_path)


@pytest.fixture
def sample_agent_report():
    """Create sample AgentReport with evidence."""
    return AgentReport(
        agent="test_agent",
        findings=[
                Insight(
                    title="Workforce Retention Analysis",
                    summary="Retention rate is 85% in the oil and gas sector.",
                    metrics={"retention_rate": 0.85, "sample_size": 1500},
                    evidence=[
                    Evidence(
                        query_id="qid_abc123",
                        dataset_id="lmis_workforce",
                        locator="/data/workforce.csv",
                        fields=["sector", "retention_rate"],
                        freshness_as_of="2024-01-15",
                        freshness_updated_at="2024-01-15T10:00:00Z",
                    )
                ],
            )
        ],
    )


@pytest.fixture
def sample_query_results():
    """Create sample QueryResult objects."""
    return [
        QueryResult(
            query_id="qid_abc123",
            rows=[Row(data={"sector": "oil_gas", "retention_rate": 0.85})],
            unit="percent",
            provenance=Provenance(
                source="csv",
                dataset_id="lmis_workforce",
                locator="/data/workforce.csv",
                fields=["sector", "retention_rate"],
            ),
            freshness=Freshness(
                asof_date="2024-01-15",
                updated_at="2024-01-15T10:00:00Z",
            ),
        )
    ]


@pytest.fixture
def mock_verification_config(tmp_path, monkeypatch):
    """Mock verification config loading to use temp directory for audit."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    # Create minimal orchestration.yml with audit config
    audit_config = {
        "audit": {
            "persist": True,
            "pack_dir": str(tmp_path / "audit_packs"),
            "sqlite_path": str(tmp_path / "audit.db"),
        }
    }

    config_path = config_dir / "orchestration.yml"
    import yaml

    with open(config_path, "w") as f:
        yaml.dump(audit_config, f)

    # Patch config loading to use our temp config
    original_path = Path("src/qnwis/config/orchestration.yml")
    original_exists = Path.exists
    original_open = Path.open

    def mock_exists(self):
        if self == original_path:
            return True
        return original_exists(self)

    def mock_open(self, *args, **kwargs):
        if self == original_path:
            return open(config_path, *args, **kwargs)
        return original_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "exists", mock_exists)
    monkeypatch.setattr(Path, "open", mock_open)

    return tmp_path


class TestAuditEndToEnd:
    """End-to-end integration tests for audit trail."""

    def test_complete_audit_flow(
        self,
        temp_audit_dir,
        sample_agent_report,
        sample_query_results,
        mock_verification_config,
    ):
        """Test complete flow from agent report to audit pack."""
        # Setup workflow state
        task = OrchestrationTask(
            intent="pattern.anomalies",
            query_text="Test query",
            request_id="req-test-123",
        )

        state = {
            "task": task,
            "agent_output": sample_agent_report,
            "logs": [],
            "metadata": {
                "agent": "test_agent",
                "method": "analyze",
                "routing": {"mode": "single"},
                "agents": ["test_agent"],
                "timings": {"total_ms": 100},
            },
            "prefetch_cache": {
                "qid_abc123": sample_query_results[0],
            },
        }

        # Run verify node (generates audit trail)
        verify_result = verify_structure(state, strict=False)

        # Check that verify succeeded
        assert "error" not in verify_result or not verify_result["error"]

        # Check that audit metadata was attached
        metadata = verify_result.get("metadata", {})
        assert "audit_id" in metadata
        assert "audit_manifest" in metadata

        audit_id = metadata["audit_id"]
        audit_manifest = metadata["audit_manifest"]

        # Verify audit pack was written
        pack_dir = temp_audit_dir / audit_id
        assert pack_dir.exists()
        assert (pack_dir / "manifest.json").exists()
        assert (pack_dir / "narrative.md").exists()
        assert (pack_dir / "evidence").exists()
        assert (pack_dir / "reproducibility.py").exists()
        assert (pack_dir / "sources").exists()
        assert (pack_dir / "replay.json").exists()

        sources_dir = pack_dir / "sources"
        assert any(sources_dir.iterdir())

        replay_payload = json.loads((pack_dir / "replay.json").read_text())
        assert replay_payload["task"]["request_id"] == "req-test-123"
        assert replay_payload["query_ids"]

        # Verify manifest contents
        manifest_data = json.loads((pack_dir / "manifest.json").read_text())
        assert manifest_data["audit_id"] == audit_id
        assert manifest_data["request_id"] == "req-test-123"
        assert len(manifest_data["data_sources"]) > 0
        assert len(manifest_data["query_ids"]) > 0
        assert "digest_sha256" in manifest_data

        # Run format node (adds audit summary)
        format_result = format_report(verify_result)

        # Check that format succeeded
        assert "error" not in format_result or not format_result["error"]

        # Check that result contains audit fields
        result = format_result["agent_output"]
        assert result.audit_id == audit_id
        assert result.audit_manifest is not None

        # Check that Audit Summary section was added
        section_titles = [s.title for s in result.sections]
        assert "Audit Summary" in section_titles

    def test_audit_pack_integrity(
        self,
        temp_audit_dir,
        sample_agent_report,
        sample_query_results,
        mock_verification_config,
    ):
        """Test that audit pack passes integrity verification."""
        from src.qnwis.verification.audit_trail import AuditTrail

        # Setup and run verification
        task = OrchestrationTask(
            intent="pattern.anomalies",
            request_id="req-test-456",
        )

        state = {
            "task": task,
            "agent_output": sample_agent_report,
            "logs": [],
            "metadata": {
                "agent": "test_agent",
                "method": "analyze",
            },
            "prefetch_cache": {
                "qid_abc123": sample_query_results[0],
            },
        }

        verify_result = verify_structure(state, strict=False)
        audit_id = verify_result["metadata"]["audit_id"]

        # Verify pack integrity
        trail = AuditTrail(pack_dir=str(temp_audit_dir))
        is_valid, reasons = trail.verify_pack(audit_id)

        assert is_valid, f"Pack verification failed: {reasons}"
        assert len(reasons) == 0

    def test_audit_pack_indexed_in_sqlite(
        self,
        temp_audit_dir,
        temp_sqlite_db,
        sample_agent_report,
        sample_query_results,
        mock_verification_config,
    ):
        """Test that audit pack is indexed in SQLite database."""
        # Setup and run verification
        task = OrchestrationTask(
            intent="pattern.anomalies",
            request_id="req-test-789",
        )

        state = {
            "task": task,
            "agent_output": sample_agent_report,
            "logs": [],
            "metadata": {
                "agent": "test_agent",
                "method": "analyze",
            },
            "prefetch_cache": {
                "qid_abc123": sample_query_results[0],
            },
        }

        verify_result = verify_structure(state, strict=False)
        audit_id = verify_result["metadata"]["audit_id"]

        # Query SQLite store
        store = SQLiteAuditTrailStore(temp_sqlite_db)
        manifest = store.get(audit_id)

        assert manifest is not None
        assert manifest.audit_id == audit_id
        assert manifest.request_id == "req-test-789"

    def test_audit_pack_filesystem_discovery(
        self,
        temp_audit_dir,
        sample_agent_report,
        sample_query_results,
        mock_verification_config,
    ):
        """Test that audit packs can be discovered via filesystem."""
        # Setup and run verification
        task = OrchestrationTask(
            intent="pattern.anomalies",
            request_id="req-test-discover",
        )

        state = {
            "task": task,
            "agent_output": sample_agent_report,
            "logs": [],
            "metadata": {
                "agent": "test_agent",
                "method": "analyze",
            },
            "prefetch_cache": {
                "qid_abc123": sample_query_results[0],
            },
        }

        verify_result = verify_structure(state, strict=False)
        audit_id = verify_result["metadata"]["audit_id"]

        # Use filesystem store
        fs_store = FileSystemAuditTrailStore(str(temp_audit_dir))

        # List all audit packs
        audit_ids = fs_store.list_all()
        assert audit_id in audit_ids

        # Get pack path
        pack_path = fs_store.get_path(audit_id)
        assert pack_path is not None
        assert Path(pack_path).exists()

        # Load manifest
        manifest = fs_store.load_manifest(audit_id)
        assert manifest is not None
        assert manifest.audit_id == audit_id

    def test_audit_pack_reproducibility_snippet(
        self,
        temp_audit_dir,
        sample_agent_report,
        sample_query_results,
        mock_verification_config,
    ):
        """Test that reproducibility snippet contains correct query IDs."""
        # Setup and run verification
        task = OrchestrationTask(
            intent="pattern.anomalies",
            request_id="req-test-repro",
        )

        state = {
            "task": task,
            "agent_output": sample_agent_report,
            "logs": [],
            "metadata": {
                "agent": "test_agent",
                "method": "analyze",
            },
            "prefetch_cache": {
                "qid_abc123": sample_query_results[0],
            },
        }

        verify_result = verify_structure(state, strict=False)
        audit_id = verify_result["metadata"]["audit_id"]

        # Read reproducibility snippet
        pack_dir = temp_audit_dir / audit_id
        snippet_path = pack_dir / "reproducibility.py"
        snippet_content = snippet_path.read_text()

        # Verify snippet contains query IDs
        assert "qid_abc123" in snippet_content
        assert "DataAPI" in snippet_content
        assert "api.fetch(qid)" in snippet_content

    def test_audit_summary_in_final_report(
        self,
        temp_audit_dir,
        sample_agent_report,
        sample_query_results,
        mock_verification_config,
    ):
        """Test that Audit Summary section contains expected fields."""
        # Setup and run complete flow
        task = OrchestrationTask(
            intent="pattern.anomalies",
            request_id="req-test-summary",
        )

        state = {
            "task": task,
            "agent_output": sample_agent_report,
            "logs": [],
            "metadata": {
                "agent": "test_agent",
                "method": "analyze",
            },
            "prefetch_cache": {
                "qid_abc123": sample_query_results[0],
            },
        }

        verify_result = verify_structure(state, strict=False)
        format_result = format_report(verify_result)

        result = format_result["agent_output"]

        # Find Audit Summary section
        audit_section = next(
            (s for s in result.sections if s.title == "Audit Summary"), None
        )
        assert audit_section is not None

        # Check summary contents
        summary_text = audit_section.body_md
        assert "Audit ID" in summary_text
        assert "Top Sources" in summary_text
        assert "Integrity:" in summary_text
        assert "SHA-256:" in summary_text
        assert "Reproducibility:" in summary_text

