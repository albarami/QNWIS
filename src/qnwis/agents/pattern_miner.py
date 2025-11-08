"""
Pattern Miner Agent for multi-period cohort analysis.

Discovers stable driver-outcome relationships across historical windows
and cohorts using deterministic pattern mining with full provenance.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

from .base import DataClient, MissingQueryDefinitionError
from .utils.derived_results import make_derived_query_result
from ..data.deterministic.models import QueryResult
from ..patterns.miner import PatternMiner, PatternSpec, PatternFinding, Window

logger = logging.getLogger(__name__)


class PatternMinerAgent:
    """
    Multi-period, cohort-aware pattern mining over deterministic aggregates.

    Uses DataClient + registry query IDs only. Returns citation-ready narratives
    with full provenance and reproducibility information.
    """

    def __init__(self, client: DataClient):
        """
        Initialize Pattern Miner agent.

        Args:
            client: DataClient for deterministic query access
        """
        self.client = client
        self.miner = PatternMiner(
            flat_threshold=0.15,
            nonlinear_threshold=0.3,
            max_cohorts=30,
        )
        logger.info("PatternMinerAgent initialized")

    def stable_relations(
        self,
        outcome: str,
        drivers: List[str],
        sector: Optional[str] = None,
        window: int = 12,
        end_date: Optional[date] = None,
        min_support: int = 12,
        method: str = "spearman",
        confidence_hint: Optional[dict[str, Any]] = None,
        timeseries_data: Optional[Dict[str, QueryResult]] = None,
    ) -> str:
        """
        Rank drivers by effect size/stability/support over the lookback window.

        Args:
            outcome: Outcome metric to analyze.
            drivers: List of driver variables to compare.
            sector: Optional sector filter for the analysis.
            window: Lookback window in months (3, 6, 12, or 24).
            end_date: Analysis end date (defaults to today).
            min_support: Minimum observations required.
            method: Correlation method ("pearson" or "spearman").
            confidence_hint: Optional Step-22 confidence payload for footer display.
            timeseries_data: Optional preloaded series map for testing/overrides.

        Returns:
            Markdown narrative with findings table and citations.
        """
        if end_date is None:
            end_date = date.today()

        if window not in [3, 6, 12, 24]:
            return f"Error: Invalid window {window}. Must be 3, 6, 12, or 24 months."

        requested_spec = PatternSpec(
            outcome=outcome,  # type: ignore[arg-type]
            drivers=drivers,  # type: ignore[arg-type]
            sector=sector,
            window=window,  # type: ignore[arg-type]
            min_support=min_support,
            method=method,  # type: ignore[arg-type]
        )

        try:
            if timeseries_data is not None:
                series_map = timeseries_data
                source_results = list(timeseries_data.values())
                warnings: List[str] = []
            else:
                metrics_list = list([requested_spec.outcome]) + list(requested_spec.drivers)
                series_map, source_results, warnings = self._load_metric_series(
                    metrics_list,
                    requested_spec.sector,
                    requested_spec.window,
                )

            if requested_spec.outcome not in series_map:
                missing_qid = self._build_timeseries_qid(
                    requested_spec.outcome, requested_spec.sector, requested_spec.window
                )
                return (
                    f"Error: deterministic outcome series '{missing_qid}' is unavailable."
                )

            available_drivers = [
                driver for driver in requested_spec.drivers if driver in series_map
            ]
            missing_drivers = [
                driver for driver in requested_spec.drivers if driver not in available_drivers
            ]
            if missing_drivers:
                warnings.append(
                    "Missing drivers: " + ", ".join(sorted(set(missing_drivers)))
                )
            if not available_drivers:
                return "No driver time series available for analysis."

            working_spec = PatternSpec(
                outcome=requested_spec.outcome,
                drivers=available_drivers,
                sector=requested_spec.sector,
                window=requested_spec.window,
                min_support=requested_spec.min_support,
                method=requested_spec.method,
            )

            findings = self.miner.mine_stable_relations(
                working_spec, end_date, series_map
            )

            source_qids, unique_sources = self._unique_sources(
                source_results or list(series_map.values())
            )
            freshness_refs = [res.freshness for res in unique_sources]

            findings_rows = [
                {
                    "driver": f.driver,
                    "effect": f.effect,
                    "support": f.support,
                    "stability": f.stability,
                    "direction": f.direction,
                    "cohort": f.cohort,
                    "n": f.n,
                    "seasonally_adjusted": f.seasonally_adjusted,
                    "composite_score": abs(f.effect) * f.support * f.stability,
                }
                for f in findings
            ]

            derived_result = make_derived_query_result(
                operation="stable_relations",
                params={
                    "outcome": outcome,
                    "drivers": drivers,
                    "sector": sector or "all",
                    "window": window,
                    "method": method,
                },
                rows=findings_rows,
                sources=source_qids,
                unit="index",
                freshness_like=freshness_refs,
            )

            narrative = self._format_stable_relations_narrative(
                findings,
                requested_spec,
                end_date,
                derived_result.query_id,
                source_qids,
                derived_result.freshness.asof_date,
                warnings,
                confidence_hint,
            )

            return narrative

        except Exception as exc:
            logger.exception("Error in stable_relations")
            return f"Error analyzing stable relations: {type(exc).__name__}: {exc}"

    def seasonal_effects(
        self,
        outcome: str,
        sector: Optional[str] = None,
        end_date: Optional[date] = None,
        min_support: int = 24,
        confidence_hint: Optional[dict[str, Any]] = None,
        timeseries_result: Optional[QueryResult] = None,
    ) -> str:
        """
        Surface seasonal lift patterns by month-of-year (or quarter).

        Args:
            outcome: Outcome metric to analyze.
            sector: Optional sector filter.
            end_date: Analysis end date (defaults to today).
            min_support: Minimum observations for seasonal analysis.
            confidence_hint: Optional Step-22 confidence payload for footer display.
            timeseries_result: Optional preloaded QueryResult override.

        Returns:
            Markdown narrative with seasonal lift table and citations.
        """
        if end_date is None:
            end_date = date.today()

        window_months = 36
        ts_qid = self._build_timeseries_qid(outcome, sector, window_months)
        warnings: List[str] = []

        try:
            result = timeseries_result or self.client.run(ts_qid)
            findings = self.miner.mine_seasonal_effects(
                outcome,
                sector,
                end_date,
                min_support,
                result,
            )

            source_qids = [result.query_id]
            freshness_refs = [result.freshness]

            findings_rows = [
                {
                    "period": f.driver,
                    "lift_pct": f.effect,
                    "support": f.support,
                    "stability": f.stability,
                    "n": f.n,
                    "seasonally_adjusted": f.seasonally_adjusted,
                }
                for f in findings
            ]

            derived_result = make_derived_query_result(
                operation="seasonal_effects",
                params={
                    "outcome": outcome,
                    "sector": sector or "all",
                    "min_support": min_support,
                    "window_months": window_months,
                },
                rows=findings_rows,
                sources=source_qids,
                unit="percent",
                freshness_like=freshness_refs,
            )

            narrative = self._format_seasonal_effects_narrative(
                findings,
                outcome,
                sector,
                derived_result.query_id,
                source_qids[0],
                derived_result.freshness.asof_date,
                warnings,
                confidence_hint,
            )

            return narrative

        except MissingQueryDefinitionError as exc:
            logger.error("Missing seasonal query: %s", ts_qid)
            return f"Error: deterministic seasonal query '{ts_qid}' is unavailable ({exc})."
        except Exception as exc:
            logger.exception("Error in seasonal_effects")
            return f"Error analyzing seasonal effects: {type(exc).__name__}: {exc}"

    def driver_screen(
        self,
        driver: str,
        outcome: str,
        cohorts: List[str],
        windows: List[int],
        sector: Optional[str] = None,
        end_date: Optional[date] = None,
        min_support: int = 12,
        confidence_hint: Optional[dict[str, Any]] = None,
        timeseries_data: Optional[Dict[str, Dict[str, QueryResult]]] = None,
    ) -> str:
        """
        Screen a single driver across multiple windows/cohorts.

        Args:
            driver: Driver variable to screen.
            outcome: Outcome variable.
            cohorts: List of cohort labels (e.g., sector names).
            windows: List of lookback windows in months.
            sector: Optional sector filter (alternative to cohorts).
            end_date: Analysis end date (defaults to today).
            min_support: Minimum observations.
            confidence_hint: Optional Step-22 confidence payload for footer display.
            timeseries_data: Optional preloaded cohort series for testing.

        Returns:
            Markdown narrative with cohort screening results.
        """
        if end_date is None:
            end_date = date.today()

        valid_windows = [w for w in windows if w in [3, 6, 12, 24]]
        if not valid_windows:
            return "Error: No valid windows. Must include 3, 6, 12, or 24 months."

        cohorts_to_use = cohorts[:] if cohorts else ([] if sector is None else [sector])
        if not cohorts_to_use:
            return "Error: At least one cohort or sector must be specified."

        try:
            if timeseries_data is not None:
                series_map = timeseries_data
                source_results = [
                    res for cohort in timeseries_data.values() for res in cohort.values()
                ]
                warnings: List[str] = []
            else:
                series_map, source_results, warnings = self._load_driver_screen_series(
                    driver, outcome, cohorts_to_use, valid_windows
                )

            if not series_map:
                return "No deterministic series available for the requested cohorts."

            findings = self.miner.screen_driver_across_cohorts(
                driver, outcome, cohorts_to_use, end_date, valid_windows, series_map, min_support
            )

            source_qids, unique_sources = self._unique_sources(
                source_results or [res for cohort in series_map.values() for res in cohort.values()]
            )
            freshness_refs = [res.freshness for res in unique_sources]

            findings_rows = [
                {
                    "cohort": f.cohort,
                    "driver": f.driver,
                    "effect": f.effect,
                    "support": f.support,
                    "stability": f.stability,
                    "n": f.n,
                    "seasonally_adjusted": f.seasonally_adjusted,
                    "composite_score": abs(f.effect) * f.support * f.stability,
                }
                for f in findings
            ]

            derived_result = make_derived_query_result(
                operation="driver_screen",
                params={
                    "driver": driver,
                    "outcome": outcome,
                    "cohorts": cohorts_to_use,
                    "windows": valid_windows,
                },
                rows=findings_rows,
                sources=source_qids,
                unit="index",
                freshness_like=freshness_refs,
            )

            narrative = self._format_driver_screen_narrative(
                findings,
                driver,
                outcome,
                cohorts_to_use,
                valid_windows,
                derived_result.query_id,
                source_qids,
                derived_result.freshness.asof_date,
                warnings,
                confidence_hint,
            )

            return narrative

        except Exception as exc:
            logger.exception("Error in driver_screen")
            return f"Error screening driver: {type(exc).__name__}: {exc}"

    def _format_stable_relations_narrative(
        self,
        findings: List[PatternFinding],
        spec: PatternSpec,
        end_date: date,
        derived_qid: str,
        source_qids: List[str],
        freshness: str,
        warnings: List[str],
        confidence_hint: Optional[dict[str, Any]],
    ) -> str:
        """Format stable relations findings into narrative."""
        lines = [
            "# Pattern Analysis: Stable Driver-Outcome Relationships",
            "",
            "## Executive Summary",
        ]

        confidence_line = self._confidence_hint_line(confidence_hint)
        if confidence_line:
            lines.extend([f"> {confidence_line}", ""])

        if not findings:
            lines.extend(
                [
                    f"No stable relationships found for {spec.outcome} over {spec.window}-month window.",
                    f"Cohort: {spec.sector or 'all sectors'}",
                    f"Minimum support threshold: {spec.min_support} observations",
                    "",
                    "**Note:** This may indicate insufficient data or genuinely flat relationships.",
                ]
            )
        else:
            top_findings = findings[:3]
            lines.append(
                f"Analyzed {len(spec.drivers)} drivers for {spec.outcome} "
                f"({spec.window}-month lookback, {spec.sector or 'all sectors'}):"
            )
            lines.append("")

            for i, f in enumerate(top_findings, 1):
                strength = self._classify_strength(abs(f.effect))
                sign = "positively" if f.direction == "pos" else "negatively"
                qualifier = "season-adjusted " if f.seasonally_adjusted else ""
                lines.append(
                    f"{i}. **{f.driver}**: {strength} {qualifier}{sign} association "
                    f"(rho={f.effect:.3f}, support={f.support:.2f}, "
                    f"stability={f.stability:.2f}, n={f.n}) (QID={derived_qid})"
                )

            lines.extend(["", "## Detailed Findings", ""])
            lines.append("### Ranked Patterns")
            lines.append(
                "| Driver | Effect | Support | Stability | Direction | Adj. | N | Composite Score |"
            )
            lines.append(
                "|--------|--------|---------|-----------|-----------|------|---|-----------------|"
            )

            for f in findings:
                composite = abs(f.effect) * f.support * f.stability
                lines.append(
                    f"| {f.driver} | {f.effect:.3f} | {f.support:.2f} | "
                    f"{f.stability:.2f} | {f.direction} | {'SA' if f.seasonally_adjusted else '-'} | "
                    f"{f.n} | {composite:.3f} |"
                )

            lines.extend(
                [
                    "",
                    f"All values reference derived result (QID={derived_qid}). *Adj.* indicates seasonally adjusted correlations.",
                ]
            )

        lines.extend(
            [
                "",
                "## Data Context",
                f"- **Analysis window:** {spec.window} months (ending {end_date.isoformat()})",
                f"- **Cohort:** {spec.sector or 'all sectors'}",
                f"- **Method:** {spec.method} rank correlation",
                f"- **Minimum support:** {spec.min_support} observations",
            ]
        )

        lines.extend(
            [
                "",
                "## Limitations",
                "- Correlations do not imply causation",
                "- Results reflect historical patterns only",
                "- Support scores below 0.8 indicate limited data confidence",
            ]
        )
        for warning in warnings:
            lines.append(f"- {warning}")
        if not warnings:
            lines.append("- No data warnings recorded")

        lines.extend(
            [
                "",
                "## Reproducibility",
                f"- **Derived Query ID:** {derived_qid}",
                f"- **Source Queries:** {', '.join(source_qids)}",
                f"- **Freshness:** {freshness}",
                f"- **Analysis Date:** {datetime.now().isoformat()}",
            ]
        )

        return "\n".join(lines)

    def _format_seasonal_effects_narrative(
        self,
        findings: List[PatternFinding],
        outcome: str,
        sector: Optional[str],
        derived_qid: str,
        source_qid: str,
        freshness: str,
        warnings: List[str],
        confidence_hint: Optional[dict[str, Any]],
    ) -> str:
        """Format seasonal effects findings into narrative."""
        lines = [
            "# Seasonal Pattern Analysis",
            "",
            f"## {outcome.replace('_', ' ').title()} - Seasonal Lift Patterns",
            "",
        ]

        confidence_line = self._confidence_hint_line(confidence_hint)
        if confidence_line:
            lines.extend([f"> {confidence_line}", ""])

        if not findings:
            lines.extend(
                [
                    "No significant seasonal patterns detected.",
                    f"Cohort: {sector or 'all sectors'}",
                    "",
                    "**Note:** Monthly variations may be within normal baseline range.",
                ]
            )
        else:
            lines.append("### Monthly Lift Analysis")
            lines.append(
                "Lift percentage vs baseline (positive = above average, negative = below average):"
            )
            lines.append("")
            lines.append("| Month | Lift (%) | Support | Stability | Adj. | N | Interpretation |")
            lines.append("|-------|----------|---------|-----------|------|---|----------------|")

            for f in findings[:6]:
                month_num = f.driver.replace("month_", "")
                direction = "above" if f.effect > 0 else "below"
                confidence = "high" if f.support > 0.8 else "moderate" if f.support > 0.6 else "low"
                lines.append(
                    f"| {month_num} | {f.effect:+.1f}% | {f.support:.2f} | {f.stability:.2f} | "
                    f"{'SA' if f.seasonally_adjusted else '-'} | {f.n} | "
                    f"{abs(f.effect):.1f}% {direction} baseline ({confidence} confidence) |"
                )

            lines.extend(
                [
                    "",
                    "### Insights",
                ]
            )

            peaks = [f for f in findings if f.effect > 0][:3]
            troughs = [f for f in findings if f.effect < 0][:3]

            if peaks:
                peak_months = ", ".join(
                    [f"{f.driver.replace('month_', 'M')} (+{f.effect:.1f}%)" for f in peaks]
                )
                lines.append(f"- **Peak months:** {peak_months}")

            if troughs:
                trough_months = ", ".join(
                    [f"{f.driver.replace('month_', 'M')} ({f.effect:.1f}%)" for f in troughs]
                )
                lines.append(f"- **Trough months:** {trough_months}")

            avg_support = sum(f.support for f in findings) / len(findings)
            confidence_note = (
                "high" if avg_support > 0.8 else "moderate" if avg_support > 0.6 else "limited"
            )
            lines.append(
                f"- **Overall confidence:** {confidence_note} (avg support={avg_support:.2f})"
            )

        lines.extend(
            [
                "",
                "## Data Context",
                f"- **Metric:** {outcome}",
                f"- **Cohort:** {sector or 'all sectors'}",
                f"- **Baseline:** Overall mean across all months",
            ]
        )

        lines.extend(
            [
                "",
                "## Limitations",
            ]
        )
        for warning in warnings:
            lines.append(f"- {warning}")
        if not warnings:
            lines.append("- No additional warnings")

        lines.extend(
            [
                "",
                "## Reproducibility",
                f"- **Derived Query ID:** {derived_qid}",
                f"- **Source Query:** {source_qid}",
                f"- **Freshness:** {freshness}",
                f"- **Analysis Date:** {datetime.now().isoformat()}",
            ]
        )

        return "\n".join(lines)

    def _format_driver_screen_narrative(
        self,
        findings: List[PatternFinding],
        driver: str,
        outcome: str,
        cohorts: List[str],
        windows: List[int],
        derived_qid: str,
        source_qids: List[str],
        freshness: str,
        warnings: List[str],
        confidence_hint: Optional[dict[str, Any]],
    ) -> str:
        """Format driver screening findings into narrative."""
        lines = [
            "# Driver Screening Analysis",
            "",
            f"## {driver.replace('_', ' ').title()} x {outcome.replace('_', ' ').title()}",
            "",
        ]

        confidence_line = self._confidence_hint_line(confidence_hint)
        if confidence_line:
            lines.extend([f"> {confidence_line}", ""])

        if not findings:
            lines.extend(
                [
                    f"No significant relationships found between {driver} and {outcome}.",
                    f"Screened {len(cohorts)} cohorts across {len(windows)} time windows.",
                    "",
                    "**Note:** Relationships may be flat or data may be insufficient.",
                ]
            )
        else:
            lines.append(
                f"Screened {len(cohorts)} cohorts and {len(windows)} windows. "
                f"Found {len(findings)} significant relationships."
            )
            lines.append("")
            lines.append("### Top Cohort-Window Combinations")
            lines.append(
                "| Cohort | Window | Effect | Support | Stability | Adj. | N | Composite | Notes |"
            )
            lines.append(
                "|--------|--------|--------|---------|-----------|------|---|-----------|-------|"
            )

            for f in findings[:8]:
                composite = abs(f.effect) * f.support * f.stability
                flags = []
                if f.support < 0.7:
                    flags.append("low support")
                if f.stability < 0.6:
                    flags.append("low stability")
                notes = ", ".join(flags) if flags else "ok"

                lines.append(
                    f"| {f.cohort} | - | {f.effect:.3f} | {f.support:.2f} | "
                    f"{f.stability:.2f} | {'SA' if f.seasonally_adjusted else '-'} | "
                    f"{f.n} | {composite:.3f} | {notes} |"
                )

            lines.extend(
                [
                    "",
                    f"All values reference derived result (QID={derived_qid}). *Adj.* indicates seasonally adjusted correlations.",
                    "",
                    "### Insights",
                ]
            )

            strongest = findings[0] if findings else None
            if strongest:
                strength = self._classify_strength(abs(strongest.effect))
                sign = "positive" if strongest.direction == "pos" else "negative"
                lines.append(
                    f"- **Strongest relationship:** {strongest.cohort} "
                    f"({strength} {sign}, rho={strongest.effect:.3f})"
                )

            cohort_effects: Dict[str, List[float]] = {}
            for f in findings:
                base_cohort = f.cohort.split("_w")[0]
                cohort_effects.setdefault(base_cohort, []).append(f.effect)

            consistent_cohorts = [
                cohort
                for cohort, effects in cohort_effects.items()
                if len(effects) >= 2 and all(e * effects[0] > 0 for e in effects)
            ]

            if consistent_cohorts:
                lines.append(
                    f"- **Cross-window consistency:** "
                    f"{len(consistent_cohorts)} cohorts show consistent direction"
                )

        lines.extend(
            [
                "",
                "## Reproducibility",
                f"- **Derived Query ID:** {derived_qid}",
                f"- **Source Queries:** {len(source_qids)} time series queries",
                f"- **Freshness:** {freshness}",
                f"- **Analysis Date:** {datetime.now().isoformat()}",
            ]
        )

        if warnings:
            lines.extend(
                [
                    "",
                    "## Limitations",
                ]
            )
            for warning in warnings:
                lines.append(f"- {warning}")

        return "\n".join(lines)

    def _build_timeseries_qid(
        self,
        metric: str,
        cohort: Optional[str],
        window: int,
    ) -> str:
        """Construct deterministic time-series query identifier."""
        metric_slug = metric.lower().replace(" ", "_")
        cohort_slug = (cohort or "all").lower().replace(" ", "_")
        return f"timeseries_{metric_slug}_{cohort_slug}_{window}m"

    def _load_metric_series(
        self,
        metrics: List[str],
        sector: Optional[str],
        window: int,
    ) -> Tuple[Dict[str, QueryResult], List[QueryResult], List[str]]:
        """
        Load deterministic time series for the requested metrics.

        Returns:
            Tuple of (series_map, source_results, warnings).
        """
        series_map: Dict[str, QueryResult] = {}
        sources: List[QueryResult] = []
        warnings: List[str] = []
        seen: set[str] = set()

        for metric in metrics:
            if metric in seen:
                continue
            seen.add(metric)
            qid = self._build_timeseries_qid(metric, sector, window)
            try:
                result = self.client.run(qid)
            except MissingQueryDefinitionError as exc:
                warnings.append(f"Missing data for '{metric}' ({qid}): {exc}")
                continue
            series_map[metric] = result
            sources.append(result)

        return series_map, sources, warnings

    def _load_driver_screen_series(
        self,
        driver: str,
        outcome: str,
        cohorts: List[str],
        windows: List[int],
    ) -> Tuple[Dict[str, Dict[str, QueryResult]], List[QueryResult], List[str]]:
        """
        Load driver/outcome series per cohort for screening.

        Always fetches the longest requested window to allow slicing for smaller windows.
        """
        history_window = max(windows)
        warnings: List[str] = []
        sources: List[QueryResult] = []
        series_map: Dict[str, Dict[str, QueryResult]] = {}

        if len(cohorts) > self.miner.max_cohorts:
            warnings.append(
                f"Scanning capped at {self.miner.max_cohorts} of {len(cohorts)} requested cohorts."
            )
        cohorts_to_scan = cohorts[: self.miner.max_cohorts]

        for cohort in cohorts_to_scan:
            cohort_data: Dict[str, QueryResult] = {}
            for metric in (outcome, driver):
                qid = self._build_timeseries_qid(metric, cohort, history_window)
                try:
                    result = self.client.run(qid)
                except MissingQueryDefinitionError as exc:
                    warnings.append(
                        f"Missing data for '{metric}' in {cohort} ({qid}): {exc}"
                    )
                    continue
                cohort_data[metric] = result
                sources.append(result)
            if cohort_data:
                series_map[cohort] = cohort_data

        return series_map, sources, warnings

    def _unique_sources(
        self,
        sources: List[QueryResult],
    ) -> Tuple[List[str], List[QueryResult]]:
        """Return sorted unique query IDs and their results."""
        dedup: Dict[str, QueryResult] = {}
        for res in sources:
            dedup[res.query_id] = res
        ordered_ids = sorted(dedup.keys())
        ordered_results = [dedup[qid] for qid in ordered_ids]
        return ordered_ids, ordered_results

    @staticmethod
    def _confidence_hint_line(
        confidence_hint: Optional[dict[str, Any]]
    ) -> Optional[str]:
        """Format a confidence hint line from Step 22 metadata."""
        if not confidence_hint:
            return None
        score = confidence_hint.get("score")
        if score is None:
            return None
        try:
            score_value = float(score)
        except (TypeError, ValueError):
            return None
        if score_value <= 1.0:
            score_value *= 100.0
        score_text = f"{score_value:.0f}/100"
        band = confidence_hint.get("band")
        if band:
            return f"Confidence hint (Step 22): {score_text} ({band})."
        return f"Confidence hint (Step 22): {score_text}."

    @staticmethod
    def _classify_strength(abs_effect: float) -> str:
        """Classify effect strength."""
        if abs_effect > 0.7:
            return "strong"
        elif abs_effect > 0.4:
            return "moderate"
        else:
            return "weak"
