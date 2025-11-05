"""
Pydantic row models for typed Data API responses.

All models validate structure and enforce type safety for
deterministic query results.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class EmploymentShareRow(BaseModel):
    """Employment distribution by gender for a given year."""

    year: int
    male_percent: float
    female_percent: float
    total_percent: float


class UnemploymentRow(BaseModel):
    """Unemployment rate for a country and year."""

    country: str
    year: int
    value: float


class QatarizationRow(BaseModel):
    """Qatarization metrics by sector and year."""

    year: int
    sector: str
    qataris: int = Field(ge=0)
    non_qataris: int = Field(ge=0)
    qatarization_percent: float


class AvgSalaryRow(BaseModel):
    """Average salary by sector and year."""

    year: int
    sector: str
    avg_salary_qr: int = Field(ge=0)


class AttritionRow(BaseModel):
    """Employee attrition rate by sector and year."""

    year: int
    sector: str
    attrition_percent: float


class CompanySizeRow(BaseModel):
    """Company distribution by size band for a given year."""

    year: int
    size_band: str
    companies: int


class SectorEmploymentRow(BaseModel):
    """Employment count by sector and year."""

    year: int
    sector: str
    employees: int


class EwiRow(BaseModel):
    """Early warning indicator: employment drop by sector."""

    year: int
    sector: str
    drop_percent: float
