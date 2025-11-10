"""
CLI interface for Alert Center Agent.

Allows offline execution of alert evaluation and management.

Usage examples:
    python -m src.qnwis.cli.qnwis_alerts validate --rules-file rules.yaml
    python -m src.qnwis.cli.qnwis_alerts status
    python -m src.qnwis.cli.qnwis_alerts run --rules retention_drop_construction
    python -m src.qnwis.cli.qnwis_alerts silence --rule-id retention_drop_construction --until 2025-12-31
"""

import argparse
import sys
from datetime import date, datetime
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.qnwis.agents.alert_center import AlertCenterAgent  # noqa: E402
from src.qnwis.agents.base import DataClient  # noqa: E402
from src.qnwis.alerts.registry import AlertRegistry  # noqa: E402


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
        description='Alert Center CLI - Rule-based early warning system',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate rule definitions
  python -m src.qnwis.cli.qnwis_alerts validate --rules-file rules/alerts.yaml

  # Show current status
  python -m src.qnwis.cli.qnwis_alerts status --rules-file rules/alerts.yaml

  # Run all enabled rules
  python -m src.qnwis.cli.qnwis_alerts run --rules-file rules/alerts.yaml

  # Run specific rules with JSON export
  python -m src.qnwis.cli.qnwis_alerts run --rules retention_drop wage_decline --export json --out report.json

  # Silence a rule
  python -m src.qnwis.cli.qnwis_alerts silence --rules-file rules/alerts.yaml --rule-id retention_drop_construction --until 2025-12-31
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate rule definitions')
    validate_parser.add_argument(
        '--rules-file',
        required=True,
        help='Path to rules file (YAML or JSON)'
    )

    # Status command
    status_parser = subparsers.add_parser('status', help='Show alert center status')
    status_parser.add_argument(
        '--rules-file',
        required=True,
        help='Path to rules file (YAML or JSON)'
    )
    status_parser.add_argument(
        '--output',
        default=None,
        help='Output file path (default: print to stdout)'
    )

    # Run command
    run_parser = subparsers.add_parser('run', help='Evaluate alert rules')
    run_parser.add_argument(
        '--rules-file',
        required=True,
        help='Path to rules file (YAML or JSON)'
    )
    run_parser.add_argument(
        '--rules',
        nargs='*',
        default=None,
        help='Specific rule IDs to evaluate (default: all enabled)'
    )
    run_parser.add_argument(
        '--start',
        type=parse_date,
        default=None,
        help='Start date for data window (YYYY-MM-DD)'
    )
    run_parser.add_argument(
        '--end',
        type=parse_date,
        default=None,
        help='End date for data window (YYYY-MM-DD)'
    )
    run_parser.add_argument(
        '--export',
        choices=['md', 'json'],
        default='md',
        help='Export format (default: md)'
    )
    run_parser.add_argument(
        '--out',
        default=None,
        help='Output file path (default: print to stdout)'
    )
    run_parser.add_argument(
        '--audit-dir',
        default='docs/audit/alerts',
        help='Directory for audit artifacts'
    )

    # Silence command
    silence_parser = subparsers.add_parser('silence', help='Silence an alert rule')
    silence_parser.add_argument(
        '--rules-file',
        required=True,
        help='Path to rules file (YAML or JSON)'
    )
    silence_parser.add_argument(
        '--rule-id',
        required=True,
        help='Rule ID to silence'
    )
    silence_parser.add_argument(
        '--until',
        required=True,
        help='Silence until date (YYYY-MM-DD)'
    )

    # Global options
    parser.add_argument(
        '--queries-dir',
        default=None,
        help='Path to query definitions directory (default: data/queries)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )

    return parser


def cmd_validate(args):
    """Validate rule definitions."""
    registry = AlertRegistry()
    try:
        count = registry.load_file(args.rules_file)
        is_valid, errors = registry.validate_all()

        if is_valid:
            print(f"✅ Validation PASSED: {count} rules loaded successfully")
            return 0
        else:
            print(f"❌ Validation FAILED: {len(errors)} errors found")
            for error in errors:
                print(f"   - {error}")
            return 1

    except Exception as e:
        print(f"ERROR: Failed to load rules: {e}", file=sys.stderr)
        return 1


def cmd_status(args):
    """Show alert center status."""
    try:
        # Load rules
        registry = AlertRegistry()
        registry.load_file(args.rules_file)

        # Initialize agent
        client = DataClient(queries_dir=args.queries_dir)
        agent = AlertCenterAgent(client, registry)

        # Get status
        report = agent.status()

        # Output
        output = report.narrative
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(output, encoding='utf-8')
            print(f"Status report written to: {output_path}")
        else:
            print(output)

        return 0

    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


def cmd_run(args):
    """Evaluate alert rules."""
    try:
        # Load rules
        registry = AlertRegistry()
        registry.load_file(args.rules_file)

        # Initialize agent
        client = DataClient(queries_dir=args.queries_dir)
        agent = AlertCenterAgent(client, registry)

        # Run evaluation
        report = agent.run(
            rules=args.rules,
            start_date=args.start,
            end_date=args.end,
        )

        # Format output
        if args.export == 'json':
            from src.qnwis.alerts.report import AlertReportRenderer
            renderer = AlertReportRenderer()
            decisions = list(agent.engine.batch_evaluate(
                    registry.get_all_rules(enabled_only=True),
                    lambda r: agent._fetch_metric_data(r, args.start, args.end)
                ))
            rules_dict = {r.rule_id: r for r in registry.get_all_rules()}
            output = renderer.render_json(decisions, rules_dict)
        else:
            output = report.narrative

        # Write output
        if args.out:
            output_path = Path(args.out)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(output, encoding='utf-8')
            print(f"Report written to: {output_path}")
        else:
            print(output)

        # Generate audit artifacts
        if args.audit_dir:
            from src.qnwis.alerts.report import AlertReportRenderer
            renderer = AlertReportRenderer()
            decisions = list(agent.engine.batch_evaluate(
                    registry.get_all_rules(enabled_only=True),
                    lambda r: agent._fetch_metric_data(r, args.start, args.end)
                ))
            rules_dict = {r.rule_id: r for r in registry.get_all_rules()}
            artifacts = renderer.generate_audit_pack(decisions, rules_dict, args.audit_dir)
            print(f"Audit artifacts generated: {len(artifacts)} files")

        return 0

    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


def cmd_silence(args):
    """Silence an alert rule."""
    try:
        # Load rules
        registry = AlertRegistry()
        registry.load_file(args.rules_file)

        # Initialize agent
        client = DataClient(queries_dir=args.queries_dir)
        agent = AlertCenterAgent(client, registry)

        # Silence rule
        success = agent.silence(args.rule_id, args.until)

        if success:
            print(f"✅ Rule '{args.rule_id}' silenced until {args.until}")
            return 0
        else:
            print(f"❌ Failed to silence rule '{args.rule_id}'", file=sys.stderr)
            return 1

    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


def main():
    """Main entry point for CLI."""
    parser = create_parser()
    args = parser.parse_args()

    # Configure logging
    if args.verbose:
        import logging
        logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    # Dispatch to command handler
    if args.command == 'validate':
        return cmd_validate(args)
    elif args.command == 'status':
        return cmd_status(args)
    elif args.command == 'run':
        return cmd_run(args)
    elif args.command == 'silence':
        return cmd_silence(args)
    else:
        parser.print_help()
        return 1


if __name__ == '__main__':
    sys.exit(main())
