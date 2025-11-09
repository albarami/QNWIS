"""
QNWIS Workflow CLI.

Command-line interface for executing orchestration workflows.

Examples:
    # Pattern analysis
    qnwis workflow --intent pattern.correlation --sector Construction --months 36

    # GCC benchmarking
    qnwis workflow --intent strategy.gcc_benchmark --min-countries 4

    # Vision 2030 alignment
    qnwis workflow --intent strategy.vision2030

    # With custom config
    qnwis workflow --intent pattern.anomalies --config custom.yml --output report.json
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

from ..agents.base import DataClient
from ..config.orchestration_loader import load_config
from ..orchestration.graph import create_graph
from ..orchestration.registry import create_default_registry
from ..orchestration.schemas import OrchestrationTask

logger = logging.getLogger(__name__)


def setup_logging(level: str = "INFO") -> None:
    """
    Configure logging for CLI.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
    """
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments.

    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="QNWIS Orchestration Workflow CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Primary input (mutually exclusive with query)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "--intent",
        choices=[
            "pattern.anomalies",
            "pattern.correlation",
            "pattern.root_causes",
            "pattern.best_practices",
            "strategy.gcc_benchmark",
            "strategy.talent_competition",
            "strategy.vision2030",
        ],
        help="Explicit intent to execute",
    )
    input_group.add_argument(
        "--query",
        type=str,
        help="Natural language query (will be classified to intent)",
    )

    # Optional workflow arguments
    parser.add_argument(
        "--request-id",
        help="Request tracking identifier",
    )

    parser.add_argument(
        "--user-id",
        help="User identifier for audit trail",
    )

    # Configuration
    parser.add_argument(
        "--config",
        type=Path,
        help="Path to orchestration config (default: src/qnwis/config/orchestration.yml)",
    )

    parser.add_argument(
        "--queries-dir",
        type=Path,
        help="Path to query definitions (default: data/queries)",
    )

    # Output
    parser.add_argument(
        "--output",
        type=Path,
        help="Output file for results (default: stdout)",
    )

    parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="json",
        help="Output format (default: json)",
    )

    # Logging
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)",
    )

    # Intent-specific parameters (dynamic)
    parser.add_argument(
        "--sector",
        help="Sector filter for pattern analysis",
    )

    parser.add_argument(
        "--months",
        type=int,
        help="Number of months for time-series analysis",
    )

    parser.add_argument(
        "--min-countries",
        type=int,
        help="Minimum countries for GCC benchmark",
    )

    parser.add_argument(
        "--z-threshold",
        type=float,
        help="Z-score threshold for anomaly detection",
    )

    parser.add_argument(
        "--min-sample-size",
        type=int,
        help="Minimum sample size for statistical tests",
    )

    parser.add_argument(
        "--metrics",
        nargs="+",
        help="Metrics to analyze (space-separated)",
    )

    parser.add_argument(
        "--start-year",
        type=int,
        help="Start year for analysis",
    )

    parser.add_argument(
        "--end-year",
        type=int,
        help="End year for analysis",
    )

    return parser.parse_args()


def build_params(args: argparse.Namespace) -> dict[str, Any]:
    """
    Build parameter dictionary from CLI arguments.

    Args:
        args: Parsed command-line arguments

    Returns:
        Parameter dictionary
    """
    params = {}

    # Map CLI args to parameters
    param_mapping = {
        "sector": "sector",
        "months": "months",
        "min_countries": "min_countries",
        "z_threshold": "z_threshold",
        "min_sample_size": "min_sample_size",
        "metrics": "metrics",
        "start_year": "start_year",
        "end_year": "end_year",
    }

    for cli_arg, param_name in param_mapping.items():
        value = getattr(args, cli_arg, None)
        if value is not None:
            params[param_name] = value

    return params


def format_markdown(result: Any) -> str:
    """
    Format OrchestrationResult as Markdown.

    Args:
        result: OrchestrationResult

    Returns:
        Markdown string
    """
    lines = []

    # Header
    lines.append(f"# QNWIS Analysis: {result.intent}")
    lines.append("")
    lines.append(f"**Status**: {'SUCCESS' if result.ok else 'FAILED'}")
    lines.append(f"**Request ID**: {result.request_id or 'N/A'}")
    lines.append(f"**Timestamp**: {result.timestamp}")
    lines.append("")

    # Sections
    for section in result.sections:
        lines.append(f"## {section.title}")
        lines.append("")
        lines.append(section.body_md)
        lines.append("")

    # Metadata
    if result.citations:
        lines.append("## Citations")
        lines.append("")
        lines.append(f"**Total Citations**: {len(result.citations)}")
        lines.append("")

    # Reproducibility
    if result.reproducibility:
        lines.append("## Reproducibility")
        lines.append("")
        lines.append(f"**Method**: `{result.reproducibility.method}`")
        lines.append(f"**Timestamp**: {result.reproducibility.timestamp}")
        lines.append("")

    # Warnings
    if result.warnings:
        lines.append("## Warnings")
        lines.append("")
        for warning in result.warnings:
            lines.append(f"- {warning}")
        lines.append("")

    return "\n".join(lines)


def main() -> int:
    """
    Main CLI entry point.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    args = parse_args()
    setup_logging(args.log_level)

    logger.info("QNWIS Workflow CLI starting")
    if args.intent:
        logger.info("Intent: %s", args.intent)
    else:
        logger.info("Query: %s", args.query[:80])

    try:
        # Load configuration
        config = load_config(args.config)
        logger.debug("Configuration loaded: %s", config.keys())

        # Check if intent is enabled (only for explicit intent)
        if args.intent:
            enabled_intents = config.get("enabled_intents", [])
            if args.intent not in enabled_intents:
                logger.error("Intent not enabled: %s", args.intent)
                logger.info("Enabled intents: %s", ", ".join(enabled_intents))
                return 1

        # Create data client
        queries_dir = str(args.queries_dir) if args.queries_dir else None
        client = DataClient(queries_dir=queries_dir)
        logger.debug("DataClient initialized")

        # Create registry
        registry = create_default_registry(client)
        logger.debug("Registry created with %d intents", len(registry.intents()))

        # Create and build graph
        graph = create_graph(registry, config)
        logger.debug("Graph built successfully")

        # Build task
        params = build_params(args)

        # Create task with either intent or query_text
        if args.intent:
            task = OrchestrationTask(
                intent=args.intent,
                params=params,
                user_id=args.user_id,
                request_id=args.request_id,
            )
            logger.info("Executing workflow: intent=%s params=%s", task.intent, list(params.keys()))
        else:
            task = OrchestrationTask(
                query_text=args.query,
                params=params,
                user_id=args.user_id,
                request_id=args.request_id,
            )
            logger.info(
                "Executing workflow: query='%s...' params=%s", args.query[:50], list(params.keys())
            )

        # Run workflow
        result = graph.run(task)

        logger.info("Workflow completed: ok=%s", result.ok)

        # Format output
        if args.format == "json":
            output = json.dumps(result.model_dump(), indent=2)
        else:
            output = format_markdown(result)

        # Write output
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output)
            logger.info("Results written to: %s", args.output)
        else:
            print(output)

        return 0 if result.ok else 1

    except FileNotFoundError as exc:
        logger.error("File not found: %s", exc)
        return 1
    except Exception as exc:
        logger.exception("Workflow execution failed")
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
