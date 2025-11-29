"""
Debate configuration settings.

UPDATED: Aligned with legendary_debate_orchestrator.py for ministerial-grade analysis.
These values determine the depth of multi-agent debate for Qatar policy questions.
"""

DEBATE_CONFIGS = {
    "simple": {
        "max_turns": 40,       # Thorough even for simple questions
        "agents": 5,           # 5 LLM agents
        "convergence_check_interval": 10,
        "phases": {
            "opening_statements": 10,
            "challenge_defense": 15,
            "edge_cases": 8,
            "risk_analysis": 5,
            "consensus_building": 2
        }
    },
    "medium": {
        "max_turns": 80,
        "agents": 5,
        "convergence_check_interval": 15,
        "phases": {
            "opening_statements": 12,
            "challenge_defense": 35,
            "edge_cases": 15,
            "risk_analysis": 12,
            "consensus_building": 6
        }
    },
    "standard": {              # Same as medium - added for compatibility
        "max_turns": 80,
        "agents": 5,
        "convergence_check_interval": 15,
        "phases": {
            "opening_statements": 12,
            "challenge_defense": 35,
            "edge_cases": 15,
            "risk_analysis": 12,
            "consensus_building": 6
        }
    },
    "complex": {
        "max_turns": 150,      # LEGENDARY depth for strategic decisions
        "agents": 8,
        "convergence_check_interval": 25,
        "phases": {
            "opening_statements": 15,
            "challenge_defense": 60,
            "edge_cases": 25,
            "risk_analysis": 25,
            "consensus_building": 25
        }
    },
    "critical": {
        "max_turns": 150,      # Same as complex for maximum depth
        "agents": 10,
        "convergence_check_interval": 25,
        "phases": {
            "opening_statements": 15,
            "challenge_defense": 60,
            "edge_cases": 25,
            "risk_analysis": 25,
            "consensus_building": 25
        }
    }
}

def get_debate_config(complexity: str) -> dict:
    """Get debate configuration based on query complexity."""
    return DEBATE_CONFIGS.get(complexity, DEBATE_CONFIGS["standard"])

