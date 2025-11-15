"""
SQL executor connector for deterministic queries with QueryDefinition.

Executes SQL queries from YAML QueryDefinition objects against the PostgreSQL database.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Row as SARow

from ..deterministic.engine import get_engine
from ..deterministic.models import Freshness, Provenance, QueryResult, Row
from ..deterministic.schema import QueryDefinition

logger = logging.getLogger(__name__)


def run_sql_query(spec: QueryDefinition) -> QueryResult:
    """
    Execute a SQL query from a QueryDefinition against the database.

    Args:
        spec: QueryDefinition containing SQL query and metadata

    Returns:
        QueryResult with rows from database execution

    Raises:
        ValueError: If SQL execution fails or returns no rows
    """
    engine = get_engine()

    # Build parameter dict from QueryDefinition parameters
    params_dict: dict[str, Any] = {}
    if spec.parameters:
        for param in spec.parameters:
            params_dict[param.name] = param.default

    # Execute SQL query
    try:
        with engine.connect() as conn:
            result = conn.execute(text(spec.sql), params_dict)
            rows_data = result.fetchall()

            if not rows_data:
                logger.warning(f"Query {spec.query_id} returned 0 rows")
                # Return empty result instead of raising error
                output_fields = [col.name for col in spec.output_schema]
                return QueryResult(
                    query_id=spec.query_id,
                    rows=[],
                    unit="unknown",
                    provenance=Provenance(
                        source="sql",
                        dataset_id=spec.dataset,
                        locator=spec.query_id,
                        fields=output_fields,
                        license="internal",
                    ),
                    freshness=Freshness(
                        asof_date=datetime.now(timezone.utc).date().isoformat(),
                        updated_at=datetime.now(timezone.utc).isoformat(),
                    ),
                    metadata={"dataset": spec.dataset, "row_count": 0},
                    warnings=["Query returned no rows"],
                )

            # Convert SQLAlchemy rows to Row objects
            rows: list[Row] = []
            for sa_row in rows_data:
                if isinstance(sa_row, SARow):
                    row_dict = dict(sa_row._mapping)
                else:
                    row_dict = dict(sa_row)
                rows.append(Row(data=row_dict))

            # Build query result
            output_fields = [col.name for col in spec.output_schema]
            return QueryResult(
                query_id=spec.query_id,
                rows=rows,
                unit="unknown",  # TODO: infer from output_schema if available
                provenance=Provenance(
                    source="sql",
                    dataset_id=spec.dataset,
                    locator=spec.query_id,
                    fields=output_fields,
                    license="internal",
                ),
                freshness=Freshness(
                    asof_date=datetime.now(timezone.utc).date().isoformat(),
                    updated_at=datetime.now(timezone.utc).isoformat(),
                ),
                metadata={
                    "dataset": spec.dataset,
                    "row_count": len(rows),
                    "cache_ttl": spec.cache_ttl,
                },
                warnings=[],
            )

    except Exception as e:
        logger.exception(f"SQL execution failed for query {spec.query_id}: {e}")
        raise ValueError(f"Failed to execute SQL query {spec.query_id}: {e}") from e


__all__ = ["run_sql_query"]
