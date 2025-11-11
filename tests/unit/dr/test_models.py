"""Unit tests for DR models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.qnwis.dr.models import (
    BackupSpec,
    EncryptionAlgorithm,
    KeyMaterial,
    Manifest,
    ManifestEntry,
    RestorePlan,
    RetentionRule,
    ScheduleSpec,
    SnapshotMeta,
    StorageBackend,
    StorageTarget,
    VerificationReport,
)


def test_backup_spec_valid():
    """Test valid BackupSpec creation."""
    spec = BackupSpec(
        spec_id="test-001",
        tag="daily",
        datasets=["dataset1", "dataset2"],
        audit_packs=True,
        config=True,
        storage_target="local-storage",
        encryption=EncryptionAlgorithm.AES_256_GCM,
        retention_days=30,
    )

    assert spec.spec_id == "test-001"
    assert spec.tag == "daily"
    assert len(spec.datasets) == 2
    assert spec.encryption == EncryptionAlgorithm.AES_256_GCM
    assert spec.retention_days == 30


def test_backup_spec_frozen():
    """Test that BackupSpec is immutable."""
    spec = BackupSpec(
        spec_id="test-001",
        tag="daily",
        storage_target="local",
        retention_days=7,
    )

    with pytest.raises(ValidationError):
        spec.tag = "weekly"  # type: ignore


def test_backup_spec_negative_retention():
    """Test that negative retention days are rejected."""
    with pytest.raises(ValidationError):
        BackupSpec(
            spec_id="test-001",
            tag="daily",
            storage_target="local",
            retention_days=-1,
        )


def test_snapshot_meta_valid():
    """Test valid SnapshotMeta creation."""
    meta = SnapshotMeta(
        snapshot_id="snap-001",
        spec_id="spec-001",
        tag="daily",
        created_at="2024-01-01T00:00:00Z",
        total_bytes=1024,
        file_count=10,
        manifest_hash="abc123",
        encrypted=True,
        storage_backend=StorageBackend.LOCAL,
        storage_path="/backups",
    )

    assert meta.snapshot_id == "snap-001"
    assert meta.total_bytes == 1024
    assert meta.file_count == 10
    assert meta.encrypted is True


def test_snapshot_meta_negative_bytes():
    """Test that negative bytes are rejected."""
    with pytest.raises(ValidationError):
        SnapshotMeta(
            snapshot_id="snap-001",
            spec_id="spec-001",
            tag="daily",
            created_at="2024-01-01T00:00:00Z",
            total_bytes=-100,
            file_count=10,
            manifest_hash="abc123",
            encrypted=False,
            storage_backend=StorageBackend.LOCAL,
            storage_path="/backups",
        )


def test_restore_plan_valid():
    """Test valid RestorePlan creation."""
    plan = RestorePlan(
        plan_id="plan-001",
        snapshot_id="snap-001",
        target_path="/restore",
        dry_run=False,
        verify_hashes=True,
        overwrite=False,
    )

    assert plan.plan_id == "plan-001"
    assert plan.dry_run is False
    assert plan.verify_hashes is True


def test_storage_target_valid():
    """Test valid StorageTarget creation."""
    target = StorageTarget(
        target_id="target-001",
        backend=StorageBackend.LOCAL,
        base_path="/storage",
        worm=True,
        compression=True,
        options={"key": "value"},
    )

    assert target.target_id == "target-001"
    assert target.backend == StorageBackend.LOCAL
    assert target.worm is True
    assert target.compression is True


def test_key_material_valid():
    """Test valid KeyMaterial creation."""
    key = KeyMaterial(
        key_id="key-001",
        algorithm=EncryptionAlgorithm.AES_256_GCM,
        created_at="2024-01-01T00:00:00Z",
        rotated_at=None,
        wrapped_key="base64encodedkey==",
        kms_key_id="kms-001",
    )

    assert key.key_id == "key-001"
    assert key.algorithm == EncryptionAlgorithm.AES_256_GCM
    assert key.rotated_at is None


def test_retention_rule_valid():
    """Test valid RetentionRule creation."""
    rule = RetentionRule(
        rule_id="rule-001",
        keep_daily=7,
        keep_weekly=4,
        keep_monthly=12,
        min_age_days=1,
    )

    assert rule.keep_daily == 7
    assert rule.keep_weekly == 4
    assert rule.keep_monthly == 12


def test_retention_rule_negative_values():
    """Test that negative retention values are rejected."""
    with pytest.raises(ValidationError):
        RetentionRule(
            rule_id="rule-001",
            keep_daily=-1,
            keep_weekly=4,
            keep_monthly=12,
            min_age_days=1,
        )


def test_schedule_spec_valid():
    """Test valid ScheduleSpec creation."""
    schedule = ScheduleSpec(
        schedule_id="sched-001",
        spec_id="spec-001",
        cron_expr="0 2 * * *",
        enabled=True,
        next_run_at="2024-01-02T02:00:00Z",
    )

    assert schedule.schedule_id == "sched-001"
    assert schedule.cron_expr == "0 2 * * *"
    assert schedule.enabled is True


def test_verification_report_valid():
    """Test valid VerificationReport creation."""
    report = VerificationReport(
        report_id="report-001",
        snapshot_id="snap-001",
        verified_at="2024-01-01T00:00:00Z",
        manifest_ok=True,
        sample_files_ok=True,
        decrypt_ok=True,
        restore_smoke_ok=True,
        errors=[],
    )

    assert report.passed is True
    assert len(report.errors) == 0


def test_verification_report_with_errors():
    """Test VerificationReport with errors."""
    report = VerificationReport(
        report_id="report-001",
        snapshot_id="snap-001",
        verified_at="2024-01-01T00:00:00Z",
        manifest_ok=True,
        sample_files_ok=False,
        decrypt_ok=True,
        restore_smoke_ok=True,
        errors=["Sample file hash mismatch"],
    )

    assert report.passed is False
    assert len(report.errors) == 1


def test_manifest_entry_valid():
    """Test valid ManifestEntry creation."""
    entry = ManifestEntry(
        path="data/file.txt",
        size_bytes=1024,
        sha256="abc123",
        encrypted=True,
    )

    assert entry.path == "data/file.txt"
    assert entry.size_bytes == 1024
    assert entry.encrypted is True


def test_manifest_entry_negative_size():
    """Test that negative file size is rejected."""
    with pytest.raises(ValidationError):
        ManifestEntry(
            path="data/file.txt",
            size_bytes=-100,
            sha256="abc123",
            encrypted=False,
        )


def test_manifest_valid():
    """Test valid Manifest creation."""
    entries = [
        ManifestEntry(
            path="file1.txt",
            size_bytes=100,
            sha256="hash1",
            encrypted=False,
        ),
        ManifestEntry(
            path="file2.txt",
            size_bytes=200,
            sha256="hash2",
            encrypted=False,
        ),
    ]

    manifest = Manifest(
        manifest_version="1.0",
        snapshot_id="snap-001",
        created_at="2024-01-01T00:00:00Z",
        entries=entries,
        metadata={"tag": "daily"},
    )

    assert manifest.manifest_version == "1.0"
    assert len(manifest.entries) == 2
    assert manifest.metadata["tag"] == "daily"


def test_manifest_empty_entries():
    """Test Manifest with no entries."""
    manifest = Manifest(
        manifest_version="1.0",
        snapshot_id="snap-001",
        created_at="2024-01-01T00:00:00Z",
        entries=[],
        metadata={},
    )

    assert len(manifest.entries) == 0


def test_encryption_algorithm_enum():
    """Test EncryptionAlgorithm enum values."""
    assert EncryptionAlgorithm.AES_256_GCM.value == "aes_256_gcm"
    assert EncryptionAlgorithm.NONE.value == "none"


def test_storage_backend_enum():
    """Test StorageBackend enum values."""
    assert StorageBackend.LOCAL.value == "local"
    assert StorageBackend.ARCHIVE.value == "archive"
    assert StorageBackend.OBJECT_STORE.value == "object_store"
