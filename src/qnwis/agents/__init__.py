"""Agent modules for QNWIS multi-agent system."""

from .base import (
    AgentReport,
    DataClient,
    Evidence,
    Insight,
    MissingQueryDefinitionError,
    QueryRegistryView,
)
from .labour_economist import LabourEconomistAgent
from .national_strategy import NationalStrategyAgent
from .nationalization import NationalizationAgent
from .pattern_detective import PatternDetectiveAgent
from .reporting.jsonl import write_report
from .skills import SkillsAgent

__all__ = [
    "AgentReport",
    "DataClient",
    "Evidence",
    "Insight",
    "MissingQueryDefinitionError",
    "QueryRegistryView",
    "LabourEconomistAgent",
    "NationalStrategyAgent",
    "NationalizationAgent",
    "PatternDetectiveAgent",
    "SkillsAgent",
    "write_report",
]
