"""Deterministic synthetic LMIS data generator."""

from __future__ import annotations

import csv
import random
from pathlib import Path

from .schemas import Aggregates, CompaniesSchema, EmploymentHistorySchema

SEED_DEFAULT = 42
YEARS_DEFAULT = range(2017, 2025)
SECTORS: tuple[str, ...] = (
    "Energy",
    "Construction",
    "Finance",
    "Hospitality",
    "Education",
    "Healthcare",
    "Public",
    "Manufacturing",
    "Transport",
    "ICT",
)
EDULEVEL: tuple[str, ...] = (
    "Secondary",
    "Diploma",
    "Bachelor",
    "Master",
    "Doctorate",
)
SIZE_BANDS: tuple[str, ...] = ("Micro", "Small", "Medium", "Large", "XL")
SALARY_FLOOR_QR = 2500
FOUNDED_YEAR_MIN = 1980
FOUNDED_YEAR_MAX = 2020
ATTRITION_MIN_PERCENT = 0.0
ATTRITION_MAX_PERCENT = 100.0
DROP_MIN_PERCENT = 0.0
DROP_MAX_PERCENT = 100.0
YEAR_MIN = 1900
YEAR_MAX = 2100
EMPLOYEE_REENTRY_PROB = 0.10
WAGE_DRIFT_LOW = -0.03
WAGE_DRIFT_HIGH = 0.08
AGGREGATE_DRIFT_LOW = -0.03
AGGREGATE_DRIFT_HIGH = 0.03


def _rng(seed: int) -> random.Random:
    """
    Create a deterministic random number generator.

    Args:
        seed: Random seed for reproducibility

    Returns:
        Initialized Random instance with warm-up for cross-platform determinism
    """
    r = random.Random(seed)
    # Warm-up for cross-platform determinism
    for _ in range(10):
        r.random()
    return r


def _weighted_choice(r: random.Random, pairs: list[tuple[str, float]]) -> str:
    """
    Select a value from weighted pairs using deterministic RNG.

    Args:
        r: Random number generator
        pairs: list of (value, weight) tuples

    Returns:
        Selected value based on weights
    """
    total = sum(w for _, w in pairs)
    pick = r.random() * total
    upto = 0.0
    for v, w in pairs:
        if upto + w >= pick:
            return v
        upto += w
    return pairs[-1][0]


def _write_companies(path: Path, n_companies: int, r: random.Random) -> None:
    """Emit companies.csv with deterministic company roster."""
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(CompaniesSchema().columns)
        for cid in range(1, n_companies + 1):
            sector = r.choice(SECTORS)
            size_band = _weighted_choice(
                r,
                [
                    ("Micro", 0.15),
                    ("Small", 0.35),
                    ("Medium", 0.30),
                    ("Large", 0.15),
                    ("XL", 0.05),
                ],
            )
            founded = r.randint(FOUNDED_YEAR_MIN, FOUNDED_YEAR_MAX)
            writer.writerow([cid, f"Company {cid:05d}", sector, size_band, founded])


def _write_employment_history(
    path: Path,
    years: list[int],
    n_companies: int,
    n_employees: int,
    r: random.Random,
) -> None:
    """Emit employment_history.csv with per person-year rows."""
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(EmploymentHistorySchema().columns)
        for pid in range(1, n_employees + 1):
            gender = _weighted_choice(r, [("Male", 0.71), ("Female", 0.29)])
            nationality = _weighted_choice(r, [("Qatari", 0.14), ("Non-Qatari", 0.86)])
            education = _weighted_choice(
                r, [(e, 1.0 / (i + 1)) for i, e in enumerate(EDULEVEL)]
            )
            anchor_company = r.randint(1, n_companies)
            base_salary = r.randint(3500, 42000)
            employed = True
            for year in years:
                if r.random() < EMPLOYEE_REENTRY_PROB:
                    employed = not employed
                company_id = anchor_company if employed else r.randint(1, n_companies)
                drift = 1.0 + r.uniform(WAGE_DRIFT_LOW, WAGE_DRIFT_HIGH)
                base_salary = max(SALARY_FLOOR_QR, int(base_salary * drift))
                status = "employed" if employed else "exited"
                writer.writerow(
                    [
                        pid,
                        year,
                        company_id,
                        gender,
                        nationality,
                        education,
                        base_salary,
                        status,
                    ]
                )


def _write_aggregates(agg_dir: Path, years: list[int], r: random.Random) -> None:  # noqa: C901
    """Emit precomputed aggregate CSV files for fast querying."""
    agg_dir.mkdir(parents=True, exist_ok=True)
    agg_schemas = Aggregates()

    # 3a) Employment share by gender
    path_gender = agg_dir / "employment_share_by_gender.csv"
    with path_gender.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(agg_schemas.employment_share_by_gender)
        for year in years:
            # Approximate with ratios near 71/29 within roughly +/-2%
            male = 71.0 + r.uniform(-2, 2)
            female = 100.0 - male
            writer.writerow([year, round(male, 2), round(female, 2), 100.0])

    # 3b) GCC unemployment synthetic snapshot
    path_gcc = agg_dir / "unemployment_gcc_latest.csv"
    with path_gcc.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(agg_schemas.unemployment_gcc)
        gcc_countries = [
            ("QAT", 0.2, 0.15),
            ("ARE", 2.5, 0.6),
            ("KWT", 2.2, 0.5),
            ("OMN", 3.0, 0.7),
            ("BHR", 2.8, 0.6),
            ("SAU", 5.0, 0.9),
        ]
        for country, base, variance in gcc_countries:
            value = max(0.1, round(base + r.uniform(-variance, variance), 2))
            writer.writerow([country, years[-1], value])

    # 3c) Qatarization by sector
    path_qatarization = agg_dir / "qatarization_by_sector.csv"
    with path_qatarization.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(agg_schemas.qatarization_by_sector)
        for year in years:
            for sector in SECTORS:
                non_qataris = r.randint(1200, 8000)
                qataris = max(50, int(non_qataris * r.uniform(0.05, 0.20)))
                percent = round(100.0 * qataris / (qataris + non_qataris), 2)
                writer.writerow([year, sector, qataris, non_qataris, percent])

    # 3d) Avg salary by sector
    path_salary = agg_dir / "avg_salary_by_sector.csv"
    with path_salary.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(agg_schemas.avg_salary_by_sector)
        start_year = years[0]
        for year in years:
            for sector in SECTORS:
                base = {"Energy": 18000, "Finance": 15500, "ICT": 15000}.get(
                    sector, 11000
                )
                drift = 1.0 + 0.02 * (year - start_year) + r.uniform(
                    AGGREGATE_DRIFT_LOW, AGGREGATE_DRIFT_HIGH
                )
                salary = max(SALARY_FLOOR_QR, int(base * drift))
                writer.writerow([year, sector, salary])

    # 3e) Attrition by sector
    path_attrition = agg_dir / "attrition_by_sector.csv"
    with path_attrition.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(agg_schemas.attrition_by_sector)
        for year in years:
            for sector in SECTORS:
                attrition = round(max(1.0, r.gauss(7.5, 2.0)), 2)
                attrition = max(
                    ATTRITION_MIN_PERCENT, min(ATTRITION_MAX_PERCENT, attrition)
                )
                writer.writerow([year, sector, attrition])

    # 3f) Company size distribution
    path_sizes = agg_dir / "company_size_distribution.csv"
    with path_sizes.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(agg_schemas.company_size_distribution)
        for year in years:
            for size_band in SIZE_BANDS:
                count = r.randint(100, 5000)
                writer.writerow([year, size_band, count])

    # 3g) Sector employment by year
    path_sector = agg_dir / "sector_employment_by_year.csv"
    with path_sector.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(agg_schemas.sector_employment_by_year)
        for year in years:
            for sector in SECTORS:
                employees = r.randint(2500, 55000)
                writer.writerow([year, sector, employees])

    # 3h) Early warning: employment drop by sector
    path_drop = agg_dir / "ewi_employment_drop.csv"
    with path_drop.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(agg_schemas.ewi_employment_drop)
        for year in years:
            for sector in SECTORS:
                drop = max(0.0, round(r.uniform(-1.0, 6.0), 2))
                drop = max(DROP_MIN_PERCENT, min(DROP_MAX_PERCENT, drop))
                writer.writerow([year, sector, drop])


def generate_synthetic_lmis(
    out_dir: str,
    start_year: int = 2017,
    end_year: int = 2024,
    n_companies: int = 800,
    n_employees: int = 20000,
    seed: int = SEED_DEFAULT,
) -> dict[str, str]:
    """
    Generate deterministic synthetic LMIS CSV files.

    Creates companies.csv, employment_history.csv, and aggregate CSVs
    for query execution without real data or network calls.

    Args:
        out_dir: Output directory for CSV files
        start_year: First year of data (inclusive)
        end_year: Last year of data (inclusive)
        n_companies: Number of companies to generate
        n_employees: Number of employees to generate
        seed: Random seed for reproducibility

    Returns:
        dictionary mapping data types to file paths

    Example:
        >>> info = generate_synthetic_lmis("data/synthetic/lmis")
        >>> print(info["companies"])
        data/synthetic/lmis/companies.csv
    """
    if start_year > end_year:
        raise ValueError("start_year must be less than or equal to end_year.")
    if not (YEAR_MIN <= start_year <= YEAR_MAX):
        raise ValueError(f"start_year must be between {YEAR_MIN} and {YEAR_MAX}.")
    if not (YEAR_MIN <= end_year <= YEAR_MAX):
        raise ValueError(f"end_year must be between {YEAR_MIN} and {YEAR_MAX}.")
    if n_companies <= 0:
        raise ValueError("n_companies must be positive.")
    if n_employees <= 0:
        raise ValueError("n_employees must be positive.")

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    r = _rng(seed)
    years = list(range(start_year, end_year + 1))

    companies_path = out / "companies.csv"
    _write_companies(companies_path, n_companies, r)

    emp_hist_path = out / "employment_history.csv"
    _write_employment_history(
        emp_hist_path,
        years,
        n_companies,
        n_employees,
        r,
    )

    aggregates_dir = out / "aggregates"
    _write_aggregates(aggregates_dir, years, r)

    return {
        "companies": str(companies_path),
        "employment_history": str(emp_hist_path),
        "aggregates_dir": str(aggregates_dir),
    }
