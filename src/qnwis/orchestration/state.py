"""
LangGraph State Schema for QNWIS Intelligence System.

Defines the shared state that flows through every LangGraph node.
Uses Annotated types with reducers to prevent concurrent update errors.
"""

from __future__ import annotations

import operator
from typing import Annotated, Any, Callable, Dict, List, Optional, TypedDict


def keep_first(existing: Any, new: Any) -> Any:
    """Reducer that keeps the first (original) value, ignoring updates."""
    if existing is not None:
        return existing
    return new


def merge_lists(existing: List, new: List) -> List:
    """Reducer that extends existing list with new items."""
    if existing is None:
        return new if new else []
    if new is None:
        return existing
    # Avoid duplicates for simple types
    result = list(existing)
    for item in new:
        if item not in result:
            result.append(item)
    return result


def take_last(existing: Any, new: Any) -> Any:
    """Reducer that always takes the latest value."""
    return new if new is not None else existing


class IntelligenceState(TypedDict, total=False):
    """
    State that flows through the entire LangGraph workflow.

    Each node reads from and writes to this state.
    Uses Annotated types with reducers to handle concurrent updates properly.
    """

    # Input - keep_first ensures query is set once and never overwritten
    query: Annotated[str, keep_first]
    complexity: Annotated[str, take_last]  # Can be updated by classifier

    # Data Extraction (from prefetch/cache)
    extracted_facts: Annotated[List[Dict[str, Any]], merge_lists]
    data_sources: Annotated[List[str], merge_lists]
    data_quality_score: Annotated[float, take_last]  # 0.0 to 1.0

    # Agent Outputs - merge reports from multiple agents
    agent_reports: Annotated[List[Dict[str, Any]], merge_lists]
    financial_analysis: Annotated[Optional[str], take_last]
    market_analysis: Annotated[Optional[str], take_last]
    operations_analysis: Annotated[Optional[str], take_last]
    research_analysis: Annotated[Optional[str], take_last]

    # Debate & Critique
    debate_synthesis: Annotated[Optional[str], take_last]
    debate_results: Annotated[Optional[Dict[str, Any]], take_last]
    critique_report: Annotated[Optional[str], take_last]

    # Verification
    fact_check_results: Annotated[Optional[Dict[str, Any]], take_last]
    fabrication_detected: Annotated[bool, take_last]

    # Final Output
    final_synthesis: Annotated[Optional[str], take_last]
    confidence_score: Annotated[float, take_last]  # 0.0 to 1.0
    reasoning_chain: Annotated[List[str], merge_lists]

    # Metadata
    metadata: Annotated[Dict[str, Any], take_last]
    nodes_executed: Annotated[List[str], merge_lists]
    execution_time: Annotated[Optional[float], take_last]
    timestamp: Annotated[str, take_last]

    # Warnings/Errors - accumulate all warnings and errors
    warnings: Annotated[List[str], merge_lists]
    errors: Annotated[List[str], merge_lists]

    # Event Callback (for real-time streaming of sub-events like debate turns)
    emit_event_fn: Annotated[Optional[Callable], keep_first]

    # Parallel Scenario Analysis (Multi-GPU)
    enable_parallel_scenarios: Annotated[bool, keep_first]
    scenarios: Annotated[Optional[List[Dict[str, Any]]], take_last]
    scenario_results: Annotated[Optional[List[Dict[str, Any]]], take_last]
    scenario_name: Annotated[Optional[str], take_last]
    scenario_metadata: Annotated[Optional[Dict[str, Any]], take_last]
    scenario_assumptions: Annotated[Optional[Dict[str, Any]], take_last]

