"""
Alert Center Agent - Production-grade early-warning system.

Continuously evaluates deterministic, rule-based alert conditions across QNWIS metrics,
produces citation-ready reports, and integrates with L19→L22 verification layers.
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from ..alerts.engine import AlertDecision, AlertEngine
from ..alerts.registry import AlertRegistry
from ..alerts.report import AlertReportRenderer
from ..alerts.rules import AlertRule
from ..data.deterministic.models import QueryResult
from .base import AgentReport, DataClient, Evidence, Insight
from .utils.derived_results import make_derived_query_result

if TYPE_CHECKING:
    from ..notify.dispatcher import NotificationDispatcher
    from ..notify.resolver import IncidentResolver
    from ..utils.clock import Clock

logger = logging.getLogger(__name__)

# Metric whitelist for alert evaluation (domain-agnostic)
ALLOWED_METRICS = [
    # Labor market metrics
    "retention",
    "employment",
    "unemployment",
    "attrition",
    "turnover",
    "vacancy",
    # Compensation metrics
    "salary",
    "wage_gap",
    # Nationalization metrics (works for any country's localization program)
    "nationalization",  # Generic term - maps to qatarization, emiratization, saudization, etc.
    "qatarization",     # Qatar-specific (legacy support)
    # Economic indicators
    "gdp_growth",
    "inflation",
    "fdi_inflow",
    "capacity_utilization",
]

# Default query ID mapping (domain-agnostic with fallbacks)
DEFAULT_METRIC_QUERIES = {
    # Labor market
    "retention": "LMIS_RETENTION_TS",
    "employment": "LMIS_EMPLOYMENT_TS",
    "unemployment": "LMIS_UNEMPLOYMENT_TS",
    "attrition": "syn_attrition_monthly",
    "turnover": "LMIS_TURNOVER_TS",
    # Compensation
    "salary": "LMIS_SALARY_TS",
    "wage_gap": "LMIS_WAGE_GAP_TS",
    # Nationalization (generic + country-specific)
    "nationalization": "LMIS_NATIONALIZATION_TS",  # Generic - system maps to country-specific
    "qatarization": "LMIS_QATARIZATION_TS",        # Qatar-specific (legacy)
    # Economic indicators
    "gdp_growth": "MACRO_GDP_GROWTH_TS",
    "inflation": "MACRO_INFLATION_TS",
    "fdi_inflow": "MACRO_FDI_TS",
    "capacity_utilization": "SECTOR_CAPACITY_TS",
}


class AlertCenterAgent:
    """
    Deterministic alert evaluation agent.

    Evaluates rule-based early-warning conditions using DataClient-only access.
    Produces citation-ready narratives and derived QueryResults with L19→L22 integration.
    """

    REQUIRED_DATA_TYPES = ["sector_metrics", "labor_market"]

    def can_analyze(self, query_context: dict[str, Any]) -> bool:
        """Check if agent has necessary data before attempting analysis."""
        available_data = query_context.get("available_data_types", [])
        
        has_required_data = any(
            data_type in available_data 
            for data_type in self.REQUIRED_DATA_TYPES
        )
        
        if not has_required_data:
            logger.info(f"{self.__class__.__name__} skipping: insufficient data")
            return False
        
        return True

    def __init__(
        self,
        data_client: DataClient,
        rule_registry: AlertRegistry | None = None,
        metric_queries: dict[str, str] | None = None,
        notification_dispatcher: NotificationDispatcher | None = None,
        incident_resolver: IncidentResolver | None = None,
        clock: Clock | None = None,
    ):
        """
        Initialize Alert Center Agent.

        Args:
            data_client: DataClient with .run(query_id, params)
            rule_registry: Optional pre-loaded AlertRegistry
            metric_queries: Optional mapping of metric names to query IDs
            notification_dispatcher: Optional notification dispatcher
            incident_resolver: Optional incident resolver
            clock: Optional clock for deterministic timestamps
        """
        self.client = data_client
        self.registry = rule_registry or AlertRegistry()
        self.engine = AlertEngine()
        self.renderer = AlertReportRenderer()
        self.metric_queries = metric_queries or DEFAULT_METRIC_QUERIES
        self.notification_dispatcher = notification_dispatcher
        self.incident_resolver = incident_resolver
        self.clock = clock
        self._silences: dict[str, str] = {}  # rule_id -> until_date (ISO)
        self._load_silences()

    def _load_silences(self) -> None:
        """Load silence configurations from audit file."""
        silence_path = Path("docs/audit/alerts/silences.json")
        if silence_path.exists():
            try:
                with open(silence_path, encoding="utf-8") as f:
                    data = json.load(f)
                    self._silences = data.get("silences", {})
                logger.info(f"Loaded {len(self._silences)} alert silences")
            except Exception as e:
                logger.warning(f"Failed to load silences: {e}")

    def _save_silences(self) -> None:
        """Persist silence configurations to audit file."""
        silence_path = Path("docs/audit/alerts/silences.json")
        silence_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            data = {
                "silences": self._silences,
                "last_updated": datetime.utcnow().isoformat() + "Z",
            }
            with open(silence_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            logger.info("Saved alert silences")
        except Exception as e:
            logger.error(f"Failed to save silences: {e}")

    def status(self) -> AgentReport:
        """
        Get current alert center status.

        Returns:
            AgentReport with rule status and last outcomes
        """
        all_rules = self.registry.get_all_rules()
        enabled_rules = [r for r in all_rules if r.enabled]
        silenced_rules = [
            r for r in all_rules
            if r.rule_id in self._silences and self._is_silenced(r.rule_id)
        ]

        insights = []

        # Summary insight
        summary = Insight(
            title="Alert Center Status",
            summary=(
                f"Loaded {len(all_rules)} rules: "
                f"{len(enabled_rules)} enabled, "
                f"{len(silenced_rules)} silenced"
            ),
            metrics={
                "total_rules": float(len(all_rules)),
                "enabled_rules": float(len(enabled_rules)),
                "silenced_rules": float(len(silenced_rules)),
            },
        )
        insights.append(summary)

        # Per-metric breakdown
        metric_counts: dict[str, int] = {}
        for rule in all_rules:
            metric_counts[rule.metric] = metric_counts.get(rule.metric, 0) + 1

        for metric, count in sorted(metric_counts.items()):
            metric_insight = Insight(
                title=f"Rules for {metric}",
                summary=f"{count} rules configured for {metric} metric",
                metrics={"rule_count": float(count)},
            )
            insights.append(metric_insight)

        narrative = self._build_status_narrative(all_rules, enabled_rules, silenced_rules)

        return AgentReport(
            agent="AlertCenter",
            insights=insights,
            narrative=narrative,
            derived_results=[],
        )

    def _build_status_narrative(
        self,
        all_rules: list[AlertRule],
        enabled_rules: list[AlertRule],
        silenced_rules: list[AlertRule],
    ) -> str:
        """Build status narrative."""
        lines = ["# Alert Center Status", ""]
        lines.append(f"**Total Rules**: {len(all_rules)}")
        lines.append(f"**Enabled**: {len(enabled_rules)}")
        lines.append(f"**Silenced**: {len(silenced_rules)}")
        lines.append("")

        if silenced_rules:
            lines.append("## Silenced Rules")
            for rule in silenced_rules:
                until = self._silences.get(rule.rule_id, "unknown")
                lines.append(f"- `{rule.rule_id}` (until {until})")
            lines.append("")

        lines.append("## Rules by Metric")
        metric_groups: dict[str, list[str]] = {}
        for rule in all_rules:
            metric_groups.setdefault(rule.metric, []).append(rule.rule_id)

        for metric, rule_ids in sorted(metric_groups.items()):
            lines.append(f"### {metric}")
            for rule_id in sorted(rule_ids):
                lines.append(f"- `{rule_id}`")
            lines.append("")

        return "\n".join(lines)

    def run(
        self,
        rules: list[str] | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> AgentReport:
        """
        Evaluate alert rules and generate citation-ready report.

        Args:
            rules: Optional list of rule IDs to evaluate (None = all enabled)
            start_date: Optional start date for data window
            end_date: Optional end date for data window

        Returns:
            AgentReport with decisions, narrative, and derived QueryResults
        """
        # Determine rules to evaluate
        rules_to_eval: list[AlertRule]
        if rules:
            rules_to_eval_raw = [self.registry.get_rule(r) for r in rules]
            rules_to_eval = [r for r in rules_to_eval_raw if r is not None]
        else:
            rules_to_eval = self.registry.get_all_rules(enabled_only=True)

        # Filter silenced rules
        rules_to_eval = [r for r in rules_to_eval if not self._is_silenced(r.rule_id)]

        if not rules_to_eval:
            return AgentReport(
                agent="AlertCenter",
                insights=[
                    Insight(
                        title="No Rules to Evaluate",
                        summary="No enabled, non-silenced rules found",
                        metrics={},
                    )
                ],
                narrative="# Alert Evaluation\n\nNo rules to evaluate.",
                derived_results=[],
            )

        logger.info(f"Evaluating {len(rules_to_eval)} alert rules")

        # Evaluate rules
        decisions = []
        for rule in rules_to_eval:
            try:
                decision = self._evaluate_rule(rule, start_date, end_date)
                decisions.append(decision)
            except Exception as e:
                logger.error(f"Error evaluating rule {rule.rule_id}: {e}")
                decisions.append(
                    AlertDecision(
                        rule_id=rule.rule_id,
                        triggered=False,
                        message=f"Evaluation error: {e}",
                    )
                )

        # Build report
        insights = self._build_insights(decisions, rules_to_eval)
        narrative = self._build_narrative(decisions, rules_to_eval)
        derived_results = self._build_derived_results(decisions, rules_to_eval)

        # Emit notifications for triggered alerts (L19→L22 integration)
        if self.notification_dispatcher and self.clock:
            from .alert_center_notify import emit_notifications

            emit_notifications(decisions, rules_to_eval, self.notification_dispatcher, self.clock)

        # Record green evaluations for auto-resolution
        if self.incident_resolver:
            from .alert_center_notify import record_green_evaluations

            record_green_evaluations(decisions, rules_to_eval, self.incident_resolver)

        return AgentReport(
            agent="AlertCenter",
            insights=insights,
            narrative=narrative,
            derived_results=derived_results,
        )

    def _evaluate_rule(
        self,
        rule: AlertRule,
        start_date: date | None,
        end_date: date | None,
    ) -> AlertDecision:
        """
        Evaluate a single alert rule.

        Args:
            rule: AlertRule to evaluate
            start_date: Optional start date
            end_date: Optional end date

        Returns:
            AlertDecision
        """
        # Validate metric whitelist
        if rule.metric not in ALLOWED_METRICS:
            return AlertDecision(
                rule_id=rule.rule_id,
                triggered=False,
                message=f"Metric '{rule.metric}' not in whitelist",
            )

        # Fetch time-series data
        series, timestamps = self._fetch_metric_data(rule, start_date, end_date)

        # Evaluate using engine
        decision = self.engine.evaluate(rule, series, timestamps)
        decision.timestamp = datetime.utcnow().isoformat() + "Z"

        return decision

    def _fetch_metric_data(
        self,
        rule: AlertRule,
        start_date: date | None,
        end_date: date | None,
    ) -> tuple[list[float], list[str]]:
        """
        Fetch time-series data for a metric via DataClient.

        Args:
            rule: AlertRule specifying metric and scope
            start_date: Optional start date
            end_date: Optional end date

        Returns:
            Tuple of (values, timestamps)
        """
        query_id = self.metric_queries.get(rule.metric)
        if not query_id:
            raise ValueError(f"No query mapping for metric: {rule.metric}")

        # Fetch via DataClient
        result = self.client.run(query_id)

        if not result.rows:
            raise ValueError(f"No data returned for query_id={query_id}")

        # Extract and filter series
        values, timestamps = self._extract_series(result, rule, start_date, end_date)

        return values, timestamps

    def _extract_series(
        self,
        result: QueryResult,
        rule: AlertRule,
        start_date: date | None,
        end_date: date | None,
    ) -> tuple[list[float], list[str]]:
        """Extract time-series from QueryResult based on rule scope."""
        records: list[tuple[date, str, float]] = []

        for row in result.rows:
            # Extract period
            period_str = row.data.get("period")
            if not period_str:
                continue

            try:
                period_dt = datetime.strptime(period_str, "%Y-%m").date()
            except ValueError:
                continue

            # Date filter
            if start_date and period_dt < start_date:
                continue
            if end_date and period_dt > end_date:
                continue

            # Scope filter
            if rule.scope.code:
                row_code = row.data.get(rule.scope.level, "")
                if row_code != rule.scope.code:
                    continue

            # Extract value
            try:
                value = float(row.data.get("value", 0.0))
            except (TypeError, ValueError):
                continue

            records.append((period_dt, period_str, value))

        # Sort by date
        records.sort(key=lambda x: x[0])

        values = [val for _, _, val in records]
        timestamps = [label for _, label, _ in records]

        return values, timestamps

    def _build_insights(
        self,
        decisions: list[AlertDecision],
        rules: list[AlertRule],
    ) -> list[Insight]:
        """Build insights from alert decisions."""
        insights = []

        triggered = [d for d in decisions if d.triggered]

        # Summary insight
        summary = Insight(
            title="Alert Evaluation Summary",
            summary=f"Evaluated {len(decisions)} rules, {len(triggered)} alerts fired",
            metrics={
                "rules_evaluated": float(len(decisions)),
                "alerts_fired": float(len(triggered)),
            },
        )
        insights.append(summary)

        # Individual triggered alerts
        rules_by_id = {r.rule_id: r for r in rules}
        for decision in triggered:
            rule = rules_by_id.get(decision.rule_id)
            if not rule:
                continue

            insight = Insight(
                title=f"Alert: {decision.rule_id}",
                summary=decision.message,
                metrics=decision.evidence,
                evidence=[
                    Evidence(
                        query_id=self.metric_queries.get(rule.metric, "unknown"),
                        dataset_id=f"alert_{rule.rule_id}",
                        locator="DataClient",
                        fields=["period", "value"],
                    )
                ],
            )
            insights.append(insight)

        return insights

    def _build_narrative(
        self,
        decisions: list[AlertDecision],
        rules: list[AlertRule],
    ) -> str:
        """Build markdown narrative from decisions."""
        rules_dict = {r.rule_id: r for r in rules}
        metadata = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "rules_count": len(decisions),
            "alerts_fired": sum(1 for d in decisions if d.triggered),
        }
        return self.renderer.render_markdown(decisions, rules_dict, metadata)

    def _build_derived_results(
        self,
        decisions: list[AlertDecision],
        rules: list[AlertRule],
    ) -> list[QueryResult]:
        """Build derived QueryResults for triggered alerts."""
        derived_results = []
        rules_dict = {r.rule_id: r for r in rules}

        for decision in decisions:
            if not decision.triggered:
                continue

            rule = rules_dict.get(decision.rule_id)
            if not rule:
                continue

            # Create derived result
            derived_qr = make_derived_query_result(
                operation="alert_fire",
                params={
                    "rule_id": rule.rule_id,
                    "metric": rule.metric,
                    "severity": rule.severity.value,
                },
                rows=[
                    {
                        "message": decision.message,
                        **decision.evidence,
                    }
                ],
                sources=[self.metric_queries.get(rule.metric, "unknown")],
            )
            derived_results.append(derived_qr)

        return derived_results

    def silence(self, rule_id: str, until_date: str) -> bool:
        """
        Silence an alert rule until specified date.

        Args:
            rule_id: Rule identifier
            until_date: ISO date string (YYYY-MM-DD)

        Returns:
            True if successfully silenced
        """
        # Validate date format
        try:
            datetime.strptime(until_date, "%Y-%m-%d")
        except ValueError:
            logger.error(f"Invalid date format: {until_date}")
            return False

        # Check rule exists
        if rule_id not in self.registry:
            logger.error(f"Rule not found: {rule_id}")
            return False

        self._silences[rule_id] = until_date
        self._save_silences()
        logger.info(f"Silenced rule {rule_id} until {until_date}")
        return True

    def _is_silenced(self, rule_id: str) -> bool:
        """Check if a rule is currently silenced."""
        if rule_id not in self._silences:
            return False

        until_str = self._silences[rule_id]
        try:
            until_date = datetime.strptime(until_str, "%Y-%m-%d").date()
            return date.today() <= until_date
        except ValueError:
            return False

    def unsilence(self, rule_id: str) -> bool:
        """
        Remove silence for an alert rule.

        Args:
            rule_id: Rule identifier

        Returns:
            True if successfully unsilenced
        """
        if rule_id in self._silences:
            del self._silences[rule_id]
            self._save_silences()
            logger.info(f"Unsilenced rule {rule_id}")
            return True
        return False
