"""
Typed structures shared across orchestration components.

Includes both agent report structures (Citation, AgentReport) and
coordination layer types (PrefetchSpec, AgentCallSpec, ExecutionTrace).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, List, NotRequired, Optional, TypedDict


class Citation(TypedDict):
    """Single citation reference within an agent narrative."""

    claim: str
    metric: str
    value: str
    source: str
    confidence: float
    extraction_reference: str  # e.g. "[Per extraction: '...' from ...]"


class AgentReport(TypedDict):
    """Structured agent analysis output sent downstream for verification."""

    agent_name: str
    narrative: str
    confidence: float
    citations: List[Citation]
    facts_used: List[str]
    assumptions: List[str]
    data_gaps: List[str]
    timestamp: str
    model: str
    tokens_in: int
    tokens_out: int


class PrefetchSpec(TypedDict):
    """
    Declarative specification for data prefetch.

    Attributes:
        fn: DataClient method name (e.g., "run")
        params: Parameters to pass to the method
        cache_key: Deterministic key to store/reuse QueryResult
    """

    fn: str
    params: dict[str, Any]
    cache_key: str


class AgentCallSpec(TypedDict):
    """
    Specification for agent method invocation.

    Attributes:
        intent: Registered intent identifier (e.g., "pattern.correlation")
        method: Concrete method name on agent
        params: Parameters for the method call
        alias: Optional unique alias used for dependency tracking
        depends_on: Optional list of aliases that must succeed before execution
    """

    intent: str
    method: str
    params: dict[str, Any]
    alias: NotRequired[str]
    depends_on: NotRequired[list[str]]


class ExecutionTrace(TypedDict):
    """
    Trace information for a single agent execution.

    Attributes:
        intent: Intent that was executed
        agent: Agent class name
        method: Method name
        elapsed_ms: Execution time in milliseconds
        attempt: Which attempt produced this trace (1 for first pass)
        success: Whether execution succeeded
        warnings: Any warnings generated
        error: Optional error message if execution failed
    """

    intent: str
    agent: str
    method: str
    elapsed_ms: float
    attempt: int
    success: bool
    warnings: list[str]
    error: NotRequired[str]
