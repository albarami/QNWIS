"""Agent modules for QNWIS multi-agent system."""

from .alert_center import AlertCenterAgent
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
from .national_strategy_llm import NationalStrategyLLMAgent
from .nationalization import NationalizationAgent
from .pattern_detective import PatternDetectiveAgent
from .pattern_detective_llm import PatternDetectiveLLMAgent
from .pattern_miner import PatternMinerAgent
from .predictor import PredictorAgent
from .reporting.jsonl import write_report
from .research_scientist import ResearchScientistAgent
from .scenario_agent import ScenarioAgent
from .skills import SkillsAgent
from .time_machine import TimeMachineAgent

__all__ = [
    "AgentReport",
    "AlertCenterAgent",
    "DataClient",
    "Evidence",
    "Insight",
    "MissingQueryDefinitionError",
    "QueryRegistryView",
    "LabourEconomistAgent",
    "NationalStrategyAgent",
    "NationalStrategyLLMAgent",
    "NationalizationAgent",
    "PatternDetectiveAgent",
    "PatternDetectiveLLMAgent",
    "PatternMinerAgent",
    "PredictorAgent",
    "ResearchScientistAgent",
    "ScenarioAgent",
    "SkillsAgent",
    "TimeMachineAgent",
    "write_report",
]
