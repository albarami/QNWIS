"""
Labour Economist Agent - Employment trends and gender distribution analysis.

This agent analyzes employment share data by gender and computes year-over-year
growth metrics using only deterministic data sources.
"""

from __future__ import annotations

from ..data.derived.metrics import yoy_growth
from .base import AgentReport, DataClient, Insight, evidence_from

EMPLOYMENT_QUERY = "q_employment_share_by_gender_2023"


class LabourEconomistAgent:
    """
    Agent focused on employment statistics and gender distribution.

    Computes year-over-year growth trends and provides latest employment
    share metrics from deterministic data sources.
    """

    def __init__(self, client: DataClient) -> None:
        """
        Initialize the Labour Economist Agent.

        Args:
            client: DataClient instance for accessing deterministic queries
        """
        self.client = client

    def run(self) -> AgentReport:
        """
        Execute analysis of employment trends.

        Returns:
            AgentReport with employment metrics and YoY growth analysis
        """
        res = self.client.run(EMPLOYMENT_QUERY)
        rows = [{"data": r.data} for r in res.rows]
        yoy = yoy_growth(rows, value_key="total_percent")
        latest = yoy[-1]["data"] if yoy else {}
        insight = Insight(
            title="Employment share (latest & YoY)",
            summary="Latest employment split and YoY percentage change for total.",
            metrics={k: float(v) for k, v in latest.items() if isinstance(v, (int, float))},
            evidence=[evidence_from(res)],
            warnings=res.warnings,
        )
        return AgentReport(agent="LabourEconomist", findings=[insight])
