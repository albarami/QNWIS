"""Schema definitions for synthetic LMIS data generation."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CompaniesSchema:
    """Schema for companies.csv."""

    columns: list[str] = field(
        default_factory=lambda: [
            "company_id",
            "company_name",
            "sector",
            "size_band",
            "founded_year",
        ]
    )


@dataclass(frozen=True)
class EmploymentHistorySchema:
    """Schema for employment_history.csv."""

    columns: list[str] = field(
        default_factory=lambda: [
            "person_id",
            "year",
            "company_id",
            "gender",
            "nationality",
            "education_level",
            "monthly_salary",
            "status",
        ]
    )


@dataclass(frozen=True)
class Aggregates:
    """Precomputed aggregate schemas for simple CSV queries."""

    employment_share_by_gender: list[str] = field(
        default_factory=lambda: [
            "year",
            "male_percent",
            "female_percent",
            "total_percent",
        ]
    )
    unemployment_gcc: list[str] = field(
        default_factory=lambda: ["country", "year", "value"]
    )
    qatarization_by_sector: list[str] = field(
        default_factory=lambda: [
            "year",
            "sector",
            "qataris",
            "non_qataris",
            "qatarization_percent",
        ]
    )
    avg_salary_by_sector: list[str] = field(
        default_factory=lambda: ["year", "sector", "avg_salary_qr"]
    )
    attrition_by_sector: list[str] = field(
        default_factory=lambda: ["year", "sector", "attrition_percent"]
    )
    company_size_distribution: list[str] = field(
        default_factory=lambda: ["year", "size_band", "companies"]
    )
    sector_employment_by_year: list[str] = field(
        default_factory=lambda: ["year", "sector", "employees"]
    )
    ewi_employment_drop: list[str] = field(
        default_factory=lambda: ["year", "sector", "drop_percent"]
    )
