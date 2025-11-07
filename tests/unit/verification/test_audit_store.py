"""
Unit tests for audit trail storage backends.

Tests SQLite indexing and filesystem storage for audit manifests.
"""

import tempfile
from pathlib import Path

import pytest

from src.qnwis.verification.audit_store import (
    FileSystemAuditTrailStore,
    SQLiteAuditTrailStore,
)
from src.qnwis.verification.audit_trail import AuditManifest


@pytest.fixture
def sample_manifest() -> AuditManifest:
    """Create a sample audit manifest for testing."""
    return AuditManifest(
        audit_id="test-audit-123",
        created_at="2024-01-15T10:00:00Z",
        request_id="req-001",
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
        pack_root="/tmp/audit_packs/test-audit-123",
        digest_sha256="a" * 64,
        hmac_sha256="b" * 64,
    )


@pytest.fixture
def temp_db_path() -> Path:
    """Create temporary database file."""
    import gc
    import time

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = Path(tmp.name)
    yield db_path
    # Cleanup - force garbage collection to close connections
    gc.collect()
    time.sleep(0.1)  # Give Windows time to release file handles

    # Try to remove files, ignore errors if still locked
    try:
        if db_path.exists():
            db_path.unlink()
    except (PermissionError, OSError):
        pass

    # Also remove WAL files if they exist
    for wal_file in [db_path.with_suffix(".db-wal"), db_path.with_suffix(".db-shm")]:
        try:
            if wal_file.exists():
                wal_file.unlink()
        except (PermissionError, OSError):
            pass


@pytest.fixture
def temp_fs_dir() -> Path:
    """Create temporary filesystem directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


class TestSQLiteAuditTrailStore:
    """Tests for SQLite storage backend."""

    def test_sqlite_upsert_get_list(
        self,
        temp_db_path: Path,
        sample_manifest: AuditManifest,
    ) -> None:
        """Test upsert, get, and list operations."""
        store = SQLiteAuditTrailStore(str(temp_db_path))

        # Upsert manifest
        store.upsert(sample_manifest)

        # Retrieve by ID
        retrieved = store.get(sample_manifest.audit_id)
        assert retrieved is not None
        assert retrieved.audit_id == sample_manifest.audit_id
        assert retrieved.request_id == sample_manifest.request_id
        assert retrieved.query_ids == sample_manifest.query_ids

        # List recent
        recent = store.list_recent(limit=10)
        assert len(recent) == 1
        assert recent[0].audit_id == sample_manifest.audit_id

    def test_sqlite_update_existing(
        self,
        temp_db_path: Path,
        sample_manifest: AuditManifest,
    ) -> None:
        """Test that upsert updates existing records."""
        store = SQLiteAuditTrailStore(str(temp_db_path))

        # Insert initial
        store.upsert(sample_manifest)

        # Create updated version
        updated_dict = sample_manifest.to_dict()
        updated_dict["code_version"] = "updated_version_xyz"
        updated_manifest = AuditManifest.from_dict(updated_dict)

        # Upsert updated version
        store.upsert(updated_manifest)

        # Should still have only one record
        recent = store.list_recent(limit=10)
        assert len(recent) == 1

        # Should have updated value
        retrieved = store.get(sample_manifest.audit_id)
        assert retrieved is not None
        assert retrieved.code_version == "updated_version_xyz"

    def test_sqlite_get_nonexistent(
        self,
        temp_db_path: Path,
    ) -> None:
        """Test that get returns None for nonexistent audit ID."""
        store = SQLiteAuditTrailStore(str(temp_db_path))

        result = store.get("nonexistent-id")
        assert result is None

    def test_sqlite_search_by_request_id(
        self,
        temp_db_path: Path,
        sample_manifest: AuditManifest,
    ) -> None:
        """Test search by request ID."""
        store = SQLiteAuditTrailStore(str(temp_db_path))

        # Insert manifest
        store.upsert(sample_manifest)

        # Search by request ID
        results = store.search_by_request_id(sample_manifest.request_id)
        assert len(results) == 1
        assert results[0].audit_id == sample_manifest.audit_id

        # Search for nonexistent request ID
        results = store.search_by_request_id("nonexistent-request")
        assert len(results) == 0

    def test_sqlite_list_failed_verifications(
        self,
        temp_db_path: Path,
        sample_manifest: AuditManifest,
    ) -> None:
        """Test listing failed verifications."""
        store = SQLiteAuditTrailStore(str(temp_db_path))

        # Create passing manifest
        store.upsert(sample_manifest)

        # Create failing manifest
        failing_dict = sample_manifest.to_dict()
        failing_dict["audit_id"] = "failed-audit-456"
        failing_dict["verification"]["ok"] = False
        failing_dict["verification"]["issues_count"] = 3
        failing_manifest = AuditManifest.from_dict(failing_dict)
        store.upsert(failing_manifest)

        # List failed verifications
        failed = store.list_failed_verifications(limit=10)
        assert len(failed) == 1
        assert failed[0].audit_id == "failed-audit-456"

    def test_sqlite_delete(
        self,
        temp_db_path: Path,
        sample_manifest: AuditManifest,
    ) -> None:
        """Test deleting manifest."""
        store = SQLiteAuditTrailStore(str(temp_db_path))

        # Insert manifest
        store.upsert(sample_manifest)
        assert store.get(sample_manifest.audit_id) is not None

        # Delete
        store.delete(sample_manifest.audit_id)
        assert store.get(sample_manifest.audit_id) is None

    def test_sqlite_limit_parameter(
        self,
        temp_db_path: Path,
        sample_manifest: AuditManifest,
    ) -> None:
        """Test that limit parameter works correctly."""
        store = SQLiteAuditTrailStore(str(temp_db_path))

        # Insert multiple manifests
        for i in range(5):
            manifest_dict = sample_manifest.to_dict()
            manifest_dict["audit_id"] = f"audit-{i:03d}"
            manifest_dict["created_at"] = f"2024-01-{15+i:02d}T10:00:00Z"
            store.upsert(AuditManifest.from_dict(manifest_dict))

        # List with limit
        recent = store.list_recent(limit=3)
        assert len(recent) == 3

        # Should be ordered by created_at DESC (newest first)
        assert recent[0].audit_id == "audit-004"
        assert recent[1].audit_id == "audit-003"
        assert recent[2].audit_id == "audit-002"


class TestFileSystemAuditTrailStore:
    """Tests for filesystem storage backend."""

    def test_filesystem_index_and_lookup(
        self,
        temp_fs_dir: Path,
        sample_manifest: AuditManifest,
    ) -> None:
        """Test indexing and path lookup."""
        store = FileSystemAuditTrailStore(str(temp_fs_dir))

        # Index manifest
        store.index(sample_manifest)

        # Lookup path
        pack_path = store.get_path(sample_manifest.audit_id)
        assert pack_path is not None
        assert Path(pack_path).exists()
        assert Path(pack_path).is_dir()

        # Check manifest.json exists
        manifest_file = Path(pack_path) / "manifest.json"
        assert manifest_file.exists()

    def test_filesystem_list_all(
        self,
        temp_fs_dir: Path,
        sample_manifest: AuditManifest,
    ) -> None:
        """Test listing all audit IDs."""
        store = FileSystemAuditTrailStore(str(temp_fs_dir))

        # Index multiple manifests
        for i in range(3):
            manifest_dict = sample_manifest.to_dict()
            manifest_dict["audit_id"] = f"audit-{i:03d}"
            manifest = AuditManifest.from_dict(manifest_dict)
            store.index(manifest)

        # List all
        audit_ids = store.list_all()
        assert len(audit_ids) == 3
        assert "audit-000" in audit_ids
        assert "audit-001" in audit_ids
        assert "audit-002" in audit_ids

        # Should be sorted in reverse order (newest first)
        assert audit_ids == sorted(audit_ids, reverse=True)

    def test_filesystem_load_manifest(
        self,
        temp_fs_dir: Path,
        sample_manifest: AuditManifest,
    ) -> None:
        """Test loading manifest from filesystem."""
        store = FileSystemAuditTrailStore(str(temp_fs_dir))

        # Index manifest
        store.index(sample_manifest)

        # Load manifest
        loaded = store.load_manifest(sample_manifest.audit_id)
        assert loaded is not None
        assert loaded.audit_id == sample_manifest.audit_id
        assert loaded.request_id == sample_manifest.request_id
        assert loaded.query_ids == sample_manifest.query_ids

    def test_filesystem_load_nonexistent(
        self,
        temp_fs_dir: Path,
    ) -> None:
        """Test loading nonexistent manifest returns None."""
        store = FileSystemAuditTrailStore(str(temp_fs_dir))

        result = store.load_manifest("nonexistent-id")
        assert result is None

    def test_filesystem_get_path_nonexistent(
        self,
        temp_fs_dir: Path,
    ) -> None:
        """Test getting path for nonexistent audit returns None."""
        store = FileSystemAuditTrailStore(str(temp_fs_dir))

        result = store.get_path("nonexistent-id")
        assert result is None

    def test_filesystem_index_idempotent(
        self,
        temp_fs_dir: Path,
        sample_manifest: AuditManifest,
    ) -> None:
        """Test that indexing same manifest twice is idempotent."""
        store = FileSystemAuditTrailStore(str(temp_fs_dir))

        # Index twice
        store.index(sample_manifest)
        store.index(sample_manifest)

        # Should still have only one
        audit_ids = store.list_all()
        assert len(audit_ids) == 1
