"""
Intelligent Agent Selection for QNWIS (H6).

Routes questions to relevant agents based on classification to:
- Reduce API costs (run 2-3 agents instead of 5)
- Improve response time (fewer agents = faster)
- Enhance quality (only relevant experts)

Ministry-grade implementation with comprehensive agent-intent mapping.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Set

logger = logging.getLogger(__name__)


def classify_data_availability(query: str, extracted_facts: List[Dict] | None = None) -> List[str]:
    """
    Determine what types of data we have available for this query.
    """
    available_types = []
    facts = extracted_facts or []
    
    # Check for time series data
    if any("time_series" in str(fact.get("type", fact.get("data_type", ""))) for fact in facts):
        available_types.append("time_series_employment")
    
    # Check for historical trends
    if any("historical" in str(fact.get("type", fact.get("data_type", ""))) for fact in facts):
        available_types.append("historical_trends")
    
    # Check for sector-specific data
    if any("sector" in str(fact.get("category", fact.get("data_type", ""))) for fact in facts):
        available_types.append("sector_metrics")
    
    # Check for labor market data
    if any(keyword in query.lower() for keyword in ["employment", "labor", "workforce", "qatarization"]):
        available_types.append("labor_market")

    # Check for economic data
    if any(keyword in query.lower() for keyword in ["gdp", "economy", "trade", "investment"]):
        available_types.append("economic_indicators")
    
    return available_types


class AgentSelector:
    """
    Intelligent agent selection based on question classification.
    
    Maps question intents and entities to relevant agent expertise areas.
    """
    
    # Agent expertise mapping
    AGENT_REGISTRY = {
        "llm_agents": {
            "MicroEconomist": {
                "type": "llm",
                "requires": None,
                "description": "Project-level cost-benefit analysis, market efficiency, ROI",
                "focus": "Firm-level economic rationality",
                "module": "qnwis.agents.micro_economist",
                "class": "MicroEconomist",
            },
            "MacroEconomist": {
                "type": "llm",
                "requires": None,
                "description": "National-level strategy, aggregate impacts, strategic security",
                "focus": "National welfare and systemic resilience",
                "module": "qnwis.agents.macro_economist",
                "class": "MacroEconomist",
            },
            "SkillsAgent": {
                "type": "llm",
                "requires": None,
                "description": "Human capital, workforce development, skills gaps",
                "focus": "Labor market and capability building",
                "module": "qnwis.agents.skills_agent",
                "class": "SkillsAgent",
            },
            "Nationalization": {
                "type": "llm",
                "requires": None,
                "description": "State ownership, sovereignty, public vs private sector",
                "focus": "Political economy and governance",
                "module": "qnwis.agents.nationalization",
                "class": "NationalizationAgent",
            },
            "PatternDetective": {
                "type": "llm",
                "requires": None,
                "description": "Cross-domain patterns, historical precedents, system dynamics",
                "focus": "Meta-analysis and pattern recognition",
                "module": "qnwis.agents.pattern_detective_llm",
                "class": "PatternDetectiveLLM",
            },
        },
        "deterministic_agents": {
            "TimeMachine": {
                "type": "deterministic",
                "requires": ["time_series_employment", "historical_trends"],
                "description": "Historical labor market trend analysis",
                "queries": ["timeseries_employment_all_12m"],
                "module": "qnwis.agents.time_machine",
                "class": "TimeMachineAgent",
            },
            "Predictor": {
                "type": "deterministic",
                "requires": ["time_series_employment"],
                "description": "Workforce forecasting and retention prediction",
                "queries": ["ts_retention_by_sector"],
                "module": "qnwis.agents.predictor",
                "class": "PredictorAgent",
            },
            "Scenario": {
                "type": "deterministic",
                "requires": ["sector_metrics", "labor_market"],
                "description": "Labor market scenario modeling",
                "queries": ["syn_sector_metrics"],
                "module": "qnwis.agents.scenario_agent",
                "class": "ScenarioAgent",
            },
            "PatternDetectiveAgent": {
                "type": "deterministic",
                "requires": ["sector_metrics", "labor_market"],
                "description": "Statistical pattern detection in labor data",
                "queries": ["syn_attrition_by_sector_latest"],
                "module": "qnwis.agents.pattern_detective",
                "class": "PatternDetectiveAgent",
            },
            "PatternMiner": {
                "type": "deterministic",
                "requires": ["time_series", "sector_metrics"],
                "description": "Automated pattern mining algorithms",
                "queries": ["timeseries_retention_all_12m"],
                "module": "qnwis.agents.pattern_miner",
                "class": "PatternMinerAgent",
            },
            "AlertCenter": {
                "type": "deterministic",
                "requires": ["alert_rules", "sector_metrics"],
                "description": "Threshold monitoring and alert evaluation",
                "queries": [],
                "module": "qnwis.agents.alert_center",
                "class": "AlertCenterAgent",
            },
        },
    }
    
    # Minimum agents to always run (baseline)
    MIN_AGENTS = 4  # Never compromise on quality
    
    # Maximum agents to run - USE ALL AVAILABLE FOR LEGENDARY DEPTH
    MAX_AGENTS = 11  # All 4 LLM + All 7 deterministic agents
    
    # Always-include agents for any question
    BASELINE_AGENTS: Set[str] = set()  # Can be configured
    
    @classmethod
    def select_agents(
        cls,
        classification: Dict[str, Any],
        min_agents: int = MIN_AGENTS,
        max_agents: int = MAX_AGENTS,
        extracted_facts: List[Dict[str, Any]] | None = None,
    ) -> List[str]:
        """
        Select relevant agents based on question classification.
        
        Args:
            classification: Question classification result
                Expected keys: intent, entities, complexity
            min_agents: Minimum number of agents to select
            max_agents: Maximum number of agents to select
            extracted_facts: Optional list of extracted fact dictionaries
            
        Returns:
            List of agent names to invoke
        """
        selected: Set[str] = set()
        scores: Dict[str, float] = {}
        
        # Extract classification data
        intent = classification.get("intent", "").lower()
        entities = classification.get("entities") or {}  # Handle None
        complexity = classification.get("complexity", "medium")
        question_text = classification.get("question", "").lower()
        fact_payload = extracted_facts or classification.get("extracted_facts")
        
        # Score each agent
        for agent_name, expertise in cls.AGENT_EXPERTISE.items():
            score = 0.0
            
            # 1. Intent matching (strongest signal)
            if intent in expertise["intents"]:
                score += 1.0
                logger.debug(f"{agent_name}: +1.0 for intent match '{intent}'")
            
            # 2. Entity matching
            entity_matches = 0
            for entity_key, entity_value in entities.items():
                if entity_value:  # If entity is present
                    for expert_entity in expertise["entities"]:
                        if expert_entity in entity_key.lower():
                            entity_matches += 1
            
            if entity_matches > 0:
                entity_score = min(0.5, entity_matches * 0.2)
                score += entity_score
                logger.debug(f"{agent_name}: +{entity_score:.1f} for {entity_matches} entity matches")
            
            # 3. Keyword matching in question (weak signal)
            keyword_matches = sum(
                1 for keyword in expertise["entities"]
                if keyword in question_text
            )
            if keyword_matches > 0:
                keyword_score = min(0.3, keyword_matches * 0.1)
                score += keyword_score
                logger.debug(f"{agent_name}: +{keyword_score:.1f} for {keyword_matches} keyword matches")
            
            # 4. Always-include flag
            if expertise["always_include"]:
                score += 0.5
                logger.debug(f"{agent_name}: +0.5 for always_include")
            
            scores[agent_name] = score
        
        # Sort agents by score
        sorted_agents = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        # Select top agents with non-zero scores
        for agent_name, score in sorted_agents:
            if score > 0.0:
                selected.add(agent_name)
        
        # Add baseline agents
        selected.update(cls.BASELINE_AGENTS)
        
        # Ensure minimum agents
        if len(selected) < min_agents:
            # Add top-scored agents even if score is 0
            for agent_name, score in sorted_agents:
                if agent_name not in selected:
                    selected.add(agent_name)
                    if len(selected) >= min_agents:
                        break
        
        # Cap at maximum agents
        if len(selected) > max_agents:
            # Keep top-scored agents
            top_agents = [agent for agent, score in sorted_agents[:max_agents]]
            selected = set(top_agents)
        
        # Special handling for high complexity
        if complexity == "high" and len(selected) < max_agents:
            # Add NationalStrategy for complex questions
            if "NationalStrategy" not in selected and len(selected) < max_agents:
                selected.add("NationalStrategy")
                logger.debug("Added NationalStrategy for high complexity")
        
        # FILTER: Deterministic Agent Graceful Degradation
        available_data = classify_data_availability(question_text, fact_payload)
        
        deterministic_requirements = {
            "TimeMachine": ["time_series_employment", "historical_trends"],
            "Predictor": ["time_series_employment"],
            "Scenario": ["sector_metrics", "labor_market"],
            "PatternDetectiveAgent": ["sector_metrics", "labor_market"],
            "PatternMiner": ["time_series_employment", "sector_metrics"],
            "NationalStrategy": ["labor_market", "economic_indicators"],
            "AlertCenter": ["sector_metrics", "labor_market"]
        }
        
        filtered_selected = []
        for agent in selected:
            # Check if agent is deterministic and needs specific data
            if agent in deterministic_requirements:
                reqs = deterministic_requirements[agent]
                if not any(r in available_data for r in reqs):
                    logger.info(f"Skipping {agent}: requires {reqs}, have {available_data}")
                    continue
            filtered_selected.append(agent)
            
        # Ensure we didn't filter everything out (keep at least LLM agents)
        if not filtered_selected and selected:
            # Restore LLM agents
            llm_agents = ["LabourEconomistLLM", "NationalizationLLM", "SkillsAgentLLM", "PatternDetectiveLLM", "NationalStrategyLLM"]
            for agent in selected:
                if agent in llm_agents:
                    filtered_selected.append(agent)
        
        result = filtered_selected
        
        logger.info(
            f"Agent selection: {len(result)}/{len(cls.AGENT_EXPERTISE)} agents "
            f"for intent '{intent}' (complexity: {complexity})"
        )
        logger.info(f"Selected agents: {result}")
        logger.debug(f"Agent scores: {scores}")
        
        return result
    
    @classmethod
    def explain_selection(
        cls,
        selected_agents: List[str],
        classification: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Explain why agents were selected.
        
        Args:
            selected_agents: List of selected agent names
            classification: Question classification
            
        Returns:
            Dictionary with selection explanation
        """
        intent = classification.get("intent", "unknown")
        complexity = classification.get("complexity", "medium")
        
        explanations = {}
        for agent in selected_agents:
            if agent in cls.AGENT_EXPERTISE:
                expertise = cls.AGENT_EXPERTISE[agent]
                reasons = []
                
                if intent in expertise["intents"]:
                    reasons.append(f"Matches intent '{intent}'")
                
                if expertise["always_include"]:
                    reasons.append("Always included")
                
                if not reasons:
                    reasons.append("Baseline selection")
                
                explanations[agent] = {
                    "description": expertise["description"],
                    "reasons": reasons
                }
        
        return {
            "selected_count": len(selected_agents),
            "total_available": len(cls.AGENT_EXPERTISE),
            "savings": f"{(1 - len(selected_agents)/len(cls.AGENT_EXPERTISE)) * 100:.0f}%",
            "intent": intent,
            "complexity": complexity,
            "agents": explanations
        }
    
    @classmethod
    def get_all_agents(cls) -> List[str]:
        """Get list of all available agents."""
        return list(cls.AGENT_EXPERTISE.keys())


def select_agents_for_question(
    classification: Dict[str, Any],
    min_agents: int = 2,
    max_agents: int = 4,
    extracted_facts: List[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    """
    Convenience function for agent selection.
    
    Args:
        classification: Question classification
        min_agents: Minimum agents to select
        max_agents: Maximum agents to select
        extracted_facts: Optional list of extracted facts for data availability checks
        
    Returns:
        Dictionary with selected agents and explanation
    """
    selector = AgentSelector()
    selected = selector.select_agents(
        classification,
        min_agents,
        max_agents,
        extracted_facts=extracted_facts,
    )
    explanation = selector.explain_selection(selected, classification)
    
    return {
        "selected_agents": selected,
        "explanation": explanation
    }
