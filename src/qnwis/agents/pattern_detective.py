"""
Pattern Detective Agent - Data consistency and quality validation.

This agent detects anomalies and inconsistencies in deterministic data,
such as sum mismatches and unexpected patterns.
"""

from __future__ import annotations

from ..data.validation.number_verifier import SUM_PERCENT_TOLERANCE
from .base import AgentReport, DataClient, Insight, evidence_from


class PatternDetectiveAgent:
    """
    Agent focused on detecting data quality issues and anomalies.

    Performs consistency checks such as validating that component values
    sum correctly to totals within acceptable tolerance.
    """

    def __init__(self, client: DataClient) -> None:
        """
        Initialize the Pattern Detective Agent.

        Args:
            client: DataClient instance for accessing deterministic queries
        """
        self.client = client

    def run(self) -> AgentReport:
        """
        Execute data consistency validation.

        Returns:
            AgentReport with consistency findings and warnings for anomalies
        """
        res = self.client.run("q_employment_share_by_gender_2023")
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
        return AgentReport(
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
