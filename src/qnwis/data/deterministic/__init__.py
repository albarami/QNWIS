"""
Deterministic query layer for QNWIS.

Provides read-only SQL queries with strong typing, parameter validation,
and caching. All agent data access flows through this layer.
"""

from .models import QueryResult
from .registry import DEFAULT_QUERY_ROOT, QueryRegistry
from .schema import OutputColumn, Parameter, QueryDefinition

__all__ = [
    "QueryResult",
    "QueryRegistry",
    "DEFAULT_QUERY_ROOT",
    "QueryDefinition",
    "Parameter",
    "OutputColumn",
]
