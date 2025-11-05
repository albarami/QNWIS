"""
National Strategy Agent - Strategic overview combining multiple data sources.

This agent provides a comprehensive strategic snapshot by combining employment
trends with GCC unemployment comparisons for policy planning.
"""

from __future__ import annotations

from .base import AgentReport, DataClient, Insight, evidence_from


class NationalStrategyAgent:
    """
    Agent focused on strategic national workforce planning.

    Combines employment distribution metrics with GCC unemployment comparisons
    to provide a comprehensive view for policy decisions.
    """

    def __init__(self, client: DataClient) -> None:
        """
        Initialize the National Strategy Agent.

        Args:
            client: DataClient instance for accessing deterministic queries
        """
        self.client = client

    def run(self) -> AgentReport:
        """
        Execute strategic analysis combining multiple data sources.

        Returns:
            AgentReport with integrated employment and GCC unemployment metrics
        """
        # Use both queries deterministically
        emp = self.client.run("q_employment_share_by_gender_2023")
        gcc = self.client.run("q_unemployment_rate_gcc_latest")
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
        return AgentReport(agent="NationalStrategy", findings=[insight])
