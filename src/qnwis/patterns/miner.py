"""
Core pattern mining engine for multi-period cohort analysis.

Scans historical windows and cohorts to surface stable relationships between
drivers and outcomes with effect sizes, support, and stability metrics.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Literal

from ..data.deterministic.models import QueryResult
from . import metrics

# Type definitions for domain vocabulary
Window = Literal[3, 6, 12, 24]
Outcome = Literal["retention_rate", "qatarization_rate"]
Driver = Literal[
    "avg_salary",
    "wage_spread",
    "promotion_rate",
    "company_size",
    "qatarization_rate",
]


@dataclass(frozen=True)
class SeriesPoint:
    """Represents a single time-series observation."""

    date: date
    value: float
    seasonally_adjusted: float | None = None


@dataclass
class AlignedSeries:
    """Aligned driver/outcome series with optional seasonal adjustments."""

    driver_values: list[float]
    outcome_values: list[float]
    driver_sa: list[float]
    outcome_sa: list[float]

    @property
    def count(self) -> int:
        """Number of overlapping observations."""
        return len(self.driver_values)

    def select_for_effect(self, min_support: int) -> tuple[list[float], list[float], bool]:
        """
        Choose whether to use raw or seasonally adjusted values for effect size.

        Returns:
            Tuple of (driver_series, outcome_series, used_sa_flag)
        """
        if len(self.driver_sa) >= min_support and len(self.driver_sa) == len(self.outcome_sa):
            return self.driver_sa, self.outcome_sa, True
        return self.driver_values, self.outcome_values, False


@dataclass
class PatternSpec:
    """
    Specification for pattern mining operation.

    Defines what to mine (outcome/drivers), where (sector/cohort),
    when (window), and how (method/thresholds). Spearman (default) should be
    used for monotonic/robust correlations; Pearson assumes linear effects.
    """

    outcome: Outcome
    drivers: list[Driver]
    sector: str | None = None
    window: Window = 12
    min_support: int = 12
    method: Literal["pearson", "spearman"] = "spearman"


@dataclass
class PatternFinding:
    """
    A single discovered pattern with metrics.

    Represents a relationship between a driver and outcome with
    statistical evidence and quality measures.
    """

    driver: Driver
    effect: float  # correlation or lift %
    support: float  # 0..1
    stability: float  # 0..1
    direction: Literal["pos", "neg", "nonlinear", "flat"]
    cohort: str  # e.g., sector or band label
    n: int  # number of observations used for effect
    seasonally_adjusted: bool = False  # True when SA series powered the effect


class PatternMiner:
    """
    Deterministic pattern mining engine.

    Extracts and ranks driver-outcome relationships across cohorts and time windows.
    All computations are reproducible and bounded in complexity.
    """

    def __init__(
        self,
        flat_threshold: float = 0.15,
        nonlinear_threshold: float = 0.3,
        max_cohorts: int = 30,
    ):
        """
        Initialize pattern miner with classification thresholds.

        Args:
            flat_threshold: |effect| below this is classified as "flat"
            nonlinear_threshold: effect variance above this suggests nonlinearity
            max_cohorts: Maximum cohorts to process (safety limit)
        """
        self.flat_threshold = flat_threshold
        self.nonlinear_threshold = nonlinear_threshold
        self.max_cohorts = max_cohorts

    def mine_stable_relations(
        self,
        spec: PatternSpec,
        end_date: date,
        timeseries_data: dict[str, QueryResult],
    ) -> list[PatternFinding]:
        """
        Mine stable relationships over the lookback window.

        Computes correlations/slopes between each driver and the outcome,
        ranks by effect size * support * stability.

        Args:
            spec: Pattern specification
            end_date: Analysis end date
            timeseries_data: Map of variable_name -> QueryResult with time series

        Returns:
            List of PatternFinding objects, ranked by strength
        """
        start_date = end_date - timedelta(days=spec.window * 30)
        findings: list[PatternFinding] = []

        # Get outcome time series
        outcome_result = timeseries_data.get(spec.outcome)
        if not outcome_result or not outcome_result.rows:
            return findings

        outcome_series = self._extract_series(
            outcome_result, start_date, end_date, spec.sector
        )

        if len(outcome_series) < spec.min_support:
            return findings

        # Analyze each driver
        for driver in spec.drivers:
            driver_result = timeseries_data.get(driver)
            if not driver_result or not driver_result.rows:
                continue

            driver_series = self._extract_series(
                driver_result, start_date, end_date, spec.sector
            )

            if not driver_series:
                continue

            aligned = self._align_series(driver_series, outcome_series)
            if aligned.count < spec.min_support:
                continue

            aligned_driver, aligned_outcome, used_sa = aligned.select_for_effect(
                spec.min_support
            )

            if len(aligned_driver) < spec.min_support:
                continue

            # Compute effect size
            if spec.method == "pearson":
                effect = metrics.pearson(aligned_driver, aligned_outcome)
            else:
                effect = metrics.spearman(aligned_driver, aligned_outcome)
            effect = max(-1.0, min(1.0, effect))

            # Compute quality metrics
            support_score = metrics.support(len(aligned_driver), spec.min_support)
            stability_score = metrics.stability(aligned_driver)

            # Classify direction
            direction = self._classify_direction(effect)

            # Only include non-flat patterns
            if direction != "flat":
                finding = PatternFinding(
                    driver=driver,
                    effect=effect,
                    support=support_score,
                    stability=stability_score,
                    direction=direction,
                    cohort=spec.sector or "all",
                    n=len(aligned_driver),
                    seasonally_adjusted=used_sa,
                )
                findings.append(finding)

        # Rank by (support, stability, |effect|) descending + deterministic tie-breaker
        findings.sort(
            key=lambda f: (-f.support, -f.stability, -abs(f.effect), f.driver)
        )

        return findings

    def mine_seasonal_effects(
        self,
        outcome: str,  # noqa: ARG002
        sector: str | None,
        end_date: date,
        min_support: int,
        timeseries_data: QueryResult,
    ) -> list[PatternFinding]:
        """
        Surface seasonal lift patterns by month-of-year or quarter.

        Computes lift for each month/quarter vs baseline to detect
        seasonal cycles.

        Args:
            outcome: Outcome metric to analyze (for context/logging)
            sector: Optional sector filter
            end_date: Analysis end date
            min_support: Minimum observations for seasonal analysis
            timeseries_data: Time series QueryResult

        Returns:
            List of seasonal findings with lift percentages
        """
        if not timeseries_data.rows:
            return []

        # Extract full time series
        series = self._extract_series(
            timeseries_data,
            end_date - timedelta(days=min_support * 30),
            end_date,
            sector,
        )

        if len(series) < min_support:
            return []

        # Group by month-of-year using seasonally adjusted values when available
        monthly_groups: dict[int, list[float]] = {m: [] for m in range(1, 13)}
        for point in series:
            value = (
                point.seasonally_adjusted
                if point.seasonally_adjusted is not None
                else point.value
            )
            monthly_groups[point.date.month].append(value)

        all_values = [v for group in monthly_groups.values() for v in group]
        if not all_values:
            return []

        baseline_mean = sum(all_values) / len(all_values)

        findings: list[PatternFinding] = []
        per_period_required = max(3, max(1, min_support // 12))

        # Compute lift for each month with sufficient data
        for month, values in monthly_groups.items():
            if len(values) < per_period_required:
                continue

            lift_pct = metrics.lift(values, [baseline_mean] * len(values))
            support_score = metrics.support(len(values), per_period_required)
            stability_score = metrics.stability(values)
            month_has_sa = any(
                point.seasonally_adjusted is not None and point.date.month == month
                for point in series
            )

            direction = self._classify_direction(lift_pct / 100.0)  # Normalize for classification

            if direction != "flat":
                finding = PatternFinding(
                    driver=f"month_{month:02d}",  # type: ignore[arg-type]
                    effect=lift_pct,
                    support=support_score,
                    stability=stability_score,
                    direction=direction,
                    cohort=sector or "all",
                    n=len(values),
                    seasonally_adjusted=month_has_sa,
                )
                findings.append(finding)

        findings.sort(
            key=lambda f: (-f.support, -f.stability, -abs(f.effect), f.driver)
        )

        return findings

    def screen_driver_across_cohorts(
        self,
        driver: str,
        outcome: str,
        cohorts: list[str],
        end_date: date,
        windows: list[int],
        timeseries_data: dict[str, dict[str, QueryResult]],
        min_support: int,
    ) -> list[PatternFinding]:
        """
        Screen a single driver vs outcome across multiple cohorts and windows.

        Useful for understanding which segments show the strongest relationship.

        Args:
            driver: Driver variable to screen
            outcome: Outcome variable
            cohorts: List of cohort labels (e.g., sectors)
            end_date: Analysis end date
            windows: List of lookback windows in months
            timeseries_data: Nested map: cohort -> variable -> QueryResult
            min_support: Minimum observations

        Returns:
            List of findings across cohorts/windows, ranked by strength
        """
        findings: list[PatternFinding] = []

        # Limit cohorts for safety
        cohorts_to_scan = cohorts[: self.max_cohorts]

        for cohort in cohorts_to_scan:
            cohort_data = timeseries_data.get(cohort, {})
            outcome_result = cohort_data.get(outcome)
            driver_result = cohort_data.get(driver)

            if not outcome_result or not driver_result:
                continue

            for window in windows:
                if window not in [3, 6, 12, 24]:
                    continue  # Only valid windows

                start_date = end_date - timedelta(days=window * 30)

                outcome_series = self._extract_series(
                    outcome_result, start_date, end_date, None
                )
                driver_series = self._extract_series(
                    driver_result, start_date, end_date, None
                )

                if not outcome_series or not driver_series:
                    continue

                aligned = self._align_series(driver_series, outcome_series)
                if aligned.count < min_support:
                    continue

                aligned_driver, aligned_outcome, used_sa = aligned.select_for_effect(
                    min_support
                )

                if len(aligned_driver) < min_support:
                    continue

                # Compute Spearman (robust to outliers)
                effect = metrics.spearman(aligned_driver, aligned_outcome)
                effect = max(-1.0, min(1.0, effect))
                support_score = metrics.support(len(aligned_driver), min_support)
                stability_score = metrics.stability(aligned_driver)

                direction = self._classify_direction(effect)

                if direction != "flat":
                    finding = PatternFinding(
                        driver=driver,  # type: ignore[arg-type]
                        effect=effect,
                        support=support_score,
                        stability=stability_score,
                        direction=direction,
                        cohort=f"{cohort}_w{window}",
                        n=len(aligned_driver),
                        seasonally_adjusted=used_sa,
                    )
                    findings.append(finding)

        findings.sort(
            key=lambda f: (-f.support, -f.stability, -abs(f.effect), f.driver)
        )

        return findings

    def _extract_series(
        self,
        result: QueryResult,
        start_date: date,
        end_date: date,
        sector: str | None,
    ) -> list[SeriesPoint]:
        """
        Extract time series values (raw + seasonally adjusted) within the window.

        Args:
            result: QueryResult with time series data
            start_date: Start of window
            end_date: End of window
            sector: Optional sector filter

        Returns:
            Sorted list of SeriesPoint entries.
        """
        series: list[tuple[date, SeriesPoint]] = []

        for row in result.rows:
            date_str = row.data.get("date") or row.data.get("month")
            if not date_str:
                continue

            if sector is not None and row.data.get("sector") != sector:
                continue

            value_field = None
            for candidate in (
                "value",
                "rate",
                "salary",
                "retention_rate",
                "qatarization_rate",
            ):
                if row.data.get(candidate) is not None:
                    value_field = candidate
                    break

            if value_field is None:
                continue

            try:
                value = float(row.data[value_field])
            except (TypeError, ValueError):
                continue

            # Seasonally adjusted variants (value_sa, {field}_sa, etc.)
            sa_value = None
            sa_candidates = []
            if value_field:
                sa_candidates.append(f"{value_field}_sa")
            sa_candidates.extend(
                ["value_sa", "seasonally_adjusted", "season_adjusted", "sa_value"]
            )
            for sa_field in sa_candidates:
                if sa_field in row.data and row.data[sa_field] is not None:
                    try:
                        sa_value = float(row.data[sa_field])
                        break
                    except (TypeError, ValueError):
                        sa_value = None

            try:
                dt = date.fromisoformat(str(date_str))
            except (ValueError, TypeError):
                continue

            if start_date <= dt <= end_date:
                series.append(
                    (
                        dt,
                        SeriesPoint(
                            date=dt,
                            value=value,
                            seasonally_adjusted=sa_value,
                        ),
                    )
                )

        series.sort(key=lambda x: x[0])
        return [point for _, point in series]

    def _align_series(
        self, series_a: list[SeriesPoint], series_b: list[SeriesPoint]
    ) -> AlignedSeries:
        """
        Align two time series using their ISO dates.

        Args:
            series_a: First series (driver)
            series_b: Second series (outcome)

        Returns:
            AlignedSeries with overlapping observations.
        """
        map_a = {point.date: point for point in series_a}
        map_b = {point.date: point for point in series_b}
        common_dates = sorted(set(map_a.keys()) & set(map_b.keys()))

        driver_values: list[float] = []
        outcome_values: list[float] = []
        driver_sa: list[float] = []
        outcome_sa: list[float] = []

        for dt in common_dates:
            pa = map_a[dt]
            pb = map_b[dt]
            driver_values.append(pa.value)
            outcome_values.append(pb.value)
            if pa.seasonally_adjusted is not None and pb.seasonally_adjusted is not None:
                driver_sa.append(pa.seasonally_adjusted)
                outcome_sa.append(pb.seasonally_adjusted)

        return AlignedSeries(
            driver_values=driver_values,
            outcome_values=outcome_values,
            driver_sa=driver_sa,
            outcome_sa=outcome_sa,
        )

    def _classify_direction(self, effect: float) -> Literal["pos", "neg", "nonlinear", "flat"]:
        """
        Classify effect direction based on magnitude.

        Args:
            effect: Effect size (correlation, lift, etc.)

        Returns:
            Direction label
        """
        abs_effect = abs(effect)

        if abs_effect < self.flat_threshold:
            return "flat"
        elif effect > 0:
            return "pos"
        else:
            return "neg"
