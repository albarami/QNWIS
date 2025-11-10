"""
Materialized view specification registry.

Loads and validates MV definitions from YAML, ensuring all required
fields are present before materialization.
"""

from __future__ import annotations

import pathlib
from typing import Any

import yaml


class MaterializedSpecError(Exception):
    """Raised when MV specification is invalid or missing."""


class MaterializedRegistry:
    """
    Loads and validates MV specs from YAML.

    Ensures each spec has all required fields before allowing
    materialization operations.
    """

    def __init__(self, path: str) -> None:
        """
        Initialize registry from YAML file.

        Args:
            path: Path to definitions YAML file

        Raises:
            MaterializedSpecError: If specs are invalid
        """
        self.path = path
        self.specs = self._load()

    def _load(self) -> list[dict[str, Any]]:
        """
        Load and validate MV specifications from YAML.

        Returns:
            List of validated spec dictionaries

        Raises:
            MaterializedSpecError: If any spec is invalid
        """
        p = pathlib.Path(self.path)
        data = yaml.safe_load(p.read_text()) or []
        for s in data:
            for k in ("name", "sql_id", "params", "refresh_cron", "indexes"):
                if k not in s:
                    raise MaterializedSpecError(f"Missing '{k}' in spec: {s}")
            for str_field in ("name", "sql_id", "refresh_cron"):
                if not isinstance(s[str_field], str):
                    raise MaterializedSpecError(
                        f"Spec '{s.get('name', '?')}' field '{str_field}' must be a string."
                    )
            if not isinstance(s["params"], dict):
                raise MaterializedSpecError(
                    f"Spec '{s.get('name', '?')}' has non-dict params."
                )
            indexes = s["indexes"]
            if not isinstance(indexes, list) or not all(isinstance(i, str) for i in indexes):
                raise MaterializedSpecError(
                    f"Spec '{s.get('name', '?')}' indexes must be a list of strings."
                )
            for idx in indexes:
                if " on " not in idx.lower():
                    raise MaterializedSpecError(
                        f"Index definition must include 'ON <table>(columns)': {idx}"
                    )
        return data

    def by_name(self, name: str) -> dict[str, Any]:
        """
        Get specification by MV name.

        Args:
            name: Materialized view name

        Returns:
            Spec dictionary

        Raises:
            MaterializedSpecError: If MV not found
        """
        for s in self.specs:
            if s["name"] == name:
                return s
        raise MaterializedSpecError(f"Unknown MV: {name}")
