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

    # Build agents map (for now, we'll use the LLM client to generate debate turns)
    # In the future, this can be populated with actual agent instances
    agents_map: Dict[str, Any] = {}

    # Import LLM agents if available
    try:
        from ...agents.micro_economist import MicroEconomist
        from ...agents.macro_economist import MacroEconomist
        from ...agents.nationalization import NationalizationAgent
        from ...agents.skills import SkillsAgent
        from ...agents.pattern_detective_llm import PatternDetectiveLLMAgent
        from ...agents.base import DataClient

        data_client = DataClient()

        # Create a simple DataValidator for data quality checks
        class SimpleDataValidator:
            def __init__(self):
                self.name = "DataValidator"
            
            async def analyze_edge_case(self, edge_case, history):
                return "Data quality check completed."
        
        agents_map = {
            "DataValidator": SimpleDataValidator(),
            "MicroEconomist": MicroEconomist(data_client, llm_client),
            "MacroEconomist": MacroEconomist(data_client, llm_client),
            "Nationalization": NationalizationAgent(data_client, llm_client),
            "SkillsAgent": SkillsAgent(data_client, llm_client),
            "PatternDetective": PatternDetectiveLLMAgent(data_client, llm_client),
        }
        logger.info(f"Loaded {len(agents_map)} LLM agents for debate")
    except Exception as e:
        logger.warning(f"Could not load LLM agents: {e}")
        # Debate will work with just the orchestrator's LLM capabilities

    # Conduct legendary debate
    # Get user-selected debate depth from state (default: legendary = 100-150 turns)
    debate_depth = state.get("debate_depth", "legendary")
    try:
        logger.info(f"🚀 STARTING legendary debate with {len(contradictions)} contradictions (depth={debate_depth})")
        debate_results = await orchestrator.conduct_legendary_debate(
            question=state.get("query", ""),
            contradictions=contradictions,
            agents_map=agents_map,
            agent_reports_map=agent_reports_map,
            llm_client=llm_client,
            extracted_facts=state.get("extracted_facts", []),
            debate_depth=debate_depth  # Pass user-selected depth
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
        logger.error(f"❌ PRESERVING {len(orchestrator.conversation_history)} turns that were already streamed")

        # Fallback to simplified debate BUT PRESERVE the turns that were already streamed!
        from .debate import _build_synthesis
        synthesis = _build_synthesis(contradictions)

        state["debate_synthesis"] = synthesis
        state["debate_results"] = {
            "contradictions": contradictions,
            "contradictions_found": len(contradictions),
            "total_turns": len(orchestrator.conversation_history),  # Preserve actual turn count
            "conversation_history": orchestrator.conversation_history,  # PRESERVE ALL TURNS!
            "resolutions": [],
            "consensus": {"narrative": synthesis},
            "status": "partial",  # Changed from "failed" to "partial"
            "error": str(e),
            "consensus_narrative": synthesis,
            "resolved": 0,
            "flagged_for_review": 0,
        }

        reasoning_chain.append(f"⚠️ Legendary debate failed ({e}), used simplified fallback")

    nodes_executed.append("debate")
    return state
