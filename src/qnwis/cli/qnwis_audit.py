"""
CLI tool for managing QNWIS audit trails.

Commands:
  show     - Display audit manifest details
  list     - List recent audit runs
  export   - Export audit pack as zip or directory
  verify   - Verify audit pack integrity (digest/HMAC)
  prune    - Delete packs older than retention policy
"""

from __future__ import annotations

import argparse
import json
import logging
import shutil
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

# Setup basic logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def _get_audit_config() -> dict[str, str | None]:
    """Load audit configuration from orchestration.yml."""
    defaults = {
        "pack_dir": "./audit_packs",
        "sqlite_path": "./audit/audit.db",
        "hmac_env": "QNWIS_AUDIT_HMAC_KEY",
        "retention_days": 90,
    }

    config_path = Path("src/qnwis/config/orchestration.yml")
    if not config_path.exists():
        logger.warning("Orchestration config not found, using defaults")
        return defaults.copy()

    try:
        import yaml

        with open(config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f)
        audit_config = config.get("audit", {})
        merged = defaults.copy()
        merged.update({k: audit_config.get(k, defaults.get(k)) for k in defaults})
        return merged
    except Exception as exc:
        logger.error("Failed to load audit config: %s", exc)
        return defaults.copy()


def _parse_iso8601(value: str) -> datetime | None:
    """
    Parse ISO 8601 timestamp into aware datetime.

    Returns:
        Parsed datetime or None on failure.
    """
    try:
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed
    except Exception:
        return None


def cmd_show(args: argparse.Namespace) -> int:
    """Show audit manifest details."""
    from ..verification.audit_store import FileSystemAuditTrailStore

    config = _get_audit_config()
    store = FileSystemAuditTrailStore(config["pack_dir"])

    manifest = store.load_manifest(args.audit_id)
    if not manifest:
        print(f"ERROR: Audit pack not found: {args.audit_id}")
        return 1

    manifest_dict = manifest.to_dict()

    if args.json:
        print(json.dumps(manifest_dict, indent=2))
    else:
        # Human-readable display
        print(f"\n{'='*70}")
        print(f"Audit Manifest: {manifest.audit_id}")
        print(f"{'='*70}\n")

        print(f"Created:         {manifest.created_at}")
        print(f"Request ID:      {manifest.request_id}")
        print(f"Registry:        {manifest.registry_version}")
        print(f"Code Version:    {manifest.code_version}")
        print(f"\nData Sources:    {len(manifest.data_sources)}")
        for source in manifest.data_sources:
            freshness = manifest.freshness.get(source, "unknown")
            print(f"  - {source} (as of {freshness})")

        print(f"\nQuery IDs:       {len(manifest.query_ids)}")
        for qid in manifest.query_ids[:10]:
            print(f"  - {qid}")
        if len(manifest.query_ids) > 10:
            print(f"  ... ({len(manifest.query_ids) - 10} more)")

        print("\nCitations:")
        cit = manifest.citations
        print(f"  Status:        {'PASS' if cit.get('ok') else 'FAIL'}")
        print(f"  Total Claims:  {cit.get('total_numbers', 0)}")
        print(f"  Cited:         {cit.get('cited_numbers', 0)}")
        print(f"  Uncited:       {cit.get('uncited_count', 0)}")

        print("\nVerification:")
        ver = manifest.verification
        print(f"  Status:        {'PASS' if ver.get('ok') else 'FAIL'}")
        print(f"  Issues:        {ver.get('issues_count', 0)}")
        print(f"  Redactions:    {ver.get('redactions_applied', 0)}")

        if "result_verification" in ver:
            rv = ver["result_verification"]
            print("\n  Result Verification:")
            print(f"    Status:      {'PASS' if rv.get('ok') else 'FAIL'}")
            print(f"    Claims:      {rv.get('claims_matched')} / {rv.get('claims_total')}")

        print("\nIntegrity:")
        print(f"  SHA-256:       {manifest.digest_sha256[:32]}...")
        if manifest.hmac_sha256:
            print(f"  HMAC-SHA256:   {manifest.hmac_sha256[:32]}...")

        print(f"\nPack Files:      {len(manifest.pack_paths)}")

    return 0


def cmd_list(args: argparse.Namespace) -> int:
    """List recent audit runs."""
    config = _get_audit_config()

    # Try SQLite first, fallback to filesystem
    manifests = []
    source = "Filesystem"
    if config.get("sqlite_path"):
        try:
            from ..verification.audit_store import SQLiteAuditTrailStore

            store = SQLiteAuditTrailStore(str(config["sqlite_path"]))
            manifests = store.list_recent(limit=args.limit)
            source = "SQLite"
        except Exception as exc:
            logger.warning("SQLite unavailable, using filesystem: %s", exc)

    if not manifests:
        from ..verification.audit_store import FileSystemAuditTrailStore

        fs_store = FileSystemAuditTrailStore(str(config["pack_dir"]))
        audit_ids = fs_store.list_all()[: args.limit]
        manifests = [fs_store.load_manifest(aid) for aid in audit_ids]
        manifests = [m for m in manifests if m]

    if not manifests:
        print("No audit packs found.")
        return 0

    print(f"\nRecent Audit Runs ({source}):\n")
    print(f"{'Audit ID':<38} {'Created':<20} {'Request ID':<20} {'Status'}")
    print("-" * 100)

    for manifest in manifests:
        ver_status = "PASS" if manifest.verification.get("ok") else "FAIL"
        cit_status = "PASS" if manifest.citations.get("ok") else "FAIL"
        status = f"V:{ver_status} C:{cit_status}"

        created = manifest.created_at[:19]  # Trim microseconds
        request_id = manifest.request_id[:18] if len(manifest.request_id) > 18 else manifest.request_id

        print(f"{manifest.audit_id:<38} {created:<20} {request_id:<20} {status}")

    print(f"\nTotal: {len(manifests)} audit pack(s)")
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    """Export audit pack as zip or directory."""
    from ..verification.audit_store import FileSystemAuditTrailStore

    config = _get_audit_config()
    store = FileSystemAuditTrailStore(config["pack_dir"])

    pack_path = store.get_path(args.audit_id)
    if not pack_path:
        print(f"ERROR: Audit pack not found: {args.audit_id}")
        return 1

    output = Path(args.out)

    if args.format == "zip":
        # Create zip archive
        if not output.suffix:
            output = output.with_suffix(".zip")

        base_name = str(output.with_suffix(""))
        shutil.make_archive(base_name, "zip", pack_path)
        print(f"Exported to: {output}")

    elif args.format == "dir":
        # Copy to directory
        output.mkdir(parents=True, exist_ok=True)
        shutil.copytree(pack_path, output / args.audit_id, dirs_exist_ok=True)
        print(f"Exported to: {output / args.audit_id}")

    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    """Verify audit pack integrity."""
    import os

    from ..verification.audit_trail import AuditTrail

    config = _get_audit_config()

    hmac_key = None
    hmac_env = config.get("hmac_env")
    if hmac_env:
        secret = os.environ.get(hmac_env)
        if secret:
            hmac_key = secret.encode("utf-8")

    def _verify(pack_dir: Path, audit_id: str) -> int:
        trail = AuditTrail(pack_dir=str(pack_dir), hmac_key=hmac_key)
        is_valid, reasons = trail.verify_pack(audit_id)
        if is_valid:
            print(f"[OK] {audit_id}")
            return 0
        print(f"[FAIL] {audit_id}")
        for reason in reasons:
            print(f"  - {reason}")
        return 1

    if args.path:
        pack_path = Path(args.path).resolve()
        if not pack_path.exists():
            print(f"ERROR: Path not found: {pack_path}")
            return 1
        return _verify(pack_path.parent, pack_path.name)

    if args.audit_id:
        pack_dir = Path(str(config["pack_dir"])).resolve()
        return _verify(pack_dir, args.audit_id)

    print("ERROR: Must specify --audit-id or --path")
    return 1


def cmd_prune(args: argparse.Namespace) -> int:  # noqa: C901
    """Prune audit packs older than the retention window."""
    from ..verification.audit_store import (
        FileSystemAuditTrailStore,
        SQLiteAuditTrailStore,
    )

    config = _get_audit_config()

    days = args.days if args.days is not None else config.get("retention_days")
    if days is None:
        print("ERROR: Retention days not configured.")
        return 1

    try:
        days_int = int(days)
    except (TypeError, ValueError):
        print(f"ERROR: Invalid retention days: {days}")
        return 1

    cutoff = datetime.now(UTC) - timedelta(days=days_int)
    fs_store = FileSystemAuditTrailStore(str(config["pack_dir"]))

    sqlite_store = None
    if config.get("sqlite_path"):
        try:
            sqlite_store = SQLiteAuditTrailStore(str(config["sqlite_path"]))
        except Exception as exc:
            logger.warning("Unable to open SQLite store for pruning: %s", exc)

    removed: list[tuple[str, str]] = []
    for audit_id in fs_store.list_all():
        manifest = fs_store.load_manifest(audit_id)
        if not manifest:
            continue
        created_dt = _parse_iso8601(manifest.created_at)
        if created_dt and created_dt < cutoff:
            pack_path = fs_store.get_path(audit_id)
            if pack_path and Path(pack_path).exists():
                shutil.rmtree(pack_path, ignore_errors=True)
            if sqlite_store:
                sqlite_store.delete(audit_id)
            removed.append((audit_id, manifest.created_at))

    if not removed:
        print(f"No audit packs older than {days_int} day(s).")
        return 0

    print(f"Removed {len(removed)} audit pack(s) older than {days_int} day(s):")
    for audit_id, created in removed:
        print(f"  - {audit_id} (created {created})")
    return 0


def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="QNWIS Audit Trail Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # show command
    show_parser = subparsers.add_parser("show", help="Display audit manifest details")
    show_parser.add_argument("audit_id", help="Audit ID to display")
    show_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # list command
    list_parser = subparsers.add_parser("list", help="List recent audit runs")
    list_parser.add_argument(
        "--limit", type=int, default=20, help="Maximum number to display"
    )

    # export command
    export_parser = subparsers.add_parser("export", help="Export audit pack")
    export_parser.add_argument("audit_id", help="Audit ID to export")
    export_parser.add_argument("--out", required=True, help="Output path")
    export_parser.add_argument(
        "--format",
        choices=["zip", "dir"],
        default="zip",
        help="Export format (zip or dir)",
    )

    # verify command
    verify_parser = subparsers.add_parser("verify", help="Verify audit pack integrity")
    verify_parser.add_argument("--audit-id", help="Audit ID to verify")
    verify_parser.add_argument("--path", help="Path to audit pack directory")

    # prune command
    prune_parser = subparsers.add_parser(
        "prune", help="Delete audit packs older than the retention window"
    )
    prune_parser.add_argument(
        "--days",
        type=int,
        help="Override retention threshold in days (defaults to config)",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Dispatch to command handler
    if args.command == "show":
        return cmd_show(args)
    elif args.command == "list":
        return cmd_list(args)
    elif args.command == "export":
        return cmd_export(args)
    elif args.command == "verify":
        return cmd_verify(args)
    elif args.command == "prune":
        return cmd_prune(args)
    else:
        print(f"ERROR: Unknown command: {args.command}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
