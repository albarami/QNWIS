"""
Lightweight verification utilities for deterministic agent responses.

These helpers ensure that every evidence reference in an AgentReport
corresponds to the exact QueryResult instances that were used during
analysis, preserving the integrity of the provenance chain.
"""

from __future__ import annotations

from collections.abc import Sequence

from ...data.deterministic.models import QueryResult
from ..base import AgentReport


class AgentVerificationError(RuntimeError):
    """Raised when an agent report cannot be reconciled with its data sources."""


class AgentResponseVerifier:
    """
    Validate that agent findings cite the supplied query results.

    The verifier performs inexpensive structural checks that support
    deterministic tests without requiring any external context.
    """

    def verify(self, report: AgentReport, results: Sequence[QueryResult]) -> None:
        """
        Ensure every evidence entry in the report references a known QueryResult.

        Args:
            report: AgentReport to evaluate.
            results: Sequence of QueryResult objects made available to the agent.

        Raises:
            AgentVerificationError: If evidence references unknown query IDs,
                query results share duplicate IDs, or mandatory metadata is absent.
        """
        result_ids: list[str] = []
        for res in results:
            if not res.query_id:
                raise AgentVerificationError("QueryResult is missing a query_id.")
            if res.provenance is None:
                raise AgentVerificationError(f"QueryResult {res.query_id} lacks provenance metadata.")
            if res.query_id in result_ids:
                raise AgentVerificationError(f"Duplicate QueryResult supplied for '{res.query_id}'.")
            result_ids.append(res.query_id)

        known_ids = set(result_ids)
        for insight in report.findings:
            for evidence in insight.evidence:
                if evidence.query_id not in known_ids:
                    raise AgentVerificationError(
                        f"Evidence references '{evidence.query_id}', which was not verified."
                    )
