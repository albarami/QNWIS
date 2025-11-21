"""
National Strategy Agent - GCC competitiveness, Vision 2030, and geopolitical analysis.

This agent provides regional benchmarking, talent competition assessment,
and strategic alignment tracking against national development goals.
All analysis uses only the deterministic data layer.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence

from ..data.deterministic.models import QueryResult
from .base import AgentReport, DataClient, Insight, evidence_from
from .utils.derived_results import make_derived_query_result
from .utils.evidence import format_evidence_table
from .utils.verification import AgentResponseVerifier

logger = logging.getLogger(__name__)

# Vision 2030 targets (illustrative - should be configured externally)
VISION_2030_TARGETS = {
    "qatarization_public_sector": 90.0,  # Target: 90% Qataris in public sector
    "qatarization_private_sector": 30.0,  # Target: 30% Qataris in private sector
    "unemployment_rate_qataris": 2.0,  # Target: <2% unemployment for Qataris
    "female_labor_participation": 45.0,  # Target: 45% female participation
}


class NationalStrategyAgent:
    """
    Agent focused on national competitiveness and strategic planning.

    Capabilities:
    - gcc_benchmark: Compare Qatar to GCC peers on key labor metrics
    - talent_competition_assessment: Analyze regional talent flows and competitive dynamics
    - vision2030_alignment: Track progress toward Vision 2030 targets
    - run: Legacy strategic snapshot (maintains backward compatibility)
    """

    REQUIRED_DATA_TYPES = ["labor_market", "economic_indicators"]

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
        Initialize the National Strategy Agent.

        Args:
            client: DataClient instance for accessing deterministic queries
            verifier: Optional response verifier enforcing provenance integrity
        """
        self.client = client
        self._verifier = verifier or AgentResponseVerifier()

    def _verify_response(self, report: AgentReport, results: Sequence[QueryResult]) -> None:
        """
        Validate that the generated report references the supplied query results.

        Args:
            report: AgentReport produced by this agent.
            results: Sequence of QueryResult instances that informed the report.
        """
        self._verifier.verify(report, list(results))

    def gcc_benchmark(
        self,
        min_countries: int = 3,
    ) -> AgentReport:
        """
        Benchmark Qatar's unemployment rate against GCC peer countries.

        Provides ranking, gap analysis, and competitive positioning insights.

        Args:
            min_countries: Minimum number of GCC countries required for comparison (default 3)

        Returns:
            AgentReport with GCC benchmarking findings
        """
        if min_countries < 2:
            raise ValueError("min_countries must be at least 2 for benchmarking.")

        logger.info(
            "gcc_benchmark params=%s queries=%s",
            {"min_countries": min_countries},
            ["syn_unemployment_rate_gcc_latest"],
        )

        # Fetch GCC unemployment data
        gcc_res = self.client.run("syn_unemployment_rate_gcc_latest")

        if len(gcc_res.rows) < min_countries:
            return AgentReport(
                agent="NationalStrategy",
                findings=[],
                warnings=[f"Insufficient GCC data: {len(gcc_res.rows)} countries (need {min_countries})"],
            )

        # Extract country unemployment rates
        country_data = []
        for row in gcc_res.rows:
            country = row.data.get("country")
            rate = row.data.get("unemployment_rate")
            year = row.data.get("year")

            if country and isinstance(rate, (int, float)):
                country_data.append({
                    "country": str(country),
                    "unemployment_rate": float(rate),
                    "year": int(year) if isinstance(year, (int, float)) else None,
                })

        if len(country_data) < min_countries:
            return AgentReport(
                agent="NationalStrategy",
                findings=[],
                warnings=["Insufficient valid GCC unemployment data"],
            )

        # Sort by unemployment rate (ascending = better)
        country_data.sort(key=lambda x: x["unemployment_rate"])

        # Find Qatar's position
        qatar_idx = next((i for i, d in enumerate(country_data) if "qatar" in d["country"].lower()), None)
        qatar_rank = qatar_idx + 1 if qatar_idx is not None else None
        qatar_rate = country_data[qatar_idx]["unemployment_rate"] if qatar_idx is not None else None

        # Calculate GCC average
        gcc_avg = sum(d["unemployment_rate"] for d in country_data) / len(country_data)

        # Add ranking
        for rank, item in enumerate(country_data, 1):
            item["rank"] = rank

        # Create derived result
        derived = make_derived_query_result(
            operation="gcc_unemployment_ranking",
            params={"metric": "unemployment_rate"},
            rows=format_evidence_table(country_data),
            sources=[gcc_res.query_id],
            unit="percent",
        )

        metrics = {
            "gcc_countries_count": len(country_data),
            "gcc_average": round(gcc_avg, 2),
        }

        if qatar_rank and qatar_rate is not None:
            metrics["qatar_rank"] = qatar_rank
            metrics["qatar_rate"] = round(qatar_rate, 2)
            metrics["gap_to_average"] = round(qatar_rate - gcc_avg, 2)

            summary = (
                f"Qatar ranks {qatar_rank}/{len(country_data)} in GCC unemployment rate ({qatar_rate:.1f}%). "
                f"GCC average: {gcc_avg:.1f}%. "
                f"Gap to average: {qatar_rate - gcc_avg:+.1f} percentage points."
            )
        else:
            summary = f"GCC unemployment benchmarking across {len(country_data)} countries. Qatar data not found."

        report = AgentReport(
            agent="NationalStrategy",
            findings=[
                Insight(
                    title="GCC unemployment benchmarking",
                    summary=summary,
                    metrics=metrics,
                    evidence=[evidence_from(gcc_res), evidence_from(derived)],
                    warnings=list(gcc_res.warnings),
                )
            ],
        )
        self._verify_response(report, [gcc_res, derived])
        return report

    def talent_competition_assessment(
        self,
        focus_metric: str = "attrition_percent",
    ) -> AgentReport:
        """
        Assess talent competition dynamics by analyzing retention patterns.

        Identifies sectors under competitive pressure based on attrition rates.

        Args:
            focus_metric: Metric to assess competition (default "attrition_percent")

        Returns:
            AgentReport with talent competition findings
        """
        if focus_metric != "attrition_percent":
            raise ValueError("focus_metric currently supports only 'attrition_percent'.")

        logger.info(
            "talent_competition_assessment params=%s queries=%s",
            {"focus_metric": focus_metric},
            ["syn_attrition_by_sector_latest"],
        )

        # Fetch attrition data as proxy for competitive pressure
        atr_res = self.client.run("syn_attrition_by_sector_latest")

        # Extract sector attrition rates
        sector_data = []
        for row in atr_res.rows:
            sector = row.data.get("sector")
            attrition = row.data.get("attrition_percent")

            if sector and isinstance(attrition, (int, float)):
                sector_data.append({
                    "sector": str(sector),
                    "attrition_percent": float(attrition),
                })

        if not sector_data:
            return AgentReport(
                agent="NationalStrategy",
                findings=[],
                warnings=["No valid attrition data for talent competition assessment"],
            )

        # Sort by attrition (high = more competitive pressure)
        sector_data.sort(key=lambda x: x["attrition_percent"], reverse=True)

        # Classify competition intensity
        avg_attrition = sum(d["attrition_percent"] for d in sector_data) / len(sector_data)

        for item in sector_data:
            rate = item["attrition_percent"]
            if rate > avg_attrition * 1.5:
                item["competition_level"] = "high"
            elif rate > avg_attrition:
                item["competition_level"] = "moderate"
            else:
                item["competition_level"] = "low"

        high_competition_count = sum(1 for d in sector_data if d.get("competition_level") == "high")

        # Create derived result
        derived = make_derived_query_result(
            operation="talent_competition_classification",
            params={"metric": focus_metric, "threshold_multiplier": 1.5},
            rows=format_evidence_table(sector_data),
            sources=[atr_res.query_id],
        )

        metrics = {
            "average_attrition": round(avg_attrition, 2),
            "high_competition_sectors": high_competition_count,
            "total_sectors": len(sector_data),
        }

        if sector_data:
            metrics["highest_attrition"] = round(sector_data[0]["attrition_percent"], 2)
            metrics["highest_attrition_sector"] = sector_data[0]["sector"]

        summary = (
            f"Talent competition assessment across {len(sector_data)} sectors. "
            f"Average attrition: {avg_attrition:.1f}%. "
            f"{high_competition_count} sectors face high competitive pressure (>1.5x average)."
        )

        report = AgentReport(
            agent="NationalStrategy",
            findings=[
                Insight(
                    title="Talent competition assessment",
                    summary=summary,
                    metrics=metrics,
                    evidence=[evidence_from(atr_res), evidence_from(derived)],
                )
            ],
        )
        self._verify_response(report, [atr_res, derived])
        return report

    def vision2030_alignment(
        self,
        target_year: int = 2030,
        current_year: int = 2024,
    ) -> AgentReport:
        """
        Track progress toward Vision 2030 qatarization targets.

        Calculates gaps, required annual growth rates, and risk assessment.

        Args:
            target_year: Target year for Vision 2030 goals (default 2030)
            current_year: Current baseline year (default 2024)

        Returns:
            AgentReport with Vision 2030 alignment findings
        """
        if current_year > target_year:
            raise ValueError("current_year cannot be greater than target_year.")

        logger.info(
            "vision2030_alignment params=%s queries=%s",
            {"target_year": target_year, "current_year": current_year},
            ["syn_qatarization_by_sector_latest"],
        )

        # Fetch current qatarization data
        qat_res = self.client.run("syn_qatarization_by_sector_latest")

        # Calculate overall qatarization rate
        total_qataris = 0
        total_employees = 0

        for row in qat_res.rows:
            qataris = row.data.get("qataris")
            non_qataris = row.data.get("non_qataris")

            if isinstance(qataris, (int, float)) and isinstance(non_qataris, (int, float)):
                total_qataris += float(qataris)
                total_employees += float(qataris) + float(non_qataris)

        if total_employees == 0:
            return AgentReport(
                agent="NationalStrategy",
                findings=[],
                warnings=["No valid employment data for Vision 2030 assessment"],
            )

        current_qatarization = (total_qataris / total_employees) * 100

        # Compare to Vision 2030 target (using private sector target as baseline)
        target_qatarization = VISION_2030_TARGETS["qatarization_private_sector"]
        gap = target_qatarization - current_qatarization
        gap_percent = (gap / target_qatarization) * 100 if target_qatarization > 0 else 0

        # Calculate required annual growth
        years_remaining = target_year - current_year
        required_annual_growth = gap / years_remaining if years_remaining > 0 else 0.0

        # Risk assessment
        if gap <= 0:
            risk_level = "on_track"
        elif abs(gap_percent) < 20:
            risk_level = "moderate"
        else:
            risk_level = "high"

        # Create derived result
        alignment_rows = [{
            "kpi": "overall_qatarization",
            "current_value": round(current_qatarization, 2),
            "target_value": target_qatarization,
            "gap": round(gap, 2),
            "gap_percent": round(gap_percent, 2),
            "years_remaining": years_remaining,
            "required_annual_growth": round(required_annual_growth, 2),
            "risk_level": risk_level,
        }]

        derived = make_derived_query_result(
            operation="vision2030_gap_analysis",
            params={"target_year": target_year, "current_year": current_year},
            rows=format_evidence_table(alignment_rows, max_rows=10),
            sources=[qat_res.query_id],
            unit="percent",
        )

        metrics = {
            "current_qatarization": round(current_qatarization, 2),
            "target_qatarization": target_qatarization,
            "gap_percentage_points": round(gap, 2),
            "required_annual_growth": round(required_annual_growth, 2),
            "years_remaining": years_remaining,
        }

        summary = (
            f"Vision 2030 qatarization alignment: Current {current_qatarization:.1f}% vs "
            f"target {target_qatarization:.1f}%. "
            f"Gap: {gap:.1f} percentage points ({gap_percent:.1f}% of target). "
            f"Requires {required_annual_growth:.2f} pp annual growth over {years_remaining} years. "
            f"Risk level: {risk_level}."
        )

        report = AgentReport(
            agent="NationalStrategy",
            findings=[
                Insight(
                    title="Vision 2030 qatarization alignment",
                    summary=summary,
                    metrics=metrics,
                    evidence=[evidence_from(qat_res), evidence_from(derived)],
                )
            ],
        )
        self._verify_response(report, [qat_res, derived])
        return report

    def run(self) -> AgentReport:
        """
        Execute legacy strategic snapshot analysis.

        Maintains backward compatibility with existing tests.

        Returns:
            AgentReport with integrated employment and GCC unemployment metrics
        """
        queries = ["syn_employment_share_by_gender_latest", "syn_unemployment_gcc_latest"]
        logger.info("run strategic_snapshot queries=%s", queries)
        # Use both queries deterministically
        emp = self.client.run(queries[0])
        gcc = self.client.run(queries[1])
        metrics = {}
        if emp.rows:
            latest = emp.rows[-1].data
            for k in ("male_percent", "female_percent", "total_percent"):
                v = latest.get(k)
                if isinstance(v, (int, float)):
                    metrics[f"employment_{k}"] = float(v)
        # GCC: record simple aggregates if possible
        vals = []
        for r in gcc.rows:
            # Skip non-unemployment fields like country code and year
            for k, v in r.data.items():
                if isinstance(v, (int, float)) and k not in ("year", "country"):
                    vals.append(float(v))
                    break
        if vals:
            metrics["gcc_unemployment_min"] = min(vals)
            metrics["gcc_unemployment_max"] = max(vals)
        insight = Insight(
            title="Strategic snapshot: employment & GCC unemployment",
            summary="Latest employment split plus GCC unemployment range.",
            metrics=metrics,
            evidence=[evidence_from(emp), evidence_from(gcc)],
            warnings=list(set(emp.warnings + gcc.warnings)),
        )
        report = AgentReport(agent="NationalStrategy", findings=[insight])
        self._verify_response(report, [emp, gcc])
        return report
