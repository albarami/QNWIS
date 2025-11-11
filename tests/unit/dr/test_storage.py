"""Storage driver safety tests for DR subsystem."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from src.qnwis.dr.models import StorageBackend, StorageTarget
from src.qnwis.dr.storage import create_storage_driver


def _make_target(tmp_path: Path, worm: bool = False) -> StorageTarget:
    return StorageTarget(
        target_id="test",
        backend=StorageBackend.LOCAL,
        base_path=str(tmp_path),
        worm=worm,
        compression=True,
        options={},
    )


def test_local_store_rejects_path_traversal() -> None:
    """Ensure storage driver blocks writes outside the configured root."""
    with tempfile.TemporaryDirectory() as temp_dir:
        target = _make_target(Path(temp_dir))
        driver = create_storage_driver(target)

        with pytest.raises(ValueError, match="escapes allowed root"):
            driver.write("../escape.txt", b"forbidden")


def test_local_store_worm_prevents_overwrite() -> None:
    """WORM mode should block overwriting an existing key."""
    with tempfile.TemporaryDirectory() as temp_dir:
        target = _make_target(Path(temp_dir), worm=True)
        driver = create_storage_driver(target)

        driver.write("snapshot/file.dat", b"original")
        with pytest.raises(ValueError, match="WORM violation"):
            driver.write("snapshot/file.dat", b"mutated")
