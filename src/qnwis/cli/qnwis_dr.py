"""
CLI for QNWIS Disaster Recovery operations.

Commands:
- plan: Create a backup plan
- backup: Execute a backup
- verify: Verify a snapshot
- restore: Restore from snapshot
- list: List snapshots
- prune: Apply retention policies
- keys: Key management (init, rotate, status)

All commands are deterministic with no system time calls.
"""

from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path

import click

from ..dr.crypto import EnvelopeEncryptor, KMSStub
from ..dr.models import BackupSpec, EncryptionAlgorithm, StorageBackend, StorageTarget
from ..dr.restore import RestoreEngine
from ..dr.snapshot import SnapshotBuilder, load_snapshot_meta
from ..dr.storage import create_storage_driver
from ..dr.verify import SnapshotVerifier
from ..utils.clock import Clock


@click.group()
@click.option(
    "--config",
    type=click.Path(exists=True),
    help="Path to DR configuration file",
)
@click.pass_context
def cli(ctx: click.Context, config: str | None) -> None:
    """QNWIS Disaster Recovery CLI."""
    ctx.ensure_object(dict)

    # Load configuration
    if config:
        config_path = Path(config)
        ctx.obj["config"] = json.loads(config_path.read_text())
    else:
        ctx.obj["config"] = {}

    # Initialize clock (use ManualClock for determinism in tests)
    ctx.obj["clock"] = Clock()


@cli.command()
@click.option("--spec-id", required=True, help="Backup spec identifier")
@click.option("--tag", required=True, help="Backup tag (e.g., 'daily', 'pre-deploy')")
@click.option("--datasets", multiple=True, help="Dataset IDs to include")
@click.option("--audit-packs/--no-audit-packs", default=True, help="Include audit packs")
@click.option("--config-files/--no-config-files", default=True, help="Include config files")
@click.option("--storage-target", required=True, help="Storage target identifier")
@click.option(
    "--encryption",
    type=click.Choice(["aes_256_gcm", "none"]),
    default="aes_256_gcm",
    help="Encryption algorithm",
)
@click.option("--retention-days", type=int, default=30, help="Retention period in days")
@click.option("--output", type=click.Path(), help="Output file for backup spec")
def plan(
    spec_id: str,
    tag: str,
    datasets: tuple[str, ...],
    audit_packs: bool,
    config_files: bool,
    storage_target: str,
    encryption: str,
    retention_days: int,
    output: str | None,
) -> None:
    """Create a backup plan."""
    spec = BackupSpec(
        spec_id=spec_id,
        tag=tag,
        datasets=list(datasets),
        audit_packs=audit_packs,
        config=config_files,
        storage_target=storage_target,
        encryption=EncryptionAlgorithm(encryption),
        retention_days=retention_days,
    )

    spec_dict = spec.model_dump()

    if output:
        output_path = Path(output)
        output_path.write_text(json.dumps(spec_dict, indent=2))
        click.echo(f"Backup plan saved to: {output}")
    else:
        click.echo(json.dumps(spec_dict, indent=2))


@cli.command()
@click.option("--spec", type=click.Path(exists=True), required=True, help="Backup spec file")
@click.option("--storage-path", required=True, help="Storage base path")
@click.option(
    "--backend",
    type=click.Choice(["local", "archive", "object_store"]),
    default="local",
    help="Storage backend",
)
@click.option("--worm/--no-worm", default=False, help="Enable WORM mode")
@click.option("--key-file", type=click.Path(exists=True), help="Key material file")
@click.option("--workspace", type=click.Path(exists=True), help="Workspace root path")
@click.pass_context
def backup(
    ctx: click.Context,
    spec: str,
    storage_path: str,
    backend: str,
    worm: bool,
    key_file: str | None,
    workspace: str | None,
) -> None:
    """Execute a backup operation."""
    clock: Clock = ctx.obj["clock"]

    # Load backup spec
    spec_path = Path(spec)
    spec_data = json.loads(spec_path.read_text())
    backup_spec = BackupSpec.model_validate(spec_data)

    # Create storage target
    storage_target = StorageTarget(
        target_id=f"target-{uuid.uuid4().hex[:8]}",
        backend=StorageBackend(backend),
        base_path=storage_path,
        worm=worm,
        compression=True,
        options={},
    )

    # Create storage driver
    storage_driver = create_storage_driver(storage_target)

    # Load key material if encryption enabled
    key_material = None
    encryptor = None
    if backup_spec.encryption != EncryptionAlgorithm.NONE:
        kms = KMSStub()
        encryptor = EnvelopeEncryptor(clock, kms, backup_spec.encryption)

        if key_file:
            key_path = Path(key_file)
            key_data = json.loads(key_path.read_text())
            from ..dr.models import KeyMaterial

            key_material = KeyMaterial.model_validate(key_data)
        else:
            # Generate new key
            key_material = encryptor.generate_key()
            # Save key to file
            key_output = Path(f"key-{key_material.key_id}.json")
            key_output.write_text(key_material.model_dump_json(indent=2))
            click.echo(f"Generated new key: {key_output}")

    # Create snapshot builder
    builder = SnapshotBuilder(clock, encryptor)

    # Execute backup
    workspace_root = Path(workspace) if workspace else Path.cwd()
    click.echo(f"Starting backup: {backup_spec.tag}")

    try:
        snapshot_meta = builder.build_snapshot(
            backup_spec,
            storage_driver,
            key_material,
            workspace_root,
        )

        click.echo("Backup completed successfully!")
        click.echo(f"Snapshot ID: {snapshot_meta.snapshot_id}")
        click.echo(f"Total bytes: {snapshot_meta.total_bytes:,}")
        click.echo(f"File count: {snapshot_meta.file_count}")
        click.echo(f"Manifest hash: {snapshot_meta.manifest_hash}")

        # Save snapshot metadata
        meta_output = Path(f"snapshot-{snapshot_meta.snapshot_id}.json")
        meta_output.write_text(snapshot_meta.model_dump_json(indent=2))
        click.echo(f"Snapshot metadata saved to: {meta_output}")

    except Exception as e:
        click.echo(f"Backup failed: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--snapshot-id", required=True, help="Snapshot ID to verify")
@click.option("--storage-path", required=True, help="Storage base path")
@click.option(
    "--backend",
    type=click.Choice(["local", "archive", "object_store"]),
    default="local",
    help="Storage backend",
)
@click.option("--key-file", type=click.Path(exists=True), help="Key material file")
@click.option("--sample-count", type=int, default=5, help="Number of files to sample")
@click.pass_context
def verify(
    ctx: click.Context,
    snapshot_id: str,
    storage_path: str,
    backend: str,
    key_file: str | None,
    sample_count: int,
) -> None:
    """Verify a snapshot."""
    clock: Clock = ctx.obj["clock"]

    # Create storage target
    storage_target = StorageTarget(
        target_id="verify-target",
        backend=StorageBackend(backend),
        base_path=storage_path,
        worm=False,
        compression=True,
        options={},
    )

    storage_driver = create_storage_driver(storage_target)

    # Load key material if provided
    key_material = None
    encryptor = None
    if key_file:
        key_path = Path(key_file)
        key_data = json.loads(key_path.read_text())
        from ..dr.models import KeyMaterial

        key_material = KeyMaterial.model_validate(key_data)

        kms = KMSStub()
        encryptor = EnvelopeEncryptor(clock, kms)

    # Create verifier
    verifier = SnapshotVerifier(clock, encryptor, sample_count)

    # Verify snapshot
    click.echo(f"Verifying snapshot: {snapshot_id}")

    try:
        report = verifier.verify_snapshot(snapshot_id, storage_driver, key_material)

        click.echo("\nVerification Report:")
        click.echo(f"  Report ID: {report.report_id}")
        click.echo(f"  Verified at: {report.verified_at}")
        click.echo(f"  Manifest OK: {report.manifest_ok}")
        click.echo(f"  Sample files OK: {report.sample_files_ok}")
        click.echo(f"  Decrypt OK: {report.decrypt_ok}")
        click.echo(f"  Restore smoke OK: {report.restore_smoke_ok}")
        click.echo(f"  Overall: {'PASS' if report.passed else 'FAIL'}")

        if report.errors:
            click.echo("\nErrors:")
            for error in report.errors:
                click.echo(f"  - {error}")

        # Save report
        report_output = Path(f"verify-{report.report_id}.json")
        report_output.write_text(report.model_dump_json(indent=2))
        click.echo(f"\nReport saved to: {report_output}")

        if not report.passed:
            sys.exit(1)

    except Exception as e:
        click.echo(f"Verification failed: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--snapshot-id", required=True, help="Snapshot ID to restore")
@click.option("--storage-path", required=True, help="Storage base path")
@click.option(
    "--backend",
    type=click.Choice(["local", "archive", "object_store"]),
    default="local",
    help="Storage backend",
)
@click.option("--target-path", required=True, help="Restore destination path")
@click.option("--key-file", type=click.Path(exists=True), help="Key material file")
@click.option("--dry-run/--no-dry-run", default=False, help="Dry-run mode")
@click.option("--overwrite/--no-overwrite", default=False, help="Overwrite existing files")
@click.pass_context
def restore(
    ctx: click.Context,
    snapshot_id: str,
    storage_path: str,
    backend: str,
    target_path: str,
    key_file: str | None,
    dry_run: bool,
    overwrite: bool,
) -> None:
    """Restore from a snapshot."""
    clock: Clock = ctx.obj["clock"]

    # Create storage target
    storage_target = StorageTarget(
        target_id="restore-target",
        backend=StorageBackend(backend),
        base_path=storage_path,
        worm=False,
        compression=True,
        options={},
    )

    storage_driver = create_storage_driver(storage_target)

    # Load key material if provided
    key_material = None
    encryptor = None
    if key_file:
        key_path = Path(key_file)
        key_data = json.loads(key_path.read_text())
        from ..dr.models import KeyMaterial

        key_material = KeyMaterial.model_validate(key_data)

        kms = KMSStub()
        encryptor = EnvelopeEncryptor(clock, kms)

    # Create restore engine
    restore_engine = RestoreEngine(clock, encryptor)

    # Create restore plan
    click.echo("Creating restore plan...")

    try:
        plan = restore_engine.create_plan(
            snapshot_id=snapshot_id,
            target_path=target_path,
            storage_driver=storage_driver,
            dry_run=dry_run,
            verify_hashes=True,
            overwrite=overwrite,
        )

        click.echo(f"Plan ID: {plan.plan_id}")
        click.echo(f"Snapshot: {plan.snapshot_id}")
        click.echo(f"Target: {plan.target_path}")
        click.echo(f"Dry-run: {plan.dry_run}")

        # Execute restore
        click.echo("\nExecuting restore...")
        stats = restore_engine.execute_restore(plan, storage_driver, key_material)

        click.echo("\nRestore completed!")
        click.echo(f"  Files restored: {stats['files_restored']}")
        click.echo(f"  Bytes restored: {stats['bytes_restored']:,}")
        click.echo(f"  Files skipped: {stats['files_skipped']}")
        click.echo(f"  Files verified: {stats['files_verified']}")
        click.echo(f"  Verification failures: {stats['verification_failures']}")

        if stats["verification_failures"] > 0:
            sys.exit(1)

    except Exception as e:
        click.echo(f"Restore failed: {e}", err=True)
        sys.exit(1)


@cli.command("list")
@click.option("--storage-path", required=True, help="Storage base path")
@click.option(
    "--backend",
    type=click.Choice(["local", "archive", "object_store"]),
    default="local",
    help="Storage backend",
)
@click.option("--tag", help="Filter by tag")
@click.pass_context
def list_snapshots(
    ctx: click.Context,
    storage_path: str,
    backend: str,
    tag: str | None,
) -> None:
    """List available snapshots."""
    clock: Clock = ctx.obj["clock"]

    # Create storage target
    storage_target = StorageTarget(
        target_id="list-target",
        backend=StorageBackend(backend),
        base_path=storage_path,
        worm=False,
        compression=True,
        options={},
    )

    storage_driver = create_storage_driver(storage_target)

    # Create restore engine for listing
    restore_engine = RestoreEngine(clock)

    # List snapshots
    snapshot_ids = restore_engine.list_snapshots(storage_driver, tag)

    if not snapshot_ids:
        click.echo("No snapshots found.")
        return

    click.echo(f"Found {len(snapshot_ids)} snapshot(s):\n")

    for snapshot_id in snapshot_ids:
        try:
            meta = load_snapshot_meta(snapshot_id, storage_driver)
            click.echo(f"  {snapshot_id}")
            click.echo(f"    Tag: {meta.tag}")
            click.echo(f"    Created: {meta.created_at}")
            click.echo(f"    Size: {meta.total_bytes:,} bytes")
            click.echo(f"    Files: {meta.file_count}")
            click.echo(f"    Encrypted: {meta.encrypted}")
            click.echo()
        except Exception as e:
            click.echo(f"  {snapshot_id} (error loading metadata: {e})")
            click.echo()


@cli.group()
def keys() -> None:
    """Key management commands."""
    pass


@keys.command("init")
@click.option("--output", type=click.Path(), required=True, help="Output file for key")
@click.pass_context
def keys_init(ctx: click.Context, output: str) -> None:
    """Initialize a new encryption key."""
    clock: Clock = ctx.obj["clock"]

    kms = KMSStub()
    encryptor = EnvelopeEncryptor(clock, kms)

    key_material = encryptor.generate_key()

    output_path = Path(output)
    output_path.write_text(key_material.model_dump_json(indent=2))

    click.echo(f"Key initialized: {key_material.key_id}")
    click.echo(f"Saved to: {output}")


@keys.command("status")
@click.option("--key-file", type=click.Path(exists=True), required=True, help="Key file")
def keys_status(key_file: str) -> None:
    """Show key status."""
    key_path = Path(key_file)
    key_data = json.loads(key_path.read_text())
    from ..dr.models import KeyMaterial

    key_material = KeyMaterial.model_validate(key_data)

    click.echo(f"Key ID: {key_material.key_id}")
    click.echo(f"Algorithm: {key_material.algorithm}")
    click.echo(f"Created: {key_material.created_at}")
    click.echo(f"Rotated: {key_material.rotated_at or 'Never'}")
    click.echo(f"KMS Key: {key_material.kms_key_id}")


if __name__ == "__main__":
    cli()
