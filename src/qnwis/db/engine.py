"""
SQLAlchemy engine helpers for QNWIS.

Provides a single entrypoint for building database engines with hardened
defaults (pre-ping, bounded pooling, deterministic recycling) so the rest
of the codebase never has to duplicate pool configuration.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool


def create_engine_from_url(
    url: str,
    *,
    pool_size: int = 20,
    max_overflow: int = 0,
    pool_timeout: int = 30,
    pool_recycle: int = 3600,
    echo: bool = False,
    **kwargs: Any,
) -> Engine:
    """
    Create a SQLAlchemy engine with hardened pooling defaults.

    Args:
        url: Database URL
        pool_size: Base pool size (default: 20)
        max_overflow: Overflow connections beyond pool_size (default: 0)
        pool_timeout: Seconds to wait for a free connection (default: 30)
        pool_recycle: Seconds before recycling a connection (default: 3600)
        echo: Enable SQL echoing for debugging (default: False)
        **kwargs: Additional keyword arguments passed to sqlalchemy.create_engine

    Returns:
        Configured SQLAlchemy Engine with QueuePool + pre-ping enabled
    """
    engine = create_engine(
        url,
        poolclass=QueuePool,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_timeout=pool_timeout,
        pool_recycle=pool_recycle,
        pool_pre_ping=True,
        future=True,
        echo=echo,
        **kwargs,
    )
    return engine


__all__ = ["create_engine_from_url"]
