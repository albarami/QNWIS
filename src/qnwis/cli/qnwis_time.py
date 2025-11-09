"""
CLI interface for Time Machine Agent.

Allows offline execution of time-series analysis reports (baseline, trend, breaks).

Usage examples:
    python -m src.qnwis.cli.qnwis_time --intent time.baseline --metric retention --start 2018-01-01 --end 2025-06-01
    python -m src.qnwis.cli.qnwis_time --intent time.trend --metric qatarization --sector Construction
    python -m src.qnwis.cli.qnwis_time --intent time.breaks --metric salary --z-threshold 3.0
"""

import argparse
import sys
from datetime import date, datetime
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from qnwis.agents.base import DataClient  # noqa: E402
from qnwis.agents.time_machine import TimeMachineAgent  # noqa: E402


def parse_date(date_str: str) -> date:
    """Parse date string in YYYY-MM-DD format."""
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"Invalid date format: '{date_str}'. Use YYYY-MM-DD."
        ) from None


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser for CLI."""
    parser = argparse.ArgumentParser(
        description='Time Machine Agent CLI - Historical time-series analysis',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Baseline report for retention
  python -m src.qnwis.cli.qnwis_time --intent time.baseline --metric retention

  # Trend report for qatarization in Construction sector
  python -m src.qnwis.cli.qnwis_time --intent time.trend --metric qatarization --sector Construction

  # Break detection with custom thresholds
  python -m src.qnwis.cli.qnwis_time --intent time.breaks --metric salary --z-threshold 3.0 --cusum-h 6.0

  # Custom date range
  python -m src.qnwis.cli.qnwis_time --intent time.baseline --metric retention --start 2020-01-01 --end 2024-12-31
        """
    )

    parser.add_argument(
        '--intent',
        required=True,
        choices=['time.baseline', 'time.trend', 'time.breaks'],
        help='Type of time-series analysis to perform'
    )

    parser.add_argument(
        '--metric',
        required=True,
        help='Metric to analyze (e.g., retention, qatarization, salary, employment, attrition)'
    )

    parser.add_argument(
        '--sector',
        default=None,
        help='Optional sector filter (e.g., Construction, Finance)'
    )

    parser.add_argument(
        '--start',
        type=parse_date,
        default=None,
        help='Start date in YYYY-MM-DD format (default: 2 years ago)'
    )

    parser.add_argument(
        '--end',
        type=parse_date,
        default=None,
        help='End date in YYYY-MM-DD format (default: today)'
    )

    parser.add_argument(
        '--base-at',
        type=int,
        default=None,
        help='Index for base period in index-100 (baseline report only)'
    )

    parser.add_argument(
        '--z-threshold',
        type=float,
        default=2.5,
        help='Z-score threshold for outlier detection (breaks report only, default: 2.5)'
    )

    parser.add_argument(
        '--cusum-h',
        type=float,
        default=5.0,
        help='CUSUM threshold for break detection (breaks report only, default: 5.0)'
    )

    parser.add_argument(
        '--queries-dir',
        default=None,
        help='Path to query definitions directory (default: data/queries)'
    )

    parser.add_argument(
        '--output',
        default=None,
        help='Output file path (default: print to stdout)'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )

    return parser


def main():
    """Main entry point for CLI."""
    parser = create_parser()
    args = parser.parse_args()

    # Configure logging
    if args.verbose:
        import logging
        logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    # Set default dates if not provided
    if args.end is None:
        args.end = date.today()
    if args.start is None:
        args.start = date(args.end.year - 2, args.end.month, args.end.day)

    # Initialize DataClient
    try:
        client = DataClient(queries_dir=args.queries_dir)
    except Exception as e:
        print(f"ERROR: Failed to initialize DataClient: {e}", file=sys.stderr)
        sys.exit(1)

    # Initialize TimeMachineAgent
    agent = TimeMachineAgent(client)

    # Execute requested analysis
    try:
        if args.intent == 'time.baseline':
            report = agent.baseline_report(
                metric=args.metric,
                sector=args.sector,
                start=args.start,
                end=args.end,
                base_at=args.base_at
            )

        elif args.intent == 'time.trend':
            report = agent.trend_report(
                metric=args.metric,
                sector=args.sector,
                start=args.start,
                end=args.end
            )

        elif args.intent == 'time.breaks':
            report = agent.breaks_report(
                metric=args.metric,
                sector=args.sector,
                start=args.start,
                end=args.end,
                z_threshold=args.z_threshold,
                cusum_h=args.cusum_h
            )

        else:
            print(f"ERROR: Unknown intent: {args.intent}", file=sys.stderr)
            sys.exit(1)

        # Output report
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(report, encoding='utf-8')
            print(f"Report written to: {output_path}")
        else:
            print(report)

    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Unexpected error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
