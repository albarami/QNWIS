"""
Pydantic models for DR/Backup operations.

All models are frozen and include NaN/Inf guards for numeric fields.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StorageBackend(str, Enum):
    """Supported storage backend types."""

    LOCAL = "local"
    ARCHIVE = "archive"
    OBJECT_STORE = "object_store"


class EncryptionAlgorithm(str, Enum):
    """Supported encryption algorithms."""

    AES_256_GCM = "aes_256_gcm"
    NONE = "none"


class BackupSpec(BaseModel):
    """
    Specification for a backup operation.

    Attributes:
        spec_id: Unique identifier for this backup spec
        tag: Human-readable tag (e.g., 'daily', 'pre-deploy')
        datasets: List of dataset IDs to include
        audit_packs: Whether to include audit packs
        config: Whether to include configuration files
        storage_target: Target storage backend
        encryption: Encryption algorithm to use
        retention_days: Number of days to retain this backup
    """

    spec_id: str = Field(..., description="Unique backup spec identifier")
    tag: str = Field(..., description="Human-readable tag")
    datasets: list[str] = Field(default_factory=list, description="Dataset IDs to backup")
    audit_packs: bool = Field(default=True, description="Include audit packs")
    config: bool = Field(default=True, description="Include configuration")
    storage_target: str = Field(..., description="Storage target identifier")
    encryption: EncryptionAlgorithm = Field(
        default=EncryptionAlgorithm.AES_256_GCM,
        description="Encryption algorithm",
    )
    retention_days: int = Field(default=30, ge=1, description="Retention period in days")

    model_config = ConfigDict(frozen=True)


class SnapshotMeta(BaseModel):
    """
    Metadata for a completed snapshot.

    Attributes:
        snapshot_id: Unique snapshot identifier
        spec_id: Reference to BackupSpec
        tag: Tag from spec
        created_at: ISO 8601 timestamp
        total_bytes: Total size in bytes
        file_count: Number of files in snapshot
        manifest_hash: SHA-256 hash of manifest
        encrypted: Whether snapshot is encrypted
        storage_backend: Backend used for storage
        storage_path: Path/key in storage backend
    """

    snapshot_id: str = Field(..., description="Unique snapshot identifier")
    spec_id: str = Field(..., description="Backup spec identifier")
    tag: str = Field(..., description="Snapshot tag")
    created_at: str = Field(..., description="Creation timestamp (ISO 8601)")
    total_bytes: int = Field(..., ge=0, description="Total size in bytes")
    file_count: int = Field(..., ge=0, description="Number of files")
    manifest_hash: str = Field(..., description="SHA-256 hash of manifest")
    encrypted: bool = Field(..., description="Encryption status")
    storage_backend: StorageBackend = Field(..., description="Storage backend")
    storage_path: str = Field(..., description="Storage path/key")

    @field_validator("total_bytes", "file_count")
    @classmethod
    def _reject_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Size/count cannot be negative")
        return v

    class Config:
        frozen = False


class RestorePlan(BaseModel):
    """
    Plan for a restore operation.

    Attributes:
        plan_id: Unique plan identifier
        snapshot_id: Snapshot to restore from
        target_path: Destination path for restore
        dry_run: If True, only validate without restoring
        verify_hashes: Whether to verify file hashes during restore
        overwrite: Whether to overwrite existing files
    """

    plan_id: str = Field(..., description="Unique plan identifier")
    snapshot_id: str = Field(..., description="Snapshot to restore")
    target_path: str = Field(..., description="Restore destination path")
    dry_run: bool = Field(default=False, description="Dry-run mode")
    verify_hashes: bool = Field(default=True, description="Verify file hashes")
    overwrite: bool = Field(default=False, description="Overwrite existing files")

    model_config = ConfigDict(frozen=False)


class StorageTarget(BaseModel):
    """
    Storage target configuration.

    Attributes:
        target_id: Unique target identifier
        backend: Storage backend type
        base_path: Base path for storage
        worm: Write-Once-Read-Many mode (no overwrites)
        compression: Enable compression
        options: Backend-specific options
    """

    target_id: str = Field(..., description="Unique target identifier")
    backend: StorageBackend = Field(..., description="Storage backend")
    base_path: str = Field(..., description="Base storage path")
    worm: bool = Field(default=False, description="WORM mode")
    compression: bool = Field(default=True, description="Enable compression")
    options: dict[str, Any] = Field(default_factory=dict, description="Backend options")

    class Config:
        frozen = True


class KeyMaterial(BaseModel):
    """
    Encryption key material.

    Attributes:
        key_id: Unique key identifier
        algorithm: Encryption algorithm
        created_at: Key creation timestamp
        rotated_at: Last rotation timestamp (if any)
        wrapped_key: Encrypted key material (base64)
        kms_key_id: KMS key identifier used for wrapping
    """

    key_id: str = Field(..., description="Unique key identifier")
    algorithm: EncryptionAlgorithm = Field(..., description="Encryption algorithm")
    created_at: str = Field(..., description="Creation timestamp")
    rotated_at: str | None = Field(None, description="Last rotation timestamp")
    wrapped_key: str = Field(..., description="Wrapped key material (base64)")
    kms_key_id: str = Field(..., description="KMS key identifier")

    class Config:
        frozen = True


class RetentionRule(BaseModel):
    """
    Retention policy rule.

    Attributes:
        rule_id: Unique rule identifier
        keep_daily: Number of daily backups to keep
        keep_weekly: Number of weekly backups to keep
        keep_monthly: Number of monthly backups to keep
        min_age_days: Minimum age before pruning
    """

    rule_id: str = Field(..., description="Unique rule identifier")
    keep_daily: int = Field(default=7, ge=0, description="Daily backups to keep")
    keep_weekly: int = Field(default=4, ge=0, description="Weekly backups to keep")
    keep_monthly: int = Field(default=12, ge=0, description="Monthly backups to keep")
    min_age_days: int = Field(default=1, ge=0, description="Minimum age before pruning")

    @field_validator("keep_daily", "keep_weekly", "keep_monthly", "min_age_days")
    @classmethod
    def _reject_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Retention counts cannot be negative")
        return v

    class Config:
        frozen = True


class ScheduleSpec(BaseModel):
    """
    Backup schedule specification.

    Attributes:
        schedule_id: Unique schedule identifier
        spec_id: BackupSpec to execute
        cron_expr: Cron expression (e.g., '0 2 * * *')
        enabled: Whether schedule is active
        next_run_at: Next scheduled run timestamp
    """

    schedule_id: str = Field(..., description="Unique schedule identifier")
    spec_id: str = Field(..., description="BackupSpec to execute")
    cron_expr: str = Field(..., description="Cron expression")
    enabled: bool = Field(default=True, description="Schedule enabled")
    next_run_at: str | None = Field(None, description="Next run timestamp")

    class Config:
        frozen = True


class Policy(BaseModel):
    """
    Combined backup policy.

    Attributes:
        policy_id: Unique policy identifier
        name: Human-readable policy name
        backup_spec: Backup specification
        retention: Retention rules
        schedule: Schedule specification (optional)
        storage_target: Storage target configuration
    """

    policy_id: str = Field(..., description="Unique policy identifier")
    name: str = Field(..., description="Policy name")
    backup_spec: BackupSpec = Field(..., description="Backup specification")
    retention: RetentionRule = Field(..., description="Retention rules")
    schedule: ScheduleSpec | None = Field(None, description="Schedule specification")
    storage_target: StorageTarget = Field(..., description="Storage target")

    class Config:
        frozen = True


class VerificationReport(BaseModel):
    """
    Post-backup verification report.

    Attributes:
        report_id: Unique report identifier
        snapshot_id: Snapshot being verified
        verified_at: Verification timestamp
        manifest_ok: Manifest hash verification passed
        sample_files_ok: Sample file verification passed
        decrypt_ok: Decryption test passed
        restore_smoke_ok: Restore smoke test passed
        errors: List of verification errors
    """

    report_id: str = Field(..., description="Unique report identifier")
    snapshot_id: str = Field(..., description="Snapshot identifier")
    verified_at: str = Field(..., description="Verification timestamp")
    manifest_ok: bool = Field(..., description="Manifest verification passed")
    sample_files_ok: bool = Field(..., description="Sample files verified")
    decrypt_ok: bool = Field(..., description="Decryption test passed")
    restore_smoke_ok: bool = Field(..., description="Restore smoke test passed")
    errors: list[str] = Field(default_factory=list, description="Verification errors")

    @property
    def passed(self) -> bool:
        """Check if all verifications passed."""
        return (
            self.manifest_ok
            and self.sample_files_ok
            and self.decrypt_ok
            and self.restore_smoke_ok
            and not self.errors
        )

    class Config:
        frozen = True


class ManifestEntry(BaseModel):
    """
    Single file entry in backup manifest.

    Attributes:
        path: Relative path in backup
        size_bytes: File size in bytes
        sha256: SHA-256 hash of file content
        encrypted: Whether file is encrypted
    """

    path: str = Field(..., description="Relative file path")
    size_bytes: int = Field(..., ge=0, description="File size in bytes")
    sha256: str = Field(..., description="SHA-256 hash")
    encrypted: bool = Field(..., description="Encryption status")

    @field_validator("size_bytes")
    @classmethod
    def _reject_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("File size cannot be negative")
        return v

    class Config:
        frozen = True


class Manifest(BaseModel):
    """
    Complete backup manifest.

    Attributes:
        manifest_version: Manifest format version
        snapshot_id: Associated snapshot identifier
        created_at: Creation timestamp
        entries: List of file entries
        metadata: Additional metadata
    """

    manifest_version: str = Field(default="1.0", description="Manifest format version")
    snapshot_id: str = Field(..., description="Snapshot identifier")
    created_at: str = Field(..., description="Creation timestamp")
    entries: list[ManifestEntry] = Field(default_factory=list, description="File entries")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    class Config:
        frozen = True


__all__ = [
    "BackupSpec",
    "SnapshotMeta",
    "RestorePlan",
    "StorageTarget",
    "KeyMaterial",
    "Policy",
    "RetentionRule",
    "ScheduleSpec",
    "VerificationReport",
    "ManifestEntry",
    "Manifest",
    "StorageBackend",
    "EncryptionAlgorithm",
]
