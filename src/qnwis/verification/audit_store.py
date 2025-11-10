"""
Storage backends for audit trail persistence and retrieval.

Provides SQLite database indexing and filesystem-based storage for audit manifests.
"""

from __future__ import annotations

import json
import logging
import shutil
import sqlite3
from pathlib import Path

from .audit_trail import AuditManifest

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 1


class SQLiteAuditTrailStore:
    """
    SQLite-backed audit trail store for indexing and retrieval.

    Maintains an index of audit manifests with key metadata for fast queries.
    Full manifests are still stored on disk; this provides search capabilities.
    """

    def __init__(self, db_path: str):
        """
        Initialize SQLite store.

        Args:
            db_path: Path to SQLite database file (will be created if needed)
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Create schema if needed
        self._init_schema()
        logger.info("SQLite audit store initialized: %s", self.db_path)

    def _init_schema(self) -> None:
        """Create or migrate schema and ensure WAL mode is enabled."""
        with sqlite3.connect(str(self.db_path)) as conn:
            # Enable WAL for concurrent readers/writers
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            current_version = conn.execute("PRAGMA user_version;").fetchone()[0]

            if current_version == 0:
                self._create_schema(conn)
                conn.execute(f"PRAGMA user_version={SCHEMA_VERSION};")
                logger.info(
                    "Initialized audit SQLite schema (version %s)", SCHEMA_VERSION
                )
            elif current_version < SCHEMA_VERSION:
                self._migrate_schema(conn, current_version, SCHEMA_VERSION)
                conn.execute(f"PRAGMA user_version={SCHEMA_VERSION};")
                logger.info(
                    "Migrated audit SQLite schema from v%s to v%s",
                    current_version,
                    SCHEMA_VERSION,
                )
            elif current_version > SCHEMA_VERSION:
                raise RuntimeError(
                    "SQLite audit store schema is newer than supported "
                    f"(db={current_version}, code={SCHEMA_VERSION}). "
                    "Please upgrade the runtime."
                )

    def _create_schema(self, conn: sqlite3.Connection) -> None:
        """Create audit_manifests table and supporting indices."""
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_manifests (
                audit_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                request_id TEXT NOT NULL,
                registry_version TEXT NOT NULL,
                code_version TEXT NOT NULL,
                data_sources TEXT NOT NULL,
                query_ids TEXT NOT NULL,
                freshness TEXT NOT NULL,
                citations_ok INTEGER NOT NULL,
                verification_ok INTEGER NOT NULL,
                digest_sha256 TEXT NOT NULL,
                hmac_sha256 TEXT,
                pack_root TEXT NOT NULL,
                manifest_json TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_created_at
            ON audit_manifests(created_at DESC)
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_request_id
            ON audit_manifests(request_id)
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_verification_ok
            ON audit_manifests(verification_ok)
            """
        )

    def _migrate_schema(
        self,
        conn: sqlite3.Connection,
        current_version: int,
        target_version: int,
    ) -> None:
        """Perform in-place schema migrations."""
        if current_version == 0:
            self._create_schema(conn)
            return

        raise RuntimeError(
            f"No migration path from version {current_version} to {target_version}"
        )

    def upsert(self, manifest: AuditManifest) -> None:
        """
        Insert or update audit manifest in store.

        Args:
            manifest: AuditManifest to store
        """
        manifest_dict = manifest.to_dict()
        manifest_json = json.dumps(manifest_dict, ensure_ascii=False)

        pack_root = manifest.pack_root or ""
        if not pack_root and manifest.pack_paths.get("manifest"):
            pack_root = str(Path(manifest.pack_paths["manifest"]).parent)

        payload = (
            manifest.audit_id,
            manifest.created_at,
            manifest.request_id,
            manifest.registry_version,
            manifest.code_version,
            json.dumps(manifest.data_sources),
            json.dumps(manifest.query_ids),
            json.dumps(manifest.freshness),
            int(manifest.citations.get("ok", False)),
            int(manifest.verification.get("ok", False)),
            manifest.digest_sha256,
            manifest.hmac_sha256,
            pack_root,
            manifest_json,
        )

        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                """
                INSERT INTO audit_manifests (
                    audit_id, created_at, request_id, registry_version, code_version,
                    data_sources, query_ids, freshness,
                    citations_ok, verification_ok,
                    digest_sha256, hmac_sha256, pack_root, manifest_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(audit_id) DO UPDATE SET
                    created_at=excluded.created_at,
                    request_id=excluded.request_id,
                    registry_version=excluded.registry_version,
                    code_version=excluded.code_version,
                    data_sources=excluded.data_sources,
                    query_ids=excluded.query_ids,
                    freshness=excluded.freshness,
                    citations_ok=excluded.citations_ok,
                    verification_ok=excluded.verification_ok,
                    digest_sha256=excluded.digest_sha256,
                    hmac_sha256=excluded.hmac_sha256,
                    pack_root=excluded.pack_root,
                    manifest_json=excluded.manifest_json
                """,
                payload,
            )

        logger.debug("Upserted audit manifest: %s", manifest.audit_id)

    def get(self, audit_id: str) -> AuditManifest | None:
        """
        Retrieve audit manifest by ID.

        Args:
            audit_id: Audit ID to retrieve

        Returns:
            AuditManifest if found, None otherwise
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute(
                "SELECT manifest_json FROM audit_manifests WHERE audit_id = ?",
                (audit_id,),
            )
            row = cursor.fetchone()

        if not row:
            return None

        manifest_data = json.loads(row[0])
        return AuditManifest.from_dict(manifest_data)

    def list_recent(self, limit: int = 50) -> list[AuditManifest]:
        """
        List recent audit manifests ordered by creation time.

        Args:
            limit: Maximum number of manifests to return

        Returns:
            List of AuditManifest objects, newest first
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute(
                """
                SELECT manifest_json FROM audit_manifests
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = cursor.fetchall()

        manifests = []
        for row in rows:
            try:
                manifest_data = json.loads(row[0])
                manifests.append(AuditManifest.from_dict(manifest_data))
            except Exception as exc:
                logger.warning("Failed to deserialize manifest: %s", exc)

        return manifests

    def delete(self, audit_id: str) -> None:
        """
        Delete manifest entry by audit ID.

        Args:
            audit_id: Identifier to delete.
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                "DELETE FROM audit_manifests WHERE audit_id = ?",
                (audit_id,),
            )
        logger.debug("Deleted audit manifest record: %s", audit_id)

    def search_by_request_id(self, request_id: str) -> list[AuditManifest]:
        """
        Find audit manifests by request ID.

        Args:
            request_id: Request ID to search for

        Returns:
            List of matching AuditManifest objects
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute(
                """
                SELECT manifest_json FROM audit_manifests
                WHERE request_id = ?
                ORDER BY created_at DESC
                """,
                (request_id,),
            )
            rows = cursor.fetchall()

        manifests = []
        for row in rows:
            try:
                manifest_data = json.loads(row[0])
                manifests.append(AuditManifest.from_dict(manifest_data))
            except Exception as exc:
                logger.warning("Failed to deserialize manifest: %s", exc)

        return manifests

    def list_failed_verifications(self, limit: int = 50) -> list[AuditManifest]:
        """
        List audit manifests with verification failures.

        Args:
            limit: Maximum number of manifests to return

        Returns:
            List of AuditManifest objects with verification_ok=False
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute(
                """
                SELECT manifest_json FROM audit_manifests
                WHERE verification_ok = 0
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = cursor.fetchall()

        manifests = []
        for row in rows:
            try:
                manifest_data = json.loads(row[0])
                manifests.append(AuditManifest.from_dict(manifest_data))
            except Exception as exc:
                logger.warning("Failed to deserialize manifest: %s", exc)

        return manifests


class FileSystemAuditTrailStore:
    """
    Filesystem-based audit trail store.

    Provides simple directory indexing and path resolution for audit packs.
    """

    def __init__(self, root_dir: str):
        """
        Initialize filesystem store.

        Args:
            root_dir: Root directory containing audit pack subdirectories
        """
        self.root_dir = Path(root_dir)
        self.root_dir.mkdir(parents=True, exist_ok=True)
        logger.info("Filesystem audit store initialized: %s", self.root_dir)

    def index(self, manifest: AuditManifest) -> None:
        """
        Ensure audit pack directory is registered under the filesystem root.

        If the pack was written outside ``root_dir`` it will be copied
        (metadata only) so commands such as ``list`` or ``show`` can still
        discover it.
        """
        pack_root = Path(manifest.pack_root).resolve() if manifest.pack_root else None
        target_dir = self.root_dir / manifest.audit_id

        if pack_root and pack_root == target_dir.resolve():
            return

        if pack_root and pack_root.exists():
            if target_dir.exists():
                return
            shutil.copytree(pack_root, target_dir, dirs_exist_ok=True)
            logger.debug(
                "Copied audit pack from %s to %s for indexing",
                pack_root,
                target_dir,
            )
        else:
            target_dir.mkdir(parents=True, exist_ok=True)
            manifest_path = target_dir / "manifest.json"
            manifest_path.write_text(
                json.dumps(manifest.to_dict(), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            logger.debug(
                "Created placeholder manifest in %s because source was missing",
                target_dir,
            )

    def get_path(self, audit_id: str) -> str | None:
        """
        Get filesystem path for an audit pack.

        Args:
            audit_id: Audit ID to locate

        Returns:
            Absolute path to audit pack directory if exists, None otherwise
        """
        pack_path = self.root_dir / audit_id
        if pack_path.exists() and pack_path.is_dir():
            return str(pack_path)
        return None

    def list_all(self) -> list[str]:
        """
        List all audit IDs in store.

        Returns:
            List of audit ID strings (directory names)
        """
        audit_ids = []
        for item in self.root_dir.iterdir():
            # Verify it looks like an audit pack (has manifest.json)
            if item.is_dir() and (item / "manifest.json").exists():
                audit_ids.append(item.name)
        return sorted(audit_ids, reverse=True)

    def load_manifest(self, audit_id: str) -> AuditManifest | None:
        """
        Load audit manifest from filesystem.

        Args:
            audit_id: Audit ID to load

        Returns:
            AuditManifest if found and valid, None otherwise
        """
        pack_path = self.root_dir / audit_id
        manifest_path = pack_path / "manifest.json"

        if not manifest_path.exists():
            return None

        try:
            manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
            return AuditManifest.from_dict(manifest_data)
        except Exception as exc:
            logger.warning("Failed to load manifest %s: %s", audit_id, exc)
            return None
