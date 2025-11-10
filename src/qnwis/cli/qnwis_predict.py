"""
CLI tool for offline forecasting and early-warning analysis.

Usage examples:
    python -m src.qnwis.cli.qnwis_predict forecast --metric retention --sector Construction --start 2019-01-01 --end 2025-06-01 --horizon 6
    python -m src.qnwis.cli.qnwis_predict warn --metric qatarization --sector Healthcare --end 2025-06-01
    python -m src.qnwis.cli.qnwis_predict compare --metric avg_salary --sector All --horizon 6 --methods seasonal_naive,ewma,robust_trend
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from qnwis.agents.base import DataClient
from qnwis.agents.predictor import PredictorAgent


def parse_date(date_str: str) -> date:
    """Parse ISO date string to date object."""
    return datetime.fromisoformat(date_str).date()


def forecast_command(args: argparse.Namespace) -> None:
    """Execute baseline forecast command."""
    client = DataClient()
    agent = PredictorAgent(client)

    start = parse_date(args.start)
    end = parse_date(args.end)

    print(f"\n{'=' * 80}")
    print(f"FORECAST: {args.metric} | Sector: {args.sector or 'All'} | Horizon: {args.horizon} months")
    print(f"{'=' * 80}\n")

    try:
        narrative = agent.forecast_baseline(
            metric=args.metric,
            sector=args.sector,
            start=start,
            end=end,
            horizon_months=args.horizon,
            season=args.season,
        )
        print(narrative)
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(1)


def warn_command(args: argparse.Namespace) -> None:
    """Execute early-warning analysis command."""
    client = DataClient()
    agent = PredictorAgent(client)

    end = parse_date(args.end)

    print(f"\n{'=' * 80}")
    print(f"EARLY WARNING: {args.metric} | Sector: {args.sector or 'All'}")
    print(f"{'=' * 80}\n")

    try:
        narrative = agent.early_warning(
            metric=args.metric,
            sector=args.sector,
            end=end,
            horizon_months=args.horizon,
        )
        print(narrative)
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(1)


def compare_command(args: argparse.Namespace) -> None:
    """Execute scenario comparison command."""
    client = DataClient()
    agent = PredictorAgent(client)

    start = parse_date(args.start)
    end = parse_date(args.end)
    methods = args.methods.split(",")

    print(f"\n{'=' * 80}")
    print(f"SCENARIO COMPARE: {args.metric} | Sector: {args.sector or 'All'}")
    print(f"Methods: {', '.join(methods)} | Horizon: {args.horizon} months")
    print(f"{'=' * 80}\n")

    try:
        narrative = agent.scenario_compare(
            metric=args.metric,
            sector=args.sector,
            start=start,
            end=end,
            horizon_months=args.horizon,
            methods=methods,
        )
        print(narrative)
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="QNWIS Predictor CLI - Baseline forecasting and early-warning analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Forecast command
    forecast_parser = subparsers.add_parser(
        "forecast",
        help="Generate baseline forecast with prediction intervals",
    )
    forecast_parser.add_argument("--metric", required=True, help="Labour market metric")
    forecast_parser.add_argument("--sector", help="Sector filter (default: All)")
    forecast_parser.add_argument("--start", required=True, help="Start date (ISO: YYYY-MM-DD)")
    forecast_parser.add_argument("--end", required=True, help="End date (ISO: YYYY-MM-DD)")
    forecast_parser.add_argument("--horizon", type=int, default=6, help="Forecast horizon in months (default: 6)")
    forecast_parser.add_argument("--season", type=int, default=12, help="Seasonal period (default: 12)")

    # Warn command
    warn_parser = subparsers.add_parser(
        "warn",
        help="Compute early-warning risk score and flags",
    )
    warn_parser.add_argument("--metric", required=True, help="Labour market metric")
    warn_parser.add_argument("--sector", help="Sector filter (default: All)")
    warn_parser.add_argument("--end", required=True, help="Evaluation date (ISO: YYYY-MM-DD)")
    warn_parser.add_argument("--horizon", type=int, default=3, help="Forecast horizon for comparison (default: 3)")

    # Compare command
    compare_parser = subparsers.add_parser(
        "compare",
        help="Compare multiple baseline forecasting methods",
    )
    compare_parser.add_argument("--metric", required=True, help="Labour market metric")
    compare_parser.add_argument("--sector", help="Sector filter (default: All)")
    compare_parser.add_argument("--start", required=True, help="Start date (ISO: YYYY-MM-DD)")
    compare_parser.add_argument("--end", required=True, help="End date (ISO: YYYY-MM-DD)")
    compare_parser.add_argument("--horizon", type=int, required=True, help="Forecast horizon in months")
    compare_parser.add_argument(
        "--methods",
        default="seasonal_naive,ewma,robust_trend",
        help="Comma-separated method names (default: seasonal_naive,ewma,robust_trend)",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Dispatch to command handler
    if args.command == "forecast":
        forecast_command(args)
    elif args.command == "warn":
        warn_command(args)
    elif args.command == "compare":
        compare_command(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
