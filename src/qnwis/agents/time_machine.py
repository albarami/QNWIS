"""
Time Machine Agent - Historical time-series analysis with deterministic data.

Fetches approved time-series via DataClient, computes seasonal baselines, YoY/QtQ deltas,
index-100 normalization, robust smoothing, and change-point detection. Returns citation-ready
narratives and derived QueryResults with reproducibility snippets.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any

from ..analysis.baselines import (
    anomaly_gaps,
    seasonal_baseline,
)
from ..analysis.change_points import (
    cusum_breaks,
    summarize_breaks,
    zscore_outliers,
)
from ..analysis.trend_utils import (
    ewma,
    index_100,
    pct_change,
    qtq,
    safe_mad,
    safe_mean,
    window_slopes,
    yoy,
)
from ..data.deterministic.models import QueryResult
from .base import DataClient
from .utils.derived_results import make_derived_query_result

logger = logging.getLogger(__name__)

MAX_EVIDENCE_ROWS = 12


class TimeMachineAgent:
    """
    Deterministic historical analytics agent.

    Fetches monthly time-series via DataClient by whitelisted query IDs, computes
    baselines/deltas/breaks, and returns executive narratives with citations and
    derived QueryResults. No direct SQL/HTTP access.
    """

    def __init__(
        self,
        data_client: DataClient,
        series_map: dict[str, str] | None = None
    ):
        """
        Initialize Time Machine Agent.

        Args:
            data_client: DataClient with .run(query_id, params)
            series_map: Map metric name to query_id (e.g., {'retention':'LMIS_RETENTION_TS'})
                       If None, uses default mapping.
        """
        self.client = data_client

        # Default series mapping (can be overridden)
        # Maps to existing query definitions in data/queries/
        self.series_map = series_map or {
            'retention': 'retention_rate_by_sector',
            'qatarization': 'qatarization_rate_by_sector',
            'salary': 'salary_distribution_by_sector',
            'employment': 'employment_share_by_gender',
            'attrition': 'attrition_rate_monthly',
            'unemployment': 'unemployment_trends_monthly',
        }

    def _fetch_series(
        self,
        metric: str,
        sector: str | None,
        start: date,
        end: date
    ) -> tuple[QueryResult, list[float], list[str]]:
        """
        Fetch time-series data from DataClient.

        Args:
            metric: Metric name (must be in series_map)
            sector: Optional sector filter
            start: Start date
            end: End date

        Returns:
            Tuple of (QueryResult, values list, date labels list)

        Raises:
            ValueError: If metric not in series_map or insufficient data
        """
        if metric not in self.series_map:
            raise ValueError(
                f"Metric '{metric}' not in series_map. "
                f"Available: {list(self.series_map.keys())}"
            )

        query_id = self.series_map[metric]
        logger.info(
            "Fetching time series: metric=%s, query_id=%s, sector=%s, range=%s to %s",
            metric, query_id, sector, start, end
        )

        # Fetch data (DataClient handles caching)
        result = self.client.run(query_id)

        if not result.rows:
            raise ValueError(f"No data returned for query_id={query_id}")

        values, dates = self._extract_series(result, start, end, sector)

        if len(values) < 3:
            raise ValueError(
                f"Insufficient data for analysis: {len(values)} points "
                f"(need at least 3)"
            )

        return result, values, dates

    def _extract_series(
        self,
        result: QueryResult,
        start: date,
        end: date,
        sector: str | None,
    ) -> tuple[list[float], list[str]]:
        """
        Extract and sort time-series rows for the requested window/segment.
        """
        records: list[tuple[date, str, float]] = []
        for row in result.rows:
            period_str = row.data.get("period")
            if not period_str:
                continue
            try:
                period_dt = datetime.strptime(period_str, "%Y-%m").date()
            except ValueError:
                continue
            if not (start <= period_dt <= end):
                continue
            row_sector = row.data.get("sector", "")
            if sector is not None and row_sector != sector:
                continue
            try:
                value = float(row.data.get("value", 0.0))
            except (TypeError, ValueError):
                continue
            records.append((period_dt, period_str, value))

        records.sort(key=lambda item: item[0])
        values = [val for _, _, val in records]
        dates = [label for _, label, _ in records]
        return values, dates

    def _seasonal_baseline_with_scope(
        self,
        result: QueryResult,
        values: list[float],
        dates: list[str],
        sector: str | None,
        start: date,
        end: date,
        season: int = 12,
    ) -> tuple[dict[str, list[float]], str]:
        """
        Compute seasonal baseline with sector-aware fallback.
        """
        if len(values) >= season:
            return seasonal_baseline(values, season=season), "segment"

        if sector is None:
            raise ValueError(
                f"Insufficient data for baseline: {len(values)} points (need >= {season})"
            )

        logger.info(
            "baseline fallback: metric_scope=sector sector=%s points=%d < %d, using economy-wide pattern",
            sector,
            len(values),
            season,
        )
        fallback_values, _ = self._extract_series(result, start, end, None)
        if len(fallback_values) < season:
            raise ValueError(
                "Insufficient data for baseline even with economy-wide fallback: "
                f"{len(fallback_values)} points (need >= {season})"
            )

        fallback_baseline = seasonal_baseline(fallback_values, season=season)
        phase_means = fallback_baseline["mean_per_phase"]
        global_mean = safe_mean(phase_means) or 0.0
        sector_mean = safe_mean(values) or global_mean or 0.0
        scale = sector_mean / global_mean if global_mean else 1.0

        scaled_phase_means = [phase * scale for phase in phase_means]
        baseline = [scaled_phase_means[i % season] for i in range(len(values))]

        deviations = [values[i] - baseline[i] for i in range(len(values))]
        mad = safe_mad(deviations)
        if mad is None or mad == 0:
            upper_band = baseline[:]
            lower_band = baseline[:]
        else:
            band_width = 1.5 * mad
            upper_band = [b + band_width for b in baseline]
            lower_band = [max(0.0, b - band_width) for b in baseline]

        return (
            {
                "mean_per_phase": scaled_phase_means,
                "baseline": baseline,
                "upper_band": upper_band,
                "lower_band": lower_band,
            },
            "economy_fallback",
        )

    def _format_data_section(
        self,
        result: QueryResult,
        values: list[float],
        dates: list[str],
        last_n: int = 12
    ) -> str:
        """Format original data section for LLM prompt."""
        lines = [
            f"Query ID: {result.query_id}",
            f"Freshness: {result.freshness.asof_date}",
            f"Total points: {len(values)}",
            "",
            f"Recent data (last {min(last_n, len(values))} points):",
        ]

        start_idx = max(0, len(values) - last_n)
        for i in range(start_idx, len(values)):
            lines.append(f"  {dates[i]}: {values[i]:.2f}")

        return "\n".join(lines)

    def _format_derived_section(
        self,
        derived_results: list[QueryResult]
    ) -> str:
        """Format derived results section for LLM prompt."""
        lines = ["Derived computations:"]

        for res in derived_results:
            lines.append(f"\n{res.query_id}:")
            lines.append(f"  Operation: {res.provenance.dataset_id}")
            lines.append(f"  Source: {res.provenance.locator}")
            lines.append(f"  Rows: {len(res.rows)}")

            # Show first few rows
            for i, row in enumerate(res.rows[:5]):
                row_str = ", ".join(f"{k}={v}" for k, v in row.data.items())
                lines.append(f"    [{i}] {row_str}")

            if len(res.rows) > 5:
                lines.append(f"    ... and {len(res.rows) - 5} more rows")

        return "\n".join(lines)

    def baseline_report(
        self,
        metric: str,
        sector: str | None = None,
        start: date | None = None,
        end: date | None = None,
        base_at: int | None = None
    ) -> str:
        """
        Build seasonal baseline & index-100 for a metric.

        Args:
            metric: Metric name (e.g., 'retention', 'qatarization')
            sector: Optional sector filter
            start: Start date (default: 2 years ago)
            end: End date (default: today)
            base_at: Index for base period in index-100 (default: 12 months ago)

        Returns:
            Executive narrative with:
            - Executive summary
            - Baseline table (last 12 points)
            - YoY & index-100 snapshots
            - Citations: original series QID + derived QID(s)

        Raises:
            ValueError: If metric invalid or insufficient data (<12 points)
        """
        # Default date range: last 2 years
        if end is None:
            end = date.today()
        if start is None:
            start = date(end.year - 2, end.month, end.day)

        logger.info(
            "baseline_report metric=%s sector=%s start=%s end=%s base_at=%s",
            metric,
            sector or "ALL",
            start,
            end,
            base_at,
        )

        # Fetch data
        result, values, dates = self._fetch_series(metric, sector, start, end)

        season = 12
        if len(values) < season and sector is None:
            raise ValueError(
                f"Insufficient data for baseline: {len(values)} points (need >= {season})"
            )

        # Compute seasonal baseline with fallback when needed
        baseline_result, baseline_scope = self._seasonal_baseline_with_scope(
            result, values, dates, sector, start, end, season=season
        )

        # Compute YoY
        yoy_values = yoy(values, period=season)

        # Compute index-100
        if base_at is None:
            base_at = max(0, len(values) - 12)  # 12 months ago
        index_values = index_100(values, base_at)

        # Create derived QueryResults
        derived_results = []

        # Baseline result
        baseline_rows = []
        for i in range(len(values)):
            baseline_rows.append({
                'period': dates[i],
                'actual': values[i],
                'baseline': baseline_result['baseline'][i],
                'upper_band': baseline_result['upper_band'][i],
                'lower_band': baseline_result['lower_band'][i],
            })

        baseline_qr = make_derived_query_result(
            operation='seasonal_baseline',
            params={'metric': metric, 'sector': sector or 'all', 'season': season},
            rows=baseline_rows[-12:],  # Last 12 months
            sources=[result.query_id],
            unit='unknown',
            freshness_like=[result.freshness],
        )
        derived_results.append(baseline_qr)

        # Index-100 result
        index_rows = []
        for i in range(len(values)):
            if index_values[i] is not None:
                index_rows.append({
                    'period': dates[i],
                    'index_100': index_values[i],
                    'actual': values[i],
                })

        index_qr = make_derived_query_result(
            operation='index_100',
            params={'metric': metric, 'base_period': dates[base_at]},
            rows=index_rows[-12:],  # Last 12 months
            sources=[result.query_id],
            unit='index',
            freshness_like=[result.freshness],
        )
        derived_results.append(index_qr)

        # YoY result
        yoy_rows = []
        for i in range(len(values)):
            if yoy_values[i] is not None:
                yoy_rows.append({
                    'period': dates[i],
                    'yoy_pct': yoy_values[i],
                    'actual': values[i],
                })

        if yoy_rows:
            yoy_qr = make_derived_query_result(
                operation='yoy_growth',
                params={'metric': metric, 'period': 12},
                rows=yoy_rows[-12:],
                sources=[result.query_id],
                unit='percent',
                freshness_like=[result.freshness],
            )
            derived_results.append(yoy_qr)

        # Build narrative
        narrative = self._build_baseline_narrative(
            result, baseline_result, baseline_qr, index_qr,
            values, dates, derived_results, baseline_scope
        )

        return narrative

    def _build_baseline_narrative(
        self,
        original: QueryResult,
        baseline_result: dict[str, list[float]],
        baseline_qr: QueryResult,
        index_qr: QueryResult,
        values: list[float],
        dates: list[str],
        derived_results: list[QueryResult],
        baseline_scope: str,
    ) -> str:
        """Build baseline report narrative."""
        scope_text = (
            "Segment-specific seasonal factors"
            if baseline_scope == "segment"
            else "Economy-wide fallback seasonal pattern (insufficient segment history)"
        )
        lines = [
            "# Time Machine: Baseline Analysis",
            "",
            "## Executive Summary",
            f"Per LMIS: Analysis of {len(values)} monthly observations (QID={original.query_id}).",
            f"Seasonal baseline computed using 12-month phase averaging (QID={baseline_qr.query_id}).",
            f"Baseline scope: {scope_text}.",
            f"Latest value: {values[-1]:.2f} in {dates[-1]}.",
            f"Data as of: {original.freshness.asof_date}",
            "",
            "## Baseline Table (Last 12 Months)",
            "| Period | Actual | Baseline | Upper Band | Lower Band | Gap % |",
            "|--------|--------|----------|------------|------------|-------|",
        ]

        # Last 12 months
        start_idx = max(0, len(values) - 12)
        gaps = anomaly_gaps(values, baseline_result['baseline'])

        for i in range(start_idx, len(values)):
            gap = gaps[i] if gaps[i] is not None else 0.0
            lines.append(
                f"| {dates[i]} | {values[i]:.2f} | "
                f"{baseline_result['baseline'][i]:.2f} | "
                f"{baseline_result['upper_band'][i]:.2f} | "
                f"{baseline_result['lower_band'][i]:.2f} | "
                f"{gap:+.1f}% |"
            )

        lines.extend([
            "",
            "## Index-100 Snapshot",
            f"Current index: {index_qr.rows[-1].data.get('index_100', 0):.1f}",
            f"(Base period: {index_qr.rows[0].data.get('period', 'unknown')} = 100)",
            "",
            "## Data Sources",
            f"- Original series: QID={original.query_id}",
            f"- Seasonal baseline: QID={baseline_qr.query_id}",
            f"- Index-100: QID={index_qr.query_id}",
            f"- Freshness: {original.freshness.asof_date}",
            "",
            "## Reproducibility",
            "```python",
            "from qnwis.analysis.baselines import seasonal_baseline",
            "from qnwis.analysis.trend_utils import index_100",
            "",
            f"# Fetch data: query_id='{original.query_id}'",
            "values = [...]  # Your time series",
            "",
            "# Compute baseline",
            "baseline = seasonal_baseline(values, season=12)",
            "",
            "# Compute index",
            "indexed = index_100(values, base_idx=12)",
            "```",
        ])

        return "\n".join(lines)

    def trend_report(
        self,
        metric: str,
        sector: str | None = None,
        start: date | None = None,
        end: date | None = None,
        confidence_hint: dict[str, Any] | None = None,
    ) -> str:
        """
        Compute YoY/QtQ, EWMA, and multi-window slopes.

        Args:
            metric: Metric name
            sector: Optional sector filter
            start: Start date (default: 2 years ago)
            end: End date (default: today)
            confidence_hint: Optional Step-22 confidence payload (e.g., {'score': 87, 'band': 'GREEN'})

        Returns:
            Executive narrative with:
            - Trend summary (direction, acceleration)
            - Table (period, value, YoY%, QtQ%, EWMA)
            - Citations + reproducibility snippet

        Raises:
            ValueError: If insufficient data
        """
        # Default date range
        if end is None:
            end = date.today()
        if start is None:
            start = date(end.year - 2, end.month, end.day)

        logger.info(
            "trend_report metric=%s sector=%s start=%s end=%s confidence_hint=%s",
            metric,
            sector or "ALL",
            start,
            end,
            confidence_hint.get("score") if confidence_hint else None,
        )

        # Fetch data
        result, values, dates = self._fetch_series(metric, sector, start, end)

        if len(values) < 12:
            raise ValueError(
                f"Insufficient data for trend: {len(values)} points (need >= 12)"
            )

        # Compute trend metrics
        yoy_values = yoy(values, period=12)
        qtq_values = qtq(values, period=3)
        ewma_values = ewma(values, alpha=0.25)
        slopes = window_slopes(values, windows=(3, 6, 12))

        # Create derived QueryResult
        trend_rows = []
        for i in range(len(values)):
            trend_rows.append({
                'period': dates[i],
                'actual': values[i],
                'yoy_pct': yoy_values[i] if yoy_values[i] is not None else None,
                'qtq_pct': qtq_values[i] if qtq_values[i] is not None else None,
                'ewma': ewma_values[i],
            })

        trend_qr = make_derived_query_result(
            operation='trend_analysis',
            params={'metric': metric, 'sector': sector or 'all'},
            rows=trend_rows[-12:],
            sources=[result.query_id],
            unit='unknown',
            freshness_like=[result.freshness],
        )

        # Build narrative
        narrative = self._build_trend_narrative(
            result, trend_qr, values, dates, yoy_values, qtq_values,
            ewma_values, slopes, confidence_hint
        )

        return narrative

    def _build_trend_narrative(
        self,
        original: QueryResult,
        trend_qr: QueryResult,
        values: list[float],
        dates: list[str],
        yoy_values: list[float | None],
        qtq_values: list[float | None],
        ewma_values: list[float],
        slopes: list[tuple[int, float | None]],
        confidence_hint: dict[str, Any] | None,
    ) -> str:
        """Build trend report narrative."""
        # Determine trend direction
        if len(values) >= 3:
            recent_slope = (values[-1] - values[-3]) / 2
            if recent_slope > 0:
                direction = "Upward"
            elif recent_slope < 0:
                direction = "Downward"
            else:
                direction = "Flat"
        else:
            direction = "Insufficient data"

        lines = ["# Time Machine: Trend Analysis"]
        confidence_line = None
        if confidence_hint:
            score = confidence_hint.get("score")
            band = confidence_hint.get("band")
            if score is not None:
                score_value = float(score)
                if score_value <= 1:
                    score_value *= 100
                score_text = f"{score_value:.0f}/100"
                confidence_line = (
                    f"Confidence hint (Step 22): {score_text} ({band})."
                    if band
                    else f"Confidence hint (Step 22): {score_text}."
                )
        if confidence_line:
            lines.append(f"> {confidence_line}")

        lines.extend([
            "",
            "## Trend Summary",
            f"Per LMIS: {direction} trend observed over {len(values)} months (QID={original.query_id}).",
            f"Latest value: {values[-1]:.2f} in {dates[-1]}.",
            f"Data as of: {original.freshness.asof_date}",
            "",
            "## Growth Rates (Last 12 Months)",
            "| Period | Value | YoY % | QtQ % | EWMA |",
            "|--------|-------|-------|-------|------|",
        ])

        # Last 12 months
        start_idx = max(0, len(values) - 12)
        for i in range(start_idx, len(values)):
            yoy_str = f"{yoy_values[i]:+.1f}%" if yoy_values[i] is not None else "N/A"
            qtq_str = f"{qtq_values[i]:+.1f}%" if qtq_values[i] is not None else "N/A"
            lines.append(
                f"| {dates[i]} | {values[i]:.2f} | {yoy_str} | {qtq_str} | "
                f"{ewma_values[i]:.2f} |"
            )

        lines.extend([
            "",
            "## Slope Analysis",
        ])

        for window, slope in slopes:
            if slope is not None:
                lines.append(f"- {window}-month slope: {slope:+.3f} units/month")
            else:
                lines.append(f"- {window}-month slope: Insufficient data")

        lines.extend([
            "",
            "## Data Sources",
            f"- Original series: QID={original.query_id}",
            f"- Trend metrics: QID={trend_qr.query_id}",
            f"- Freshness: {original.freshness.asof_date}",
            "",
            "## Reproducibility",
            "```python",
            "from qnwis.analysis.trend_utils import yoy, qtq, ewma, window_slopes",
            "",
            f"# Fetch data: query_id='{original.query_id}'",
            "values = [...]  # Your time series",
            "",
            "# Compute growth rates",
            "yoy_pct = yoy(values, period=12)",
            "qtq_pct = qtq(values, period=3)",
            "smoothed = ewma(values, alpha=0.25)",
            "slopes = window_slopes(values, windows=(3, 6, 12))",
            "```",
        ])

        return "\n".join(lines)

    def breaks_report(
        self,
        metric: str,
        sector: str | None = None,
        start: date | None = None,
        end: date | None = None,
        z_threshold: float = 2.5,
        cusum_h: float = 5.0
    ) -> str:
        """
        Detect structural breaks/outliers.

        Args:
            metric: Metric name
            sector: Optional sector filter
            start: Start date (default: 2 years ago)
            end: End date (default: today)
            z_threshold: Z-score threshold for outlier detection
            cusum_h: CUSUM threshold for break detection

        Returns:
            Executive narrative with:
            - Break points and size
            - Context vs seasonal baseline
            - Recommended checks
            - Full audit (QIDs + freshness)

        Raises:
            ValueError: If insufficient data
        """
        # Default date range
        if end is None:
            end = date.today()
        if start is None:
            start = date(end.year - 2, end.month, end.day)

        logger.info(
            "breaks_report metric=%s sector=%s start=%s end=%s z_threshold=%s cusum_h=%s",
            metric,
            sector or "ALL",
            start,
            end,
            z_threshold,
            cusum_h,
        )

        # Fetch data
        result, values, dates = self._fetch_series(metric, sector, start, end)

        if len(values) < 12:
            raise ValueError(
                f"Insufficient data for break detection: {len(values)} points (need >= 12)"
            )

        # Detect breaks
        cusum_breaks_list = sorted(cusum_breaks(values, k=1.0, h=cusum_h))
        z_outliers = sorted(zscore_outliers(values, z=z_threshold))
        summary = summarize_breaks(values)

        # Compute baseline for context
        baseline_result = seasonal_baseline(values, season=12)

        # Create derived QueryResult
        break_rows = []
        for idx in cusum_breaks_list:
            if idx < len(values):
                prev_val = values[idx - 1] if idx > 0 else values[idx]
                curr_val = values[idx]
                jump = curr_val - prev_val
                jump_pct = pct_change(curr_val, prev_val)
                baseline_value = baseline_result['baseline'][idx]
                gap_pct = (
                    ((curr_val - baseline_value) / baseline_value) * 100
                    if baseline_value != 0
                    else None
                )

                break_rows.append({
                    'index': idx,
                    'period': dates[idx],
                    'value_before': prev_val,
                    'value_after': curr_val,
                    'jump_abs': jump,
                    'jump_pct': jump_pct,
                    'baseline': baseline_value,
                    'baseline_gap_pct': gap_pct,
                    'method': 'CUSUM',
                })

        for idx in z_outliers:
            if idx < len(values):
                baseline_value = baseline_result['baseline'][idx]
                deviation_pct = (
                    ((values[idx] - baseline_value) / baseline_value) * 100
                    if baseline_value != 0
                    else None
                )
                break_rows.append({
                    'index': idx,
                    'period': dates[idx],
                    'value': values[idx],
                    'baseline': baseline_value,
                    'deviation_pct': deviation_pct,
                    'method': 'Z-score',
                })

        annotated_rows = self._annotate_break_rows(break_rows)
        trimmed_rows = annotated_rows[:MAX_EVIDENCE_ROWS]

        breaks_qr = make_derived_query_result(
            operation='break_detection',
            params={
                'metric': metric,
                'z_threshold': z_threshold,
                'cusum_h': cusum_h
            },
            rows=trimmed_rows,
            sources=[result.query_id],
            unit='unknown',
            freshness_like=[result.freshness],
        )

        # Build narrative
        narrative = self._build_breaks_narrative(
            result, breaks_qr, values, dates, cusum_breaks_list,
            z_outliers, summary, baseline_result, z_threshold, cusum_h
        )

        return narrative

    def _annotate_break_rows(self, break_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Sort break rows and attach why-flagged hints for evidence tables.
        """
        sorted_rows = sorted(
            break_rows, key=lambda row: (row.get('index', 0), row.get('method', ''))
        )
        previous_idx: int | None = None
        for row in sorted_rows:
            method = row.get('method')
            if method == 'CUSUM':
                idx = int(row.get('index', 0))
                months_since = idx if previous_idx is None else idx - previous_idx
                previous_idx = idx
                row['months_since_prior_break'] = max(months_since, 0)
                parts = []
                jump_pct = row.get('jump_pct')
                if isinstance(jump_pct, (int, float)):
                    parts.append(f"{jump_pct:+.1f}% vs prior month")
                baseline_gap = row.get('baseline_gap_pct')
                if isinstance(baseline_gap, (int, float)):
                    parts.append(f"{baseline_gap:+.1f}% vs seasonal baseline")
                parts.append(f"{max(months_since, 0)} months since prior break")
                row['why_flagged'] = "; ".join(parts)
            elif method == 'Z-score':
                deviation = row.get('deviation_pct')
                if isinstance(deviation, (int, float)):
                    row['why_flagged'] = f"{deviation:+.1f}% vs seasonal baseline"
        return sorted_rows

    def _build_breaks_narrative(
        self,
        original: QueryResult,
        breaks_qr: QueryResult,
        values: list[float],
        dates: list[str],
        cusum_breaks_list: list[int],
        z_outliers: list[int],
        summary: dict[str, float | None],
        baseline_result: dict[str, list[float]],
        z_threshold: float,
        cusum_h: float
    ) -> str:
        """Build breaks report narrative."""
        lines = [
            "# Time Machine: Structural Break Detection",
            "",
            "## Summary",
            f"Per LMIS: Analyzed {len(values)} months for structural breaks (QID={original.query_id}).",
            f"CUSUM breaks detected: {len(cusum_breaks_list)}",
            f"Z-score outliers detected: {len(z_outliers)}",
            f"Data as of: {original.freshness.asof_date}",
            "",
        ]
        annotated_rows = [row.data for row in breaks_qr.rows]
        cusum_rows = [row for row in annotated_rows if row.get('method') == 'CUSUM']
        z_rows = [row for row in annotated_rows if row.get('method') == 'Z-score']

        if cusum_rows:
            lines.extend([
                "## Break Points (CUSUM)",
                "| Index | Period | Value Before | Value After | Jump | Jump % |",
                "|-------|--------|--------------|-------------|------|--------|",
            ])

            for row in cusum_rows:
                prev_val = row.get('value_before')
                curr_val = row.get('value_after')
                jump = row.get('jump_abs')
                jump_pct = row.get('jump_pct')
                if prev_val is None or curr_val is None or jump is None:
                    continue
                jump_pct_str = f"{jump_pct:+.1f}%" if isinstance(jump_pct, (int, float)) else "N/A"
                lines.append(
                    f"| {row.get('index')} | {row.get('period')} | {prev_val:.2f} | {curr_val:.2f} | "
                    f"{jump:+.2f} | {jump_pct_str} |"
                )

            lines.append("")

        if z_rows:
            lines.extend([
                "## Outliers (Z-score)",
                "| Index | Period | Actual | Baseline | Deviation % |",
                "|-------|--------|--------|----------|-------------|",
            ])

            for row in z_rows:
                actual = row.get('value')
                baseline_val = row.get('baseline')
                dev_pct = row.get('deviation_pct')
                if actual is None or baseline_val is None:
                    continue
                dev_str = f"{dev_pct:+.1f}%" if isinstance(dev_pct, (int, float)) else "N/A"
                lines.append(
                    f"| {row.get('index')} | {row.get('period')} | {actual:.2f} | {baseline_val:.2f} | "
                    f"{dev_str} |"
                )

            lines.append("")

        explanation_lines = [
            f"- {row.get('period')}: {row.get('why_flagged')}"
            for row in cusum_rows
            if row.get('why_flagged')
        ]
        if explanation_lines:
            lines.extend([
                "## Why Flagged",
                *explanation_lines,
                "",
            ])

        lines.extend([
            "## Recommended Actions",
            "- Review data quality for break periods",
            "- Investigate policy changes or external events",
            "- Consider seasonally adjusted analysis",
            "- Validate with subject-matter experts",
            "",
            "## Audit Trail",
            f"- Original series: QID={original.query_id}",
            f"- Break detection: QID={breaks_qr.query_id}",
            f"- Methods: CUSUM (k=1.0, h={cusum_h}), Z-score (threshold={z_threshold})",
            f"- Freshness: {original.freshness.asof_date}",
            "",
            "## Reproducibility",
            "```python",
            "from qnwis.analysis.change_points import cusum_breaks, zscore_outliers",
            "from qnwis.analysis.baselines import seasonal_baseline",
            "",
            f"# Fetch data: query_id='{original.query_id}'",
            "values = [...]  # Your time series",
            "",
            "# Detect breaks",
            f"breaks = cusum_breaks(values, k=1.0, h={cusum_h})",
            f"outliers = zscore_outliers(values, z={z_threshold})",
            "",
            "# Context",
            "baseline = seasonal_baseline(values, season=12)",
            "```",
        ])

        return "\n".join(lines)
