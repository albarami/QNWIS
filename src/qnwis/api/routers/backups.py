"""
DR/Backup API endpoints with RBAC and standard envelopes.

Routes (RBAC: admin/service):
- POST /api/v1/dr/backup
- POST /api/v1/dr/restore
- GET /api/v1/dr/snapshots
- POST /api/v1/dr/verify/{id}
- POST /api/v1/dr/prune
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from ...dr.crypto import EnvelopeEncryptor, KMSStub
from ...dr.models import (
    BackupSpec,
    EncryptionAlgorithm,
    KeyMaterial,
    StorageBackend,
    StorageTarget,
)
from ...dr.restore import RestoreEngine
from ...dr.snapshot import SnapshotBuilder, load_snapshot_meta
from ...dr.storage import create_storage_driver
from ...dr.verify import SnapshotVerifier
from ...security import Principal
from ...security.rbac import allowed_roles, require_roles
from ...utils.clock import Clock
from ._shared import get_clock

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/dr", tags=["dr"])


# ============================================================================
# Request/Response Models
# ============================================================================


class BackupRequest(BaseModel):
    """Request to create a backup."""

    spec: BackupSpec = Field(..., description="Backup specification")
    storage_target_id: str = Field(..., description="Storage target identifier")
    key_id: str | None = Field(None, description="Encryption key ID (if using existing key)")


class BackupResponse(BaseModel):
    """Response for backup operation."""

    request_id: str = Field(..., description="Request identifier")
    snapshot_id: str = Field(..., description="Created snapshot ID")
    total_bytes: int = Field(..., description="Total bytes backed up")
    file_count: int = Field(..., description="Number of files backed up")
    manifest_hash: str = Field(..., description="Manifest hash")
    timings_ms: dict[str, int] = Field(default_factory=dict, description="Timing breakdown")


class RestoreRequest(BaseModel):
    """Request to restore from snapshot."""

    snapshot_id: str = Field(..., description="Snapshot to restore")
    target_path: str = Field(..., description="Restore destination")
    storage_target_id: str = Field(..., description="Storage target identifier")
    key_id: str | None = Field(None, description="Decryption key ID")
    dry_run: bool = Field(default=False, description="Dry-run mode")
    overwrite: bool = Field(default=False, description="Overwrite existing files")


class RestoreResponse(BaseModel):
    """Response for restore operation."""

    request_id: str = Field(..., description="Request identifier")
    plan_id: str = Field(..., description="Restore plan ID")
    files_restored: int = Field(..., description="Number of files restored")
    bytes_restored: int = Field(..., description="Bytes restored")
    files_skipped: int = Field(..., description="Files skipped")
    timings_ms: dict[str, int] = Field(default_factory=dict, description="Timing breakdown")


class SnapshotInfo(BaseModel):
    """Snapshot information."""

    snapshot_id: str
    tag: str
    created_at: str
    total_bytes: int
    file_count: int
    encrypted: bool


class SnapshotsResponse(BaseModel):
    """Response for list snapshots."""

    request_id: str = Field(..., description="Request identifier")
    snapshots: list[SnapshotInfo] = Field(default_factory=list, description="Snapshot list")
    count: int = Field(..., description="Total count")


class VerifyResponse(BaseModel):
    """Response for verify operation."""

    request_id: str = Field(..., description="Request identifier")
    report_id: str = Field(..., description="Verification report ID")
    passed: bool = Field(..., description="Verification passed")
    manifest_ok: bool = Field(..., description="Manifest verification")
    sample_files_ok: bool = Field(..., description="Sample files verification")
    decrypt_ok: bool = Field(..., description="Decryption test")
    restore_smoke_ok: bool = Field(..., description="Restore smoke test")
    errors: list[str] = Field(default_factory=list, description="Verification errors")
    timings_ms: dict[str, int] = Field(default_factory=dict, description="Timing breakdown")


# ============================================================================
# Helper Functions
# ============================================================================


def _get_storage_target(target_id: str) -> StorageTarget:
    """
    Get storage target configuration.

    In production, load from database or config.
    For now, use default local storage.
    """
    # TODO: Load from configuration/database
    return StorageTarget(
        target_id=target_id,
        backend=StorageBackend.LOCAL,
        base_path=f"./dr_storage/{target_id}",
        worm=False,
        compression=True,
        options={},
    )


def _get_key_material(key_id: str | None, clock: Clock) -> KeyMaterial | None:
    """
    Get key material by ID.

    In production, load from secure key store.
    For now, generate new key if not provided.
    """
    if not key_id:
        return None

    # TODO: Load from secure key store
    # For now, generate a new key
    kms = KMSStub()
    encryptor = EnvelopeEncryptor(clock, kms)
    return encryptor.generate_key()


# ============================================================================
# Endpoints
# ============================================================================


@router.post("/backup", response_model=BackupResponse)
async def create_backup(
    request_body: BackupRequest,
    request: Request,
    principal: Principal = Depends(require_roles(*allowed_roles("dr.backup"))),
) -> BackupResponse:
    """
    Create a backup snapshot.

    Requires admin or service role.
    """
    clock = get_clock(request)
    request_id = str(uuid.uuid4())
    started_ts = clock.time()

    logger.info(
        f"DR backup request {request_id} from {principal.user_id} "
        f"(spec={request_body.spec.spec_id}, tag={request_body.spec.tag})"
    )

    try:
        # Get storage target
        storage_target = _get_storage_target(request_body.storage_target_id)
        storage_driver = create_storage_driver(storage_target)

        # Get or generate key material
        key_material = None
        encryptor = None
        if request_body.spec.encryption != EncryptionAlgorithm.NONE:
            kms = KMSStub()
            encryptor = EnvelopeEncryptor(clock, kms)
            key_material = _get_key_material(request_body.key_id, clock)
            if not key_material:
                key_material = encryptor.generate_key()

        # Create snapshot
        builder = SnapshotBuilder(clock, encryptor)
        snapshot_meta = builder.build_snapshot(
            request_body.spec,
            storage_driver,
            key_material,
        )

        # Calculate timings
        total_ms = int((clock.time() - started_ts) * 1000)

        logger.info(
            f"DR backup {request_id} completed: snapshot={snapshot_meta.snapshot_id}, "
            f"bytes={snapshot_meta.total_bytes}, files={snapshot_meta.file_count}"
        )

        return BackupResponse(
            request_id=request_id,
            snapshot_id=snapshot_meta.snapshot_id,
            total_bytes=snapshot_meta.total_bytes,
            file_count=snapshot_meta.file_count,
            manifest_hash=snapshot_meta.manifest_hash,
            timings_ms={"total": total_ms},
        )

    except Exception as e:
        logger.error(f"DR backup {request_id} failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Backup failed: {str(e)}",
        ) from e


@router.post("/restore", response_model=RestoreResponse)
async def restore_snapshot(
    request_body: RestoreRequest,
    request: Request,
    principal: Principal = Depends(require_roles(*allowed_roles("dr.restore"))),
) -> RestoreResponse:
    """
    Restore from a snapshot.

    Requires admin or service role.
    """
    clock = get_clock(request)
    request_id = str(uuid.uuid4())
    started_ts = clock.time()

    logger.info(
        f"DR restore request {request_id} from {principal.user_id} "
        f"(snapshot={request_body.snapshot_id}, target={request_body.target_path})"
    )

    try:
        # Get storage target
        storage_target = _get_storage_target(request_body.storage_target_id)
        storage_driver = create_storage_driver(storage_target)

        # Get key material if needed
        key_material = _get_key_material(request_body.key_id, clock)
        encryptor = None
        if key_material:
            kms = KMSStub()
            encryptor = EnvelopeEncryptor(clock, kms)

        # Create restore engine
        restore_engine = RestoreEngine(clock, encryptor)

        # Create and execute restore plan
        plan = restore_engine.create_plan(
            snapshot_id=request_body.snapshot_id,
            target_path=request_body.target_path,
            storage_driver=storage_driver,
            dry_run=request_body.dry_run,
            verify_hashes=True,
            overwrite=request_body.overwrite,
        )

        stats = restore_engine.execute_restore(plan, storage_driver, key_material)

        # Calculate timings
        total_ms = int((clock.time() - started_ts) * 1000)

        logger.info(
            f"DR restore {request_id} completed: plan={plan.plan_id}, "
            f"files={stats['files_restored']}, bytes={stats['bytes_restored']}"
        )

        return RestoreResponse(
            request_id=request_id,
            plan_id=plan.plan_id,
            files_restored=stats["files_restored"],
            bytes_restored=stats["bytes_restored"],
            files_skipped=stats["files_skipped"],
            timings_ms={"total": total_ms},
        )

    except Exception as e:
        logger.error(f"DR restore {request_id} failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Restore failed: {str(e)}",
        ) from e


@router.get("/snapshots", response_model=SnapshotsResponse)
async def list_snapshots(
    request: Request,
    storage_target_id: str,
    tag: str | None = None,
    principal: Principal = Depends(require_roles(*allowed_roles("dr.list"))),
) -> SnapshotsResponse:
    """
    List available snapshots.

    Requires admin, service, or analyst role.
    """
    clock = get_clock(request)
    request_id = str(uuid.uuid4())

    logger.info(
        f"DR list request {request_id} from {principal.user_id} "
        f"(target={storage_target_id}, tag={tag})"
    )

    try:
        # Get storage target
        storage_target = _get_storage_target(storage_target_id)
        storage_driver = create_storage_driver(storage_target)

        # List snapshots
        restore_engine = RestoreEngine(clock)
        snapshot_ids = restore_engine.list_snapshots(storage_driver, tag)

        # Load metadata for each snapshot
        snapshots: list[SnapshotInfo] = []
        for snapshot_id in snapshot_ids:
            try:
                meta = load_snapshot_meta(snapshot_id, storage_driver)
                snapshots.append(
                    SnapshotInfo(
                        snapshot_id=meta.snapshot_id,
                        tag=meta.tag,
                        created_at=meta.created_at,
                        total_bytes=meta.total_bytes,
                        file_count=meta.file_count,
                        encrypted=meta.encrypted,
                    )
                )
            except Exception as e:
                logger.warning(f"Failed to load metadata for snapshot {snapshot_id}: {e}")
                continue

        logger.info(f"DR list {request_id} completed: {len(snapshots)} snapshots")

        return SnapshotsResponse(
            request_id=request_id,
            snapshots=snapshots,
            count=len(snapshots),
        )

    except Exception as e:
        logger.error(f"DR list {request_id} failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"List failed: {str(e)}",
        ) from e


@router.post("/verify/{snapshot_id}", response_model=VerifyResponse)
async def verify_snapshot(
    snapshot_id: str,
    request: Request,
    storage_target_id: str,
    key_id: str | None = None,
    sample_count: int = 5,
    principal: Principal = Depends(require_roles(*allowed_roles("dr.verify"))),
) -> VerifyResponse:
    """
    Verify a snapshot.

    Requires admin or service role.
    """
    clock = get_clock(request)
    request_id = str(uuid.uuid4())
    started_ts = clock.time()

    logger.info(
        f"DR verify request {request_id} from {principal.user_id} " f"(snapshot={snapshot_id})"
    )

    try:
        # Get storage target
        storage_target = _get_storage_target(storage_target_id)
        storage_driver = create_storage_driver(storage_target)

        # Get key material if needed
        key_material = _get_key_material(key_id, clock)
        encryptor = None
        if key_material:
            kms = KMSStub()
            encryptor = EnvelopeEncryptor(clock, kms)

        # Create verifier
        verifier = SnapshotVerifier(clock, encryptor, sample_count)

        # Verify snapshot
        report = verifier.verify_snapshot(snapshot_id, storage_driver, key_material)

        # Calculate timings
        total_ms = int((clock.time() - started_ts) * 1000)

        logger.info(
            f"DR verify {request_id} completed: report={report.report_id}, "
            f"passed={report.passed}"
        )

        return VerifyResponse(
            request_id=request_id,
            report_id=report.report_id,
            passed=report.passed,
            manifest_ok=report.manifest_ok,
            sample_files_ok=report.sample_files_ok,
            decrypt_ok=report.decrypt_ok,
            restore_smoke_ok=report.restore_smoke_ok,
            errors=report.errors,
            timings_ms={"total": total_ms},
        )

    except Exception as e:
        logger.error(f"DR verify {request_id} failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Verification failed: {str(e)}",
        ) from e


__all__ = ["router"]
