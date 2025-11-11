"""Integration test for backup→restore round-trip."""

from __future__ import annotations

import tempfile
from datetime import UTC, datetime
from pathlib import Path

import pytest

from src.qnwis.dr.crypto import EnvelopeEncryptor, KMSStub
from src.qnwis.dr.models import (
    BackupSpec,
    EncryptionAlgorithm,
    StorageBackend,
    StorageTarget,
)
from src.qnwis.dr.restore import RestoreEngine
from src.qnwis.dr.snapshot import SnapshotBuilder
from src.qnwis.dr.storage import create_storage_driver
from src.qnwis.dr.verify import SnapshotVerifier
from src.qnwis.utils.clock import ManualClock


def test_backup_restore_roundtrip_unencrypted():
    """Test backup and restore round-trip without encryption."""
    clock = ManualClock(start=datetime(2024, 1, 1, tzinfo=UTC))

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create test files
        workspace = temp_path / "workspace"
        workspace.mkdir()
        (workspace / "file1.txt").write_text("Content 1")
        (workspace / "file2.txt").write_text("Content 2")
        subdir = workspace / "subdir"
        subdir.mkdir()
        (subdir / "file3.txt").write_text("Content 3")

        # Setup storage
        storage_target = StorageTarget(
            target_id="test-target",
            backend=StorageBackend.LOCAL,
            base_path=str(temp_path / "storage"),
            worm=False,
            compression=True,
            options={},
        )
        storage_driver = create_storage_driver(storage_target)

        # Create backup spec
        spec = BackupSpec(
            spec_id="test-spec",
            tag="test",
            datasets=[],
            audit_packs=False,
            config=False,
            storage_target="test-target",
            encryption=EncryptionAlgorithm.NONE,
            retention_days=7,
        )

        # Backup
        builder = SnapshotBuilder(clock)
        snapshot_meta = builder.build_snapshot(spec, storage_driver, None, workspace)

        assert snapshot_meta.file_count == 3
        assert snapshot_meta.encrypted is False

        # Restore
        restore_dir = temp_path / "restored"
        restore_engine = RestoreEngine(clock, None, allowed_targets=[str(restore_dir)])

        plan = restore_engine.create_plan(
            snapshot_id=snapshot_meta.snapshot_id,
            target_path=str(restore_dir),
            storage_driver=storage_driver,
            dry_run=False,
            verify_hashes=True,
        )

        stats = restore_engine.execute_restore(plan, storage_driver)

        assert stats["files_restored"] == 3
        assert stats["verification_failures"] == 0

        # Verify content
        assert (restore_dir / "file1.txt").read_text() == "Content 1"
        assert (restore_dir / "file2.txt").read_text() == "Content 2"
        assert (restore_dir / "subdir" / "file3.txt").read_text() == "Content 3"


def test_backup_restore_roundtrip_encrypted():
    """Test backup and restore round-trip with encryption."""
    clock = ManualClock(start=datetime(2024, 1, 1, tzinfo=UTC))

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create test files
        workspace = temp_path / "workspace"
        workspace.mkdir()
        (workspace / "secret1.txt").write_text("Secret data 1")
        (workspace / "secret2.txt").write_text("Secret data 2")

        # Setup storage and encryption
        storage_target = StorageTarget(
            target_id="test-target",
            backend=StorageBackend.LOCAL,
            base_path=str(temp_path / "storage"),
            worm=False,
            compression=True,
            options={},
        )
        storage_driver = create_storage_driver(storage_target)

        kms = KMSStub()
        encryptor = EnvelopeEncryptor(clock, kms)
        key_material = encryptor.generate_key()

        # Create backup spec
        spec = BackupSpec(
            spec_id="encrypted-spec",
            tag="encrypted",
            datasets=[],
            audit_packs=False,
            config=False,
            storage_target="test-target",
            encryption=EncryptionAlgorithm.AES_256_GCM,
            retention_days=7,
        )

        # Backup
        builder = SnapshotBuilder(clock, encryptor)
        snapshot_meta = builder.build_snapshot(spec, storage_driver, key_material, workspace)

        assert snapshot_meta.file_count == 2
        assert snapshot_meta.encrypted is True

        # Verify stored data is encrypted
        stored_file = storage_driver.read(f"{snapshot_meta.snapshot_id}/secret1.txt")
        assert b"Secret data 1" not in stored_file  # Should be encrypted

        # Restore
        restore_dir = temp_path / "restored"
        restore_engine = RestoreEngine(clock, encryptor, allowed_targets=[str(restore_dir)])

        plan = restore_engine.create_plan(
            snapshot_id=snapshot_meta.snapshot_id,
            target_path=str(restore_dir),
            storage_driver=storage_driver,
            dry_run=False,
            verify_hashes=True,
        )

        stats = restore_engine.execute_restore(plan, storage_driver, key_material)

        assert stats["files_restored"] == 2
        assert stats["verification_failures"] == 0

        # Verify decrypted content
        assert (restore_dir / "secret1.txt").read_text() == "Secret data 1"
        assert (restore_dir / "secret2.txt").read_text() == "Secret data 2"


def test_backup_verify_restore():
    """Test full backup→verify→restore pipeline."""
    clock = ManualClock(start=datetime(2024, 1, 1, tzinfo=UTC))

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create test corpus
        workspace = temp_path / "workspace"
        workspace.mkdir()
        for i in range(10):
            (workspace / f"file{i:02d}.txt").write_text(f"Content {i}")

        # Setup
        storage_target = StorageTarget(
            target_id="test-target",
            backend=StorageBackend.LOCAL,
            base_path=str(temp_path / "storage"),
            worm=False,
            compression=True,
            options={},
        )
        storage_driver = create_storage_driver(storage_target)

        kms = KMSStub()
        encryptor = EnvelopeEncryptor(clock, kms)
        key_material = encryptor.generate_key()

        spec = BackupSpec(
            spec_id="verify-spec",
            tag="verify-test",
            datasets=[],
            audit_packs=False,
            config=False,
            storage_target="test-target",
            encryption=EncryptionAlgorithm.AES_256_GCM,
            retention_days=7,
        )

        # Backup
        builder = SnapshotBuilder(clock, encryptor)
        snapshot_meta = builder.build_snapshot(spec, storage_driver, key_material, workspace)

        # Verify
        verifier = SnapshotVerifier(clock, encryptor, sample_count=5)
        report = verifier.verify_snapshot(
            snapshot_meta.snapshot_id, storage_driver, key_material
        )

        assert report.passed is True
        assert report.manifest_ok is True
        assert report.sample_files_ok is True
        assert report.decrypt_ok is True
        assert report.restore_smoke_ok is True
        assert len(report.errors) == 0

        # Restore
        restore_dir = temp_path / "restored"
        restore_engine = RestoreEngine(clock, encryptor, allowed_targets=[str(restore_dir)])

        plan = restore_engine.create_plan(
            snapshot_id=snapshot_meta.snapshot_id,
            target_path=str(restore_dir),
            storage_driver=storage_driver,
            dry_run=False,
            verify_hashes=True,
        )

        stats = restore_engine.execute_restore(plan, storage_driver, key_material)

        assert stats["files_restored"] == 10
        assert stats["verification_failures"] == 0


def test_restore_dry_run():
    """Test dry-run restore mode."""
    clock = ManualClock(start=datetime(2024, 1, 1, tzinfo=UTC))

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create and backup test files
        workspace = temp_path / "workspace"
        workspace.mkdir()
        (workspace / "test.txt").write_text("Test content")

        storage_target = StorageTarget(
            target_id="test-target",
            backend=StorageBackend.LOCAL,
            base_path=str(temp_path / "storage"),
            worm=False,
            compression=True,
            options={},
        )
        storage_driver = create_storage_driver(storage_target)

        spec = BackupSpec(
            spec_id="dryrun-spec",
            tag="dryrun",
            datasets=[],
            audit_packs=False,
            config=False,
            storage_target="test-target",
            encryption=EncryptionAlgorithm.NONE,
            retention_days=7,
        )

        builder = SnapshotBuilder(clock)
        snapshot_meta = builder.build_snapshot(spec, storage_driver, None, workspace)

        # Dry-run restore
        restore_dir = temp_path / "restored"
        restore_engine = RestoreEngine(clock, None, allowed_targets=[str(restore_dir)])

        plan = restore_engine.create_plan(
            snapshot_id=snapshot_meta.snapshot_id,
            target_path=str(restore_dir),
            storage_driver=storage_driver,
            dry_run=True,
        )

        stats = restore_engine.execute_restore(plan, storage_driver)

        # Files should be counted but not actually written
        assert stats["files_restored"] == 1
        assert not (restore_dir / "test.txt").exists()


def test_restore_overwrite_protection():
    """Test restore overwrite protection."""
    clock = ManualClock(start=datetime(2024, 1, 1, tzinfo=UTC))

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create and backup test files
        workspace = temp_path / "workspace"
        workspace.mkdir()
        (workspace / "test.txt").write_text("Original content")

        storage_target = StorageTarget(
            target_id="test-target",
            backend=StorageBackend.LOCAL,
            base_path=str(temp_path / "storage"),
            worm=False,
            compression=True,
            options={},
        )
        storage_driver = create_storage_driver(storage_target)

        spec = BackupSpec(
            spec_id="overwrite-spec",
            tag="overwrite",
            datasets=[],
            audit_packs=False,
            config=False,
            storage_target="test-target",
            encryption=EncryptionAlgorithm.NONE,
            retention_days=7,
        )

        builder = SnapshotBuilder(clock)
        snapshot_meta = builder.build_snapshot(spec, storage_driver, None, workspace)

        # Create existing file in restore location
        restore_dir = temp_path / "restored"
        restore_dir.mkdir()
        (restore_dir / "test.txt").write_text("Existing content")

        restore_engine = RestoreEngine(clock, None, allowed_targets=[str(restore_dir)])

        # Restore without overwrite
        plan = restore_engine.create_plan(
            snapshot_id=snapshot_meta.snapshot_id,
            target_path=str(restore_dir),
            storage_driver=storage_driver,
            dry_run=False,
            overwrite=False,
        )

        stats = restore_engine.execute_restore(plan, storage_driver)

        # File should be skipped
        assert stats["files_skipped"] == 1
        assert (restore_dir / "test.txt").read_text() == "Existing content"

        # Restore with overwrite
        plan_overwrite = restore_engine.create_plan(
            snapshot_id=snapshot_meta.snapshot_id,
            target_path=str(restore_dir),
            storage_driver=storage_driver,
            dry_run=False,
            overwrite=True,
        )

        stats_overwrite = restore_engine.execute_restore(plan_overwrite, storage_driver)

        # File should be overwritten
        assert stats_overwrite["files_restored"] == 1
        assert (restore_dir / "test.txt").read_text() == "Original content"


def test_restore_rejects_disallowed_target():
    """Restore plans should refuse targets outside the allowlist."""
    clock = ManualClock(start=datetime(2024, 1, 1, tzinfo=UTC))

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        workspace = temp_path / "workspace"
        workspace.mkdir()
        (workspace / "doc.txt").write_text("payload")

        storage_target = StorageTarget(
            target_id="test-target",
            backend=StorageBackend.LOCAL,
            base_path=str(temp_path / "storage"),
            worm=False,
            compression=True,
            options={},
        )
        storage_driver = create_storage_driver(storage_target)

        spec = BackupSpec(
            spec_id="allowlist-spec",
            tag="dr",
            datasets=[],
            audit_packs=False,
            config=False,
            storage_target="test-target",
            encryption=EncryptionAlgorithm.NONE,
            retention_days=7,
        )

        builder = SnapshotBuilder(clock)
        snapshot_meta = builder.build_snapshot(spec, storage_driver, None, workspace)

        allowed_dir = temp_path / "allowed"
        allowed_dir.mkdir()
        forbidden_dir = temp_path / "forbidden"
        forbidden_dir.mkdir()

        restore_engine = RestoreEngine(clock, None, allowed_targets=[str(allowed_dir)])

        # Allowed target succeeds
        restore_engine.create_plan(
            snapshot_id=snapshot_meta.snapshot_id,
            target_path=str(allowed_dir),
            storage_driver=storage_driver,
        )

        # Direct forbidden target is rejected
        with pytest.raises(ValueError, match="not in allowed list"):
            restore_engine.create_plan(
                snapshot_id=snapshot_meta.snapshot_id,
                target_path=str(forbidden_dir),
                storage_driver=storage_driver,
            )

        # Traversal attempt is also rejected
        traversal_target = allowed_dir / ".." / "forbidden"
        with pytest.raises(ValueError, match="not in allowed list"):
            restore_engine.create_plan(
                snapshot_id=snapshot_meta.snapshot_id,
                target_path=str(traversal_target),
                storage_driver=storage_driver,
            )


def test_restore_execute_revalidates_target():
    """Even if a plan is tampered with, execute_restore should re-check targets."""
    clock = ManualClock(start=datetime(2024, 1, 1, tzinfo=UTC))

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        workspace = temp_path / "workspace"
        workspace.mkdir()
        (workspace / "doc.txt").write_text("payload")

        storage_target = StorageTarget(
            target_id="test-target",
            backend=StorageBackend.LOCAL,
            base_path=str(temp_path / "storage"),
            worm=False,
            compression=True,
            options={},
        )
        storage_driver = create_storage_driver(storage_target)

        spec = BackupSpec(
            spec_id="tamper-spec",
            tag="dr",
            datasets=[],
            audit_packs=False,
            config=False,
            storage_target="test-target",
            encryption=EncryptionAlgorithm.NONE,
            retention_days=7,
        )

        builder = SnapshotBuilder(clock)
        snapshot_meta = builder.build_snapshot(spec, storage_driver, None, workspace)

        allowed_dir = temp_path / "allowed"
        allowed_dir.mkdir()
        forbidden_dir = temp_path / "forbidden"
        forbidden_dir.mkdir()

        restore_engine = RestoreEngine(clock, None, allowed_targets=[str(allowed_dir)])

        plan = restore_engine.create_plan(
            snapshot_id=snapshot_meta.snapshot_id,
            target_path=str(allowed_dir),
            storage_driver=storage_driver,
            dry_run=False,
        )

        # Simulate tampering after plan creation
        plan.target_path = str(forbidden_dir)

        with pytest.raises(ValueError, match="not in allowed list"):
            restore_engine.execute_restore(plan, storage_driver)
