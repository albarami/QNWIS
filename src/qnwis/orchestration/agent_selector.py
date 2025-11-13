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


class AgentSelector:
    """
    Intelligent agent selection based on question classification.
    
    Maps question intents and entities to relevant agent expertise areas.
    """
    
    # Agent expertise mapping
    AGENT_EXPERTISE = {
        "LabourEconomist": {
            "intents": ["unemployment", "employment", "trends", "economy"],
            "entities": ["unemployment", "employment", "jobs", "economy"],
            "always_include": False,
            "description": "Employment trends & economic indicators"
        },
        "Nationalization": {
            "intents": ["qatarization", "gcc_comparison", "nationalization", "vision_2030"],
            "entities": ["qatari", "gcc", "nationalization", "vision", "2030"],
            "always_include": False,
            "description": "Qatarization & GCC benchmarking"
        },
        "SkillsAgent": {
            "intents": ["skills", "education", "training", "workforce_development"],
            "entities": ["skills", "education", "training", "qualification"],
            "always_include": False,
            "description": "Skills gaps & workforce development"
        },
        "PatternDetective": {
            "intents": [],  # Data quality agent - selective
            "entities": ["anomaly", "pattern", "trend", "quality"],
            "always_include": False,
            "description": "Data quality & pattern detection"
        },
        "NationalStrategy": {
            "intents": ["strategy", "policy", "vision_2030", "planning"],
            "entities": ["strategy", "policy", "vision", "2030", "planning"],
            "always_include": False,
            "description": "Strategic planning & Vision 2030 alignment"
        }
    }
    
    # Minimum agents to always run (baseline)
    MIN_AGENTS = 2
    
    # Maximum agents to run
    MAX_AGENTS = 4
    
    # Always-include agents for any question
    BASELINE_AGENTS: Set[str] = set()  # Can be configured
    
    @classmethod
    def select_agents(
        cls,
        classification: Dict[str, Any],
        min_agents: int = MIN_AGENTS,
        max_agents: int = MAX_AGENTS
    ) -> List[str]:
        """
        Select relevant agents based on question classification.
        
        Args:
            classification: Question classification result
                Expected keys: intent, entities, complexity
            min_agents: Minimum number of agents to select
            max_agents: Maximum number of agents to select
            
        Returns:
            List of agent names to invoke
        """
        selected: Set[str] = set()
        scores: Dict[str, float] = {}
        
        # Extract classification data
        intent = classification.get("intent", "").lower()
        entities = classification.get("entities", {})
        complexity = classification.get("complexity", "medium")
        question_text = classification.get("question", "").lower()
        
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
        
        result = list(selected)
        
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
    max_agents: int = 4
) -> Dict[str, Any]:
    """
    Convenience function for agent selection.
    
    Args:
        classification: Question classification
        min_agents: Minimum agents to select
        max_agents: Maximum agents to select
        
    Returns:
        Dictionary with selected agents and explanation
    """
    selector = AgentSelector()
    selected = selector.select_agents(classification, min_agents, max_agents)
    explanation = selector.explain_selection(selected, classification)
    
    return {
        "selected_agents": selected,
        "explanation": explanation
    }
