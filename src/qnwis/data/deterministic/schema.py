"""
Pydantic schema for YAML query definitions.

Enforces read-only SELECTs, named parameters, and safety constraints.
"""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, Field, StrictStr, conlist, field_validator


class Parameter(BaseModel):
    """Query parameter definition with type and optionality."""

    name: StrictStr
    type: Literal["string", "integer", "float", "date", "datetime", "bool"]
    required: bool = False
    default: Any | None = None
    description: str | None = None


class OutputColumn(BaseModel):
    """Output column schema definition."""

    name: StrictStr
    type: Literal["string", "integer", "float", "date", "datetime", "boolean", "json"]


class QueryDefinition(BaseModel):
    """
    Complete query definition loaded from YAML.

    Enforces safety constraints:
    - SQL must be read-only SELECT
    - Must use named :parameters (not positional ?)
    - No dangerous SQL constructs
    """

    query_id: StrictStr
    description: StrictStr
    dataset: Literal["LMIS", "GCC_STAT", "WORLD_BANK", "VISION_2030"]
    sql: StrictStr  # must use :named parameters
    parameters: list[Parameter] = Field(default_factory=list)
    output_schema: conlist(OutputColumn, min_length=1)  # type: ignore[valid-type]
    cache_ttl: int = 3600
    freshness_sla: int = 86400
    access_level: Literal["public", "restricted", "confidential"] = "public"
    tags: list[str] = Field(default_factory=list)

    @field_validator("sql")
    @classmethod
    def forbid_dangerous(cls, v: str) -> str:
        """
        Enforce read-only SELECT queries and reject dangerous constructs.

        Raises:
            ValueError: If SQL contains forbidden patterns or uses ? placeholders
        """
        # Normalize whitespace for checking
        normalized = re.sub(r"\s+", " ", v.strip().upper())

        # Dangerous patterns to reject
        dangerous_patterns = [
            ";--",
            "/*",
            "*/",
            "DROP ",
            "ALTER ",
            "TRUNCATE ",
            "DELETE FROM",
            "INSERT INTO",
            "UPDATE ",
            "CREATE ",
            "EXEC",
            "EXECUTE",
        ]

        for pattern in dangerous_patterns:
            if pattern.upper() in normalized:
                raise ValueError(
                    f"SQL must be read-only SELECT and safe. "
                    f"Forbidden pattern: {pattern}"
                )

        # Reject positional placeholders
        if "?" in v:
            raise ValueError("Use named :parameters, not positional placeholders.")

        # Ensure query is primarily SELECT (allow WITH clauses)
        if not normalized.startswith("WITH ") and not normalized.startswith("SELECT "):
            raise ValueError("SQL must be a SELECT query (WITH ... SELECT allowed).")

        return v

    @field_validator("query_id")
    @classmethod
    def validate_query_id(cls, v: str) -> str:
        """Ensure query_id is a valid identifier."""
        if not re.match(r"^[a-z][a-z0-9_]*$", v):
            raise ValueError(
                "query_id must be lowercase, start with a letter, "
                "and contain only letters, numbers, and underscores."
            )
        return v

    @field_validator("cache_ttl", "freshness_sla")
    @classmethod
    def validate_positive(cls, v: int) -> int:
        """Ensure TTL/SLA values are positive."""
        if v <= 0:
            raise ValueError("cache_ttl and freshness_sla must be positive.")
        return v
