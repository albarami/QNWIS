"""
Scenario Planner Agent - What-if analysis and forecast adjustments.

Provides deterministic scenario application, comparison, and batch processing
with full provenance tracking and citation-ready narratives.
"""

from __future__ import annotations

import logging
from typing import Any

from ..data.deterministic.models import QueryResult
from ..scenario.apply import apply_scenario, cascade_sector_to_national
from ..scenario.dsl import ScenarioSpec, parse_scenario
from ..scenario.qa import stability_check
from .base import DataClient

logger = logging.getLogger(__name__)

# Whitelisted metrics for scenario planning
ALLOWED_METRICS = {
    "retention",
    "qatarization",
    "salary",
    "employment",
    "turnover",
    "attrition",
    "wage",
    "productivity",
}


class ScenarioAgent:
    """
    Deterministic scenario planning agent with strict data access controls.

    Capabilities:
    - apply: Apply single scenario to baseline forecast
    - compare: Compare multiple scenarios side-by-side
    - batch: Process multiple sector scenarios with national aggregation
    """

    def __init__(self, client: DataClient):
        """
        Initialize Scenario Agent.

        Args:
            client: DataClient for deterministic query access
        """
        self.client = client
        logger.info("ScenarioAgent initialized")

    def _validate_metric(self, metric: str) -> None:
        """
        Validate metric is whitelisted.

        Args:
            metric: Metric name to validate

        Raises:
            ValueError: If metric is not whitelisted
        """
        if metric.lower() not in ALLOWED_METRICS:
            raise ValueError(
                f"Metric '{metric}' not whitelisted. "
                f"Allowed: {sorted(ALLOWED_METRICS)}"
            )

    def _fetch_baseline_forecast(
        self,
        metric: str,
        sector: str | None,
        horizon_months: int,
    ) -> QueryResult:
        """
        Fetch or generate baseline forecast from DataClient.

        This method attempts to fetch a pre-computed forecast. If not available,
        it raises an error (no on-the-fly forecasting to maintain determinism).

        Args:
            metric: Metric name
            sector: Optional sector filter
            horizon_months: Required forecast horizon

        Returns:
            QueryResult with baseline forecast

        Raises:
            ValueError: If baseline forecast is unavailable
        """
        # Construct deterministic query ID for baseline forecast
        sector_slug = (sector or "all").lower().replace(" ", "_")
        qid = f"forecast_baseline_{metric}_{sector_slug}_{horizon_months}m"

        try:
            result = self.client.run(qid)
            logger.info(
                "Fetched baseline forecast: %s (rows=%d)",
                qid,
                len(result.rows),
            )
            return result
        except Exception as exc:
            raise ValueError(
                f"Baseline forecast unavailable for {metric}/{sector}. "
                f"Expected query_id: {qid}. Error: {exc}"
            ) from exc

    def apply(
        self,
        scenario_spec: str | dict[str, Any] | ScenarioSpec,
        spec_format: str = "yaml",
        baseline_override: QueryResult | None = None,
        confidence_hint: dict[str, Any] | None = None,
    ) -> str:
        """
        Apply a single scenario to a baseline forecast.

        Args:
            scenario_spec: Scenario specification (YAML string, dict, or ScenarioSpec)
            spec_format: Format of scenario_spec ("yaml", "json", or "dict")
            baseline_override: Optional baseline QueryResult (for testing/manual input)
            confidence_hint: Optional Step-22 confidence payload

        Returns:
            Citation-ready markdown narrative with scenario results

        Examples:
            >>> agent = ScenarioAgent(client)
            >>> narrative = agent.apply('''
            ... name: Retention Boost
            ... description: 10% retention improvement
            ... metric: retention
            ... sector: Construction
            ... horizon_months: 12
            ... transforms:
            ...   - type: multiplicative
            ...     value: 0.10
            ...     start_month: 0
            ... ''')
        """
        try:
            # Parse scenario specification
            if isinstance(scenario_spec, ScenarioSpec):
                spec = scenario_spec
            else:
                spec = parse_scenario(scenario_spec, format=spec_format)  # type: ignore[arg-type]

            # Validate metric
            self._validate_metric(spec.metric)

            logger.info(
                "Applying scenario: name=%s metric=%s sector=%s horizon=%d",
                spec.name,
                spec.metric,
                spec.sector,
                spec.horizon_months,
            )

            # Fetch or use provided baseline
            if baseline_override is not None:
                baseline = baseline_override
            else:
                baseline = self._fetch_baseline_forecast(
                    spec.metric, spec.sector, spec.horizon_months
                )

            # Apply scenario
            adjusted_qr = apply_scenario(baseline, spec)

            # Run stability check
            adjusted_values = [
                float(row.data.get("adjusted", 0.0))
                for row in adjusted_qr.rows
            ]
            stability = stability_check(adjusted_values)

            # Build narrative
            narrative = self._format_apply_narrative(
                spec, baseline, adjusted_qr, stability, confidence_hint
            )

            return narrative

        except Exception as exc:
            logger.exception("Error applying scenario")
            return f"Error applying scenario: {type(exc).__name__}: {exc}"

    def compare(
        self,
        scenario_specs: list[str | dict[str, Any] | ScenarioSpec],
        spec_format: str = "yaml",
        baseline_override: QueryResult | None = None,
        confidence_hint: dict[str, Any] | None = None,
    ) -> str:
        """
        Compare multiple scenarios side-by-side.

        Args:
            scenario_specs: List of scenario specifications
            spec_format: Format of specs ("yaml", "json", or "dict")
            baseline_override: Optional baseline QueryResult
            confidence_hint: Optional Step-22 confidence payload

        Returns:
            Citation-ready markdown narrative with scenario comparison
        """
        try:
            # Parse all scenarios
            specs: list[ScenarioSpec] = []
            for spec_input in scenario_specs:
                if isinstance(spec_input, ScenarioSpec):
                    specs.append(spec_input)
                else:
                    specs.append(parse_scenario(spec_input, format=spec_format))  # type: ignore[arg-type]

            if not specs:
                return "Error: No scenarios provided for comparison"

            # Validate all specs have same metric and sector
            base_metric = specs[0].metric
            base_sector = specs[0].sector
            base_horizon = specs[0].horizon_months

            for spec in specs[1:]:
                if spec.metric != base_metric:
                    return (
                        f"Error: Inconsistent metrics ({base_metric} vs {spec.metric})"
                    )
                if spec.sector != base_sector:
                    return (
                        f"Error: Inconsistent sectors ({base_sector} vs {spec.sector})"
                    )
                if spec.horizon_months != base_horizon:
                    return (
                        f"Error: Inconsistent horizons ({base_horizon} vs {spec.horizon_months})"
                    )

            # Validate metric
            self._validate_metric(base_metric)

            logger.info(
                "Comparing %d scenarios for metric=%s sector=%s",
                len(specs),
                base_metric,
                base_sector,
            )

            # Fetch baseline
            if baseline_override is not None:
                baseline = baseline_override
            else:
                baseline = self._fetch_baseline_forecast(
                    base_metric, base_sector, base_horizon
                )

            # Apply all scenarios
            results: dict[str, QueryResult] = {}
            for spec in specs:
                adjusted_qr = apply_scenario(baseline, spec)
                results[spec.name] = adjusted_qr

            # Build comparison narrative
            narrative = self._format_compare_narrative(
                specs, baseline, results, confidence_hint
            )

            return narrative

        except Exception as exc:
            logger.exception("Error comparing scenarios")
            return f"Error comparing scenarios: {type(exc).__name__}: {exc}"

    def batch(
        self,
        scenario_specs: dict[str, str | dict[str, Any] | ScenarioSpec],
        spec_format: str = "yaml",
        sector_weights: dict[str, float] | None = None,
        confidence_hint: dict[str, Any] | None = None,
    ) -> str:
        """
        Process multiple sector scenarios with national aggregation.

        Args:
            scenario_specs: Map of sector name to scenario specification
            spec_format: Format of specs ("yaml", "json", or "dict")
            sector_weights: Optional sector weights for national aggregation
            confidence_hint: Optional Step-22 confidence payload

        Returns:
            Citation-ready markdown narrative with batch results
        """
        try:
            # Parse all sector scenarios
            sector_specs: dict[str, ScenarioSpec] = {}
            for sector, spec_input in scenario_specs.items():
                if isinstance(spec_input, ScenarioSpec):
                    sector_specs[sector] = spec_input
                else:
                    sector_specs[sector] = parse_scenario(spec_input, format=spec_format)  # type: ignore[arg-type]

            if not sector_specs:
                return "Error: No sector scenarios provided"

            # Validate consistent metric and horizon
            first_spec = next(iter(sector_specs.values()))
            base_metric = first_spec.metric
            base_horizon = first_spec.horizon_months

            for sector, spec in sector_specs.items():
                if spec.metric != base_metric:
                    return (
                        f"Error: Sector '{sector}' has different metric "
                        f"({spec.metric} vs {base_metric})"
                    )
                if spec.horizon_months != base_horizon:
                    return (
                        f"Error: Sector '{sector}' has different horizon "
                        f"({spec.horizon_months} vs {base_horizon})"
                    )

            # Validate metric
            self._validate_metric(base_metric)

            logger.info(
                "Batch processing %d sectors for metric=%s",
                len(sector_specs),
                base_metric,
            )

            # Apply scenarios to each sector
            sector_results: dict[str, QueryResult] = {}
            for sector, spec in sector_specs.items():
                try:
                    baseline = self._fetch_baseline_forecast(
                        spec.metric, sector, spec.horizon_months
                    )
                    adjusted_qr = apply_scenario(baseline, spec)
                    sector_results[sector] = adjusted_qr
                except Exception as exc:
                    logger.warning(
                        "Failed to process sector '%s': %s", sector, exc
                    )
                    continue

            if not sector_results:
                return "Error: No sector scenarios successfully processed"

            # Cascade to national level
            national_qr = cascade_sector_to_national(sector_results, sector_weights)

            # Build batch narrative
            narrative = self._format_batch_narrative(
                sector_specs,
                sector_results,
                national_qr,
                sector_weights,
                confidence_hint,
            )

            return narrative

        except Exception as exc:
            logger.exception("Error in batch scenario processing")
            return f"Error in batch processing: {type(exc).__name__}: {exc}"

    def _format_apply_narrative(
        self,
        spec: ScenarioSpec,
        baseline: QueryResult,
        adjusted: QueryResult,
        stability: dict[str, Any],
        confidence_hint: dict[str, Any] | None,
    ) -> str:
        """Format single scenario application as narrative."""
        lines = [
            "# Scenario Analysis: " + spec.name,
            "",
            "## Executive Summary",
            f"Per LMIS: Applied scenario '{spec.name}' to {spec.metric} baseline.",
            f"- **Metric**: {spec.metric}",
            f"- **Sector**: {spec.sector or 'National'}",
            f"- **Horizon**: {spec.horizon_months} months",
            f"- **Transforms**: {len(spec.transforms)} sequential adjustments",
            f"- **Description**: {spec.description}",
            "",
        ]

        # Confidence hint
        if confidence_hint:
            score = confidence_hint.get("score")
            band = confidence_hint.get("band")
            if score is not None:
                score_val = float(score) * 100 if float(score) <= 1 else float(score)
                conf_line = f"Confidence hint (Step 22): {score_val:.0f}/100"
                if band:
                    conf_line += f" ({band})"
                lines.extend([f"> {conf_line}", ""])

        # Stability assessment
        if not stability["stable"]:
            lines.extend([
                "### ⚠️ Stability Warning",
                f"Forecast shows instability: {stability['reason']}",
                f"- Coefficient of Variation: {stability['cv']:.3f}",
                f"- Trend Reversals: {stability['reversals']}",
                "",
            ])

        # Scenario table (first 12 months)
        lines.extend([
            "## Scenario Forecast (First 12 Months)",
            "| Month | Baseline | Adjusted | Delta | Delta % |",
            "|-------|----------|----------|-------|---------|",
        ])

        for i, row in enumerate(adjusted.rows[:12]):
            baseline_val = row.data.get("baseline")
            adjusted_val = row.data.get("adjusted")
            delta = row.data.get("delta")
            delta_pct = row.data.get("delta_pct")

            baseline_str = f"{baseline_val:.2f}" if baseline_val is not None else "N/A"
            adjusted_str = f"{adjusted_val:.2f}" if adjusted_val is not None else "N/A"
            delta_str = f"{delta:+.2f}" if delta is not None else "N/A"
            delta_pct_str = f"{delta_pct:+.1f}%" if delta_pct is not None else "N/A"

            lines.append(
                f"| {i+1} | {baseline_str} | {adjusted_str} | "
                f"{delta_str} | {delta_pct_str} |"
            )

        lines.extend([
            "",
            f"(QID={adjusted.query_id})",
            "",
            "## Transform Details",
        ])

        for i, transform in enumerate(spec.transforms, 1):
            lines.append(
                f"{i}. **{transform.type.title()}**: value={transform.value}, "
                f"months {transform.start_month}-{transform.end_month or 'end'}"
            )

        lines.extend([
            "",
            "## Data Sources",
            f"- **Baseline**: (QID={baseline.query_id})",
            f"- **Scenario Result**: (QID={adjusted.query_id})",
            f"- **Freshness**: {baseline.freshness.asof_date}",
            "",
            "## Reproducibility",
            "```python",
            f'ScenarioAgent.apply(scenario_spec="{spec.name}")',
            "```",
        ])

        return "\n".join(lines)

    def _format_compare_narrative(
        self,
        specs: list[ScenarioSpec],
        baseline: QueryResult,
        results: dict[str, QueryResult],
        confidence_hint: dict[str, Any] | None,
    ) -> str:
        """Format scenario comparison as narrative."""
        lines = [
            "# Scenario Comparison",
            "",
            "## Executive Summary",
            f"Per LMIS: Compared {len(specs)} scenarios for {specs[0].metric}.",
            f"- **Metric**: {specs[0].metric}",
            f"- **Sector**: {specs[0].sector or 'National'}",
            f"- **Horizon**: {specs[0].horizon_months} months",
            "",
        ]

        # Confidence hint
        if confidence_hint:
            score = confidence_hint.get("score")
            if score is not None:
                score_val = float(score) * 100 if float(score) <= 1 else float(score)
                lines.extend([f"> Confidence hint: {score_val:.0f}/100", ""])

        # Scenario summaries
        lines.extend([
            "## Scenarios",
        ])

        for spec in specs:
            lines.append(f"- **{spec.name}**: {spec.description} ({len(spec.transforms)} transforms)")

        lines.extend([
            "",
            "## Comparison Table (Month 6 and 12)",
            "| Scenario | Month 6 | Month 12 | Avg Delta % |",
            "|----------|---------|----------|-------------|",
        ])

        for spec in specs:
            qr = results[spec.name]
            m6_val = qr.rows[5].data.get("adjusted") if len(qr.rows) > 5 else None
            m12_val = qr.rows[11].data.get("adjusted") if len(qr.rows) > 11 else None

            # Calculate average delta %
            deltas = [
                row.data.get("delta_pct")
                for row in qr.rows
                if row.data.get("delta_pct") is not None
            ]
            avg_delta = sum(deltas) / len(deltas) if deltas else 0.0

            m6_str = f"{m6_val:.2f}" if m6_val is not None else "N/A"
            m12_str = f"{m12_val:.2f}" if m12_val is not None else "N/A"

            lines.append(
                f"| {spec.name} | {m6_str} | {m12_str} | {avg_delta:+.1f}% |"
            )

        lines.extend([
            "",
            "## Data Sources",
            f"- **Baseline**: (QID={baseline.query_id})",
        ])

        for spec in specs:
            qr = results[spec.name]
            lines.append(f"- **{spec.name}**: (QID={qr.query_id})")

        lines.extend([
            "",
            f"- **Freshness**: {baseline.freshness.asof_date}",
        ])

        return "\n".join(lines)

    def _format_batch_narrative(
        self,
        specs: dict[str, ScenarioSpec],
        results: dict[str, QueryResult],
        national: QueryResult,
        weights: dict[str, float] | None,
        confidence_hint: dict[str, Any] | None,
    ) -> str:
        """Format batch processing results as narrative."""
        base_spec = next(iter(specs.values()))

        lines = [
            "# Batch Scenario Processing",
            "",
            "## Executive Summary",
            f"Per LMIS: Processed {len(specs)} sector scenarios for {base_spec.metric}.",
            f"- **Metric**: {base_spec.metric}",
            f"- **Sectors**: {', '.join(specs.keys())}",
            f"- **Horizon**: {base_spec.horizon_months} months",
            "- **Aggregation**: Weighted average → National",
            "",
        ]

        # Sector results
        lines.extend([
            "## Sector Results (Month 12)",
            "| Sector | Scenario | Adjusted Value | QID |",
            "|--------|----------|----------------|-----|",
        ])

        for sector, spec in specs.items():
            if sector in results:
                qr = results[sector]
                m12_row = qr.rows[11] if len(qr.rows) > 11 else qr.rows[-1]
                m12_val = m12_row.data.get("adjusted")
                val_str = f"{m12_val:.2f}" if m12_val is not None else "N/A"
                lines.append(
                    f"| {sector} | {spec.name} | {val_str} | (QID={qr.query_id}) |"
                )

        lines.extend([
            "",
            "## National Aggregation (First 12 Months)",
            "| Month | National Forecast |",
            "|-------|-------------------|",
        ])

        for i, row in enumerate(national.rows[:12]):
            val = row.data.get("adjusted")
            val_str = f"{val:.2f}" if val is not None else "N/A"
            lines.append(f"| {i+1} | {val_str} |")

        lines.extend([
            "",
            f"(QID={national.query_id})",
            "",
            "## Weights",
        ])

        if weights:
            for sector, weight in weights.items():
                lines.append(f"- **{sector}**: {weight:.3f}")
        else:
            lines.append("- Equal weighting applied")

        lines.extend([
            "",
            "## Data Sources",
        ])

        for sector, qr in results.items():
            lines.append(f"- **{sector}**: (QID={qr.query_id})")

        lines.append(f"- **National**: (QID={national.query_id})")

        return "\n".join(lines)
