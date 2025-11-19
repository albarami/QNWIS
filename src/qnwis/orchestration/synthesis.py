"""
Council report synthesis and consensus computation.

Merges findings from multiple agents into a unified council report with
consensus metrics computed as simple averages across agent outputs.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..agents.base import AgentReport, Insight


@dataclass
class CouncilReport:
    """
    Synthesized output from multi-agent council execution.

    Attributes:
        agents: List of agent names that participated
        findings: All insights from all agents
        consensus: Average metric values across agents (for metrics with 2+ values)
        warnings: Deduplicated warnings from all agents and insights
    """

    agents: list[str]
    findings: list[Insight]
    consensus: dict[str, float] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


def _collect_metrics(reports: list[AgentReport]) -> dict[str, list[float]]:
    """
    Collect all numeric metrics from agent reports into a dictionary of lists.

    Args:
        reports: List of AgentReport objects

    Returns:
        Dictionary mapping metric names to lists of observed values
    """
    bag: dict[str, list[float]] = {}
    for rep in reports:
        for ins in rep.findings:
            for k, v in (ins.metrics or {}).items():
                if isinstance(v, (int, float)):
                    bag.setdefault(k, []).append(float(v))
    return bag


def _compute_consensus(bag: dict[str, list[float]]) -> dict[str, float]:
    """
    Compute consensus metrics as simple averages.

    Only includes metrics that appear in 2+ reports to avoid
    single-agent bias in the consensus view.

    Args:
        bag: Dictionary mapping metric names to lists of values

    Returns:
        Dictionary of averaged consensus metrics
    """
    out: dict[str, float] = {}
    for k, vals in bag.items():
        if len(vals) >= 2:
            out[k] = sum(vals) / len(vals)
    return out


def synthesize(reports: list[AgentReport]) -> CouncilReport:
    """
    Synthesize a council report from multiple agent reports.

    Combines all findings, computes consensus metrics, and deduplicates warnings.

    Args:
        reports: List of AgentReport objects from council execution

    Returns:
        CouncilReport with synthesized findings and consensus
    """
    agents = [rep.agent for rep in reports]
    bag = _collect_metrics(reports)
    consensus = _compute_consensus(bag)
    warnings: list[str] = []
    for rep in reports:
        warnings.extend(rep.warnings)
        for ins in rep.findings:
            warnings.extend(ins.warnings)
    findings: list[Insight] = []
    for rep in reports:
        findings.extend(rep.findings)
    return CouncilReport(
        agents=agents, findings=findings, consensus=consensus, warnings=sorted(set(warnings))
    )
