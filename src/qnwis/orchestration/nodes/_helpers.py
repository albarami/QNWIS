"""Shared helpers for LangGraph nodes."""

from __future__ import annotations

import os
from typing import Any, Awaitable, Callable, Dict, List

from ...llm.client import LLMClient
from ..state import IntelligenceState


def create_llm_client(state: IntelligenceState) -> LLMClient:
    """
    Create an LLM client with configured provider (Azure, Anthropic, or OpenAI).
    
    CRITICAL: Stub mode is DELETED. System requires real LLM.
    Reads provider from QNWIS_LLM_PROVIDER or QNWIS_LANGGRAPH_LLM_PROVIDER.
    
    Raises:
        ValueError: If required API key is not set for the chosen provider
    """

    metadata = state.setdefault("metadata", {})
    provider = (
        metadata.get("llm_provider")
        or os.getenv("QNWIS_LANGGRAPH_LLM_PROVIDER")
        or os.getenv("QNWIS_LLM_PROVIDER")
        or "azure"  # Default to Azure (ministry deployment)
    )
    
    # Validate API key exists
    if provider == "azure":
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "AZURE_OPENAI_API_KEY is required. "
                "Set in .env file: AZURE_OPENAI_API_KEY=your-key"
            )
    elif provider == "anthropic":
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY is required. "
                "Set in .env file: ANTHROPIC_API_KEY=sk-ant-..."
            )
    elif provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY is required. "
                "Set in .env file: OPENAI_API_KEY=sk-..."
            )
    else:
        raise ValueError(
            f"Unsupported provider: {provider}. "
            "Use 'azure', 'anthropic', or 'openai'. Stub mode is deleted."
        )
    
    model = metadata.get("llm_model") or os.getenv("QNWIS_LANGGRAPH_LLM_MODEL")
    if not model:
        if provider == "azure":
            model = os.getenv("QNWIS_AZURE_MODEL", "gpt-4o")
        elif provider == "anthropic":
            model = "claude-sonnet-4-20250514"  # Sonnet 4.5
        elif provider == "openai":
            model = "gpt-4-turbo"

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
    
    Emits proper agent events for frontend tracking:
    - agent:{name} running - when analysis starts
    - agent:{name} complete - when analysis finishes with report
    - agent:{name} error - if analysis fails
    
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
    from datetime import datetime, timezone
    import logging
    
    logger = logging.getLogger(__name__)

    reasoning_chain = state.setdefault("reasoning_chain", [])
    warnings = state.setdefault("warnings", [])
    errors = state.setdefault("errors", [])
    
    # Get event emitter
    emit_fn = state.get("emit_event_fn")
    
    # Extract display name from agent_key (e.g., "financial_economist" -> "financial")
    display_name = target_field.replace("_analysis", "") if "_analysis" in target_field else agent_key
    
    start_time = datetime.now(timezone.utc)
    
    # Emit running event
    if emit_fn:
        try:
            await emit_fn(f"agent:{display_name}", "running", {"agent": agent_key})
        except Exception as e:
            logger.warning(f"Failed to emit agent running event: {e}")

    try:
        llm_client = create_llm_client(state)
        extracted_facts = state.get("extracted_facts", [])
        
        # Validate input data
        if not extracted_facts:
            warnings.append(f"{agent_key}: No extracted facts available for analysis.")
        
        report = await analyzer(state["query"], extracted_facts, llm_client)
        
        # Calculate latency
        latency_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        
        # Store narrative and full report
        state[target_field] = report.get("narrative")
        record_agent_report(state, agent_key, report)
        reasoning_chain.append(success_message)
        
        # Emit complete event with report
        if emit_fn:
            try:
                await emit_fn(
                    f"agent:{display_name}",
                    "complete",
                    {
                        "agent": agent_key,
                        "report": report,
                        "narrative": report.get("narrative", "")[:500],  # Preview
                    },
                    latency_ms
                )
            except Exception as e:
                logger.warning(f"Failed to emit agent complete event: {e}")
        
        logger.info(f"Agent {agent_key} completed in {latency_ms:.0f}ms")
        
    except TimeoutError as exc:
        error_msg = f"{agent_key} timed out after extended analysis period."
        warnings.append(error_msg)
        errors.append(str(exc))
        state[target_field] = None
        
        # Emit error event
        if emit_fn:
            try:
                await emit_fn(f"agent:{display_name}", "error", {"error": error_msg})
            except Exception:
                pass
        
    except Exception as exc:  # pragma: no cover - defensive
        error_msg = f"{agent_key} agent failed: {type(exc).__name__}"
        warnings.append(error_msg)
        errors.append(str(exc))
        state[target_field] = None
        
        # Emit error event
        if emit_fn:
            try:
                await emit_fn(f"agent:{display_name}", "error", {"error": error_msg})
            except Exception:
                pass

