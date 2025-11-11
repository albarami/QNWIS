"""
Idempotent restore pipeline for DR backups.

Supports:
- Snapshot selection by ID/tag
- Hash verification during restore
- Decryption of encrypted snapshots
- Dry-run mode (plan only)
- Policy checks for allowed targets
"""

from __future__ import annotations

import hashlib
import uuid
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..utils.clock import Clock

from .crypto import EnvelopeEncryptor
from .models import KeyMaterial, RestorePlan
from .snapshot import load_manifest
from .storage import StorageDriver


class RestoreEngine:
    """
    Idempotent restore engine for DR backups.

    Handles restore operations with verification and policy enforcement.
    """

    def __init__(
        self,
        clock: Clock,
        encryptor: EnvelopeEncryptor | None = None,
        allowed_targets: list[str] | None = None,
    ) -> None:
        """
        Initialize restore engine.

        Args:
            clock: Injected clock for deterministic timestamps
            encryptor: Optional encryptor for decryption
            allowed_targets: List of allowed restore target paths (security)
        """
        self._clock = clock
        self._encryptor = encryptor
        self._allowed_targets = [Path(target).resolve() for target in (allowed_targets or [])]

    def create_plan(
        self,
        snapshot_id: str,
        target_path: str,
        storage_driver: StorageDriver,
        dry_run: bool = False,
        verify_hashes: bool = True,
        overwrite: bool = False,
    ) -> RestorePlan:
        """
        Create a restore plan.

        Args:
            snapshot_id: Snapshot to restore
            target_path: Destination path
            storage_driver: Storage driver to read from
            dry_run: If True, only validate without restoring
            verify_hashes: Whether to verify file hashes
            overwrite: Whether to overwrite existing files

        Returns:
            RestorePlan

        Raises:
            ValueError: If target path not allowed
        """
        # Validate target path
        safe_target = self._validate_target(target_path)

        plan_id = str(uuid.uuid4())

        return RestorePlan(
            plan_id=plan_id,
            snapshot_id=snapshot_id,
            target_path=str(safe_target),
            dry_run=dry_run,
            verify_hashes=verify_hashes,
            overwrite=overwrite,
        )

    def execute_restore(
        self,
        plan: RestorePlan,
        storage_driver: StorageDriver,
        key_material: KeyMaterial | None = None,
    ) -> dict[str, int]:
        """
        Execute a restore plan.

        Args:
            plan: Restore plan to execute
            storage_driver: Storage driver to read from
            key_material: Key material for decryption (if needed)

        Returns:
            Statistics dict with files_restored, bytes_restored, files_skipped

        Raises:
            ValueError: If encrypted snapshot but no key material
            FileNotFoundError: If snapshot not found
        """
        # Load manifest
        manifest = load_manifest(plan.snapshot_id, storage_driver)

        # Check if decryption needed
        needs_decryption = any(entry.encrypted for entry in manifest.entries)
        if needs_decryption and key_material is None:
            raise ValueError("Snapshot is encrypted but no key material provided")

        target_root = Path(plan.target_path)
        self._validate_target(target_root)

        stats = {
            "files_restored": 0,
            "bytes_restored": 0,
            "files_skipped": 0,
            "files_verified": 0,
            "verification_failures": 0,
        }

        for entry in manifest.entries:
            # Determine target file path
            target_file = target_root / entry.path
            target_file.parent.mkdir(parents=True, exist_ok=True)

            # Check if file exists and overwrite policy
            if target_file.exists() and not plan.overwrite:
                stats["files_skipped"] += 1
                continue

            # Read from storage
            storage_key = f"{plan.snapshot_id}/{entry.path}"
            content = storage_driver.read(storage_key)

            # Decrypt if needed
            if entry.encrypted and key_material and self._encryptor:
                content = self._encryptor.decrypt(content, key_material)

            # Verify hash if requested
            if plan.verify_hashes:
                actual_hash = hashlib.sha256(content).hexdigest()
                if actual_hash != entry.sha256:
                    stats["verification_failures"] += 1
                    raise ValueError(
                        f"Hash mismatch for '{entry.path}': "
                        f"expected {entry.sha256}, got {actual_hash}"
                    )
                stats["files_verified"] += 1

            # Write to target (unless dry-run)
            if not plan.dry_run:
                target_file.write_bytes(content)
                stats["files_restored"] += 1
                stats["bytes_restored"] += entry.size_bytes
            else:
                # Dry-run: just count what would be restored
                stats["files_restored"] += 1
                stats["bytes_restored"] += entry.size_bytes

        return stats

    def _validate_target(self, target_path: str | Path) -> Path:
        """
        Ensure the requested restore target stays within the allowlist.

        Args:
            target_path: User-provided target path

        Returns:
            Resolved Path within allowed roots

        Raises:
            ValueError: If target escapes the allowlist
        """
        target = Path(target_path).resolve()
        if self._allowed_targets:
            for allowed in self._allowed_targets:
                if target.is_relative_to(allowed):
                    return target
            raise ValueError(f"Restore target '{target_path}' not in allowed list")
        return target

    def list_snapshots(
        self,
        storage_driver: StorageDriver,
        tag_filter: str | None = None,
    ) -> list[str]:
        """
        List available snapshots in storage.

        Args:
            storage_driver: Storage driver to query
            tag_filter: Optional tag filter

        Returns:
            List of snapshot IDs
        """
        # List all keys and extract snapshot IDs
        all_keys = storage_driver.list_keys()
        snapshot_ids = set()

        for key in all_keys:
            # Keys are in format: snapshot_id/path
            parts = key.split("/")
            if len(parts) >= 2:
                snapshot_ids.add(parts[0])

        # Filter by tag if requested
        if tag_filter:
            filtered_ids = []
            for snapshot_id in snapshot_ids:
                try:
                    manifest = load_manifest(snapshot_id, storage_driver)
                    if manifest.metadata.get("tag") == tag_filter:
                        filtered_ids.append(snapshot_id)
                except Exception:
                    # Skip snapshots we can't read
                    continue
            return sorted(filtered_ids)

        return sorted(snapshot_ids)


def validate_restore_target(target_path: str, allowed_targets: list[str]) -> bool:
    """
    Validate that restore target is in allowed list.

    Args:
        target_path: Target path to validate
        allowed_targets: List of allowed target paths

    Returns:
        True if allowed

    Raises:
        ValueError: If target not allowed
    """
    if not allowed_targets:
        return True

    target = Path(target_path).resolve()
    for allowed in allowed_targets:
        allowed_path = Path(allowed).resolve()
        try:
            target.relative_to(allowed_path)
            return True
        except ValueError:
            continue

    raise ValueError(f"Restore target '{target_path}' not in allowed list")


__all__ = [
    "RestoreEngine",
    "validate_restore_target",
]
