"""
Disaster Recovery & Backups module for QNWIS.

Provides deterministic, production-grade backup/restore capabilities with:
- Snapshot creation with integrity verification
- Pluggable storage backends (local, archive, object store)
- Envelope encryption with key management
- Retention policies and scheduling
- Restore with dry-run and validation
- Full auditability and metrics
"""

from __future__ import annotations

__all__ = [
    "BackupSpec",
    "SnapshotMeta",
    "RestorePlan",
    "StorageTarget",
    "KeyMaterial",
    "Policy",
]
