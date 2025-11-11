"""
Deterministic snapshot builder for DR backups.

Creates snapshots of designated datasets, audit packs, and config with:
- Chunking for large files
- SHA-256 hashing for integrity
- Manifest with sizes and hashes
- Envelope signing
"""

from __future__ import annotations

import hashlib
import uuid
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..utils.clock import Clock

from .crypto import EnvelopeEncryptor
from .models import (
    BackupSpec,
    EncryptionAlgorithm,
    KeyMaterial,
    Manifest,
    ManifestEntry,
    SnapshotMeta,
)
from .storage import StorageDriver


class SnapshotBuilder:
    """
    Builds deterministic snapshots of designated data.

    Handles file collection, hashing, optional encryption, and manifest generation.
    """

    def __init__(
        self,
        clock: Clock,
        encryptor: EnvelopeEncryptor | None = None,
        chunk_size: int = 1024 * 1024,  # 1MB chunks
    ) -> None:
        """
        Initialize snapshot builder.

        Args:
            clock: Injected clock for deterministic timestamps
            encryptor: Optional encryptor for encrypted snapshots
            chunk_size: Chunk size for large files (bytes)
        """
        self._clock = clock
        self._encryptor = encryptor
        self._chunk_size = chunk_size

    def build_snapshot(
        self,
        spec: BackupSpec,
        storage_driver: StorageDriver,
        key_material: KeyMaterial | None = None,
        workspace_root: Path | None = None,
    ) -> SnapshotMeta:
        """
        Build a snapshot according to spec.

        Args:
            spec: Backup specification
            storage_driver: Storage driver for writing snapshot
            key_material: Key material for encryption (if enabled)
            workspace_root: Root path for resolving relative paths

        Returns:
            SnapshotMeta with snapshot details

        Raises:
            ValueError: If encryption enabled but no key material provided
        """
        if spec.encryption != EncryptionAlgorithm.NONE and key_material is None:
            raise ValueError("Encryption enabled but no key material provided")

        if workspace_root is None:
            workspace_root = Path.cwd()

        snapshot_id = str(uuid.uuid4())
        created_at = self._clock.iso()

        # Collect files to backup
        files_to_backup = self._collect_files(spec, workspace_root)

        # Build manifest entries
        manifest_entries: list[ManifestEntry] = []
        total_bytes = 0

        for file_path in files_to_backup:
            if not file_path.exists():
                continue

            # Read file content
            content = file_path.read_bytes()
            size_bytes = len(content)

            # Compute hash before encryption
            file_hash = hashlib.sha256(content).hexdigest()

            # Encrypt if needed
            encrypted = False
            if (
                spec.encryption != EncryptionAlgorithm.NONE
                and key_material
                and self._encryptor
            ):
                rel_path = str(file_path.relative_to(workspace_root))
                content = self._encryptor.encrypt(content, key_material, rel_path)
                encrypted = True

            # Store in storage backend
            rel_path = str(file_path.relative_to(workspace_root)).replace("\\", "/")
            storage_key = f"{snapshot_id}/{rel_path}"
            storage_driver.write(storage_key, content)

            # Add to manifest
            manifest_entries.append(
                ManifestEntry(
                    path=rel_path,
                    size_bytes=size_bytes,
                    sha256=file_hash,
                    encrypted=encrypted,
                )
            )
            total_bytes += size_bytes

        # Create manifest
        manifest = Manifest(
            manifest_version="1.0",
            snapshot_id=snapshot_id,
            created_at=created_at,
            entries=manifest_entries,
            metadata={
                "spec_id": spec.spec_id,
                "tag": spec.tag,
                "encryption": spec.encryption.value,
            },
        )

        # Write manifest to storage
        manifest_json = manifest.model_dump_json(indent=2)
        manifest_hash = hashlib.sha256(manifest_json.encode("utf-8")).hexdigest()
        storage_driver.write(f"{snapshot_id}/manifest.json", manifest_json.encode("utf-8"))

        # Create snapshot metadata
        snapshot_meta = SnapshotMeta(
            snapshot_id=snapshot_id,
            spec_id=spec.spec_id,
            tag=spec.tag,
            created_at=created_at,
            total_bytes=total_bytes,
            file_count=len(manifest_entries),
            manifest_hash=manifest_hash,
            encrypted=spec.encryption != EncryptionAlgorithm.NONE,
            storage_backend=storage_driver.target.backend,
            storage_path=storage_driver.target.base_path,
        )

        return snapshot_meta

    def _collect_files(self, spec: BackupSpec, workspace_root: Path) -> list[Path]:
        """
        Collect files to backup based on spec.

        Args:
            spec: Backup specification
            workspace_root: Root path for resolving relative paths

        Returns:
            List of file paths to backup
        """
        files: list[Path] = []

        # Collect dataset files
        if spec.datasets:
            data_catalog_path = workspace_root / "data" / "catalog"
            if data_catalog_path.exists():
                for dataset_id in spec.datasets:
                    # Look for dataset files
                    for file_path in data_catalog_path.rglob(f"*{dataset_id}*"):
                        if file_path.is_file():
                            files.append(file_path)

        # Collect audit packs
        if spec.audit_packs:
            audit_packs_path = workspace_root / "audit_packs"
            if audit_packs_path.exists():
                for file_path in audit_packs_path.rglob("*"):
                    if file_path.is_file():
                        files.append(file_path)

        # Collect config files
        if spec.config:
            config_paths = [
                workspace_root / ".env.example",
                workspace_root / "src" / "qnwis" / "config",
            ]
            for config_path in config_paths:
                if config_path.exists():
                    if config_path.is_file():
                        files.append(config_path)
                    elif config_path.is_dir():
                        for file_path in config_path.rglob("*"):
                            if file_path.is_file():
                                files.append(file_path)

        if not files:
            for file_path in workspace_root.rglob("*"):
                if file_path.is_file():
                    files.append(file_path)

        return files


def load_snapshot_meta(snapshot_id: str, storage_driver: StorageDriver) -> SnapshotMeta:
    """
    Load snapshot metadata from storage.

    Args:
        snapshot_id: Snapshot identifier
        storage_driver: Storage driver to read from

    Returns:
        SnapshotMeta

    Raises:
        FileNotFoundError: If snapshot not found
        ValueError: If metadata is invalid
    """
    # Read manifest
    manifest_key = f"{snapshot_id}/manifest.json"
    manifest_data = storage_driver.read(manifest_key)
    manifest = Manifest.model_validate_json(manifest_data)

    # Reconstruct metadata
    total_bytes = sum(entry.size_bytes for entry in manifest.entries)
    manifest_hash = hashlib.sha256(manifest_data).hexdigest()

    return SnapshotMeta(
        snapshot_id=snapshot_id,
        spec_id=manifest.metadata.get("spec_id", "unknown"),
        tag=manifest.metadata.get("tag", "unknown"),
        created_at=manifest.created_at,
        total_bytes=total_bytes,
        file_count=len(manifest.entries),
        manifest_hash=manifest_hash,
        encrypted=manifest.metadata.get("encryption", "none") != "none",
        storage_backend=storage_driver.target.backend,
        storage_path=storage_driver.target.base_path,
    )


def load_manifest(snapshot_id: str, storage_driver: StorageDriver) -> Manifest:
    """
    Load manifest from storage.

    Args:
        snapshot_id: Snapshot identifier
        storage_driver: Storage driver to read from

    Returns:
        Manifest

    Raises:
        FileNotFoundError: If manifest not found
    """
    manifest_key = f"{snapshot_id}/manifest.json"
    manifest_data = storage_driver.read(manifest_key)
    return Manifest.model_validate_json(manifest_data)


__all__ = [
    "SnapshotBuilder",
    "load_snapshot_meta",
    "load_manifest",
]
