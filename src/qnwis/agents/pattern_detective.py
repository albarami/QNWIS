"""
Pattern Detective Agent - Correlation, anomaly detection, and best practices analysis.

This agent discovers hidden patterns, identifies statistical anomalies,
investigates root causes, and surfaces best practices from high performers.
All analysis uses only the deterministic data layer.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Literal

from ..data.deterministic.models import QueryResult
from ..data.validation.number_verifier import SUM_PERCENT_TOLERANCE
from .base import AgentReport, DataClient, Insight, evidence_from
from .utils.derived_results import make_derived_query_result
from .utils.evidence import format_evidence_table
from .utils.statistics import pearson, spearman, winsorize, z_scores
from .utils.verification import AgentResponseVerifier

logger = logging.getLogger(__name__)


class PatternDetectiveAgent:
    """
    Agent focused on pattern discovery, anomaly detection, and causal analysis.

    Capabilities:
    - detect_anomalous_retention: Find sectors with unusual retention patterns
    - find_correlations: Discover relationships between metrics
    - identify_root_causes: Investigate drivers of sector performance
    - best_practices: Surface characteristics of high performers
    - run: Legacy consistency validation (maintains backward compatibility)
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

    def __init__(self, client: DataClient, verifier: AgentResponseVerifier | None = None) -> None:
        """
        Initialize the Pattern Detective Agent.

        Args:
            client: DataClient instance for accessing deterministic queries
            verifier: Optional response verifier enforcing provenance completeness
        """
        self.client = client
        self._verifier = verifier or AgentResponseVerifier()

    def _verify_response(self, report: AgentReport, results: Sequence[QueryResult]) -> None:
        """
        Run deterministic verification on the agent's output.

        Args:
            report: AgentReport produced by the agent.
            results: QueryResult objects (original and derived) used in analysis.
        """
        self._verifier.verify(report, list(results))

    def detect_anomalous_retention(
        self,
        z_threshold: float = 2.5,
        min_sample_size: int = 3,
    ) -> AgentReport:
        """
        Detect sectors with statistically anomalous retention/attrition rates.

        Uses z-score analysis with winsorization to identify outliers while
        being robust to extreme values.

        Args:
            z_threshold: Z-score threshold for anomaly detection (default 2.5)
            min_sample_size: Minimum number of sectors required (default 3)

        Returns:
            AgentReport with anomaly findings and ranked outliers
        """
        if z_threshold <= 0:
            raise ValueError("z_threshold must be greater than 0.")
        if min_sample_size < 3:
            raise ValueError("min_sample_size must be at least 3.")

        logger.info(
            "detect_anomalous_retention params=%s queries=%s",
            {"z_threshold": z_threshold, "min_sample_size": min_sample_size},
            ["attrition_rate_monthly"],
        )

        # Fetch attrition data - use available query
        try:
            res = self.client.run("attrition_rate_monthly")
        except Exception as e:
            logger.warning(f"Attrition data not available: {e}")
            return AgentReport(
                agent="PatternDetective",
                findings=[],
                warnings=["Attrition by sector data not available from current sources"],
            )

        if len(res.rows) < min_sample_size:
            return AgentReport(
                agent="PatternDetective",
                findings=[],
                warnings=[f"Insufficient data: {len(res.rows)} sectors (need {min_sample_size})"],
            )

        # Extract attrition percentages
        sectors: list[str] = []
        attrition_rates: list[float] = []
        for row in res.rows:
            sector = row.data.get("sector")
            attrition = row.data.get("attrition_percent")
            if sector and isinstance(attrition, (int, float)):
                sectors.append(str(sector))
                attrition_rates.append(float(attrition))

        if len(attrition_rates) < min_sample_size:
            return AgentReport(
                agent="PatternDetective",
                findings=[],
                warnings=["Insufficient numeric attrition data"],
            )

        # Winsorize to handle extreme outliers
        winsorized = winsorize(attrition_rates, p=0.05)

        # Calculate z-scores
        z_vals = z_scores(winsorized)

        # Identify anomalies
        anomalies: list[dict[str, object]] = []
        for sector, rate, z_val in zip(sectors, attrition_rates, z_vals):
            if abs(z_val) >= z_threshold:
                rounded_rate = round(rate, 2)
                rounded_z = round(z_val, 3)
                anomalies.append(
                    {
                        "sector": sector,
                        "attrition_percent": rounded_rate,
                        "z_score": rounded_z,
                        "threshold": round(float(z_threshold), 2),
                        "why_flagged": (
                            f"{rounded_rate:.2f}% attrition with z={rounded_z:+.3f} "
                            f"breaches ±{z_threshold:.2f}"
                        ),
                        "type": "high" if z_val > 0 else "low",
                    }
                )

        # Sort by absolute z-score
        anomalies.sort(key=lambda row: abs(row["z_score"]), reverse=True)

        # Create derived result
        formatted_rows = format_evidence_table(anomalies)

        derived = make_derived_query_result(
            operation="z_score_anomaly_detection",
            params={"z_threshold": z_threshold, "metric": "attrition_percent"},
            rows=formatted_rows,
            sources=[res.query_id],
            unit="percent",
        )

        metrics = {
            "anomaly_count": len(anomalies),
            "total_sectors": len(sectors),
            "threshold": float(z_threshold),
        }

        if anomalies:
            metrics["max_z_score"] = max(abs(float(a["z_score"])) for a in anomalies)

        summary = (
            f"Found {len(anomalies)} sectors with anomalous attrition rates out of {len(sectors)} total."
        )

        report = AgentReport(
            agent="PatternDetective",
            findings=[
                Insight(
                    title="Attrition anomaly detection",
                    summary=summary,
                    metrics=metrics,
                    evidence=[evidence_from(res), evidence_from(derived)],
                    warnings=list(res.warnings),
                )
            ],
        )
        self._verify_response(report, [res, derived])
        return report

    def find_correlations(
        self,
        method: Literal["pearson", "spearman"] = "spearman",
        min_correlation: float = 0.5,
        min_sample_size: int = 5,
    ) -> AgentReport:
        """
        Find correlations between qatarization and attrition rates by sector.

        Args:
            method: Correlation method ("pearson" or "spearman", default "spearman")
            min_correlation: Minimum absolute correlation to report (default 0.5)
            min_sample_size: Minimum number of sectors required (default 5)

        Returns:
            AgentReport with correlation findings
        """
        if method not in ("pearson", "spearman"):
            raise ValueError("method must be either 'pearson' or 'spearman'.")
        if not 0 <= min_correlation <= 1:
            raise ValueError("min_correlation must be between 0 and 1 (inclusive).")
        if min_sample_size < 3:
            raise ValueError("min_sample_size must be at least 3.")

        logger.info(
            "find_correlations params=%s queries=%s",
            {
                "method": method,
                "requested_method": method,
                "min_correlation": min_correlation,
                "min_sample_size": min_sample_size,
            },
            ["syn_qatarization_by_sector_latest", "syn_attrition_by_sector_latest"],
        )

        # Fetch both datasets
        qat_res = self.client.run("syn_qatarization_by_sector_latest")
        atr_res = self.client.run("syn_attrition_by_sector_latest")

        # Build sector-indexed maps
        qat_map: dict[str, float] = {}
        for row in qat_res.rows:
            sector = row.data.get("sector")
            qat_pct = row.data.get("qatarization_percent")
            if sector and isinstance(qat_pct, (int, float)):
                qat_map[str(sector)] = float(qat_pct)

        atr_map: dict[str, float] = {}
        for row in atr_res.rows:
            sector = row.data.get("sector")
            atr_pct = row.data.get("attrition_percent")
            if sector and isinstance(atr_pct, (int, float)):
                atr_map[str(sector)] = float(atr_pct)

        # Find common sectors
        common_sectors = set(qat_map.keys()) & set(atr_map.keys())

        if len(common_sectors) < min_sample_size:
            return AgentReport(
                agent="PatternDetective",
                findings=[],
                warnings=[f"Insufficient overlap: {len(common_sectors)} sectors (need {min_sample_size})"],
            )

        # Extract matched pairs
        sectors = sorted(common_sectors)
        qat_vals = [qat_map[s] for s in sectors]
        atr_vals = [atr_map[s] for s in sectors]

        requested_method = method
        actual_method = method

        zero_variance = len(set(qat_vals)) <= 1 or len(set(atr_vals)) <= 1
        if requested_method == "pearson" and zero_variance:
            actual_method = "spearman"

        if actual_method == "pearson":
            corr = pearson(qat_vals, atr_vals)
        else:
            corr = spearman(qat_vals, atr_vals)

        derived_row: dict[str, object] = {
            "variables": "qatarization_percent~attrition_percent",
            "requested_method": requested_method,
            "method": actual_method,
            "r": round(corr, 4),
            "n": len(sectors),
            "min_correlation": round(min_correlation, 3),
        }
        if actual_method != requested_method:
            derived_row["fallback_reason"] = "zero_variance"

        derived = make_derived_query_result(
            operation=f"{actual_method}_correlation",
            params={
                "variable_x": "qatarization_percent",
                "variable_y": "attrition_percent",
                "requested_method": requested_method,
            },
            rows=format_evidence_table([derived_row], max_rows=10),
            sources=[qat_res.query_id, atr_res.query_id],
            unit="index",
        )

        metrics = {
            "correlation": round(corr, 3),
            "sample_size": len(sectors),
            "method_used": actual_method,
            "requested_method": requested_method,
            "threshold": float(min_correlation),
        }

        significant = abs(corr) >= min_correlation

        summary = (
            f"{actual_method.capitalize()} correlation between qatarization and attrition: "
            f"{corr:.3f} (n={len(sectors)})."
        )
        if actual_method != requested_method:
            summary += f" Fallback from {requested_method} due to zero variance."

        if significant:
            direction = "positive" if corr > 0 else "negative"
            summary += f" {direction.capitalize()} relationship meets threshold ({min_correlation})."
        else:
            summary += f" Below significance threshold ({min_correlation})."

        report = AgentReport(
            agent="PatternDetective",
            findings=[
                Insight(
                    title=f"Correlation analysis: Qatarization vs Attrition ({actual_method})",
                    summary=summary,
                    metrics=metrics,
                    evidence=[evidence_from(qat_res), evidence_from(atr_res), evidence_from(derived)],
                    warnings=sorted(set(qat_res.warnings + atr_res.warnings)),
                )
            ],
        )
        self._verify_response(report, [qat_res, atr_res, derived])
        return report

    def identify_root_causes(
        self,
        top_n: int = 3,
    ) -> AgentReport:
        """
        Identify potential root causes of high attrition by comparing sector characteristics.

        Compares top vs bottom attrition sectors on qatarization levels.
        Note: This is correlation-based hypothesis generation, not causal proof.

        Args:
            top_n: Number of top/bottom sectors to compare (default 3)

        Returns:
            AgentReport with root cause hypotheses
        """
        if not 1 <= top_n <= 50:
            raise ValueError("top_n must be between 1 and 50 for root cause analysis.")

        logger.info(
            "identify_root_causes params=%s queries=%s",
            {"top_n": top_n},
            ["syn_attrition_by_sector_latest", "syn_qatarization_by_sector_latest"],
        )

        # Fetch data
        atr_res = self.client.run("syn_attrition_by_sector_latest")
        qat_res = self.client.run("syn_qatarization_by_sector_latest")

        # Build attrition map
        atr_map = {}
        for row in atr_res.rows:
            sector = row.data.get("sector")
            atr = row.data.get("attrition_percent")
            if sector and isinstance(atr, (int, float)):
                atr_map[str(sector)] = float(atr)

        # Build qatarization map
        qat_map = {}
        for row in qat_res.rows:
            sector = row.data.get("sector")
            qat = row.data.get("qatarization_percent")
            if sector and isinstance(qat, (int, float)):
                qat_map[str(sector)] = float(qat)

        # Find common sectors
        common = set(atr_map.keys()) & set(qat_map.keys())

        if len(common) < top_n * 2:
            return AgentReport(
                agent="PatternDetective",
                findings=[],
                warnings=[f"Insufficient sectors for comparison: {len(common)} (need {top_n * 2})"],
            )

        # Sort by attrition
        high_attrition = sorted(common, key=lambda s: (-atr_map[s], s))[:top_n]
        low_attrition = sorted(common, key=lambda s: (atr_map[s], s))[:top_n]

        # Compare qatarization levels
        high_qat_avg = sum(qat_map[s] for s in high_attrition) / len(high_attrition)
        low_qat_avg = sum(qat_map[s] for s in low_attrition) / len(low_attrition)
        qat_diff = high_qat_avg - low_qat_avg

        # Build comparison table
        comparison_rows: list[dict[str, object]] = []
        for sector in high_attrition:
            comparison_rows.append(
                {
                    "group": "high_attrition",
                    "sector": sector,
                    "attrition_percent": round(atr_map[sector], 2),
                    "qatarization_percent": round(qat_map[sector], 2),
                }
            )
        for sector in low_attrition:
            comparison_rows.append(
                {
                    "group": "low_attrition",
                    "sector": sector,
                    "attrition_percent": round(atr_map[sector], 2),
                    "qatarization_percent": round(qat_map[sector], 2),
                }
            )

        # Enforce deterministic ordering: high attrition (desc), then low attrition (asc)
        order_rank = {"high_attrition": 0, "low_attrition": 1}

        def _sort_key(row: dict[str, object]) -> tuple[int, float, str]:
            group = str(row["group"])
            attr = float(row["attrition_percent"])
            sector = str(row["sector"])
            if group == "high_attrition":
                attr = -attr
            return (order_rank[group], attr, sector)

        comparison_rows.sort(key=_sort_key)

        derived = make_derived_query_result(
            operation="root_cause_comparison",
            params={"top_n": top_n, "outcome": "attrition_percent"},
            rows=format_evidence_table(comparison_rows),
            sources=[atr_res.query_id, qat_res.query_id],
        )

        metrics = {
            "high_attrition_qat_avg": round(high_qat_avg, 2),
            "low_attrition_qat_avg": round(low_qat_avg, 2),
            "qatarization_diff": round(qat_diff, 2),
            "top_n": top_n,
        }

        summary = (
            f"High attrition sectors (top {top_n}) have average qatarization of {high_qat_avg:.1f}%, "
            f"vs {low_qat_avg:.1f}% for low attrition sectors. "
            f"Difference: {qat_diff:+.1f} percentage points. "
            "Note: Correlation does not imply causation."
        )

        report = AgentReport(
            agent="PatternDetective",
            findings=[
                Insight(
                    title=f"Root cause analysis: Attrition drivers (top {top_n} comparison)",
                    summary=summary,
                    metrics=metrics,
                    evidence=[evidence_from(atr_res), evidence_from(qat_res), evidence_from(derived)],
                )
            ],
        )
        self._verify_response(report, [atr_res, qat_res, derived])
        return report

    def best_practices(
        self,
        metric: Literal["qatarization", "retention"] = "qatarization",
        top_n: int = 5,
    ) -> AgentReport:
        """
        Identify best practices from top-performing sectors.

        Args:
            metric: Performance metric ("qatarization" or "retention", default "qatarization")
            top_n: Number of top performers to highlight (default 5)

        Returns:
            AgentReport with best practice findings
        """
        if metric not in ("qatarization", "retention"):
            raise ValueError("metric must be either 'qatarization' or 'retention'.")
        if not 1 <= top_n <= 50:
            raise ValueError("top_n must be between 1 and 50 for best practice analysis.")

        logger.info(
            "best_practices params=%s queries=%s",
            {"metric": metric, "top_n": top_n},
            [
                "syn_qatarization_by_sector_latest"
                if metric == "qatarization"
                else "syn_attrition_by_sector_latest"
            ],
        )

        if metric == "qatarization":
            res = self.client.run("syn_qatarization_by_sector_latest")
            value_field = "qatarization_percent"
        else:  # retention uses inverse of attrition
            res = self.client.run("syn_attrition_by_sector_latest")
            value_field = "retention_percent"

        # Extract and sort
        sector_values: list[tuple[str, float]] = []
        for row in res.rows:
            sector = row.data.get("sector")
            if metric == "qatarization":
                value = row.data.get("qatarization_percent")
                if sector and isinstance(value, (int, float)):
                    sector_values.append((str(sector), float(value)))
            else:
                attr_value = row.data.get("attrition_percent")
                if sector and isinstance(attr_value, (int, float)):
                    retention_value = 100.0 - float(attr_value)
                    sector_values.append((str(sector), retention_value))

        if not sector_values:
            return AgentReport(
                agent="PatternDetective",
                findings=[],
                warnings=["No valid sector data found"],
            )

        # Sort by performance (descending always after retention conversion)
        sector_values.sort(key=lambda item: (-item[1], item[0]))

        top_performers = sector_values[:min(top_n, len(sector_values))]

        # Build best practice rows
        bp_rows: list[dict[str, object]] = []
        for rank, (sector, value) in enumerate(top_performers, 1):
            bp_rows.append(
                {
                    "rank": rank,
                    "sector": sector,
                    value_field: round(value, 2),
                    "metric": metric,
                }
            )

        derived = make_derived_query_result(
            operation="best_practices_ranking",
            params={"metric": metric, "top_n": top_n},
            rows=format_evidence_table(bp_rows),
            sources=[res.query_id],
        )

        avg_top = sum(v for _, v in top_performers) / len(top_performers)
        avg_all = sum(v for _, v in sector_values) / len(sector_values)

        metrics = {
            "metric": metric,
            f"top_{top_n}_average": round(avg_top, 2),
            "overall_average": round(avg_all, 2),
            "performance_gap": round(avg_top - avg_all, 2),
        }

        report = AgentReport(
            agent="PatternDetective",
            findings=[
                Insight(
                    title=f"Best practices: Top {top_n} sectors by {metric}",
                    summary=f"Top {top_n} sectors average {avg_top:.1f}% vs overall {avg_all:.1f}%.",
                    metrics=metrics,
                    evidence=[evidence_from(res), evidence_from(derived)],
                )
            ],
        )
        self._verify_response(report, [res, derived])
        return report

    def run(self) -> AgentReport:
        """
        Execute legacy data consistency validation.

        Maintains backward compatibility with existing tests.

        Returns:
            AgentReport with consistency findings and warnings for anomalies
        """
        employment_query = "syn_employment_share_by_gender_latest"
        logger.info("run legacy_consistency queries=%s", [employment_query])
        res = self.client.run(employment_query)
        warnings = list(res.warnings)
        # Detect discrepancy: male+female != total by tolerance used in number verifier
        latest = res.rows[-1].data if res.rows else {}
        discrepancy = None
        if all(k in latest for k in ("male_percent", "female_percent", "total_percent")):
            s = 0.0
            for k in ("male_percent", "female_percent"):
                v = latest.get(k)
                s += float(v) if isinstance(v, (int, float)) else 0.0
            t = latest.get("total_percent")
            if isinstance(t, (int, float)) and abs(s - float(t)) > SUM_PERCENT_TOLERANCE:
                discrepancy = round(s - float(t), 3)
                warnings.append(f"sum_mismatch:{discrepancy}")
        report = AgentReport(
            agent="PatternDetective",
            findings=[
                Insight(
                    title="Consistency check (gender shares vs total)",
                    summary="Check that male+female equals total within tolerance.",
                    metrics={"delta_percent": discrepancy} if discrepancy is not None else {},
                    evidence=[evidence_from(res)],
                    warnings=warnings,
                )
            ],
            warnings=warnings,
        )
        self._verify_response(report, [res])
        return report
