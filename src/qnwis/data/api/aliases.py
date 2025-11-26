"""
Canonical query ID resolver for Data API.

Maps canonical query keys to preferred registry IDs, allowing code to work
with both synthetic (syn_*) and production (q_*) query identifiers transparently.
"""

from __future__ import annotations

# Canonical map to preferred IDs; resolve at runtime against registry.all_ids()
CANONICAL_TO_IDS: dict[str, list[str]] = {
    "employment_share_all": [
        "syn_employment_share_by_gender_2017_2024",
        "q_employment_share_by_gender_2017_2024",
    ],
    "employment_share_latest": ["syn_employment_share_by_gender_latest"],
    "employment_male_share": ["syn_employment_male_share"],
    "employment_female_share": ["syn_employment_female_share"],
    "employment_total_latest": [
        "syn_employment_latest_total",
        "q_employment_latest_total",
    ],
    "unemployment_gcc_latest": [
        "syn_unemployment_gcc_latest",
        "q_unemployment_rate_gcc_latest",
    ],
    "qatarization_by_sector": [
        "syn_qatarization_by_sector_latest",
        "q_qatarization_rate_by_sector",
    ],
    "qatarization_components": [
        "syn_qatarization_components",
        "q_qatarization_components",
    ],
    "avg_salary_by_sector": [
        "syn_avg_salary_by_sector_latest",
        "q_avg_salary_by_sector",
    ],
    "attrition_by_sector": [
        "syn_attrition_by_sector_latest",
        "q_attrition_rate_by_sector",
    ],
    "company_size_distribution": [
        "syn_company_size_distribution_latest",
        "q_company_size_distribution",
    ],
    "sector_employment": [
        "syn_sector_employment_latest",
        "syn_sector_employment_by_year",
        "q_sector_employment_by_year",
        "syn_sector_employment_2019",
    ],
    "ewi_employment_drop": [
        "syn_ewi_employment_drop_latest",
        "q_ewi_employment_drop",
    ],
    "employees_by_sector_official": ["q_employees_by_sector_nationality"],
    "compensation_by_sector_official": ["q_compensation_by_sector"],
    "training_enrollment": ["q_training_center_trainees"],
    "labor_force_sector": ["q_labor_force_by_sector"],
}
