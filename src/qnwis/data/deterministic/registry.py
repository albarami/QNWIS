from __future__ import annotations

from pathlib import Path

import yaml  # type: ignore[import-untyped]

from .models import QuerySpec


class QueryRegistry:
    """In-memory registry of deterministic query specifications."""

    def __init__(self, root: str) -> None:
        self.root = Path(root)
        self._items: dict[str, QuerySpec] = {}

    def load_all(self) -> None:
        """Load every YAML query definition from the registry root."""
        if not self.root.exists():
            raise FileNotFoundError(f"Query registry directory not found: {self.root}")

        for file_path in self.root.glob("*.yaml"):
            data = yaml.safe_load(file_path.read_text(encoding="utf-8"))
            spec = QuerySpec(**data)
            if spec.id in self._items:
                raise ValueError(f"Duplicate QuerySpec id: {spec.id}")
            self._items[spec.id] = spec

    def get(self, qid: str) -> QuerySpec:
        """Retrieve a query specification by ID."""
        return self._items[qid]

    def all_ids(self) -> list[str]:
        """Return all registered query identifiers."""
        return list(self._items.keys())
