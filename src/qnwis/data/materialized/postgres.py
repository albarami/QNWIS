"""
PostgreSQL materialized view manager.

Uses existing low-level DB adapter to create/refresh materialized views
with proper indexing for performance.
"""

from __future__ import annotations

import textwrap
from typing import Any, List


class PostgresMaterializer:
    """
    Uses the existing low-level DB adapter on DataClient (db.execute_sql)
    to create/refresh materialized views with indexes.

    All SQL is derived from registered queries - no ad-hoc SQL allowed.
    """

    def __init__(self, db: Any) -> None:
        """
        Initialize materializer with database adapter.

        Args:
            db: Database adapter with execute_sql(sql: str) -> None method
        """
        self.db = db

    def create_or_replace(
        self, name: str, sql_select: str, indexes: List[str]
    ) -> None:
        """
        Create or refresh a materialized view with indexes.

        Args:
            name: Materialized view name
            sql_select: SELECT statement (from registered query)
            indexes: List of index definitions (name ON table(columns))
        """
        sql_body = textwrap.dedent(sql_select).strip().rstrip(";")
        sql = f"""
        CREATE MATERIALIZED VIEW IF NOT EXISTS {name} AS
        {sql_body}
        WITH NO DATA;
        """
        self.db.execute_sql(textwrap.dedent(sql))
        self.db.execute_sql(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {name};")
        for idx in indexes:
            if " on " not in idx.lower():
                raise ValueError(f"Invalid index definition '{idx}'. Expected 'name ON table(cols)'.")
            self.db.execute_sql(f"CREATE INDEX IF NOT EXISTS {idx};")

    def refresh(self, name: str) -> None:
        """
        Refresh an existing materialized view.

        Args:
            name: Materialized view name
        """
        self.db.execute_sql(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {name};")

    def drop(self, name: str) -> None:
        """
        Drop a materialized view.

        Args:
            name: Materialized view name
        """
        self.db.execute_sql(f"DROP MATERIALIZED VIEW IF EXISTS {name};")
