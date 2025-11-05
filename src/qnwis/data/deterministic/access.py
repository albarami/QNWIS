from __future__ import annotations

from ..connectors.csv_catalog import run_csv_query
from ..connectors.world_bank_det import run_world_bank_query
from ..validation.number_verifier import verify_result
from .models import QueryResult, QuerySpec
from .registry import QueryRegistry


def execute(
    query_id: str,
    registry: QueryRegistry,
    spec_override: QuerySpec | None = None,
) -> QueryResult:
    """
    Execute a deterministic query by ID and run post-fetch validation.

    Args:
        query_id: Registered query identifier.
        registry: Registry that stores query specifications.
        spec_override: Optional QuerySpec to execute instead of fetching
            from the registry. Used for per-request parameter overrides.

    Returns:
        QueryResult containing deterministic rows and warnings.

    Raises:
        ValueError: If the query source type is not supported.
    """
    spec = spec_override or registry.get(query_id)
    if spec.id != query_id:
        raise ValueError(f"Spec ID mismatch: expected {query_id}, got {spec.id}")

    if spec.source == "csv":
        result = run_csv_query(spec)
    elif spec.source == "world_bank":
        result = run_world_bank_query(spec)
    else:
        raise ValueError(f"Unsupported source: {spec.source}")

    result.warnings.extend(verify_result(spec, result))
    return result
