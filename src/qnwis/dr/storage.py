"""
Pluggable storage backends for DR backups.

Provides LocalStore (filesystem), ArchiveStore (tar.gz), and ObjectStoreStub (S3-like).
All backends support WORM mode and integrity verification.
"""

from __future__ import annotations

import gzip
import hashlib
from abc import ABC, abstractmethod
from pathlib import Path

from .models import StorageBackend, StorageTarget


class StorageDriver(ABC):
    """Abstract base class for storage drivers."""

    def __init__(self, target: StorageTarget) -> None:
        """
        Initialize storage driver.

        Args:
            target: Storage target configuration
        """
        self.target = target
        self._base_path = Path(target.base_path).resolve()
        self._base_path.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    def write(self, key: str, data: bytes) -> str:
        """
        Write data to storage.

        Args:
            key: Storage key/path
            data: Data to write

        Returns:
            Full storage path/key

        Raises:
            ValueError: If WORM mode and key exists
        """
        pass

    @abstractmethod
    def read(self, key: str) -> bytes:
        """
        Read data from storage.

        Args:
            key: Storage key/path

        Returns:
            Data bytes

        Raises:
            FileNotFoundError: If key doesn't exist
        """
        pass

    @abstractmethod
    def exists(self, key: str) -> bool:
        """
        Check if key exists in storage.

        Args:
            key: Storage key/path

        Returns:
            True if exists
        """
        pass

    @abstractmethod
    def delete(self, key: str) -> None:
        """
        Delete data from storage.

        Args:
            key: Storage key/path

        Raises:
            ValueError: If WORM mode enabled
        """
        pass

    @abstractmethod
    def list_keys(self, prefix: str = "") -> list[str]:
        """
        List keys with optional prefix.

        Args:
            prefix: Key prefix filter

        Returns:
            List of matching keys
        """
        pass

    def _resolve_relative(self, relative: str | Path) -> Path:
        """Resolve a path relative to the storage base safely."""
        return self._resolve_under(self._base_path, relative)

    @staticmethod
    def _resolve_under(root: Path, relative: str | Path) -> Path:
        """Resolve a path under a provided root while preventing traversal."""
        candidate = (root / relative).resolve()
        try:
            candidate.relative_to(root)
        except ValueError as exc:  # pragma: no cover - safety net
            raise ValueError(f"Path '{relative}' escapes allowed root '{root}'") from exc
        return candidate

    def verify_integrity(self, key: str, expected_hash: str) -> bool:
        """
        Verify data integrity using SHA-256.

        Args:
            key: Storage key/path
            expected_hash: Expected SHA-256 hash (hex)

        Returns:
            True if hash matches
        """
        data = self.read(key)
        actual_hash = hashlib.sha256(data).hexdigest()
        return actual_hash == expected_hash


class LocalStore(StorageDriver):
    """
    Local filesystem storage driver.

    Stores files directly in the filesystem with optional WORM protection.
    """

    def write(self, key: str, data: bytes) -> str:
        """Write data to local filesystem."""
        file_path = self._resolve_relative(key)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # WORM check
        if self.target.worm and file_path.exists():
            raise ValueError(f"WORM violation: key '{key}' already exists")

        # Write data
        file_path.write_bytes(data)

        # Verify write
        actual_hash = hashlib.sha256(data).hexdigest()
        written_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()
        if actual_hash != written_hash:
            raise OSError(f"Write verification failed for key '{key}'")

        return str(file_path)

    def read(self, key: str) -> bytes:
        """Read data from local filesystem."""
        file_path = self._resolve_relative(key)
        if not file_path.exists():
            raise FileNotFoundError(f"Key '{key}' not found")
        return file_path.read_bytes()

    def exists(self, key: str) -> bool:
        """Check if key exists."""
        return self._resolve_relative(key).exists()

    def delete(self, key: str) -> None:
        """Delete key from storage."""
        if self.target.worm:
            raise ValueError("Cannot delete in WORM mode")

        file_path = self._resolve_relative(key)
        if file_path.exists():
            file_path.unlink()

    def list_keys(self, prefix: str = "") -> list[str]:
        """List keys with prefix."""
        keys: list[str] = []
        search_path = self._resolve_relative(prefix) if prefix else self._base_path

        if search_path.is_dir():
            for path in search_path.rglob("*"):
                if path.is_file():
                    rel_path = path.relative_to(self._base_path)
                    keys.append(str(rel_path).replace("\\", "/"))
        return sorted(keys)


class ArchiveStore(StorageDriver):
    """
    Archive storage driver using tar.gz.

    Stores backups as compressed tar archives with optional WORM protection.
    """

    def write(self, key: str, data: bytes) -> str:
        """Write data as tar.gz archive."""
        archive_path = self._resolve_relative(f"{key}.tar.gz")
        archive_path.parent.mkdir(parents=True, exist_ok=True)

        # WORM check
        if self.target.worm and archive_path.exists():
            raise ValueError(f"WORM violation: key '{key}' already exists")

        # Write compressed data
        if self.target.compression:
            compressed = gzip.compress(data, compresslevel=6)
            archive_path.write_bytes(compressed)
        else:
            archive_path.write_bytes(data)

        return str(archive_path)

    def read(self, key: str) -> bytes:
        """Read data from tar.gz archive."""
        archive_path = self._resolve_relative(f"{key}.tar.gz")
        if not archive_path.exists():
            raise FileNotFoundError(f"Key '{key}' not found")

        data = archive_path.read_bytes()

        # Decompress if needed
        if self.target.compression:
            try:
                return gzip.decompress(data)
            except gzip.BadGzipFile:
                # Fallback to uncompressed
                return data
        return data

    def exists(self, key: str) -> bool:
        """Check if key exists."""
        return self._resolve_relative(f"{key}.tar.gz").exists()

    def delete(self, key: str) -> None:
        """Delete archive from storage."""
        if self.target.worm:
            raise ValueError("Cannot delete in WORM mode")

        archive_path = self._resolve_relative(f"{key}.tar.gz")
        if archive_path.exists():
            archive_path.unlink()

    def list_keys(self, prefix: str = "") -> list[str]:
        """List archive keys with prefix."""
        keys: list[str] = []
        search_path = self._resolve_relative(prefix) if prefix else self._base_path

        if search_path.is_dir():
            for path in search_path.rglob("*.tar.gz"):
                if path.is_file():
                    rel_path = path.relative_to(self._base_path)
                    # Remove .tar.gz extension
                    key = str(rel_path).replace("\\", "/")
                    if key.endswith(".tar.gz"):
                        key = key[:-7]
                    keys.append(key)
        return sorted(keys)


class ObjectStoreStub(StorageDriver):
    """
    Object store stub with S3-like interface.

    Writes to local filesystem but mimics S3 API for testing.
    In production, replace with actual S3/Azure/GCS client.
    """

    def __init__(self, target: StorageTarget) -> None:
        """Initialize object store stub."""
        super().__init__(target)
        self._bucket = target.options.get("bucket", "dr-backups")
        self._objects_path = self._resolve_relative(self._bucket)
        self._objects_path.mkdir(parents=True, exist_ok=True)

    def _resolve_object_key(self, key: str | Path) -> Path:
        """Resolve a key inside the bucket safely."""
        return self._resolve_under(self._objects_path, key)

    def write(self, key: str, data: bytes) -> str:
        """Write object to store."""
        object_path = self._resolve_object_key(key)
        object_path.parent.mkdir(parents=True, exist_ok=True)

        # WORM check
        if self.target.worm and object_path.exists():
            raise ValueError(f"WORM violation: key '{key}' already exists")

        # Write data
        object_path.write_bytes(data)

        # Return S3-like URI
        return f"s3://{self._bucket}/{key}"

    def read(self, key: str) -> bytes:
        """Read object from store."""
        object_path = self._resolve_object_key(key)
        if not object_path.exists():
            raise FileNotFoundError(f"Key '{key}' not found in bucket '{self._bucket}'")
        return object_path.read_bytes()

    def exists(self, key: str) -> bool:
        """Check if object exists."""
        return self._resolve_object_key(key).exists()

    def delete(self, key: str) -> None:
        """Delete object from store."""
        if self.target.worm:
            raise ValueError("Cannot delete in WORM mode")

        object_path = self._resolve_object_key(key)
        if object_path.exists():
            object_path.unlink()

    def list_keys(self, prefix: str = "") -> list[str]:
        """List object keys with prefix."""
        keys: list[str] = []
        search_path = self._resolve_under(self._objects_path, prefix) if prefix else self._objects_path

        if search_path.is_dir():
            for path in search_path.rglob("*"):
                if path.is_file():
                    rel_path = path.relative_to(self._objects_path)
                    keys.append(str(rel_path).replace("\\", "/"))
        return sorted(keys)


def create_storage_driver(target: StorageTarget) -> StorageDriver:
    """
    Factory function to create storage driver.

    Args:
        target: Storage target configuration

    Returns:
        Appropriate storage driver instance

    Raises:
        ValueError: If backend type is unsupported
    """
    if target.backend == StorageBackend.LOCAL:
        return LocalStore(target)
    elif target.backend == StorageBackend.ARCHIVE:
        return ArchiveStore(target)
    elif target.backend == StorageBackend.OBJECT_STORE:
        return ObjectStoreStub(target)
    else:
        raise ValueError(f"Unsupported storage backend: {target.backend}")


__all__ = [
    "StorageDriver",
    "LocalStore",
    "ArchiveStore",
    "ObjectStoreStub",
    "create_storage_driver",
]
