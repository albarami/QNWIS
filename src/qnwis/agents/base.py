"""
Core data structures and deterministic data client for agents.

This module provides the foundational classes for building agents that access
deterministic data only. No SQL, RAG, or network calls are permitted here.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List

from ..data.deterministic.cache_access import execute_cached
from ..data.deterministic.models import QueryResult, QuerySpec, Row
from ..data.deterministic.normalize import normalize_rows
from ..data.deterministic.registry import DEFAULT_QUERY_ROOT, QueryRegistry

if TYPE_CHECKING:  # pragma: no cover - import only for typing
    from ..orchestration.types import Citation
else:  # Fallback to maintain runtime independence
    Citation = Dict[str, Any]

logger = logging.getLogger(__name__)


class MissingQueryDefinitionError(LookupError):
    """Raised when a deterministic query definition cannot be found."""


class QueryRegistryView:
    """Read-only facade over a QueryRegistry to prevent accidental mutation."""

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
        freshness_as_of: ISO date indicating data currency
        freshness_updated_at: Timestamp for the upstream refresh (if available)
    """

    query_id: str
    dataset_id: str
    locator: str
    fields: list[str]
    freshness_as_of: str | None = None
    freshness_updated_at: str | None = None


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
        insights: Alias for findings (backwards compatibility)
        warnings: Agent-level warnings
        narrative: Optional markdown/text narrative
        derived_results: Optional deterministic QueryResults (e.g., derived metrics)
        metadata: Arbitrary metadata blob for downstream renderers
    """

    agent: str
    findings: list[Insight] | None = None
    warnings: list[str] = field(default_factory=list)
    insights: list[Insight] | None = None
    narrative: str | None = None
    derived_results: list[Any] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        base_insights: list[Insight]
        if self.findings is not None:
            base_insights = list(self.findings)
        elif self.insights is not None:
            base_insights = list(self.insights)
        else:
            base_insights = []

        self.findings = base_insights
        self.insights = base_insights
        self.warnings = list(self.warnings)
        self.metadata = dict(self.metadata)


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
        root = Path(queries_dir) if queries_dir is not None else DEFAULT_QUERY_ROOT
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
            # Log cache status for observability (no behavior change)
            logger.debug(
                "Query executed: %s (rows=%d, cache_ttl=%ds)",
                query_id,
                len(res.rows),
                self.ttl_s,
            )
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
        freshness_as_of=res.freshness.asof_date,
        freshness_updated_at=res.freshness.updated_at,
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


def extract_citations_from_narrative(
    narrative: str, extracted_facts: List[Dict[str, Any]]
) -> List[Citation]:
    """Parse agent narrative text to extract structured citation references."""

    citations: List[Citation] = []
    citation_pattern = r"\[Per extraction: ([^\]]+)\]"

    for match in re.finditer(citation_pattern, narrative or ""):
        citation_body = match.group(1)
        claim = get_claim_context(narrative, match.start())

        parts = citation_body.split(" from ")
        if len(parts) != 2:
            continue

        value_part, source = parts[0].strip(), parts[1].strip()
        metric_match = re.search(r"['\"]([^'\"]+)['\"]", value_part)
        if not metric_match:
            continue

        metric = metric_match.group(1)
        value_text = (
            value_part.replace(f"'{metric}'", "").replace(f'"{metric}"', "").strip()
        )
        fact = next((f for f in extracted_facts if f.get("metric") == metric), None)

        citations.append(
            Citation(
                claim=claim,
                metric=metric,
                value=value_text,
                source=source,
                confidence=float(fact.get("confidence", 0.5)) if fact else 0.5,
                extraction_reference=match.group(0),
            )
        )

    return citations


def get_claim_context(text: str, citation_pos: int, radius: int = 150) -> str:
    """Return the sentence fragment surrounding a citation position."""

    if not text:
        return ""

    start = max(0, citation_pos - radius)
    end = min(len(text), citation_pos + radius)

    before = text[start:citation_pos]
    after = text[citation_pos:end]

    last_period = before.rfind(".")
    if last_period != -1:
        before = before[last_period + 1 :]

    next_period = after.find(".")
    if next_period != -1:
        after = after[: next_period + 1]

    return (before + after).strip()


def extract_data_gaps(narrative: str) -> List[str]:
    """Identify explicit data gap statements within an agent narrative."""

    gaps: set[str] = set()
    patterns = [
        r"NOT IN DATA[:\-\s]*([^\.]+)",
        r"CANNOT CALCULATE[:\-\s]*([^\.]+)",
        r"cannot determine ([^\.]+) without",
        r"Missing ([^\.]+) data",
    ]

    for pattern in patterns:
        for match in re.finditer(pattern, narrative or "", flags=re.IGNORECASE):
            gap = match.group(1).strip()
            if gap and len(gap) > 10:
                gaps.add(gap)

    return sorted(gaps)


def extract_assumptions(narrative: str) -> List[str]:
    """Collect ASSUMPTION statements along with their confidence levels."""

    assumptions: List[str] = []
    pattern = r"ASSUMPTION \(confidence: (\d+)%\): ([^\.]+\.)"

    for match in re.finditer(pattern, narrative or ""):
        confidence = match.group(1)
        statement = match.group(2).strip()
        assumptions.append(f"{statement} (confidence: {confidence}%)")

    return assumptions


def coerce_llm_response_text(response: Any) -> str:
    """Best-effort conversion of an LLM client response into plain text."""

    if isinstance(response, str):
        return response

    content = getattr(response, "content", None)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif hasattr(item, "text"):
                text_value = getattr(item, "text")
                if text_value is not None:
                    parts.append(str(text_value))
            else:
                parts.append(str(item))
        if parts:
            return "\n".join(parts)

    if hasattr(response, "text"):
        text_value = getattr(response, "text")
        if text_value is not None:
            return str(text_value)

    return str(response)


def extract_usage_tokens(response: Any) -> tuple[int, int]:
    """Extract token usage metadata from an LLM client response when available."""

    tokens_in = tokens_out = 0
    usage = getattr(response, "usage", None)
    if usage is None:
        return tokens_in, tokens_out

    if isinstance(usage, dict):
        tokens_in = int(usage.get("input_tokens") or usage.get("prompt_tokens") or 0)
        tokens_out = int(usage.get("output_tokens") or usage.get("completion_tokens") or 0)
        return tokens_in, tokens_out

    tokens_in = int(
        getattr(usage, "input_tokens", getattr(usage, "prompt_tokens", 0)) or 0
    )
    tokens_out = int(
        getattr(usage, "output_tokens", getattr(usage, "completion_tokens", 0)) or 0
    )
    return tokens_in, tokens_out


def resolve_response_model(response: Any, llm_client: Any) -> str:
    """Resolve the model name for an LLM response with sensible fallbacks."""

    model_name = getattr(response, "model", None)
    if isinstance(model_name, str) and model_name:
        return model_name
    return getattr(llm_client, "model", "unknown")
