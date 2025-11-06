"""
Coordination policies for multi-agent execution.

Defines policies controlling parallelism, timeouts, and execution modes
based on query complexity and system load.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class CoordinationPolicy:
    """
    Policy controlling coordination behavior.

    Attributes:
        max_parallel: Maximum parallel agent executions (normal mode)
        crisis_parallel: Maximum parallel executions in crisis mode
        per_agent_timeout_ms: Timeout per agent call in milliseconds
        total_timeout_ms: Total workflow timeout in milliseconds
        strict_merge: If True, fail on missing mandatory sections
        retry_transient: Number of retries for transient failures
    """

    max_parallel: int = 3
    crisis_parallel: int = 5
    per_agent_timeout_ms: int = 30000
    total_timeout_ms: int = 60000
    strict_merge: bool = False
    retry_transient: int = 1

    def __post_init__(self) -> None:
        """Validate policy constraints."""
        if self.max_parallel < 1:
            raise ValueError("max_parallel must be at least 1")
        if self.crisis_parallel < self.max_parallel:
            raise ValueError("crisis_parallel must be >= max_parallel")
        if self.per_agent_timeout_ms < 1000:
            raise ValueError("per_agent_timeout_ms must be at least 1000ms")
        if self.total_timeout_ms < self.per_agent_timeout_ms:
            raise ValueError("total_timeout_ms must be >= per_agent_timeout_ms")
        if self.retry_transient < 0:
            raise ValueError("retry_transient must be non-negative")


def get_policy_for_complexity(
    complexity: Literal["simple", "medium", "complex", "crisis"]
) -> CoordinationPolicy:
    """
    Get coordination policy based on query complexity.

    Args:
        complexity: Query complexity level

    Returns:
        Appropriate CoordinationPolicy instance
    """
    if complexity == "crisis":
        return CoordinationPolicy(
            max_parallel=5,
            crisis_parallel=5,
            per_agent_timeout_ms=20000,
            total_timeout_ms=45000,
            strict_merge=False,
            retry_transient=0,
        )
    if complexity == "complex":
        return CoordinationPolicy(
            max_parallel=3,
            crisis_parallel=5,
            per_agent_timeout_ms=30000,
            total_timeout_ms=60000,
            strict_merge=False,
            retry_transient=1,
        )
    if complexity == "medium":
        return CoordinationPolicy(
            max_parallel=2,
            crisis_parallel=4,
            per_agent_timeout_ms=30000,
            total_timeout_ms=50000,
            strict_merge=False,
            retry_transient=1,
        )
    # simple
    return CoordinationPolicy(
        max_parallel=1,
        crisis_parallel=3,
        per_agent_timeout_ms=25000,
        total_timeout_ms=40000,
        strict_merge=True,
        retry_transient=1,
    )


DEFAULT_POLICY = CoordinationPolicy()
