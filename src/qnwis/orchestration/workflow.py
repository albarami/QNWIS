"""
LangGraph Workflow for QNWIS Intelligence System.

Implements multi-GPU parallel scenario analysis with backward compatibility.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Literal

from langgraph.graph import END, StateGraph

from .nodes import (
    classify_query_node,
    critique_node,
    data_extraction_node,
    financial_agent_node,
    market_agent_node,
    operations_agent_node,
    research_agent_node,
    verification_node,
)
# Import legendary debate node instead of simplified debate
from .nodes.debate_legendary import legendary_debate_node
# Import ministerial synthesis for executive-ready output
from .nodes.synthesis_ministerial import ministerial_synthesis_node
# Import parallel scenario analysis components
from .nodes.scenario_generator import ScenarioGenerator
from .parallel_executor import ParallelDebateExecutor
from .nodes.meta_synthesis import meta_synthesis_node
from .state import IntelligenceState

logger = logging.getLogger(__name__)


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


async def scenario_generation_node(state: IntelligenceState) -> IntelligenceState:
    """
    Generate scenarios for parallel testing.
    
    Checks if parallel scenario analysis is enabled and generates 4-6 scenarios
    for simultaneous execution across GPUs 0-5.
    """
    # Check if parallel scenarios are enabled
    if not state.get('enable_parallel_scenarios', True):
        logger.info("Parallel scenarios disabled, using single analysis path")
        state['scenarios'] = None
        return state
    
    # Check if complexity warrants parallel analysis
    complexity = state.get('complexity', 'medium')
    if complexity == 'simple':
        logger.info("Simple query detected, skipping parallel scenarios")
        state['scenarios'] = None
        return state
    
    try:
        logger.info("Generating scenarios for parallel analysis...")
        generator = ScenarioGenerator()
        
        # Await async scenario generation (don't use asyncio.run - we're already in async context)
        scenarios = await generator.generate_scenarios(
            query=state['query'],
            extracted_facts=state.get('extracted_facts', {})
        )
        
        state['scenarios'] = scenarios
        state['reasoning_chain'].append(
            f"🎯 Generated {len(scenarios)} scenarios for parallel GPU analysis"
        )
        
        logger.info(f"✅ Generated {len(scenarios)} scenarios")
        return state
        
    except Exception as e:
        logger.error(f"Scenario generation failed: {e}", exc_info=True)
        # Fall back to single analysis
        state['scenarios'] = None
        state['warnings'].append(f"Scenario generation failed: {e}")
        return state


async def parallel_execution_node(state: IntelligenceState) -> IntelligenceState:
    """
    Execute multiple debates in parallel across GPUs 0-5.
    
    Distributes scenarios across available GPUs and runs complete
    debate workflows simultaneously.
    """
    scenarios = state.get('scenarios')
    if not scenarios:
        logger.info("No scenarios to execute, skipping parallel execution")
        return state
    
    try:
        logger.info(f"Starting parallel execution of {len(scenarios)} scenarios...")
        
        # Get event callback from state
        event_callback = state.get('emit_event_fn')
        
        # Create parallel executor with event callback
        executor = ParallelDebateExecutor(num_parallel=6, event_callback=event_callback)
        
        # Build base workflow (single-scenario workflow without scenario generation)
        base_workflow = build_base_workflow()
        
        # Execute scenarios in parallel (await directly - we're already in async context)
        scenario_results = await executor.execute_scenarios(scenarios, base_workflow, state)
        
        state['scenario_results'] = scenario_results
        state['reasoning_chain'].append(
            f"✅ Completed {len(scenario_results)}/{len(scenarios)} parallel scenarios"
        )
        
        logger.info(f"✅ Parallel execution complete: {len(scenario_results)} scenarios")
        return state
        
    except Exception as e:
        logger.error(f"Parallel execution failed: {e}", exc_info=True)
        state['errors'].append(f"Parallel execution failed: {e}")
        state['scenario_results'] = []
        return state


async def aggregate_scenarios_for_debate_node(state: IntelligenceState) -> IntelligenceState:
    """
    Aggregate scenario results into agent analysis format for main debate.
    
    After parallel execution, prepares state for cross-scenario debate
    by converting scenario results into agent analyses format.
    """
    scenario_results = state.get('scenario_results', [])
    if not scenario_results:
        logger.info("No scenario results to aggregate")
        return state
    
    logger.info(f"Aggregating {len(scenario_results)} scenario results for main debate...")
    
    # Create synthetic agent analyses from scenario results
    # Each scenario's synthesis becomes an "agent" position for the main debate
    for i, result in enumerate(scenario_results):
        scenario_name = result.get('scenario_name', f'Scenario {i+1}')
        synthesis = result.get('synthesis', result.get('final_synthesis', ''))
        
        # Add as agent analysis for debate nodes to process
        if i == 0:
            state['financial_analysis'] = f"[{scenario_name}] {synthesis}"
        elif i == 1:
            state['market_analysis'] = f"[{scenario_name}] {synthesis}"
        elif i == 2:
            state['operations_analysis'] = f"[{scenario_name}] {synthesis}"
        elif i == 3:
            state['research_analysis'] = f"[{scenario_name}] {synthesis}"
    
    # Store all scenario syntheses for debate context
    state['scenario_syntheses'] = [
        {
            'name': r.get('scenario_name', f'Scenario {i+1}'),
            'synthesis': r.get('synthesis', r.get('final_synthesis', ''))
        }
        for i, r in enumerate(scenario_results)
    ]
    
    state['reasoning_chain'].append(
        f"✅ Aggregated {len(scenario_results)} scenarios for cross-scenario debate"
    )
    
    logger.info("✅ Scenario aggregation complete")
    return state


async def meta_synthesis_wrapper(state: IntelligenceState) -> IntelligenceState:
    """
    Synthesize insights across all scenario results.
    
    Creates ministerial-grade strategic intelligence by identifying
    robust recommendations, scenario-dependent strategies, and early warning indicators.
    """
    scenario_results = state.get('scenario_results')
    if not scenario_results:
        logger.info("No scenario results to synthesize")
        return state
    
    try:
        logger.info(f"Synthesizing insights across {len(scenario_results)} scenarios...")
        
        # Await meta-synthesis (already in async context)
        meta_synthesis = await meta_synthesis_node(scenario_results)
        
        state['final_synthesis'] = meta_synthesis
        state['reasoning_chain'].append("✅ Meta-synthesis complete")
        
        logger.info("✅ Meta-synthesis complete")
        return state
        
    except Exception as e:
        logger.error(f"Meta-synthesis failed: {e}", exc_info=True)
        state['errors'].append(f"Meta-synthesis failed: {e}")
        # Use emergency fallback
        state['final_synthesis'] = f"Meta-synthesis error: {e}"
        return state


def build_base_workflow() -> StateGraph:
    """
    Build base workflow for individual scenario execution.
    
    This is the single-scenario workflow used by the parallel executor.
    Does not include scenario generation/parallel execution nodes.
    
    Returns:
        Compiled StateGraph for single scenario
    """
    workflow = StateGraph(IntelligenceState)
    
    # Add single-scenario nodes
    workflow.add_node("financial", financial_agent_node)
    workflow.add_node("market", market_agent_node)
    workflow.add_node("operations", operations_agent_node)
    workflow.add_node("research", research_agent_node)
    workflow.add_node("debate", legendary_debate_node)
    workflow.add_node("critique", critique_node)
    workflow.add_node("verification", verification_node)
    workflow.add_node("synthesis", ministerial_synthesis_node)
    
    # Wire nodes in sequence
    workflow.set_entry_point("financial")
    workflow.add_edge("financial", "market")
    workflow.add_edge("market", "operations")
    workflow.add_edge("operations", "research")
    workflow.add_edge("research", "debate")
    workflow.add_edge("debate", "critique")
    workflow.add_edge("critique", "verification")
    workflow.add_edge("verification", "synthesis")
    workflow.add_edge("synthesis", END)
    
    return workflow.compile()


def create_intelligence_graph() -> StateGraph:
    """
    Create the LangGraph workflow with parallel scenario analysis.
    
    Supports two execution paths:
    1. Parallel path: Multiple scenarios across GPUs 0-5 → meta-synthesis
    2. Single path: Traditional sequential analysis → regular synthesis
    
    Both paths terminate at END (Bug Fix #2 - complete backward compatibility).
    """

    workflow = StateGraph(IntelligenceState)

    # === Core nodes ===
    workflow.add_node("classifier", classify_query_node)
    workflow.add_node("extraction", data_extraction_node)
    workflow.add_node("scenario_gen", scenario_generation_node)
    
    # === Parallel path nodes ===
    workflow.add_node("parallel_exec", parallel_execution_node)
    workflow.add_node("aggregate_scenarios", aggregate_scenarios_for_debate_node)
    workflow.add_node("meta_synthesis", meta_synthesis_wrapper)
    
    # === Single path nodes ===
    workflow.add_node("financial", financial_agent_node)
    workflow.add_node("market", market_agent_node)
    workflow.add_node("operations", operations_agent_node)
    workflow.add_node("research", research_agent_node)
    workflow.add_node("debate", legendary_debate_node)
    workflow.add_node("critique", critique_node)
    workflow.add_node("verification", verification_node)
    workflow.add_node("synthesis", ministerial_synthesis_node)

    # === Entry point ===
    workflow.set_entry_point("classifier")
    
    # === Main flow ===
    workflow.add_edge("classifier", "extraction")
    
    # === Conditional routing based on complexity ===
    # Simple queries skip agents and go directly to synthesis
    # Medium/Complex queries go through scenario generation
    workflow.add_conditional_edges(
        "extraction",
        lambda state: "simple" if state.get("complexity") == "simple" else "scenario_gen",
        {
            "simple": "synthesis",       # Fast path for simple queries
            "scenario_gen": "scenario_gen"  # Full analysis path
        }
    )
    
    # === Conditional routing after scenario generation ===
    # If scenarios generated → parallel path
    # If no scenarios → single path
    workflow.add_conditional_edges(
        "scenario_gen",
        lambda state: "parallel" if state.get('scenarios') else "single",
        {
            "parallel": "parallel_exec",  # Parallel scenario analysis
            "single": "financial"         # Traditional single analysis
        }
    )
    
    # === PARALLEL PATH (Fixed: Run all stages after parallel scenarios) ===
    # After parallel scenarios complete:
    # 1. Aggregate scenario results for main debate
    # 2. Run main debate across all scenarios
    # 3. Run critique, verification
    # 4. Final meta-synthesis combines everything
    workflow.add_edge("parallel_exec", "aggregate_scenarios")
    workflow.add_edge("aggregate_scenarios", "debate")  # Main debate on scenario results
    workflow.add_edge("debate", "critique")
    workflow.add_edge("critique", "verification")
    workflow.add_edge("verification", "meta_synthesis")  # Meta-synthesis combines everything
    workflow.add_edge("meta_synthesis", END)
    
    # === SINGLE PATH (Bug Fix #2 - complete path to END) ===
    workflow.add_edge("financial", "market")
    workflow.add_edge("market", "operations")
    workflow.add_edge("operations", "research")
    workflow.add_edge("research", "debate")
    workflow.add_edge("debate", "critique")
    workflow.add_edge("critique", "verification")
    workflow.add_edge("verification", "synthesis")
    workflow.add_edge("synthesis", END)  # Single path terminates here
    
    logger.info("✅ Intelligence graph compiled with parallel and single paths")

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
        "debate_results": None,
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
        # Parallel scenario fields
        "enable_parallel_scenarios": True,  # Enable by default
        "scenarios": None,
        "scenario_results": None,
        "scenario_name": None,
        "scenario_metadata": None,
    }

    graph = create_intelligence_graph()

    start_time = datetime.now()
    result = await graph.ainvoke(initial_state)
    result["execution_time"] = (datetime.now() - start_time).total_seconds()

    return result

