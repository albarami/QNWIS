"""
PostgreSQL materialized view manager.

Uses existing low-level DB adapter to create/refresh materialized views
with proper indexing for performance.
"""

from __future__ import annotations

import textwrap
from typing import Any


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
        self, name: str, sql_select: str, indexes: list[str]
    ) -> None:
        """
        Create or refresh a materialized view with indexes.

        Args:
            name: Materialized view name
            sql_select: SELECT statement (from registered query)
            indexes: List of index definitions (name ON table(columns))
        """
        sql_body = textwrap.dedent(sql_select).strip().rstrip(";")
        sql_template = textwrap.dedent(
            """
            CREATE MATERIALIZED VIEW IF NOT EXISTS {name} AS
            {sql_body}
            WITH NO DATA;
            """
        )
        rendered_sql = sql_template.format(name=name, sql_body=sql_body)
        self.db.execute_sql(rendered_sql)
        refresh_stmt = "REFRESH MATERIALIZED VIEW CONCURRENTLY {name};".format(name=name)
        self.db.execute_sql(refresh_stmt)
        for idx in indexes:
            if " on " not in idx.lower():
                raise ValueError(f"Invalid index definition '{idx}'. Expected 'name ON table(cols)'.")
            index_stmt = "CREATE INDEX IF NOT EXISTS {idx};".format(idx=idx)
            self.db.execute_sql(index_stmt)

    def refresh(self, name: str) -> None:
        """
        Refresh an existing materialized view.

        Args:
            name: Materialized view name
        """
        refresh_stmt = "REFRESH MATERIALIZED VIEW CONCURRENTLY {name};".format(name=name)
        self.db.execute_sql(refresh_stmt)

    def drop(self, name: str) -> None:
        """
        Drop a materialized view.

        Args:
            name: Materialized view name
        """
        drop_stmt = "DROP MATERIALIZED VIEW IF EXISTS {name};".format(name=name)
        self.db.execute_sql(drop_stmt)
