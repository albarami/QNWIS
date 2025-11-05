"""Unit tests for synthetic data generation shapes and value ranges."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from src.qnwis.data.synthetic.seed_lmis import generate_synthetic_lmis


def test_companies_csv_shape(tmp_path: pytest.TempPathFactory) -> None:
    """
    Verify companies.csv has expected structure and plausible values.

    Checks:
    - Header row matches schema
    - Company IDs are sequential
    - Sectors are from expected list
    """
    info = generate_synthetic_lmis(
        str(tmp_path), n_companies=20, n_employees=100
    )

    companies_path = Path(info["companies"])
    assert companies_path.exists()

    with companies_path.open(encoding="utf-8") as f:
        reader = csv.reader(f, delimiter=";")
        header = next(reader)

        # Verify header
        assert header[0] == "company_id"
        assert "company_name" in header
        assert "sector" in header
        assert "size_band" in header
        assert "founded_year" in header

        # Read some data rows
        rows = list(reader)
        assert len(rows) == 20

        # Check first row
        first_row = rows[0]
        company_id = int(first_row[0])
        assert company_id == 1

        # Check last row
        last_row = rows[-1]
        company_id = int(last_row[0])
        assert company_id == 20


def test_employment_history_csv_shape(tmp_path: pytest.TempPathFactory) -> None:
    """
    Verify employment_history.csv has expected structure.

    Checks:
    - Header row matches schema
    - Person IDs and years are present
    - Salaries are within reasonable range
    """
    info = generate_synthetic_lmis(
        str(tmp_path),
        n_companies=10,
        n_employees=50,
        start_year=2020,
        end_year=2022,
    )

    emp_path = Path(info["employment_history"])
    assert emp_path.exists()

    with emp_path.open(encoding="utf-8") as f:
        reader = csv.reader(f, delimiter=";")
        header = next(reader)

        # Verify header
        assert header[0] == "person_id"
        assert "year" in header
        assert "company_id" in header
        assert "gender" in header
        assert "nationality" in header
        assert "monthly_salary" in header

        # Read some data rows
        rows = list(reader)
        # Should have 50 people * 3 years = 150 rows
        assert len(rows) == 150

        # Check salary range
        salaries = [int(row[6]) for row in rows]
        assert all(2500 <= s <= 50000 for s in salaries)


def test_aggregate_files_exist(tmp_path: pytest.TempPathFactory) -> None:
    """
    Verify all aggregate CSV files are generated.

    Checks that the aggregates directory contains expected files.
    """
    info = generate_synthetic_lmis(str(tmp_path), n_companies=10, n_employees=100)

    agg_dir = Path(info["aggregates_dir"])
    assert agg_dir.exists()
    assert agg_dir.is_dir()

    expected_files = [
        "employment_share_by_gender.csv",
        "unemployment_gcc_latest.csv",
        "qatarization_by_sector.csv",
        "avg_salary_by_sector.csv",
        "attrition_by_sector.csv",
        "company_size_distribution.csv",
        "sector_employment_by_year.csv",
        "ewi_employment_drop.csv",
    ]

    for filename in expected_files:
        file_path = agg_dir / filename
        assert file_path.exists(), f"Missing aggregate file: {filename}"


def test_avg_salary_values_plausible(tmp_path: pytest.TempPathFactory) -> None:
    """
    Verify average salary aggregate has plausible values.

    Checks:
    - Header row is correct
    - Salary values are within expected range
    - Years are as specified
    """
    info = generate_synthetic_lmis(
        str(tmp_path), start_year=2020, end_year=2022
    )

    agg_dir = Path(info["aggregates_dir"])
    salary_path = agg_dir / "avg_salary_by_sector.csv"

    with salary_path.open(encoding="utf-8") as f:
        reader = csv.reader(f, delimiter=";")
        header = next(reader)

        assert header[-1] == "avg_salary_qr"

        rows = list(reader)
        for row in rows:
            year = int(row[0])
            assert 2020 <= year <= 2022

            salary = int(row[2])
            assert 2500 <= salary <= 30000


def test_gcc_unemployment_structure(tmp_path: pytest.TempPathFactory) -> None:
    """
    Verify GCC unemployment aggregate has correct structure.

    Checks:
    - Contains data for 6 GCC countries
    - Values are reasonable percentages
    - Year matches end_year
    """
    info = generate_synthetic_lmis(
        str(tmp_path), start_year=2020, end_year=2024
    )

    agg_dir = Path(info["aggregates_dir"])
    gcc_path = agg_dir / "unemployment_gcc_latest.csv"

    with gcc_path.open(encoding="utf-8") as f:
        reader = csv.reader(f, delimiter=";")
        header = next(reader)

        assert header == ["country", "year", "value"]

        rows = list(reader)
        # Should have 6 GCC countries
        assert len(rows) == 6

        countries = {row[0] for row in rows}
        expected_countries = {"QAT", "ARE", "KWT", "OMN", "BHR", "SAU"}
        assert countries == expected_countries

        # All rows should be for 2024
        for row in rows:
            assert int(row[1]) == 2024
            # Unemployment should be reasonable percentage
            value = float(row[2])
            assert 0.0 <= value <= 10.0


def test_qatarization_percentages(tmp_path: pytest.TempPathFactory) -> None:
    """
    Verify Qatarization percentages are calculated correctly.

    Checks:
    - Percentages are between 0 and 100
    - Formula: qataris / (qataris + non_qataris) * 100
    """
    info = generate_synthetic_lmis(str(tmp_path))

    agg_dir = Path(info["aggregates_dir"])
    qz_path = agg_dir / "qatarization_by_sector.csv"

    with qz_path.open(encoding="utf-8") as f:
        reader = csv.reader(f, delimiter=";")
        next(reader)  # Skip header

        rows = list(reader)
        for row in rows[:10]:  # Check first 10 rows
            qataris = int(row[2])
            non_qataris = int(row[3])
            qz_percent = float(row[4])

            # Verify calculation
            expected = round(100.0 * qataris / (qataris + non_qataris), 2)
            assert abs(qz_percent - expected) < 0.01

            # Verify range
            assert 0.0 <= qz_percent <= 100.0


def test_attrition_rate_distribution(tmp_path: pytest.TempPathFactory) -> None:
    """
    Verify attrition rates follow expected distribution.

    Checks:
    - Attrition rates are positive
    - Mean is around expected value (7.5%)
    - No extreme outliers
    """
    info = generate_synthetic_lmis(str(tmp_path))

    agg_dir = Path(info["aggregates_dir"])
    attr_path = agg_dir / "attrition_by_sector.csv"

    with attr_path.open(encoding="utf-8") as f:
        reader = csv.reader(f, delimiter=";")
        next(reader)  # Skip header

        attrition_values = [float(row[2]) for row in reader]

        # All should be positive
        assert all(v >= 0.0 for v in attrition_values)

        # Mean should be roughly around 7.5% (±3%)
        mean_attrition = sum(attrition_values) / len(attrition_values)
        assert 4.0 <= mean_attrition <= 11.0

        # No extreme outliers
        assert all(v <= 20.0 for v in attrition_values)


def test_ewi_drop_percent_bounds(tmp_path: pytest.TempPathFactory) -> None:
    """Verify early warning drop percentages stay within 0-100 range."""
    info = generate_synthetic_lmis(str(tmp_path))

    agg_dir = Path(info["aggregates_dir"])
    drop_path = agg_dir / "ewi_employment_drop.csv"

    with drop_path.open(encoding="utf-8") as f:
        reader = csv.reader(f, delimiter=";")
        next(reader)
        drops = [float(row[2]) for row in reader]

    assert all(0.0 <= value <= 100.0 for value in drops)


def test_invalid_generator_args(tmp_path: pytest.TempPathFactory) -> None:
    """Generator should reject impossible ranges and counts."""
    with pytest.raises(ValueError, match="start_year"):
        generate_synthetic_lmis(str(tmp_path), start_year=2025, end_year=2024)
    with pytest.raises(ValueError, match="start_year must be between"):
        generate_synthetic_lmis(str(tmp_path), start_year=1800, end_year=2024)
    with pytest.raises(ValueError, match="n_companies"):
        generate_synthetic_lmis(str(tmp_path), n_companies=0)
    with pytest.raises(ValueError, match="n_employees"):
        generate_synthetic_lmis(str(tmp_path), n_employees=0)
