"""
Orchestration workflow nodes.

This package now hosts:
- Legacy router/formatter/invoker nodes used by the classic council workflow
- LangGraph intelligence nodes powering the multi-agent intelligence system
"""

from .error import error_handler
from .format import format_report
from .invoke import invoke_agent
from .router import route_intent
from .verify import verify_structure

# LangGraph intelligence nodes (added progressively)
from .classifier import classify_query_node
from .extraction import data_extraction_node
from .financial import financial_agent_node
from .market import market_agent_node
from .operations import operations_agent_node
from .research import research_agent_node
from .debate import debate_node
from .critique import critique_node
from .verification import verification_node
from .synthesis import synthesis_node
from .synthesis_strategic import strategic_synthesis_node
from .scenario_generator import ScenarioGenerator
from .scenario_baseline_requirements import (
    analyze_query_requirements,
    enhance_facts_with_scenario_baselines,
    format_baselines_for_prompt,
    SCENARIO_BASELINE_REQUIREMENTS,
)
from .first_principles_reasoning import (
    feasibility_gate_node,
    arithmetic_validator_node,
    enhance_agent_prompt_with_first_principles,
    FIRST_PRINCIPLES_PROTOCOL,
)
from .structure_data import structure_data_node, convert_structured_to_model_input
from .calculate import calculate_node, get_calculated_summary, format_comparison_table

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
    # Financial calculation nodes
    "structure_data_node",
    "convert_structured_to_model_input",
    "calculate_node",
    "get_calculated_summary",
    "format_comparison_table",
]
