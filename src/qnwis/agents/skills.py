"""
Skills Agent - Skills pipeline analysis through gender distribution.

This agent uses gender distribution in employment as a proxy metric for
analyzing the skills pipeline and workforce composition.
"""

from __future__ import annotations

from .base import AgentReport, DataClient, Insight, evidence_from


class SkillsAgent:
    """
    Agent focused on skills pipeline through gender distribution metrics.

    Uses employment gender distribution as a deterministic proxy for
    analyzing skills availability and workforce composition.
    """

    def __init__(self, client: DataClient) -> None:
        """
        Initialize the Skills Agent.

        Args:
            client: DataClient instance for accessing deterministic queries
        """
        self.client = client

    def run(self) -> AgentReport:
        """
        Execute skills pipeline analysis.

        Returns:
            AgentReport with gender distribution metrics as skills proxy
        """
        res = self.client.run("q_employment_share_by_gender_2023")
        latest = res.rows[-1].data if res.rows else {}
        metrics = {}
        for k in ("male_percent", "female_percent", "total_percent"):
            v = latest.get(k)
            if isinstance(v, (int, float)):
                metrics[k] = float(v)
        return AgentReport(
            agent="Skills",
            findings=[
                Insight(
                    title="Gender distribution (employment)",
                    summary="Latest split by gender.",
                    metrics=metrics,
                    evidence=[evidence_from(res)],
                    warnings=res.warnings,
                )
            ],
        )
