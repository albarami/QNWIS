from __future__ import annotations

from ..connectors.csv_catalog import run_csv_query
from ..connectors.world_bank_det import run_world_bank_query
from ..validation.number_verifier import verify_result
from .models import QueryResult
from .registry import QueryRegistry


def execute(query_id: str, registry: QueryRegistry) -> QueryResult:
    """Execute a deterministic query by ID and run post-fetch validation."""
    spec = registry.get(query_id)
    if spec.source == "csv":
        result = run_csv_query(spec)
    elif spec.source == "world_bank":
        result = run_world_bank_query(spec)
    else:
        raise ValueError(f"Unsupported source: {spec.source}")

    result.warnings.extend(verify_result(spec, result))
    return result
