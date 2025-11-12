"""
Database engine for deterministic data layer.

Provides a singleton engine instance for the deterministic data access layer.
"""

from __future__ import annotations

import os
from typing import Any

from sqlalchemy.engine import Engine

from ...db.engine import create_engine_from_url

_engine: Engine | None = None


def get_engine(**kwargs: Any) -> Engine:
    """
    Get or create the global database engine instance.
    
    Args:
        **kwargs: Additional keyword arguments passed to create_engine_from_url
        
    Returns:
        SQLAlchemy Engine instance
        
    Raises:
        ValueError: If DATABASE_URL environment variable is not set
    """
    global _engine
    
    if _engine is None:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise ValueError("DATABASE_URL environment variable must be set")
        
        pool_size = int(os.getenv("DB_POOL_SIZE", "20"))
        max_overflow = int(os.getenv("DB_MAX_OVERFLOW", "0"))
        
        _engine = create_engine_from_url(
            database_url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            **kwargs
        )
    
    return _engine


def reset_engine() -> None:
    """
    Reset the global engine instance.
    
    Useful for testing or when configuration changes require a new engine.
    """
    global _engine
    if _engine is not None:
        _engine.dispose()
        _engine = None


__all__ = ["get_engine", "reset_engine"]
