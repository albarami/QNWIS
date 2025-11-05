"""
Typed Data API package.

Provides type-safe accessors over the Deterministic Data Layer.
All operations are deterministic, in-memory transforms with no network or SQL.
"""

from .client import DataAPI
from .models import (
    AttritionRow,
    AvgSalaryRow,
    CompanySizeRow,
    EmploymentShareRow,
    EwiRow,
    QatarizationRow,
    SectorEmploymentRow,
    UnemploymentRow,
)

__all__ = [
    "DataAPI",
    "EmploymentShareRow",
    "UnemploymentRow",
    "QatarizationRow",
    "AvgSalaryRow",
    "AttritionRow",
    "CompanySizeRow",
    "SectorEmploymentRow",
    "EwiRow",
]
