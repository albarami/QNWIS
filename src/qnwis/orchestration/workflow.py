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
    feasibility_gate_node,
    arithmetic_validator_node,
)
# Import legendary debate node instead of simplified debate
from .nodes.debate_legendary import legendary_debate_node
# Import legendary synthesis for consultant-killing output
from .nodes.synthesis_legendary import legendary_synthesis_node_sync as legendary_synthesis_node
from .nodes.synthesis_strategic import strategic_synthesis_node
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
    # CRITICAL DEBUG
    logger.warning(f"🔍 scenario_generation_node: enable_parallel_scenarios = {state.get('enable_parallel_scenarios')}")
    logger.warning(f"🔍 scenario_generation_node: complexity = {state.get('complexity')}")
    logger.warning(f"🔍 scenario_generation_node: query length = {len(state.get('query', ''))}")
    
    # Check if parallel scenarios are enabled - ALWAYS default to True for complex queries
    enable_parallel = state.get('enable_parallel_scenarios')
    if enable_parallel is None:
        enable_parallel = True  # Default to True if not set
        logger.warning("🔧 enable_parallel_scenarios was None, defaulting to True")
    
    if not enable_parallel:
        logger.info("Parallel scenarios disabled, using single analysis path")
        state['scenarios'] = None
        return state
    
    # MINISTER-GRADE: ALL queries get full analysis
    # NO QUERY IS "SIMPLE" FOR MINISTERIAL INTELLIGENCE
    complexity = state.get('complexity', 'medium')
    # REMOVED: Skip logic for simple queries
    # ALL queries go through full parallel scenario analysis
    logger.info(f"Query complexity: {complexity} - proceeding with FULL analysis (minister-grade)")
    
    try:
        logger.info("🚀 Generating scenarios for parallel analysis...")
        generator = ScenarioGenerator()
        
        # Await async scenario generation
        query = state.get('query', '')
        facts = state.get('extracted_facts', [])
        
        if not query:
            raise ValueError("No query provided for scenario generation")
        
        logger.info(f"📝 Query for scenarios: {query[:100]}...")
        logger.info(f"📊 Facts count: {len(facts) if isinstance(facts, list) else 'dict format'}")
        
        scenarios = await generator.generate_scenarios(
            query=query,
            extracted_facts=facts
        )
        
        if scenarios and len(scenarios) >= 4:
            state['scenarios'] = scenarios
            state['reasoning_chain'].append(
                f"🎯 Generated {len(scenarios)} scenarios for parallel GPU analysis"
            )
            logger.info(f"✅ Scenarios: {[s.get('name', 'Unknown') for s in scenarios]}")
            return state
        else:
            raise ValueError(f"Insufficient scenarios generated: {len(scenarios) if scenarios else 0}")
        
    except Exception as e:
        error_msg = f"{type(e).__name__}: {e}"
        logger.error(f"❌ Scenario generation failed: {error_msg}", exc_info=True)
        
        # Create intelligent default scenarios based on query keywords
        query_lower = state.get('query', '').lower()
        
        if any(kw in query_lower for kw in ['qatarization', 'workforce', 'labor', 'employment']):
            default_scenarios = [
                {"id": "base", "name": "Base Case", "description": "Current Qatarization trajectory continues with gradual private sector improvement", "probability": 0.35, "modified_assumptions": {"qatarization_rate": "steady"}},
                {"id": "acceleration", "name": "Policy Acceleration", "description": "Government mandates stricter quotas, faster enforcement", "probability": 0.25, "modified_assumptions": {"policy_intensity": "high"}},
                {"id": "skills_gap", "name": "Skills Gap Crisis", "description": "Private sector demand outpaces Qatari skill development", "probability": 0.20, "modified_assumptions": {"skills_mismatch": "severe"}},
                {"id": "competition", "name": "GCC Competition", "description": "Saudi/UAE offer better packages, causing talent drain", "probability": 0.20, "modified_assumptions": {"regional_competition": "intense"}},
            ]
        elif any(kw in query_lower for kw in ['oil', 'energy', 'gas', 'lng']):
            default_scenarios = [
                {"id": "base", "name": "Stable Prices", "description": "Oil at $70-80/barrel, steady LNG demand", "probability": 0.35, "modified_assumptions": {"oil_price": 75}},
                {"id": "price_crash", "name": "Price Collapse", "description": "Sustained prices below $50, fiscal pressure", "probability": 0.20, "modified_assumptions": {"oil_price": 45}},
                {"id": "lng_boom", "name": "LNG Demand Surge", "description": "Asian energy transition drives LNG premium", "probability": 0.25, "modified_assumptions": {"lng_premium": "high"}},
                {"id": "transition", "name": "Energy Transition", "description": "Accelerated global shift reduces hydrocarbon demand", "probability": 0.20, "modified_assumptions": {"transition_speed": "fast"}},
            ]
        else:
            default_scenarios = [
                {"id": "base", "name": "Base Case", "description": "Current trends continue with moderate growth", "probability": 0.35, "modified_assumptions": {"growth_rate": 0.03}},
                {"id": "optimistic", "name": "Optimistic", "description": "Favorable conditions drive accelerated progress", "probability": 0.25, "modified_assumptions": {"growth_rate": 0.05}},
                {"id": "pessimistic", "name": "Pessimistic", "description": "External shocks create headwinds", "probability": 0.20, "modified_assumptions": {"growth_rate": 0.01}},
                {"id": "disruption", "name": "Disruption", "description": "Major structural change reshapes landscape", "probability": 0.20, "modified_assumptions": {"disruption_level": "high"}},
            ]
        
        state['scenarios'] = default_scenarios
        state['warnings'].append(f"Scenario generation error ({error_msg}) - using context-aware defaults")
        state['reasoning_chain'].append(
            f"⚠️ Used default scenarios due to generation error: {error_msg}"
        )
        logger.warning(f"✅ Fallback: Using {len(default_scenarios)} context-aware default scenarios")
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
    
    CRITICAL: This node populates agent_reports which critique and synthesis need.
    After parallel execution, prepares state for cross-scenario debate
    by converting scenario results into agent analyses format.
    """
    scenario_results = state.get('scenario_results', [])
    if not scenario_results:
        logger.warning("⚠️ No scenario results to aggregate - critique will have no data!")
        return state
    
    logger.info(f"🔄 Aggregating {len(scenario_results)} scenario results for main debate...")
    
    # Initialize agent_reports
    agent_reports = []
    
    # Also aggregate extracted facts from all scenarios
    all_facts = state.get('extracted_facts', [])
    
    # Create agent reports from scenario results
    # Each scenario's analysis becomes an "agent" position for the main debate
    for i, result in enumerate(scenario_results):
        scenario_name = result.get('scenario_name', f'Scenario {i+1}')
        
        # Get synthesis - try multiple field names
        synthesis = (
            result.get('final_synthesis') or 
            result.get('synthesis') or 
            result.get('meta_synthesis') or
            f"Analysis for {scenario_name} completed"
        )
        
        confidence = result.get('confidence_score', result.get('confidence', 0.7))
        
        # CRITICAL: Extract internal agent reports from scenario
        # These contain the actual agent analyses that critique needs
        scenario_agent_reports = result.get('agent_reports', [])
        if scenario_agent_reports:
            for sar in scenario_agent_reports:
                if isinstance(sar, dict) and sar.get('report'):
                    # Add scenario context to each report
                    sar_copy = dict(sar)
                    if isinstance(sar_copy.get('report'), dict):
                        sar_copy['report']['scenario'] = scenario_name
                    agent_reports.append(sar_copy)
                    logger.debug(f"  Added agent report: {sar.get('agent')}")
        
        # Also extract individual agent analyses from scenario state
        for agent_type in ['financial', 'market', 'operations', 'research']:
            analysis_key = f'{agent_type}_analysis'
            if result.get(analysis_key):
                analysis = result[analysis_key]
                agent_reports.append({
                    "agent": f"{agent_type}_{scenario_name.replace(' ', '_')}",
                    "report": {
                        "narrative": str(analysis)[:2000] if analysis else "",
                        "confidence": float(confidence) if confidence else 0.7,
                        "scenario_name": scenario_name,
                    }
                })
        
        # Create a scenario-level synthesis report
        if synthesis and len(synthesis) > 50:  # Only if meaningful synthesis
            agent_report = {
                "agent": f"Scenario_{scenario_name.replace(' ', '_')}",
                "report": {
                    "narrative": synthesis[:2000],
                    "confidence": float(confidence) if confidence else 0.7,
                    "scenario_name": scenario_name,
                    "data_gaps": result.get('warnings', []),
                    "assumptions": result.get('scenario_metadata', {}).get('modified_assumptions', {}),
                }
            }
            agent_reports.append(agent_report)
        
        # Populate agent analysis fields for debate nodes (first 4 scenarios)
        agent_fields = ['financial_analysis', 'market_analysis', 'operations_analysis', 'research_analysis']
        if i < len(agent_fields):
            state[agent_fields[i]] = f"[{scenario_name}] {synthesis[:1500] if synthesis else 'Analysis complete'}"
        
        # Aggregate facts from scenarios
        scenario_facts = result.get('extracted_facts', [])
        if scenario_facts:
            all_facts.extend(scenario_facts)
        
        logger.info(f"  📊 {scenario_name}: {len(synthesis) if synthesis else 0} chars, {len(result.get('agent_reports', []))} internal reports")
    
    # Store aggregated data
    state['agent_reports'] = agent_reports
    state['extracted_facts'] = all_facts
    
    # Store all scenario syntheses for debate context
    state['scenario_syntheses'] = [
        {
            'name': r.get('scenario_name', f'Scenario {i+1}'),
            'synthesis': r.get('final_synthesis') or r.get('synthesis') or ''
        }
        for i, r in enumerate(scenario_results)
    ]
    
    # Aggregate debate conversation history from all scenarios
    all_conversation_history = state.get('conversation_history', [])
    total_debate_turns = 0
    total_challenges = 0
    total_consensus = 0
    
    for i, result in enumerate(scenario_results):
        scenario_name = result.get('scenario_name', f'Scenario {i+1}')
        
        # Collect conversation history
        scenario_history = result.get('conversation_history', [])
        for msg in scenario_history:
            if isinstance(msg, dict):
                msg['scenario'] = scenario_name
                all_conversation_history.append(msg)
        
        # Collect debate statistics
        scenario_debate = result.get('debate_results', {})
        if scenario_debate:
            total_debate_turns += scenario_debate.get('total_turns', 0)
            total_challenges += len(scenario_debate.get('challenges', []))
            total_consensus += len([r for r in scenario_debate.get('resolutions', []) if r.get('consensus_reached')])
    
    state['conversation_history'] = all_conversation_history
    
    # Store aggregate debate statistics for synthesis to use
    state['aggregate_debate_stats'] = {
        'total_turns': total_debate_turns,
        'total_challenges': total_challenges,
        'total_consensus': total_consensus,
        'scenarios_analyzed': len(scenario_results)
    }
    
    # Calculate data quality score from scenarios
    confidences = [r.get('confidence_score', r.get('confidence', 0.7)) for r in scenario_results]
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.7
    state['data_quality_score'] = avg_confidence
    state['confidence_score'] = avg_confidence  # Also set main confidence score
    
    state['reasoning_chain'].append(
        f"✅ Aggregated {len(scenario_results)} scenarios: {len(agent_reports)} agent reports, "
        f"{len(all_facts)} facts, {total_debate_turns} debate turns"
    )
    
    logger.info(
        f"✅ Aggregation complete: {len(agent_reports)} agent reports, "
        f"{len(all_facts)} facts, {total_debate_turns} debate turns, "
        f"{total_challenges} challenges, {total_consensus} consensus points"
    )
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
    workflow.add_node("synthesis", legendary_synthesis_node)
    
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
    workflow.add_node("feasibility_gate", feasibility_gate_node)  # FIRST-PRINCIPLES CHECK
    workflow.add_node("extraction", data_extraction_node)
    workflow.add_node("scenario_gen", scenario_generation_node)
    
    # === Parallel path nodes ===
    workflow.add_node("parallel_exec", parallel_execution_node)
    workflow.add_node("aggregate_scenarios", aggregate_scenarios_for_debate_node)
    workflow.add_node("arithmetic_validator", arithmetic_validator_node)  # POST-DEBATE CHECK
    workflow.add_node("meta_synthesis", meta_synthesis_wrapper)
    
    # === Single path nodes ===
    workflow.add_node("financial", financial_agent_node)
    workflow.add_node("market", market_agent_node)
    workflow.add_node("operations", operations_agent_node)
    workflow.add_node("research", research_agent_node)
    workflow.add_node("debate", legendary_debate_node)
    workflow.add_node("critique", critique_node)
    workflow.add_node("verification", verification_node)
    workflow.add_node("synthesis", legendary_synthesis_node)

    # === Entry point ===
    workflow.set_entry_point("classifier")
    
    # === Main flow with FEASIBILITY GATE ===
    workflow.add_edge("classifier", "feasibility_gate")  # Check arithmetic FIRST
    
    # Route based on feasibility: infeasible targets go straight to synthesis with explanation
    workflow.add_conditional_edges(
        "feasibility_gate",
        lambda state: "infeasible" if state.get("target_infeasible") else "feasible",
        {
            "infeasible": "synthesis",  # Short-circuit: explain why impossible
            "feasible": "extraction"     # Continue normal flow
        }
    )
    
    # === MINISTER-GRADE: ALL QUERIES GET FULL ANALYSIS ===
    # NO SHORTCUTS - Every query goes through scenario generation and agents
    # The "simple" path is REMOVED - ministers expect thorough analysis
    workflow.add_edge("extraction", "scenario_gen")  # Direct edge - no conditions
    
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
    # 3. ARITHMETIC VALIDATION - catch impossible conclusions
    # 4. Run critique, verification
    # 5. Final meta-synthesis combines everything
    workflow.add_edge("parallel_exec", "aggregate_scenarios")
    workflow.add_edge("aggregate_scenarios", "debate")  # Main debate on scenario results
    workflow.add_edge("debate", "arithmetic_validator")  # VALIDATE MATH AFTER DEBATE
    workflow.add_edge("arithmetic_validator", "critique")
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

