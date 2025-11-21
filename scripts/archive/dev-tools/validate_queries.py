#!/usr/bin/env python
"""
Validation script for QNWIS query definitions.

Checks all YAML query files for:
- Schema compliance with QueryDefinition model
- SQL safety (read-only, no dangerous operations)
- Parameter consistency (declared params match SQL usage)
- Required fields present
- Valid data types

Usage:
    python scripts/validate_queries.py
    python scripts/validate_queries.py --verbose
    python scripts/validate_queries.py --query unemployment_rate_latest
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import List, Tuple

import yaml

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from qnwis.data.deterministic.schema import QueryDefinition

# Regular expression to find named parameters in SQL
# Negative lookbehind to avoid matching PostgreSQL cast operators (::type)
NAMED_PARAM_RE = re.compile(r"(?<!:):([a-zA-Z_][a-zA-Z0-9_]*)")


def validate_query_file(
    file_path: Path, verbose: bool = False
) -> Tuple[bool, List[str]]:
    """
    Validate a single query YAML file.

    Args:
        file_path: Path to YAML file
        verbose: Print detailed success messages

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors: List[str] = []

    try:
        # Load YAML
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not data:
            errors.append(f"{file_path.name}: Empty or invalid YAML")
            return False, errors

        # Validate against Pydantic schema
        try:
            query_def = QueryDefinition(**data)
        except Exception as e:
            errors.append(f"{file_path.name}: Schema validation failed: {e}")
            return False, errors

        # Extract parameters from SQL
        sql_params = set(NAMED_PARAM_RE.findall(query_def.sql))

        # Get declared parameters
        declared_params = {p.name for p in query_def.parameters}

        # Check for undeclared parameters used in SQL
        undeclared = sql_params - declared_params
        if undeclared:
            errors.append(
                f"{file_path.name}: SQL uses undeclared parameters: {sorted(undeclared)}"
            )

        # Check for declared parameters not used in SQL
        unused = declared_params - sql_params
        if unused:
            errors.append(
                f"{file_path.name}: Declared parameters not used in SQL: {sorted(unused)}"
            )

        # Verify query_id matches filename
        expected_id = file_path.stem
        if query_def.query_id != expected_id:
            errors.append(
                f"{file_path.name}: query_id '{query_def.query_id}' should match filename '{expected_id}'"
            )

        # Check output_schema is not empty
        if not query_def.output_schema:
            errors.append(f"{file_path.name}: output_schema cannot be empty")

        # Verify reasonable cache_ttl
        if query_def.cache_ttl < 60 or query_def.cache_ttl > 604800:
            errors.append(
                f"{file_path.name}: cache_ttl should be between 60s and 604800s (7 days)"
            )

        # Verify reasonable freshness_sla
        if query_def.freshness_sla < 3600 or query_def.freshness_sla > 2592000:
            errors.append(
                f"{file_path.name}: freshness_sla should be between 1 hour and 30 days"
            )

        if errors:
            return False, errors

        if verbose:
            print(f"✅ {file_path.name}: Valid ({query_def.query_id})")

        return True, []

    except yaml.YAMLError as e:
        errors.append(f"{file_path.name}: YAML parsing error: {e}")
        return False, errors
    except Exception as e:
        errors.append(f"{file_path.name}: Unexpected error: {e}")
        return False, errors


def validate_all_queries(
    query_dir: Path, verbose: bool = False
) -> Tuple[int, int, List[str]]:
    """
    Validate all query files in directory.

    Args:
        query_dir: Directory containing query YAML files
        verbose: Print detailed messages

    Returns:
        Tuple of (valid_count, total_count, all_errors)
    """
    yaml_files = sorted(query_dir.glob("*.yaml"))

    if not yaml_files:
        return 0, 0, [f"No YAML files found in {query_dir}"]

    valid_count = 0
    all_errors: List[str] = []

    for yaml_file in yaml_files:
        is_valid, errors = validate_query_file(yaml_file, verbose=verbose)
        if is_valid:
            valid_count += 1
        else:
            all_errors.extend(errors)

    return valid_count, len(yaml_files), all_errors


def main() -> int:
    """Main entry point for validation script."""
    parser = argparse.ArgumentParser(
        description="Validate QNWIS query definitions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--query",
        "-q",
        help="Validate specific query file by name (without .yaml extension)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show detailed validation results"
    )
    parser.add_argument(
        "--dir",
        "-d",
        default="data/queries",
        help="Query directory (default: data/queries)",
    )

    args = parser.parse_args()

    query_dir = Path(args.dir)
    if not query_dir.exists():
        print(f"❌ Error: Query directory not found: {query_dir}")
        return 1

    print(f"🔍 Validating queries in: {query_dir.absolute()}")
    print("=" * 80)

    if args.query:
        # Validate single query
        query_file = query_dir / f"{args.query}.yaml"
        if not query_file.exists():
            print(f"❌ Error: Query file not found: {query_file}")
            return 1

        is_valid, errors = validate_query_file(query_file, verbose=True)

        if is_valid:
            print("\n✅ Query is valid")
            return 0
        else:
            print("\n❌ Validation failed:")
            for error in errors:
                print(f"  - {error}")
            return 1

    # Validate all queries
    valid_count, total_count, all_errors = validate_all_queries(
        query_dir, verbose=args.verbose
    )

    print("\n" + "=" * 80)
    print(f"\n📊 Results: {valid_count}/{total_count} queries valid")

    if all_errors:
        print(f"\n❌ Found {len(all_errors)} validation errors:\n")
        for error in all_errors:
            print(f"  - {error}")
        return 1

    print("\n✅ All queries valid!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
