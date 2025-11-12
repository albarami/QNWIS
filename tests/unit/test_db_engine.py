"""Tests for database engine helper."""

from sqlalchemy.engine import Engine

from qnwis.db.engine import create_engine_from_url


def test_create_engine_from_url_enables_pre_ping() -> None:
    """Helper should enable pool_pre_ping to avoid stale connections."""
    engine: Engine = create_engine_from_url("sqlite://")
    assert getattr(engine.pool, "_pre_ping", False) is True
