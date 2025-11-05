"""
Nationalization Agent - GCC unemployment comparison and ranking.

This agent analyzes unemployment rates across GCC countries and determines
Qatar's relative position for policy insights.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from .base import AgentReport, DataClient, Insight, evidence_from

UNEMPLOY_QUERY = "q_unemployment_rate_gcc_latest"


class NationalizationAgent:
    """
    Agent focused on nationalization policy through GCC unemployment comparison.

    Analyzes unemployment rates across GCC countries to determine Qatar's
    competitive position and identify best practices.
    """

    def __init__(self, client: DataClient) -> None:
        """
        Initialize the Nationalization Agent.

        Args:
            client: DataClient instance for accessing deterministic queries
        """
        self.client = client

    def run(self) -> AgentReport:
        """
        Execute GCC unemployment comparison analysis.

        Returns:
            AgentReport with Qatar's unemployment rate and GCC ranking
        """
        res = self.client.run(UNEMPLOY_QUERY)
        # Determine best (min) unemployment among GCC and Qatar's rank
        records = [r.data for r in res.rows]

        def _coerce(value: Any) -> float | None:
            """Coerce numeric-like fields safely to float."""
            if isinstance(value, bool):
                return None
            if isinstance(value, (int, float)):
                return float(value)
            if isinstance(value, str):
                try:
                    return float(value.strip())
                except ValueError:
                    return None
            return None

        ignore_fields = {"year", "country", "iso", "iso_code"}
        candidate_counts: Counter[str] = Counter()
        for record in records:
            for field, value in record.items():
                if field in ignore_fields:
                    continue
                if _coerce(value) is not None:
                    candidate_counts[field] += 1

        key = None
        if candidate_counts:
            if "value" in candidate_counts:
                key = "value"
            else:
                key = max(candidate_counts.items(), key=lambda item: (item[1], item[0]))[0]

        qatar_value: float | None = None
        values: list[float] = []
        if key is not None:
            for record in records:
                numeric = _coerce(record.get(key))
                if numeric is None:
                    continue
                values.append(numeric)
                country = str(record.get("country", "")).strip().upper()
                if country in {"QAT", "QATAR"}:
                    qatar_value = numeric
        rank = None
        if key and qatar_value is not None:
            sorted_vals = sorted(values)
            rank = sorted_vals.index(qatar_value) + 1 if qatar_value in sorted_vals else None
        metrics = {}
        if key and qatar_value is not None:
            metrics["qatar_unemployment_percent"] = float(qatar_value)
        if rank is not None:
            metrics["qatar_rank_gcc"] = float(rank)
        return AgentReport(
            agent="Nationalization",
            findings=[
                Insight(
                    title="GCC unemployment comparison",
                    summary="Qatar unemployment and GCC rank (lower is better).",
                    metrics=metrics,
                    evidence=[evidence_from(res)],
                    warnings=res.warnings,
                )
            ],
        )
