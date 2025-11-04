"""Dataset catalog for license and metadata enrichment."""

from __future__ import annotations

import fnmatch
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]


class DatasetCatalog:
    """Registry of dataset patterns with license and notes."""

    def __init__(self, path: str | Path) -> None:
        """Load catalog from YAML file if present."""
        self._items: list[dict[str, Any]] = []
        catalog_path = Path(path)
        if not catalog_path.exists() or not catalog_path.is_file():
            return
        try:
            raw_text = catalog_path.read_text(encoding="utf-8")
        except OSError:
            return
        try:
            data = yaml.safe_load(raw_text) or []
        except yaml.YAMLError:
            return
        if isinstance(data, dict):
            data = data.get("datasets", [])
        if isinstance(data, list):
            self._items = [item for item in data if isinstance(item, dict)]

    def match(self, locator: str) -> dict[str, Any] | None:
        """Find first catalog entry matching the locator pattern."""
        for item in self._items:
            patt = item.get("pattern", "")
            if patt and fnmatch.fnmatch(locator, patt):
                return item
        return None
