"""
Database tuning helpers for QNWIS.

Provides connection pool configuration, query analysis tools,
and timeout management for PostgreSQL/SQLAlchemy.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Any, Dict, Generator

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool

logger = logging.getLogger(__name__)


def configure_pool(
    engine: Engine,
    pool_size: int = 20,
    max_overflow: int = 20,
    timeout: int = 30,
    recycle: int = 3600,
) -> None:
    """
    Configure SQLAlchemy connection pool parameters.
    
    Args:
        engine: SQLAlchemy engine to configure
        pool_size: Base pool size (connections kept open)
        max_overflow: Additional connections allowed beyond pool_size
        timeout: Seconds to wait for connection from pool
        recycle: Seconds before recycling connections (prevent stale)
        
    Note:
        This modifies the engine's pool in-place. Call before first query.
        
    Example:
        >>> from sqlalchemy import create_engine
        >>> engine = create_engine("postgresql://...")
        >>> configure_pool(engine, pool_size=30, max_overflow=10)
    """
    if not isinstance(engine.pool, QueuePool):
        logger.warning(
            f"Engine pool is {type(engine.pool).__name__}, not QueuePool. "
            "Pool configuration may not apply."
        )
        return

    # Update pool parameters
    engine.pool._pool.maxsize = pool_size  # type: ignore
    engine.pool._max_overflow = max_overflow  # type: ignore
    engine.pool._timeout = timeout  # type: ignore
    engine.pool._recycle = recycle  # type: ignore

    logger.info(
        f"Configured pool: size={pool_size}, overflow={max_overflow}, "
        f"timeout={timeout}s, recycle={recycle}s"
    )


def explain(engine: Engine, sql: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run EXPLAIN on a query and return plan as dict.
    
    Args:
        engine: SQLAlchemy engine
        sql: SQL query string (parameterized)
        params: Query parameters
        
    Returns:
        Dictionary with query plan details
        
    Example:
        >>> plan = explain(engine, "SELECT * FROM jobs WHERE id = :id", {"id": 123})
        >>> print(plan["Plan"]["Node Type"])
    """
    with engine.connect() as conn:
        result = conn.execute(
            text(f"EXPLAIN (FORMAT JSON) {sql}"),
            params,
        )
        row = result.fetchone()
        if row:
            return row[0][0]  # type: ignore
        return {}


def analyze(engine: Engine, sql: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run EXPLAIN ANALYZE on a query and return execution stats.
    
    WARNING: This executes the query. Use only on read-only queries
    or in test environments.
    
    Args:
        engine: SQLAlchemy engine
        sql: SQL query string (parameterized)
        params: Query parameters
        
    Returns:
        Dictionary with execution plan and timing stats
        
    Example:
        >>> stats = analyze(engine, "SELECT COUNT(*) FROM jobs", {})
        >>> print(stats["Execution Time"])
    """
    with engine.connect() as conn:
        result = conn.execute(
            text(f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {sql}"),
            params,
        )
        row = result.fetchone()
        if row:
            return row[0][0]  # type: ignore
        return {}


@contextmanager
def with_timeout(
    engine: Engine, seconds: int
) -> Generator[Engine, None, None]:
    """
    Context manager to set statement timeout for queries.
    
    Args:
        engine: SQLAlchemy engine
        seconds: Statement timeout in seconds
        
    Yields:
        Engine with timeout configured
        
    Example:
        >>> with with_timeout(engine, 30):
        ...     result = session.execute(text("SELECT * FROM large_table"))
    """
    with engine.connect() as conn:
        # Set timeout for this connection
        conn.execute(text(f"SET statement_timeout = '{seconds}s'"))
        try:
            yield engine
        finally:
            # Reset to default
            conn.execute(text("SET statement_timeout = 0"))


def set_work_mem(engine: Engine, mb: int) -> None:
    """
    Set work_mem for the current session.
    
    work_mem controls memory for sort/hash operations per query.
    Higher values speed up complex queries but use more RAM.
    
    Args:
        engine: SQLAlchemy engine
        mb: Memory limit in megabytes
        
    Example:
        >>> set_work_mem(engine, 256)  # 256MB for complex aggregations
    """
    with engine.connect() as conn:
        conn.execute(text(f"SET work_mem = '{mb}MB'"))
        logger.info(f"Set work_mem to {mb}MB for session")
