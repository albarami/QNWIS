"""
Protocol types for orchestration coordination layer.

Defines lightweight TypedDict specifications for prefetch declarations
and agent call specifications used by the Coordinator.
"""

from __future__ import annotations

from typing import Any, Dict, List, NotRequired, TypedDict


class PrefetchSpec(TypedDict):
    """
    Declarative specification for data prefetch.

    Attributes:
        fn: DataClient method name (e.g., "run")
        params: Parameters to pass to the method
        cache_key: Deterministic key to store/reuse QueryResult
    """

    fn: str
    params: Dict[str, Any]
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
    params: Dict[str, Any]
    alias: NotRequired[str]
    depends_on: NotRequired[List[str]]


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
    warnings: List[str]
    error: NotRequired[str]
