from __future__ import annotations

import os

from ..connectors.csv_catalog import run_csv_query
from ..connectors.sql_executor import run_sql_query
from ..connectors.world_bank_det import run_world_bank_query
from ..validation.number_verifier import verify_result
from .models import QueryResult, QuerySpec
from .postprocess import apply_postprocess
from .registry import QueryRegistry
from .schema import QueryDefinition


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
    source_spec = spec_override or registry.get(query_id)
    spec = source_spec.model_copy(deep=True)

    # Handle both QuerySpec and QueryDefinition
    if isinstance(spec, QueryDefinition):
        spec_id = spec.query_id
        spec_source = spec.dataset.lower()
    else:
        spec_id = spec.id
        spec_source = spec.source

    if spec_id != query_id:
        raise ValueError(f"Spec ID mismatch: expected {query_id}, got {spec_id}")

    # Execute based on spec type and source
    if isinstance(spec, QueryDefinition):
        # New YAML-based queries with SQL - execute directly against database
        result = run_sql_query(spec)
    elif spec_source in ("csv", "lmis"):
        result = run_csv_query(spec)
    elif spec_source in ("world_bank", "gcc_stat", "vision_2030"):
        result = run_world_bank_query(spec)
    elif spec_source == "qatar_api":
        from ..connectors.qatar_opendata_api import run_qatar_api_query
        result = run_qatar_api_query(spec)
    else:
        # Try to infer source from query type for API-based queries
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Unknown source '{spec_source}' for query {query_id}, falling back to CSV")
        result = run_csv_query(spec)

    # Apply postprocess transforms if defined (only for QuerySpec, not QueryDefinition)
    if hasattr(spec, 'postprocess') and spec.postprocess:
        processed_rows, trace = apply_postprocess(result.rows, spec.postprocess)
        result.rows = processed_rows
        if os.getenv("QNWIS_TRANSFORM_TRACE") == "1":
            result.warnings.extend(f"transform:{name}" for name in trace)

    # Verify result (only for QuerySpec with constraints)
    if not isinstance(spec, QueryDefinition):
        result.warnings.extend(verify_result(spec, result))

    return result
