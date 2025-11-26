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
]
