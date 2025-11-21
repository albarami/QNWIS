"""CLI script to generate deterministic synthetic LMIS CSV pack."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _ensure_project_root() -> None:
    """Ensure the repository root is available on sys.path."""
    project_root = Path(__file__).resolve().parents[1]
    root_str = str(project_root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)


def main() -> None:
    """
    Generate synthetic LMIS CSV files for offline development.

    Example:
        python scripts/seed_synthetic_lmis.py --out data/synthetic/lmis
    """
    _ensure_project_root()
    from src.qnwis.data.synthetic.seed_lmis import generate_synthetic_lmis

    parser = argparse.ArgumentParser(
        description="Generate deterministic synthetic LMIS data pack"
    )
    parser.add_argument(
        "--out",
        default="data/synthetic/lmis",
        help="Output directory for synthetic CSVs (default: data/synthetic/lmis)",
    )
    parser.add_argument(
        "--start_year",
        type=int,
        default=2017,
        help="Start year for data generation (default: 2017)",
    )
    parser.add_argument(
        "--end_year",
        type=int,
        default=2024,
        help="End year for data generation (default: 2024)",
    )
    parser.add_argument(
        "--companies",
        type=int,
        default=800,
        help="Number of companies to generate (default: 800)",
    )
    parser.add_argument(
        "--employees",
        type=int,
        default=20000,
        help="Number of employees to generate (default: 20000)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility (default: 42)",
    )
    parser.add_argument(
        "--small",
        action="store_true",
        help="Use the demo preset (200 companies, 3000 employees). "
        "Explicit --companies/--employees values win if provided.",
    )

    raw_args = sys.argv[1:]
    args = parser.parse_args()

    def _flag_provided(name: str) -> bool:
        flag = f"--{name}"
        return any(arg == flag or arg.startswith(f"{flag}=") for arg in raw_args)

    if args.small:
        preset_companies = 200
        preset_employees = 3000
        updates: list[str] = []
        if not _flag_provided("companies"):
            args.companies = preset_companies
            updates.append(f"companies={args.companies}")
        if not _flag_provided("employees"):
            args.employees = preset_employees
            updates.append(f"employees={args.employees}")
        if updates:
            print("Applying --small preset (" + ", ".join(updates) + ").")

    print("Generating synthetic LMIS data pack...")
    print(f"  Output: {args.out}")
    print(f"  Years: {args.start_year}-{args.end_year}")
    print(f"  Companies: {args.companies}")
    print(f"  Employees: {args.employees}")
    print(f"  Seed: {args.seed}")
    print()

    info = generate_synthetic_lmis(
        args.out,
        args.start_year,
        args.end_year,
        args.companies,
        args.employees,
        args.seed,
    )

    print("Synthetic LMIS data pack generated successfully!")
    print()
    print("Files created:")
    for key, path in info.items():
        print(f"  - {key}: {path}")
    print()
    print("Next steps:")
    print("  1. Run tests: pytest tests/unit/test_synthetic_shapes.py -v")
    print("  2. Set QNWIS_QUERIES_DIR=src/qnwis/data/queries")
    print("  3. Start API: uvicorn src.qnwis.app:app --reload")


if __name__ == "__main__":
    main()
