"""
LangGraph Workflow for QNWIS Intelligence System.

Implements the foundational 10-node graph (currently 2 nodes wired).
"""

from __future__ import annotations

from datetime import datetime

from typing import Literal

from langgraph.graph import END, StateGraph

from .nodes import (
    classify_query_node,
    critique_node,
    data_extraction_node,
    debate_node,
    financial_agent_node,
    market_agent_node,
    operations_agent_node,
    research_agent_node,
    synthesis_node,
    verification_node,
)
from .state import IntelligenceState


def route_by_complexity(state: IntelligenceState) -> Literal["simple", "medium", "complex"]:
    """
    Route workflow based on query complexity.
    
    Returns:
        "simple": Skip debate/critique for quick fact lookup
        "medium": Standard flow with all nodes
        "complex": Full multi-agent debate with extended analysis
    """
    complexity = state.get("complexity", "medium")
    
    # Map critical to complex for routing purposes
    if complexity == "critical":
        return "complex"
    
    # Return normalized routing key
    if complexity in ("simple", "medium", "complex"):
        return complexity  # type: ignore
    
    return "medium"


def create_intelligence_graph() -> StateGraph:
    """
    Create the LangGraph workflow with all nodes.

    Nodes implemented in this milestone:
    1. Classifier - Determine complexity
    2. Extraction - Fetch data from cache/APIs
    """

    workflow = StateGraph(IntelligenceState)

    workflow.add_node("classifier", classify_query_node)
    workflow.add_node("extraction", data_extraction_node)
    workflow.add_node("financial", financial_agent_node)
    workflow.add_node("market", market_agent_node)
    workflow.add_node("operations", operations_agent_node)
    workflow.add_node("research", research_agent_node)
    workflow.add_node("debate", debate_node)
    workflow.add_node("critique", critique_node)
    workflow.add_node("verification", verification_node)
    workflow.add_node("synthesis", synthesis_node)

    # Entry point
    workflow.set_entry_point("classifier")
    
    # Always go through extraction after classification
    workflow.add_edge("classifier", "extraction")
    
    # Conditional routing after extraction based on complexity
    # Simple: Skip directly to synthesis (minimal analysis)
    # Medium/Complex: Run through all agent nodes
    workflow.add_conditional_edges(
        "extraction",
        route_by_complexity,
        {
            "simple": "synthesis",      # Fast path: skip agents for simple queries
            "medium": "financial",      # Standard path: all nodes
            "complex": "financial",     # Full path: all nodes + extended debate
        }
    )
    
    # Agent execution chain (medium/complex queries only)
    workflow.add_edge("financial", "market")
    workflow.add_edge("market", "operations")
    workflow.add_edge("operations", "research")
    workflow.add_edge("research", "debate")
    workflow.add_edge("debate", "critique")
    workflow.add_edge("critique", "verification")
    workflow.add_edge("verification", "synthesis")
    
    # All paths converge at synthesis, then complete
    workflow.add_edge("synthesis", END)

    return workflow.compile()


async def run_intelligence_query(query: str) -> IntelligenceState:
    """
    Run a query through the intelligence graph.

    Args:
        query: Natural language ministerial query.

    Returns:
        Complete state after flowing through the LangGraph.
    """

    initial_state: IntelligenceState = {
        "query": query,
        "complexity": "",
        "agent_reports": [],
        "extracted_facts": [],
        "data_sources": [],
        "data_quality_score": 0.0,
        "financial_analysis": None,
        "market_analysis": None,
        "operations_analysis": None,
        "research_analysis": None,
        "debate_synthesis": None,
        "debate_results": None,  # Initialize debate results field
        "critique_report": None,
        "fact_check_results": None,
        "fabrication_detected": False,
        "final_synthesis": None,
        "confidence_score": 0.0,
        "reasoning_chain": [],
        "nodes_executed": [],
        "metadata": {},
        "execution_time": None,
        "timestamp": datetime.now().isoformat(),
        "warnings": [],
        "errors": [],
    }

    graph = create_intelligence_graph()

    start_time = datetime.now()
    result = await graph.ainvoke(initial_state)
    result["execution_time"] = (datetime.now() - start_time).total_seconds()

    return result

