"""
Feature flags for gradual migration to new LangGraph architecture.

Allows toggling between the monolithic graph_llm.py and modular workflow.py
implementations during the transition period.
"""

from __future__ import annotations

import os
from typing import Literal

WorkflowImplementation = Literal["legacy", "langgraph"]


def get_workflow_implementation() -> WorkflowImplementation:
    """
    Determine which workflow implementation to use.
    
    Returns:
        "legacy": Use graph_llm.py (monolithic, 2016 lines)
        "langgraph": Use workflow.py (modular, 10 nodes with GPU fact verification)
    
    Configuration:
        Set QNWIS_WORKFLOW_IMPL environment variable to:
        - "legacy" or "graph_llm" for old implementation
        - "langgraph" or "modular" for new implementation (DEFAULT)
        
    Default: "langgraph" (production-ready as of 2025-11-24)
    """
    
    # Default to langgraph (modular workflow with GPU fact verification)
    env_value = os.getenv("QNWIS_WORKFLOW_IMPL", "langgraph").lower()
    
    if env_value in ("langgraph", "modular", "new"):
        return "langgraph"
    
    # Only use legacy if explicitly requested
    return "legacy"


def use_legacy_workflow() -> bool:
    """Return True if legacy graph_llm.py should be used."""
    return get_workflow_implementation() == "legacy"


def use_langgraph_workflow() -> bool:
    """Return True if new modular workflow.py should be used."""
    return get_workflow_implementation() == "langgraph"


# Migration status tracking
MIGRATION_STATUS = {
    "current_default": "langgraph",  # Changed from legacy on 2025-11-24
    "target_default": "langgraph",
    "migration_complete_date": "2025-11-24",  # LangGraph now default
    "deprecation_date": None,  # Legacy still available via env var
}

