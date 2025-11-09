"""
CLI tool for QNWIS Scenario Planner.

Provides commands to:
- Apply single scenario to baseline forecast
- Compare multiple scenarios
- Validate scenario specifications
- Run batch sector scenarios
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from ..agents.base import DataClient
from ..agents.scenario_agent import ScenarioAgent
from ..scenario.dsl import validate_scenario_file

logger = logging.getLogger(__name__)


def apply_scenario(
    agent: ScenarioAgent,
    spec_path: str,
    format: str = "yaml",
) -> None:
    """
    Apply scenario from file.

    Args:
        agent: ScenarioAgent instance
        spec_path: Path to scenario specification file
        format: File format ("yaml" or "json")
    """
    try:
        with open(spec_path, encoding="utf-8") as f:
            spec_content = f.read()

        print(f"Applying scenario from: {spec_path}")
        print()

        narrative = agent.apply(spec_content, spec_format=format)
        print(narrative)

    except FileNotFoundError:
        print(f"Error: File not found: {spec_path}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"Error applying scenario: {exc}", file=sys.stderr)
        sys.exit(1)


def compare_scenarios(
    agent: ScenarioAgent,
    spec_paths: list[str],
    format: str = "yaml",
) -> None:
    """
    Compare multiple scenarios from files.

    Args:
        agent: ScenarioAgent instance
        spec_paths: List of paths to scenario specification files
        format: File format ("yaml" or "json")
    """
    try:
        specs: list[str] = []
        for spec_path in spec_paths:
            with open(spec_path, encoding="utf-8") as f:
                specs.append(f.read())

        print(f"Comparing {len(specs)} scenarios")
        print()

        narrative = agent.compare(specs, spec_format=format)
        print(narrative)

    except FileNotFoundError as exc:
        print(f"Error: File not found: {exc}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"Error comparing scenarios: {exc}", file=sys.stderr)
        sys.exit(1)


def batch_scenarios(
    agent: ScenarioAgent,
    specs_dir: str,
    weights_path: str | None = None,
    format: str = "yaml",
) -> None:
    """
    Run batch scenarios from directory.

    Args:
        agent: ScenarioAgent instance
        specs_dir: Directory containing sector scenario files
        weights_path: Optional path to JSON file with sector weights
        format: File format ("yaml" or "json")
    """
    try:
        specs_path = Path(specs_dir)
        if not specs_path.is_dir():
            print(f"Error: Not a directory: {specs_dir}", file=sys.stderr)
            sys.exit(1)

        # Collect scenario files
        pattern = f"*.{format}"
        spec_files = list(specs_path.glob(pattern))

        if not spec_files:
            print(f"Error: No {pattern} files found in {specs_dir}", file=sys.stderr)
            sys.exit(1)

        # Build sector specs map
        sector_specs: dict[str, str] = {}
        for spec_file in spec_files:
            sector_name = spec_file.stem
            with open(spec_file, encoding="utf-8") as f:
                sector_specs[sector_name] = f.read()

        # Load weights if provided
        weights: dict[str, float] | None = None
        if weights_path:
            with open(weights_path, encoding="utf-8") as f:
                weights = json.load(f)

        print(f"Batch processing {len(sector_specs)} sectors from: {specs_dir}")
        print()

        narrative = agent.batch(
            sector_specs,
            spec_format=format,
            sector_weights=weights,
        )
        print(narrative)

    except FileNotFoundError as exc:
        print(f"Error: File not found: {exc}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as exc:
        print(f"Error parsing weights JSON: {exc}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"Error in batch processing: {exc}", file=sys.stderr)
        sys.exit(1)


def validate_spec(spec_path: str) -> None:
    """
    Validate scenario specification file.

    Args:
        spec_path: Path to scenario specification file
    """
    try:
        is_valid, message = validate_scenario_file(spec_path)

        if is_valid:
            print(f"✓ {message}")
            sys.exit(0)
        else:
            print(f"✗ {message}", file=sys.stderr)
            sys.exit(1)

    except Exception as exc:
        print(f"Error validating spec: {exc}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    """
    Main entry point for scenario CLI.

    Supports:
    - apply: Apply single scenario
    - compare: Compare multiple scenarios
    - batch: Process batch of sector scenarios
    - validate: Validate scenario specification
    """
    ap = argparse.ArgumentParser(
        prog="qnwis-scenario",
        description="QNWIS Scenario Planner CLI",
    )

    ap.add_argument(
        "--action",
        choices=["apply", "compare", "batch", "validate"],
        required=True,
        help="Scenario operation to perform",
    )

    ap.add_argument(
        "--spec",
        type=str,
        help="Path to scenario specification file (for apply/validate)",
    )

    ap.add_argument(
        "--specs",
        type=str,
        nargs="+",
        help="List of scenario specification files (for compare)",
    )

    ap.add_argument(
        "--specs-dir",
        type=str,
        help="Directory containing sector scenarios (for batch)",
    )

    ap.add_argument(
        "--weights",
        type=str,
        help="Path to JSON file with sector weights (for batch)",
    )

    ap.add_argument(
        "--format",
        choices=["yaml", "json"],
        default="yaml",
        help="Scenario specification format (default: yaml)",
    )

    ap.add_argument(
        "--queries-dir",
        type=str,
        default="data/queries",
        help="Path to deterministic queries directory",
    )

    ap.add_argument(
        "--cache-ttl",
        type=int,
        default=300,
        help="Cache TTL in seconds (default: 300)",
    )

    ap.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = ap.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # Handle validate action (no agent needed)
    if args.action == "validate":
        if not args.spec:
            print("Error: --spec required for validate action", file=sys.stderr)
            sys.exit(1)
        validate_spec(args.spec)
        return

    # Initialize DataClient and ScenarioAgent
    try:
        client = DataClient(
            queries_dir=args.queries_dir,
            ttl_s=args.cache_ttl,
        )
        agent = ScenarioAgent(client)
    except Exception as exc:
        print(f"Error initializing agent: {exc}", file=sys.stderr)
        sys.exit(1)

    # Execute requested action
    if args.action == "apply":
        if not args.spec:
            print("Error: --spec required for apply action", file=sys.stderr)
            sys.exit(1)
        apply_scenario(agent, args.spec, args.format)

    elif args.action == "compare":
        if not args.specs or len(args.specs) < 2:
            print("Error: --specs with at least 2 files required for compare", file=sys.stderr)
            sys.exit(1)
        compare_scenarios(agent, args.specs, args.format)

    elif args.action == "batch":
        if not args.specs_dir:
            print("Error: --specs-dir required for batch action", file=sys.stderr)
            sys.exit(1)
        batch_scenarios(agent, args.specs_dir, args.weights, args.format)


if __name__ == "__main__":
    main()
