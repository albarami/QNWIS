"""
CLI job to create and refresh materialized views.

Reads MV specifications from YAML, renders SQL from query registry,
and materializes views with proper indexing.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from ..data.deterministic.registry import DEFAULT_QUERY_ROOT, QueryRegistry
from ..data.materialized.postgres import PostgresMaterializer
from ..data.materialized.registry import MaterializedRegistry


def _resolve_query_registry(db: Any) -> Any:
    """Resolve a query registry from the DB adapter or fall back to default."""
    candidate = getattr(db, "query_registry", None)
    if candidate is not None:
        return candidate

    registry = QueryRegistry(str(DEFAULT_QUERY_ROOT))
    registry.load_all()
    return registry


def main(db: Any, registry_path: str) -> None:
    """
    Ensure all materialized views are created/refreshed.

    Args:
        db: Database adapter with execute_sql and query_registry
        registry_path: Path to MV definitions YAML
    """
    reg = MaterializedRegistry(registry_path)
    mat = PostgresMaterializer(db)
    query_registry = _resolve_query_registry(db)

    if not hasattr(query_registry, "render_select"):
        raise AttributeError(
            "Query registry must expose a 'render_select(sql_id, params)' method."
        )

    created: list[dict[str, str]] = []
    for spec in reg.specs:
        # Validate the query exists in the registry
        query_registry.get(spec["sql_id"])
        sql_select = query_registry.render_select(spec["sql_id"], spec["params"])
        mat.create_or_replace(spec["name"], sql_select, spec["indexes"])
        created.append({"name": spec["name"], "sql_id": spec["sql_id"]})

    print(json.dumps({"materialized": created}, separators=(",", ":"), sort_keys=True))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Refresh QNWIS materialized views"
    )
    parser.add_argument(
        "--registry",
        default="src/qnwis/data/materialized/definitions.yml",
        help="Path to MV definitions YAML",
    )
    args = parser.parse_args()

    # NOTE: Wire 'db' using your project bootstrap (left to CLI wrapper)
    sys.exit(
        json.dumps(
            {
                "error": "bootstrap-required",
                "message": "Use project bootstrap to pass DB connection to main(db, registry_path).",
                "registry_path": args.registry,
            },
            separators=(",", ":"),
            sort_keys=True,
        )
    )
