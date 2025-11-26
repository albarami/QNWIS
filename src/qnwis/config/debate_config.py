"""
Debate configuration settings.
"""

DEBATE_CONFIGS = {
    "simple": {
        "max_turns": 10,
        "agents": 3,  # Only most relevant agents
        "convergence_check_interval": 3
    },
    "medium": {
        "max_turns": 15,
        "agents": 5,
        "convergence_check_interval": 5
    },
    "complex": {
        "max_turns": 25,
        "agents": 8,
        "convergence_check_interval": 5
    },
    "critical": {
        "max_turns": 30,
        "agents": 10,  # All hands on deck
        "convergence_check_interval": 7
    }
}

def get_debate_config(complexity: str) -> dict:
    """Get debate configuration based on query complexity."""
    return DEBATE_CONFIGS.get(complexity, DEBATE_CONFIGS["medium"])

