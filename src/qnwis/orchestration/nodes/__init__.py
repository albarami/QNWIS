"""
Orchestration workflow nodes.

This package now hosts:
- Legacy router/formatter/invoker nodes used by the classic council workflow
- LangGraph intelligence nodes powering the multi-agent intelligence system
"""

from .calculate import calculate_node, format_comparison_table, get_calculated_summary

# LangGraph intelligence nodes (added progressively)
from .classifier import classify_query_node
from .critique import critique_node
from .debate import debate_node
from .error import error_handler
from .extraction import data_extraction_node
from .financial import financial_agent_node
from .first_principles_reasoning import (
    FIRST_PRINCIPLES_PROTOCOL,
    arithmetic_validator_node,
    enhance_agent_prompt_with_first_principles,
    feasibility_gate_node,
)
from .format import format_report
from .infeasible_analysis import infeasible_analysis_node
from .invoke import invoke_agent
from .market import market_agent_node
from .operations import operations_agent_node
from .research import research_agent_node
from .router import route_intent
from .scenario_baseline_requirements import (
    SCENARIO_BASELINE_REQUIREMENTS,
    analyze_query_requirements,
    enhance_facts_with_scenario_baselines,
    format_baselines_for_prompt,
)
from .scenario_generator import ScenarioGenerator
from .structure_data import convert_structured_to_model_input, structure_data_node
from .synthesis import synthesis_node
from .synthesis_strategic import strategic_synthesis_node
from .verification import verification_node
from .verify import verify_structure

__all__ = [
    # Legacy nodes
    "route_intent",
    "invoke_agent",
    "verify_structure",
    "format_report",
    "error_handler",
    # LangGraph nodes
    "classify_query_node",
    "data_extraction_node",
    "financial_agent_node",
    "market_agent_node",
    "operations_agent_node",
    "research_agent_node",
    "debate_node",
    "critique_node",
    "verification_node",
    "synthesis_node",
    "strategic_synthesis_node",
    # Scenario generation
    "ScenarioGenerator",
    "analyze_query_requirements",
    "enhance_facts_with_scenario_baselines",
    "format_baselines_for_prompt",
    "SCENARIO_BASELINE_REQUIREMENTS",
    # First-principles reasoning
    "feasibility_gate_node",
    "arithmetic_validator_node",
    "enhance_agent_prompt_with_first_principles",
    "FIRST_PRINCIPLES_PROTOCOL",
    # Infeasible target analysis
    "infeasible_analysis_node",
    # Financial calculation nodes
    "structure_data_node",
    "convert_structured_to_model_input",
    "calculate_node",
    "get_calculated_summary",
    "format_comparison_table",
]
