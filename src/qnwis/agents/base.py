"""
Core data structures and deterministic data client for agents.

This module provides the foundational classes for building agents that access
deterministic data only. No SQL, RAG, or network calls are permitted here.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from ..data.deterministic.cache_access import execute_cached
from ..data.deterministic.models import QueryResult, QuerySpec, Row
from ..data.deterministic.normalize import normalize_rows
from ..data.deterministic.registry import QueryRegistry


class MissingQueryDefinitionError(LookupError):
    """Raised when a deterministic query definition cannot be found."""


class QueryRegistryView:
    """Read-only façade over a QueryRegistry to prevent accidental mutation."""

    def __init__(self, registry: QueryRegistry) -> None:
        self._registry = registry

    @property
    def root(self) -> Path:
        """Return the root path containing query YAML definitions."""
        return self._registry.root

    def get(self, query_id: str) -> QuerySpec:
        """Return a defensive copy of a query specification."""
        spec = self._registry.get(query_id)
        return spec.model_copy(deep=True)

    def all_ids(self) -> list[str]:
        """List all registered query identifiers."""
        return self._registry.all_ids()


@dataclass
class Evidence:
    """
    Provenance information linking an insight back to its source data.

    Attributes:
        query_id: The deterministic query identifier
        dataset_id: Source dataset identifier
        locator: File path or API endpoint
        fields: List of field names in the result
    """

    query_id: str
    dataset_id: str
    locator: str
    fields: list[str]


@dataclass
class Insight:
    """
    A single analytical finding with structured metrics and provenance.

    Attributes:
        title: Human-readable insight title
        summary: Brief description of the finding
        metrics: Quantitative measurements as key-value pairs
        evidence: Provenance information for this insight
        warnings: Any data quality or freshness warnings
        confidence_score: Derived quality score (0.5-1.0) based on warnings
    """

    title: str
    summary: str
    metrics: dict[str, float] = field(default_factory=dict)
    evidence: list[Evidence] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    confidence_score: float = field(init=False)

    def __post_init__(self) -> None:
        """Derive a bounded confidence score from the number of warnings."""
        self.warnings = list(self.warnings)
        penalty = 0.1 * len(self.warnings)
        self.confidence_score = max(0.5, 1.0 - penalty)


@dataclass
class AgentReport:
    """
    Complete report from an agent execution.

    Attributes:
        agent: Agent name/identifier
        findings: List of insights discovered
        warnings: Agent-level warnings
    """

    agent: str
    findings: list[Insight]
    warnings: list[str] = field(default_factory=list)


class DataClient:
    """
    Strict gateway to deterministic layer. Never use SQL/RAG/network here.

    This client enforces deterministic data access patterns and provides
    normalized, cached results from registered queries.
    """

    def __init__(self, queries_dir: str | None = None, ttl_s: int = 300) -> None:
        """
        Initialize the data client.

        Args:
            queries_dir: Path to query definitions directory (default: data/queries)
            ttl_s: Cache TTL in seconds (default: 300)
        """
        root = Path(queries_dir) if queries_dir is not None else Path("data/queries")
        self.ttl_s = ttl_s
        self._registry = QueryRegistry(str(root))
        self._registry_view = QueryRegistryView(self._registry)
        self._load_error: FileNotFoundError | None = None
        try:
            self._registry.load_all()
        except FileNotFoundError as exc:
            # Allow tests to inject/monkeypatch run() without YAML definitions.
            self._load_error = exc

    @property
    def registry(self) -> QueryRegistryView:
        """
        Expose a read-only view of the underlying query registry.

        The view returns defensive copies of QuerySpec objects, ensuring
        agents cannot mutate the shared registry state.
        """
        return self._registry_view

    @property
    def queries_dir(self) -> Path:
        """Directory that should contain deterministic query YAML files."""
        return self._registry.root

    def _raise_missing(self, query_id: str, *, cause: Exception | None = None) -> None:
        """Raise a consistent error when a query definition cannot be found."""
        directory = self.queries_dir
        if self._load_error is not None:
            hint = f"Query directory '{directory}' is missing."
        else:
            hint = f"No YAML definition was loaded for '{query_id}'."
        raise MissingQueryDefinitionError(
            f"Deterministic query '{query_id}' is not registered in '{directory}'. {hint}"
        ) from cause

    def run(self, query_id: str) -> QueryResult:
        """
        Execute a cached deterministic query with normalized results.

        Args:
            query_id: Registered query identifier

        Returns:
            QueryResult with normalized row keys and enriched provenance
        """
        if self._load_error is not None:
            self._raise_missing(query_id, cause=self._load_error)
        try:
            res = execute_cached(query_id, self._registry, ttl_s=self.ttl_s)
        except KeyError as exc:
            self._raise_missing(query_id, cause=exc)
        normalized = normalize_rows([{"data": r.data} for r in res.rows])
        res.rows = [Row(data=r["data"]) for r in normalized]
        res.warnings = list(res.warnings)
        return res


def _numeric_fields(rows: Iterable[Row]) -> list[str]:
    """
    Extract field names that contain numeric values.

    Args:
        rows: Iterable of Row objects

    Returns:
        List of field names with numeric values
    """
    names: list[str] = []
    for r in rows:
        for k, v in r.data.items():
            if isinstance(v, (int, float)) and k not in names:
                names.append(k)
    return names


def evidence_from(res: QueryResult) -> Evidence:
    """
    Create Evidence object from QueryResult provenance.

    Args:
        res: Query result with provenance information

    Returns:
        Evidence object with extracted provenance details
    """
    return Evidence(
        query_id=res.query_id,
        dataset_id=res.provenance.dataset_id,
        locator=res.provenance.locator,
        fields=list(res.rows[0].data.keys()) if res.rows else [],
    )


def metric_from_rows(rows: list[Row], key: str) -> float:
    """
    Deterministically compute a simple metric: last row's numeric value for key.

    Args:
        rows: List of Row objects
        key: Field name to extract

    Returns:
        Float value from last row, or 0.0 if not found
    """
    val: float = 0.0
    for r in rows:
        v = r.data.get(key)
        if isinstance(v, (int, float)):
            val = float(v)
    return val
