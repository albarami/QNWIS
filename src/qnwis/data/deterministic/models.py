from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

SourceType = Literal["csv", "world_bank", "sql", "qatar_api"]
UnitType = Literal["count", "percent", "qar", "usd", "index", "unknown"]


class Provenance(BaseModel):
    source: SourceType
    dataset_id: str
    locator: str  # file path or API endpoint
    fields: list[str]
    license: str | None = None


class Freshness(BaseModel):
    """Freshness metadata for a deterministic query result."""

    asof_date: str  # ISO date
    updated_at: str | None = None

    @field_validator("asof_date")
    @classmethod
    def _validate_asof_date(cls, value: str) -> str:
        """Ensure ``asof_date`` is a valid ISO-8601 date string."""
        date.fromisoformat(value)
        return value

    @field_validator("updated_at")
    @classmethod
    def _validate_updated_at(cls, value: str | None) -> str | None:
        """Ensure ``updated_at`` is either ``None`` or a valid ISO timestamp."""
        if value is None:
            return None
        datetime.fromisoformat(value)
        return value

    @property
    def days_old(self) -> int:
        """Calculate how many days old the data is from asof_date to today."""
        asof = date.fromisoformat(self.asof_date)
        today = date.today()
        return (today - asof).days


class TransformStep(BaseModel):
    """Single transform step in postprocess pipeline."""
    name: str  # must exist in transforms catalog
    params: dict[str, Any] = Field(default_factory=dict)


class QuerySpec(BaseModel):
    id: str
    title: str
    description: str
    source: SourceType
    params: dict[str, Any] = Field(default_factory=dict)
    expected_unit: UnitType = "unknown"
    constraints: dict[str, Any] = Field(default_factory=dict)  # e.g. {"sum_to_one": True}
    postprocess: list[TransformStep] = Field(default_factory=list)  # optional transform pipeline


class Row(BaseModel):
    data: dict[str, Any]


class QueryResult(BaseModel):
    query_id: str
    rows: list[Row]
    unit: UnitType
    provenance: Provenance
    freshness: Freshness
    metadata: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
