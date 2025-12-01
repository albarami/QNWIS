from __future__ import annotations

from collections.abc import Iterable
from hashlib import sha256
from pathlib import Path

import yaml  # type: ignore[import-untyped]

from .schema import QueryDefinition

PROJECT_ROOT = Path(__file__).resolve().parents[4]


def _resolve_default_roots() -> list[Path]:
    """Return ALL query directories that exist and have YAML files."""
    candidates = [
        PROJECT_ROOT / "data" / "queries",
        PROJECT_ROOT / "src" / "qnwis" / "data" / "queries",
    ]
    roots = []
    for candidate in candidates:
        if candidate.exists() and any(candidate.glob("*.yaml")):
            roots.append(candidate)
    return roots if roots else [candidates[-1]]


def _resolve_default_root() -> Path:
    """Determine the PRIMARY queries root for backwards compatibility."""
    roots = _resolve_default_roots()
    return roots[0] if roots else PROJECT_ROOT / "data" / "queries"


DEFAULT_QUERY_ROOT = _resolve_default_root()
DEFAULT_QUERY_ROOTS = _resolve_default_roots()  # ALL directories


def _digest_paths(files: Iterable[Path]) -> str:
    """Compute deterministic checksum for the provided YAML files."""
    hasher = sha256()
    for file_path in sorted(files, key=lambda p: p.name):
        hasher.update(file_path.name.encode("utf-8"))
        hasher.update(b"\0")
        hasher.update(file_path.read_bytes())
    return hasher.hexdigest()[:12]


class QueryRegistry:
    """In-memory registry of deterministic query specifications."""

    def __init__(self, root: str | None = None) -> None:
        """
        Initialize a registry pointing at the given directory.

        Args:
            root: Directory containing deterministic query YAML definitions.
                  Defaults to DEFAULT_QUERY_ROOT if not provided.
        """
        self.root = Path(root) if root else DEFAULT_QUERY_ROOT
        self._items: dict[str, QueryDefinition] = {}
        self._version: str = "unloaded"

    @property
    def version(self) -> str:
        """Checksum representing the currently loaded registry contents."""
        return self._version

    @staticmethod
    def compute_version(root: str) -> str:
        """
        Compute a stable checksum for all YAML files in ``root``.

        Args:
            root: Directory containing deterministic query definitions.

        Returns:
            First 12 characters of the SHA256 digest across file names and
            contents. Returns ``"empty"``, if the directory exists but has no
            YAML definitions.
        """
        directory = Path(root)
        if not directory.exists():
            raise FileNotFoundError(f"Query registry directory not found: {directory}")
        files = list(directory.glob("*.yaml"))
        if not files:
            return "empty"
        return _digest_paths(files)

    def load_all(self) -> None:
        """Load every YAML query definition from ALL registry directories."""
        # Load from all query directories to get both data/queries and src/qnwis/data/queries
        all_roots = [self.root] + [r for r in DEFAULT_QUERY_ROOTS if r != self.root]
        all_files = []
        
        for root in all_roots:
            if not root.exists():
                continue
            
            files = list(root.glob("*.yaml"))
            for file_path in sorted(files, key=lambda p: p.name):
                try:
                    data = yaml.safe_load(file_path.read_text(encoding="utf-8")) or {}
                    # Handle both 'query_id' and 'id' keys
                    qid = data.get("query_id") or data.get("id")
                    if not qid:
                        continue
                    data["query_id"] = qid  # Normalize to query_id
                    query_def = QueryDefinition(**data)
                    if query_def.query_id not in self._items:  # Don't overwrite, first wins
                        self._items[query_def.query_id] = query_def
                        all_files.append(file_path)
                except Exception as e:
                    # Skip invalid YAML files but log the error
                    import logging
                    logging.getLogger(__name__).warning(f"Skipping invalid query file {file_path}: {e}")

        self._version = _digest_paths(all_files) if all_files else "empty"

    def get(self, query_id: str) -> QueryDefinition:
        """Retrieve a query definition by ID."""
        if query_id not in self._items:
            raise KeyError(f"Query not found: {query_id}")
        return self._items[query_id]

    def all_ids(self) -> list[str]:
        """Return all registered query identifiers."""
        return list(self._items.keys())

    def list_query_ids(self) -> list[str]:
        """Return all registered query identifiers (alias for all_ids)."""
        return self.all_ids()


def _default_registry_version() -> str:
    """Best-effort computation of the registry checksum for default root."""
    try:
        return QueryRegistry.compute_version(str(DEFAULT_QUERY_ROOT))
    except FileNotFoundError:
        return "dev"


REGISTRY_VERSION: str = _default_registry_version()
