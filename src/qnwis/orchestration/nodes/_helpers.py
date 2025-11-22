"""Shared helpers for LangGraph nodes."""

from __future__ import annotations

import os
from typing import Any, Awaitable, Callable, Dict, List

from ...llm.client import LLMClient
from ..state import IntelligenceState


def create_llm_client(state: IntelligenceState) -> LLMClient:
    """
    Create an LLM client based on state metadata or environment overrides.

    Defaults to the deterministic stub client to avoid accidental API usage
    during local development unless a provider is explicitly configured.
    """

    metadata = state.setdefault("metadata", {})
    provider = (
        metadata.get("llm_provider")
        or os.getenv("QNWIS_LANGGRAPH_LLM_PROVIDER")
        or "stub"
    )
    model = metadata.get("llm_model") or os.getenv("QNWIS_LANGGRAPH_LLM_MODEL")

    return LLMClient(provider=provider, model=model)


def record_agent_report(
    state: IntelligenceState, agent_name: str, report: Dict[str, Any]
) -> None:
    """Append the agent report to the shared state."""

    agent_reports = state.setdefault("agent_reports", [])
    agent_reports.append(
        {
            "agent": agent_name,
            "report": report,
        }
    )


AnalysisFn = Callable[
    [str, List[Dict[str, Any]], LLMClient],
    Awaitable[Dict[str, Any]],
]


async def execute_agent_analysis(
    state: IntelligenceState,
    *,
    agent_key: str,
    target_field: str,
    analyzer: AnalysisFn,
    success_message: str,
) -> None:
    """
    Run an agent analyzer, record the narrative, and append to state.
    
    Includes robust error handling:
    - LLM timeout errors are logged but don't crash the workflow
    - Missing data is handled gracefully
    - Partial results are preserved even on failure
    
    Args:
        state: Current workflow state
        agent_key: Agent identifier (e.g., "financial_economist")
        target_field: State field to store narrative (e.g., "financial_analysis")
        analyzer: Async analysis function
        success_message: Message to add to reasoning chain on success
    """

    reasoning_chain = state.setdefault("reasoning_chain", [])
    warnings = state.setdefault("warnings", [])
    errors = state.setdefault("errors", [])

    try:
        llm_client = create_llm_client(state)
        extracted_facts = state.get("extracted_facts", [])
        
        # Validate input data
        if not extracted_facts:
            warnings.append(f"{agent_key}: No extracted facts available for analysis.")
        
        report = await analyzer(state["query"], extracted_facts, llm_client)
        
        # Store narrative and full report
        state[target_field] = report.get("narrative")
        record_agent_report(state, agent_key, report)
        reasoning_chain.append(success_message)
        
    except TimeoutError as exc:
        error_msg = f"{agent_key} timed out after extended analysis period."
        warnings.append(error_msg)
        errors.append(str(exc))
        state[target_field] = None
        
    except Exception as exc:  # pragma: no cover - defensive
        error_msg = f"{agent_key} agent failed: {type(exc).__name__}"
        warnings.append(error_msg)
        errors.append(str(exc))
        state[target_field] = None

