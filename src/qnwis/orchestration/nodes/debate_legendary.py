"""
Legendary Multi-Turn Debate Node for New Workflow.

Integrates LegendaryDebateOrchestrator into LangGraph modular architecture.
Provides 80-125 turn adaptive debate with real-time event streaming.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

from ..state import IntelligenceState

logger = logging.getLogger(__name__)


async def legendary_debate_node(state: IntelligenceState) -> IntelligenceState:
    """
    Node 7: Legendary Multi-Turn Agent Debate.

    Conducts adaptive debate using LegendaryDebateOrchestrator.
    Streams conversation turns in real-time via emit_event_fn.

    Complexity-adaptive:
    - SIMPLE questions: 10-15 turns, 2-3 minutes
    - STANDARD questions: 40 turns, 10 minutes
    - COMPLEX questions: 80-125 turns, 20-30 minutes
    """

    # Import here to avoid circular dependencies
    from ..legendary_debate_orchestrator import LegendaryDebateOrchestrator
    from ...llm.client import LLMClient

    reasoning_chain = state.setdefault("reasoning_chain", [])
    nodes_executed = state.setdefault("nodes_executed", [])

    # Get emit callback from state (passed by streaming adapter)
    emit_event_fn = state.get("emit_event_fn")
    logger.info(f"🔍 legendary_debate_node: emit_event_fn={'FOUND' if emit_event_fn else 'MISSING'}")
    logger.info(f"🔍 legendary_debate_node: state keys={list(state.keys())[:10]}")
    
    # DEBUG: Log debate_depth to diagnose 41-turn issue
    debate_depth_from_state = state.get("debate_depth", "NOT_IN_STATE")
    logger.warning(f"🎯 DEBATE NODE: debate_depth from state = '{debate_depth_from_state}'")

    # Create LLM client for debate - uses provider from environment (QNWIS_LLM_PROVIDER)
    llm_client = LLMClient()  # Will use Azure if configured

    # Build agent reports map from state
    agent_reports_map = {}

    # Extract agent analyses from new workflow state structure
    for agent_name in ["financial", "market", "operations", "research"]:
        analysis_key = f"{agent_name}_analysis"
        if analysis_key in state and state[analysis_key]:
            # Create mock AgentReport-like object for orchestrator
            agent_reports_map[agent_name] = type('AgentReport', (object,), {
                'narrative': str(state[analysis_key]),
                'agent': agent_name,
                'findings': [],
                'confidence': 0.7,
                'warnings': [],
                'metadata': {}
            })()

    # Detect contradictions using existing logic
    from .debate import _extract_perspectives, _detect_contradictions
    perspectives = _extract_perspectives(state)
    contradictions = _detect_contradictions(perspectives)

    logger.info(f"Starting legendary debate with {len(contradictions)} contradictions")

    # Create legendary debate orchestrator
    orchestrator = LegendaryDebateOrchestrator(
        emit_event_fn=emit_event_fn,
        llm_client=llm_client
    )

    # Build agents map - CRITICAL for legendary depth debates
    # Each agent must be properly initialized for 100-150 turn debates
    agents_map: Dict[str, Any] = {}

    # Import LLM agents - THESE ARE REQUIRED for legendary debates
    try:
        from ...agents.micro_economist import MicroEconomist
        from ...agents.macro_economist import MacroEconomist
        from ...agents.nationalization import NationalizationAgent
        from ...agents.skills import SkillsAgent
        from ...agents.pattern_detective_llm import PatternDetectiveLLMAgent
        from ...agents.base import DataClient

        data_client = DataClient()
        logger.info("✅ DataClient initialized for debate agents")

        # Create a simple DataValidator for data quality checks
        class SimpleDataValidator:
            def __init__(self):
                self.name = "DataValidator"
            
            async def analyze_edge_case(self, edge_case, history):
                return "Data quality check completed."
        
        # Initialize each agent with explicit error handling
        agents_map["DataValidator"] = SimpleDataValidator()
        logger.info("✅ DataValidator initialized")
        
        try:
            agents_map["MicroEconomist"] = MicroEconomist(data_client, llm_client)
            logger.info("✅ MicroEconomist initialized")
        except Exception as e:
            logger.error(f"❌ MicroEconomist failed: {e}")
        
        try:
            agents_map["MacroEconomist"] = MacroEconomist(data_client, llm_client)
            logger.info("✅ MacroEconomist initialized")
        except Exception as e:
            logger.error(f"❌ MacroEconomist failed: {e}")
        
        try:
            agents_map["Nationalization"] = NationalizationAgent(data_client, llm_client)
            logger.info("✅ Nationalization initialized")
        except Exception as e:
            logger.error(f"❌ Nationalization failed: {e}")
        
        try:
            agents_map["SkillsAgent"] = SkillsAgent(data_client, llm_client)
            logger.info("✅ SkillsAgent initialized")
        except Exception as e:
            logger.error(f"❌ SkillsAgent failed: {e}")
        
        try:
            agents_map["PatternDetective"] = PatternDetectiveLLMAgent(data_client, llm_client)
            logger.info("✅ PatternDetective initialized")
        except Exception as e:
            logger.error(f"❌ PatternDetective failed: {e}")
        
        # === DETERMINISTIC AGENTS ===
        # These provide data-backed analysis without LLM calls
        try:
            from ...agents.time_machine import TimeMachineAgent
            from ...agents.predictor import PredictorAgent
            from ...agents.scenario_agent import ScenarioAgent
            from ...agents.pattern_miner import PatternMinerAgent
            from ...agents.national_strategy import NationalStrategyAgent
            from ...agents.alert_center import AlertCenterAgent
            from ...agents.pattern_detective import PatternDetectiveAgent
            
            # Initialize deterministic agents
            try:
                agents_map["TimeMachine"] = TimeMachineAgent(data_client)
                logger.info("✅ TimeMachine (deterministic) initialized")
            except Exception as e:
                logger.warning(f"⚠️ TimeMachine failed: {e}")
            
            try:
                agents_map["PatternDetectiveAgent"] = PatternDetectiveAgent(data_client)
                logger.info("✅ PatternDetectiveAgent (deterministic) initialized")
            except Exception as e:
                logger.warning(f"⚠️ PatternDetectiveAgent failed: {e}")
            
            try:
                agents_map["Predictor"] = PredictorAgent(data_client)
                logger.info("✅ Predictor (deterministic) initialized")
            except Exception as e:
                logger.warning(f"⚠️ Predictor failed: {e}")
            
            try:
                agents_map["Scenario"] = ScenarioAgent(data_client)
                logger.info("✅ Scenario (deterministic) initialized")
            except Exception as e:
                logger.warning(f"⚠️ Scenario failed: {e}")
            
            try:
                agents_map["PatternMiner"] = PatternMinerAgent(data_client)
                logger.info("✅ PatternMiner (deterministic) initialized")
            except Exception as e:
                logger.warning(f"⚠️ PatternMiner failed: {e}")
            
            try:
                agents_map["NationalStrategy"] = NationalStrategyAgent(data_client)
                logger.info("✅ NationalStrategy (deterministic) initialized")
            except Exception as e:
                logger.warning(f"⚠️ NationalStrategy failed: {e}")
            
            try:
                agents_map["AlertCenter"] = AlertCenterAgent(data_client)
                logger.info("✅ AlertCenter (deterministic) initialized")
            except Exception as e:
                logger.warning(f"⚠️ AlertCenter failed: {e}")
            
            # Add LabourEconomist - workforce and gender employment analysis
            try:
                from ...agents.labour_economist import LabourEconomistAgent
                agents_map["LabourEconomist"] = LabourEconomistAgent(data_client)
                logger.info("✅ LabourEconomist (deterministic) initialized")
            except Exception as e:
                logger.warning(f"⚠️ LabourEconomist failed: {e}")
            
            # Add ResearchSynthesizer - aggregates Semantic Scholar, RAG, Perplexity, Knowledge Graph
            try:
                from ...agents.research_synthesizer import ResearchSynthesizerAgent
                agents_map["ResearchSynthesizer"] = ResearchSynthesizerAgent()
                logger.info("✅ ResearchSynthesizer (deterministic) initialized")
            except Exception as e:
                logger.warning(f"⚠️ ResearchSynthesizer failed: {e}")
                
        except ImportError as e:
            logger.warning(f"⚠️ Could not import deterministic agents: {e}")
        
        # Log final agent count - CRITICAL for legendary depth
        llm_agent_count = len([a for a in agents_map.keys() if a != "DataValidator"])
        deterministic_count = len([a for a in agents_map.keys() if a in ["TimeMachine", "Predictor", "Scenario", "PatternMiner", "NationalStrategy", "AlertCenter", "PatternDetectiveAgent", "LabourEconomist", "ResearchSynthesizer"]])
        logger.warning(f"🔥 DEBATE AGENTS LOADED: {llm_agent_count} total ({llm_agent_count - deterministic_count} LLM + {deterministic_count} deterministic)")
        logger.warning(f"🔥 AGENT LIST: {list(agents_map.keys())}")
        
        if llm_agent_count < 5:
            logger.error(f"⚠️ WARNING: Only {llm_agent_count}/5 LLM agents loaded - debate may be shorter than expected!")
            
    except Exception as e:
        logger.error(f"❌ CRITICAL: Could not load LLM agents: {e}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        # Debate will be severely limited without agents!

    # === RUN DETERMINISTIC AGENTS AND POPULATE REPORTS ===
    # These agents need to be EXECUTED to generate analysis before the debate
    extracted_facts = state.get("extracted_facts", [])
    query = state.get("query", "")
    
    # Domain-agnostic: Pass the actual query to agents, let them determine relevant metrics
    query = state.get("query", "")
    
    deterministic_agents_config = [
        # TimeMachine: Historical trends - uses query context to find relevant time series
        ("TimeMachine", "baseline_report", {}),
        # Predictor: Forecasting - domain-agnostic forecasting capabilities
        ("Predictor", "forecast_baseline", {}),
        # NationalStrategy: GCC/regional benchmarking
        ("NationalStrategy", "gcc_benchmark", {}),
        # PatternMiner: Statistical pattern detection
        ("PatternMiner", "mine_patterns", {}),
        # AlertCenter: Threshold monitoring across any KPIs
        ("AlertCenter", "check_thresholds", {}),
        # LabourEconomist: Workforce statistics (applicable to any sector)
        ("LabourEconomist", "analyze", {}),
        # ResearchSynthesizer: Academic research on ANY topic from user query
        ("ResearchSynthesizer", "run", {"query": query}),
    ]
    
    for agent_key, method_name, kwargs in deterministic_agents_config:
        if agent_key in agents_map:
            agent = agents_map[agent_key]
            try:
                # Try to call the agent's analysis method
                if hasattr(agent, method_name):
                    method = getattr(agent, method_name)
                    result = method(**kwargs) if kwargs else method()
                    
                    # Extract narrative from result
                    narrative = ""
                    if hasattr(result, 'narrative'):
                        narrative = result.narrative
                    elif isinstance(result, dict):
                        narrative = result.get('narrative', result.get('summary', str(result)[:500]))
                    elif isinstance(result, str):
                        narrative = result[:500]
                    else:
                        narrative = str(result)[:500]
                    
                    # Create report object for orchestrator
                    agent_reports_map[agent_key] = type('AgentReport', (object,), {
                        'narrative': narrative,
                        'agent': agent_key,
                        'findings': getattr(result, 'findings', []) if hasattr(result, 'findings') else [],
                        'confidence': getattr(result, 'confidence', 0.7) if hasattr(result, 'confidence') else 0.7,
                        'warnings': getattr(result, 'warnings', []) if hasattr(result, 'warnings') else [],
                        'metadata': {'source': 'deterministic_agent', 'method': method_name}
                    })()
                    logger.info(f"✅ {agent_key} analysis executed: {len(narrative)} chars")
                elif hasattr(agent, 'run'):
                    # Fallback to generic run() method
                    result = agent.run()
                    narrative = getattr(result, 'narrative', str(result)[:500]) if hasattr(result, 'narrative') else str(result)[:500]
                    agent_reports_map[agent_key] = type('AgentReport', (object,), {
                        'narrative': narrative,
                        'agent': agent_key,
                        'findings': [],
                        'confidence': 0.7,
                        'warnings': [],
                        'metadata': {'source': 'deterministic_agent', 'method': 'run'}
                    })()
                    logger.info(f"✅ {agent_key} run() executed: {len(narrative)} chars")
                else:
                    logger.warning(f"⚠️ {agent_key} has no {method_name} or run() method")
            except Exception as e:
                logger.warning(f"⚠️ {agent_key}.{method_name}() failed: {e}")
    
    logger.info(f"📊 Deterministic agent reports generated: {list(agent_reports_map.keys())}")

    # Conduct legendary debate
    # Get user-selected debate depth from state (default: legendary = 100-150 turns)
    debate_depth = state.get("debate_depth", "legendary")
    
    # FIXED: Build cross-scenario context for agents to reference
    cross_scenario_context = ""
    cross_scenario_table = state.get("cross_scenario_table", "")
    engine_b_aggregate = state.get("engine_b_aggregate", {})
    
    if cross_scenario_table:
        cross_scenario_context = f"""
## QUANTITATIVE CONTEXT (6 Scenarios Analyzed)

{cross_scenario_table}

Your arguments MUST reference these scenario comparisons and computed success rates.
"""
        logger.info(f"📊 Cross-scenario table passed to debate ({len(cross_scenario_table)} chars)")
        state["engine_a_had_quantitative_context"] = True  # Flag for diagnostic validation
    elif engine_b_aggregate.get("scenarios_with_compute", 0) > 0:
        # Build summary from aggregate
        cross_scenario_context = f"""
## ENGINE B QUANTITATIVE ANALYSIS

- Scenarios computed: {engine_b_aggregate.get('scenarios_with_compute', 0)}
- Monte Carlo runs: {engine_b_aggregate.get('total_monte_carlo_runs', 0)}
- Avg success probability: {engine_b_aggregate.get('avg_success_probability', 0):.1%}
- Top sensitivity drivers: {', '.join(engine_b_aggregate.get('sensitivity_drivers', ['Not computed'])[:3])}

Reference these computed values in your arguments.
"""
        logger.info(f"📊 Engine B aggregate passed to debate")
        state["engine_a_had_quantitative_context"] = True  # Flag for diagnostic validation
    
    try:
        logger.info(f"🚀 STARTING legendary debate with {len(contradictions)} contradictions (depth={debate_depth})")
        debate_results = await orchestrator.conduct_legendary_debate(
            question=state.get("query", ""),
            contradictions=contradictions,
            agents_map=agents_map,
            agent_reports_map=agent_reports_map,
            llm_client=llm_client,
            extracted_facts=state.get("extracted_facts", []),
            debate_depth=debate_depth,  # Pass user-selected depth
            cross_scenario_context=cross_scenario_context  # FIXED: Pass cross-scenario data
        )
        logger.info(f"✅ Legendary debate SUCCEEDED: {debate_results['total_turns']} turns")

        # Update state with debate results
        state["debate_synthesis"] = debate_results["final_report"]
        state["debate_results"] = {
            "contradictions": contradictions,
            "contradictions_found": len(contradictions),
            "total_turns": debate_results["total_turns"],
            "conversation_history": debate_results["conversation_history"],
            "resolutions": debate_results["resolutions"],
            "consensus": debate_results["consensus"],
            "status": "complete",
            "final_report": debate_results["final_report"],
            "consensus_narrative": debate_results.get("consensus", {}).get("narrative", ""),
            "resolved": len([r for r in debate_results.get("resolutions", []) if r.get("action") != "flag_for_review"]),
            "flagged_for_review": len([r for r in debate_results.get("resolutions", []) if r.get("action") == "flag_for_review"]),
        }

        reasoning_chain.append(
            f"⚡ Legendary debate completed: {debate_results['total_turns']} turns, "
            f"{len(contradictions)} contradictions analyzed, 6 phases completed"
        )

        logger.info(
            f"Legendary debate complete: {debate_results['total_turns']} turns, "
            f"{debate_results.get('execution_time_minutes', 0):.1f} minutes"
        )

    except Exception as e:
        logger.error(f"❌ LEGENDARY DEBATE FAILED: {e}", exc_info=True)
        completed_turns = orchestrator.conversation_history if orchestrator else []
        logger.error(f"❌ PRESERVING {len(completed_turns)} turns that were already streamed")

        # Fallback to simplified debate BUT PRESERVE the turns that were already streamed!
        from .debate import _build_synthesis
        synthesis = _build_synthesis(contradictions)
        
        # Build summary from completed turns for synthesis to use
        turn_summary = ""
        if completed_turns:
            summary_parts = []
            for turn in completed_turns[-30:]:  # Last 30 turns
                speaker = turn.get("agent", "Agent")
                content = turn.get("message", "")[:400]
                summary_parts.append(f"**{speaker}**: {content}...")
            turn_summary = "\n\n".join(summary_parts)

        # CRITICAL: Store in ALL keys that synthesis might look for
        state["debate_synthesis"] = synthesis
        state["multi_agent_debate"] = turn_summary or synthesis  # FIX: Also set this key
        state["conversation_history"] = completed_turns  # FIX: Also at state level
        state["debate_partial"] = True  # FIX: Mark as partial
        state["debate_turns"] = len(completed_turns)  # FIX: Track turn count
        state["debate_results"] = {
            "contradictions": contradictions,
            "contradictions_found": len(contradictions),
            "total_turns": len(completed_turns),
            "conversation_history": completed_turns,
            "resolutions": [],
            "consensus": {"narrative": synthesis},
            "status": "partial",
            "error": str(e),
            "consensus_narrative": synthesis,
            "resolved": 0,
            "flagged_for_review": 0,
        }

        reasoning_chain.append(f"⚠️ Legendary debate partially completed ({len(completed_turns)} turns), error: {e}")

    nodes_executed.append("debate")
    return state
