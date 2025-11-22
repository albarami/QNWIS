"""
LangGraph State Schema for QNWIS Intelligence System.

Defines the shared state that flows through every LangGraph node.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict


class IntelligenceState(TypedDict, total=False):
    """
    State that flows through the entire LangGraph workflow.

    Each node reads from and writes to this state.
    """

    # Input
    query: str
    complexity: str  # "simple", "medium", "complex", "critical"

    # Data Extraction (from prefetch/cache)
    extracted_facts: List[Dict[str, Any]]
    data_sources: List[str]
    data_quality_score: float  # 0.0 to 1.0

    # Agent Outputs
    agent_reports: List[Dict[str, Any]]
    financial_analysis: Optional[str]
    market_analysis: Optional[str]
    operations_analysis: Optional[str]
    research_analysis: Optional[str]

    # Debate & Critique
    debate_synthesis: Optional[str]
    debate_results: Optional[Dict[str, Any]]  # Debate outcomes and metadata
    critique_report: Optional[str]

    # Verification
    fact_check_results: Optional[Dict[str, Any]]
    fabrication_detected: bool

    # Final Output
    final_synthesis: Optional[str]
    confidence_score: float  # 0.0 to 1.0
    reasoning_chain: List[str]

    # Metadata
    metadata: Dict[str, Any]
    nodes_executed: List[str]
    execution_time: Optional[float]
    timestamp: str

    # Warnings/Errors
    warnings: List[str]
    errors: List[str]

